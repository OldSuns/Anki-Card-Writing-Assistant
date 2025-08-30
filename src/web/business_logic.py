"""业务逻辑处理模块"""

import asyncio
import concurrent.futures
import logging
from typing import List, Dict, Any
from pathlib import Path

from src.core.card_generator import GenerationConfig, CardData
from src.web.utils import ResponseUtils


class CardProcessor:
    """卡片处理器"""
    
    @staticmethod
    def convert_to_card_objects(cards_data: List[Dict], deck_name: str = None) -> List[CardData]:
        """将卡片数据转换为CardData对象"""
        cards = []
        default_deck = deck_name or '默认牌组'
        
        for card_dict in cards_data:
            card = CardData(
                front=card_dict.get('front', ''),
                back=card_dict.get('back', ''),
                deck=card_dict.get('deck', default_deck),
                tags=card_dict.get('tags', []),
                model=card_dict.get('model', 'Basic'),
                fields=card_dict.get('fields', {})
            )
            cards.append(card)
        return cards

    @staticmethod
    def serialize_cards(cards: List[CardData]) -> List[Dict]:
        """将CardData对象序列化为字典"""
        return [c.to_dict() if hasattr(c, 'to_dict') else c for c in cards]


class ConfigProcessor:
    """配置处理器"""
    
    @staticmethod
    def get_generation_config(data: dict, assistant) -> GenerationConfig:
        """获取生成配置"""
        return GenerationConfig(
            template_name=data.get('template', 'Quizify'),
            prompt_type=data.get('prompt_type', 'cloze'),
            card_count=data.get('card_count', assistant.config["generation"]["default_card_count"]),
            custom_deck_name=data.get('deck_name'),
            difficulty=data.get('difficulty', assistant.config["generation"]["default_difficulty"])
        )

    @staticmethod
    def ensure_json_in_formats(export_formats: list) -> list:
        """确保导出格式中包含JSON"""
        if 'json' not in export_formats:
            export_formats.insert(0, 'json')
        return export_formats

    @staticmethod
    def update_llm_settings(assistant, llm_settings: dict):
        """更新LLM设置"""
        llm_config = assistant.config.setdefault('llm', {})

        for key, value in llm_settings.items():
            if key in ['temperature', 'max_tokens', 'timeout']:
                llm_config[key] = type(value)(value) if value else value
            else:
                llm_config[key] = value

        assistant.update_llm_config(llm_settings)


class AsyncTaskRunner:
    """异步任务运行器"""
    
    def __init__(self, logger):
        self.logger = logger

    def run_async_task(self, coro):
        """运行异步任务的辅助方法"""
        with concurrent.futures.ThreadPoolExecutor(max_workers=1) as executor:
            future = executor.submit(self._run_coro_in_thread, coro)
            return future.result()

    def _run_coro_in_thread(self, coro):
        """在线程中运行协程"""
        try:
            loop = asyncio.new_event_loop()
            asyncio.set_event_loop(loop)
            try:
                return loop.run_until_complete(coro)
            finally:
                loop.close()
        except (RuntimeError, OSError, asyncio.TimeoutError) as e:
            self.logger.error("在线程中运行协程失败: %s", e)
            raise


class ErrorAnalyzer:
    """错误分析器"""
    
    @staticmethod
    def is_cloudflare_error(error_text: str) -> bool:
        """检查是否为Cloudflare错误"""
        cf_markers = ['cf-error-details', 'Cloudflare Ray ID', '/cdn-cgi/',
                      'Attention Required! | Cloudflare']
        return any(marker in error_text for marker in cf_markers)

    @staticmethod
    def is_html_response(error_text: str) -> bool:
        """检查是否为HTML响应"""
        return ('<!DOCTYPE html>' in error_text) or ('<html' in error_text.lower())

    @classmethod
    def analyze_llm_error(cls, error: Exception, base_url: str) -> str:
        """分析LLM错误并返回友好的错误信息"""
        err_text = str(error)
        
        if cls.is_cloudflare_error(err_text):
            return (
                f'请求可能被Cloudflare防护拦截（{base_url}）。'
                '请在"AI设置"中将 API 基础URL(base_url) 换为可直连、无浏览器质询的后端域名，'
                '例如官方 OpenAI: https://api.openai.com/v1，'
                '或你的服务商提供的后端专用域名/加速地址。'
            )
        elif cls.is_html_response(err_text):
            return (
                f'目标返回HTML页面（{base_url}）。可能是网关/反向代理错误或需要浏览器验证。'
                '请检查 base_url 是否正确指向后端API地址，并确认网络可直连；'
                '如使用第三方服务商，请使用其后端API域名。'
            )
        else:
            return err_text


class BusinessLogicHandler:
    """业务逻辑处理器 - 整合所有业务逻辑组件"""
    
    def __init__(self, assistant, logger=None):
        self.assistant = assistant
        self.logger = logger or logging.getLogger(__name__)
        
        # 初始化各个处理器
        self.card_processor = CardProcessor()
        self.config_processor = ConfigProcessor()
        self.async_runner = AsyncTaskRunner(self.logger)
        self.error_analyzer = ErrorAnalyzer()

    def process_card_generation(self, content: str, data: dict) -> Dict[str, Any]:
        """处理卡片生成的完整流程"""
        # 获取生成配置
        config = self.config_processor.get_generation_config(data, self.assistant)
        
        # 异步生成卡片
        cards = self.async_runner.run_async_task(
            self.assistant.generate_cards(content, config)
        )

        # 处理导出格式
        export_formats = data.get(
            'export_formats', self.assistant.config["export"]["default_formats"]
        )
        export_formats = self.config_processor.ensure_json_in_formats(export_formats)
        
        # 导出卡片
        export_paths = self.assistant.export_cards(
            cards, export_formats,
            original_content=content,
            generation_config=self._build_generation_config_dict(config)
        )

        # 生成摘要和序列化卡片
        summary = self.assistant.get_export_summary(cards)
        serializable_cards = self.card_processor.serialize_cards(cards)

        return {
            'cards': serializable_cards,
            'export_paths': export_paths,
            'summary': summary
        }

    def process_file_generation(self, temp_file_path: str, selected_sections: List[int], 
                              data: dict, file_processor) -> Dict[str, Any]:
        """处理从文件生成卡片的完整流程"""
        # 处理文件内容
        processed_content = file_processor.process_file(temp_file_path)

        # 选择要处理的章节
        if selected_sections:
            sections_to_process = [
                processed_content.sections[i] for i in selected_sections
                if i < len(processed_content.sections)
            ]
        else:
            sections_to_process = processed_content.sections

        if not sections_to_process:
            raise ValueError('没有可处理的内容')

        # 生成卡片
        config = self.config_processor.get_generation_config(data, self.assistant)
        combined_content = '\n\n'.join(sections_to_process)
        cards = self.async_runner.run_async_task(
            self.assistant.generate_cards(combined_content, config)
        )

        # 导出处理
        export_formats = data.get(
            'export_formats', self.assistant.config["export"]["default_formats"]
        )
        export_formats = self.config_processor.ensure_json_in_formats(export_formats)
        
        generation_config = self._build_generation_config_dict(config)
        generation_config['source_file'] = processed_content.original_file.filename
        
        export_paths = self.assistant.export_cards(
            cards, export_formats,
            original_content=combined_content,
            generation_config=generation_config
        )

        summary = self.assistant.get_export_summary(cards)
        serializable_cards = self.card_processor.serialize_cards(cards)

        return {
            'cards': serializable_cards,
            'export_paths': export_paths,
            'summary': summary,
            'processed_sections': len(sections_to_process)
        }

    def process_apkg_export(self, cards_data: List[Dict], template_name: str = None, 
                           filename: str = None) -> Dict[str, Any]:
        """处理APKG导出"""
        cards = self.card_processor.convert_to_card_objects(cards_data)

        if template_name:
            export_path = self.assistant.export_apkg_with_custom_template(
                cards, template_name, filename
            )
        else:
            export_path = self.assistant.export_apkg(cards, filename)

        return {
            'export_path': export_path,
            'filename': Path(export_path).name
        }

    def handle_llm_test_error(self, error: Exception) -> str:
        """处理LLM测试错误"""
        base_url = self.assistant.config.get('llm', {}).get('base_url', '')
        error_message = self.error_analyzer.analyze_llm_error(error, base_url)
        self.logger.error("API测试失败: %s", error_message)
        return error_message

    def _build_generation_config_dict(self, config: GenerationConfig) -> Dict[str, Any]:
        """构建生成配置字典"""
        return {
            'template_name': config.template_name,
            'prompt_type': config.prompt_type,
            'card_count': config.card_count,
            'custom_deck_name': config.custom_deck_name,
            'difficulty': config.difficulty
        }