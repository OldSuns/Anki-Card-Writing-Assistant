"""核心业务服务模块"""

import logging
from pathlib import Path
from typing import List, Dict, Any, Optional

from src.core.card_generator import GenerationConfig


class ExportService:
    """导出服务"""
    
    def __init__(self, exporter, config: Dict[str, Any]):
        self.exporter = exporter
        self.config = config
        self.logger = logging.getLogger(__name__)
    
    def export_cards(self, cards: list, formats: Optional[list] = None,
                    original_content: str = None,
                    generation_config: Dict = None) -> dict:
        """导出卡片"""
        formats = self._validate_export_formats(formats)
        
        try:
            export_paths = self.exporter.export_multiple_formats(
                cards, formats,
                original_content=original_content,
                generation_config=generation_config
            )
            self.logger.info("已导出卡片到: %s", export_paths)
            return export_paths
        except Exception as e:
            self.logger.error("导出卡片失败: %s", e)
            raise
    
    def export_apkg(self, cards: list, filename: str = None,
                   template_name: str = None) -> str:
        """导出为apkg格式"""
        return self.exporter.export_to_apkg(cards, filename, template_name)
    
    def export_apkg_with_custom_template(self, cards: list, template_name: str,
                                       filename: str = None) -> str:
        """使用自定义模板导出为apkg格式"""
        return self.exporter.export_to_apkg_with_custom_template(
            cards, template_name, filename
        )
    
    def get_export_summary(self, cards: list) -> dict:
        """获取导出摘要"""
        return self.exporter.get_export_summary(cards)
    
    def _validate_export_formats(self, formats: Optional[list]) -> list:
        """验证并规范化导出格式列表"""
        valid_formats = ['json', 'csv', 'apkg', 'txt', 'html']
        
        if formats is None or not isinstance(formats, list):
            formats = self.config["export"]["default_formats"].copy()
        else:
            formats = [
                fmt for fmt in formats
                if isinstance(fmt, str) and fmt in valid_formats
            ]
            if not formats:
                formats = self.config["export"]["default_formats"].copy()
        
        # 强制包含 json
        if 'json' not in formats:
            formats.insert(0, 'json')
        
        return formats


class PromptService:
    """提示词服务"""
    
    def __init__(self, prompt_manager, component_manager):
        self.prompt_manager = prompt_manager
        self.component_manager = component_manager
        self.logger = logging.getLogger(__name__)
    
    def list_prompts(self, category: str = None, template_name: str = None) -> list:
        """列出可用提示词（可按模板过滤）"""
        return self.prompt_manager.list_prompts(
            category=category,
            template_name=template_name
        )
    
    def list_prompt_names(self, category: str = None, template_name: str = None) -> list:
        """列出可用提示词名称（用于显示，可按模板过滤）"""
        return self.prompt_manager.list_prompt_names(
            category=category,
            template_name=template_name
        )
    
    def get_prompt_content(self, prompt_type: str, template_name: str = None) -> str:
        """获取提示词内容，优先读取用户文件，支持模板子目录优先级"""
        try:
            prompt_content = self.prompt_manager.get_prompt(
                prompt_type, template_name
            )
            return prompt_content
        except Exception as e:
            self.logger.error("获取提示词内容失败: %s", e)
            raise
    
    def save_prompt_content(self, prompt_type: str, content: str,
                          template_name: str = None) -> None:
        """保存提示词内容到用户文件；若提供模板名则保存到该模板子目录"""
        try:
            save_dir = self._get_template_prompt_dir(template_name)
            save_dir.mkdir(parents=True, exist_ok=True)
            user_prompt_file = save_dir / f"{prompt_type}_user.md"
            
            with open(user_prompt_file, 'w', encoding='utf-8') as f:
                f.write(content)
            
            # 重新加载提示词管理器
            self.component_manager.reload_prompt_manager()
            self.prompt_manager = self.component_manager.get_component('prompt_manager')
            
            self.logger.info("提示词内容已保存: %s", user_prompt_file)
        except Exception as e:
            self.logger.error("保存提示词内容失败: %s", e)
            raise
    
    def reset_prompt_content(self, prompt_type: str, template_name: str = None) -> str:
        """重置提示词内容，从原始文件恢复；优先模板目录"""
        try:
            read_dir = self._get_template_prompt_dir(template_name)
            
            # 读取原始文件
            original_prompt_file = read_dir / f"{prompt_type}.md"
            if not original_prompt_file.exists():
                raise FileNotFoundError(
                    f"原始提示词文件不存在: {original_prompt_file}"
                )
            
            with open(original_prompt_file, 'r', encoding='utf-8') as f:
                original_content = f.read()
            
            # 将原始内容写入目标用户文件
            user_prompt_file = read_dir / f"{prompt_type}_user.md"
            with open(user_prompt_file, 'w', encoding='utf-8') as f:
                f.write(original_content)
            
            # 重新加载提示词管理器
            self.component_manager.reload_prompt_manager()
            self.prompt_manager = self.component_manager.get_component('prompt_manager')
            
            self.logger.info("提示词内容已重置为原始版本: %s", user_prompt_file)
            return original_content
        except Exception as e:
            self.logger.error("重置提示词内容失败: %s", e)
            raise
    
    def _get_template_prompt_dir(self, template_name: str = None) -> Path:
        """获取模板提示词目录"""
        base_dir = Path("src/prompts")
        if template_name:
            folder = self.prompt_manager.template_dir_map.get(template_name)
            if folder:
                return base_dir / folder
        return base_dir


class CardGenerationService:
    """卡片生成服务"""
    
    def __init__(self, card_generator, batch_generator, config: Dict[str, Any]):
        self.card_generator = card_generator
        self.batch_generator = batch_generator
        self.config = config
        self.logger = logging.getLogger(__name__)
    
    async def generate_cards(self, content: str, config=None) -> list:
        """生成卡片"""
        if config is None:
            config = GenerationConfig(
                template_name=self.config["generation"]["default_template"],
                prompt_type=self.config["generation"]["default_prompt_type"],
                temperature=self.config["llm"]["temperature"],
                max_tokens=self.config["llm"]["max_tokens"],
                card_count=self.config["generation"]["default_card_count"]
            )
        
        try:
            cards = await self.card_generator.generate_cards(content, config)
            self.logger.info("成功生成 %d 张卡片", len(cards))
            return cards
        except Exception as e:
            self.logger.error("生成卡片失败: %s", e)
            raise
    
    async def generate_from_file(self, file_path: str, config=None) -> list:
        """从文件生成卡片"""
        try:
            cards = await self.batch_generator.generate_from_file(file_path, config)
            self.logger.info("从文件生成 %d 张卡片", len(cards))
            return cards
        except Exception as e:
            self.logger.error("从文件生成卡片失败: %s", e)
            raise