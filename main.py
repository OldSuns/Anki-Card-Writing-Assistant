#!/usr/bin/env python3
import asyncio
import argparse
import json
import logging
import sys
from pathlib import Path
from typing import Optional, Dict

# 添加src目录到Python路径
sys.path.insert(0, str(Path(__file__).parent / "src"))

from src.core.llm_client import LLMManager, LLMConfig
from src.core.card_generator import CardGenerator, BatchCardGenerator, GenerationConfig, CardData
from src.core.unified_exporter import UnifiedExporter
from src.templates.template_manager import TemplateManager
from src.prompts.base_prompts import BasePromptManager
from src.utils.config_manager import ConfigManager
from src.utils.file_processor import FileProcessor

class AnkiCardAssistant:
    """Anki写卡助手主类"""
    
    def __init__(self, config_path: str = None):
        # 使用ConfigManager加载配置
        config_file_path = config_path or "config.json"
        self.config_manager = ConfigManager(config_file_path)
        self.config = self.config_manager.get_config()
        
        # 加载用户级设置（持久化）
        try:
            self.load_user_settings()
        except Exception as e:
            print(f"警告：加载用户设置失败：{e}")
        
        # 设置日志
        self._setup_logging()
        self.logger = logging.getLogger(__name__)
        
        # 初始化组件
        self.llm_manager = LLMManager()
        self.template_manager = TemplateManager(self.config["templates"]["directory"])
        self.prompt_manager = BasePromptManager("src/prompts")
        self.file_processor = FileProcessor()
        self.card_generator = CardGenerator(
            self.llm_manager,
            self.template_manager,
            self.prompt_manager
        )
        self.batch_generator = BatchCardGenerator(self.card_generator)
        self.exporter = UnifiedExporter(self.config["export"]["output_directory"], self.template_manager)
        
        # 加载LLM客户端
        self._load_llm_clients()
        
        self.logger.info("Anki写卡助手初始化完成")
    
    
    # ---------- 持久化用户设置 ----------
    def get_user_settings_path(self) -> Path:
        """获取用户设置文件路径"""
        # 直接使用静态方法，避免实例化引发不存在文件的日志
        user_dir = ConfigManager.get_user_config_dir()
        return user_dir / "settings.json"

    def load_user_settings(self):
        """加载用户设置并合并到内存配置"""
        # LLM配置现在直接存储在config.json中，无需额外加载
        # 此方法保留以兼容性，但不再执行任何操作
        pass

    def save_user_settings(self):
        """将当前设置持久化到配置文件"""
        # LLM配置现在直接存储在config.json中
        # 保存配置到文件
        self.config_manager.save_config()
    
    def _setup_logging(self):
        """设置日志系统"""
        # 创建日志目录
        log_path = Path("logs/app.log")
        log_path.parent.mkdir(exist_ok=True)
        
        # 配置日志格式
        log_format = "%(asctime)s - %(name)s - %(levelname)s - %(message)s"
        
        # 配置根日志器
        logging.basicConfig(
            level=logging.INFO,
            format=log_format,
            handlers=[]
        )
        
        # 添加处理器
        handlers = []
        handlers.append(logging.StreamHandler())
        
        from logging.handlers import RotatingFileHandler
        handlers.append(RotatingFileHandler(
            log_path,
            maxBytes=10*1024*1024,  # 10MB
            backupCount=5
        ))
        
        # 为所有处理器设置格式
        formatter = logging.Formatter(log_format)
        for handler in handlers:
            handler.setFormatter(formatter)
            logging.getLogger().addHandler(handler)
    
    def _load_llm_clients(self):
        """加载LLM客户端"""
        try:
            # 从内存配置中获取LLM设置
            llm_config = self.config.get("llm", {})
            api_key = llm_config.get("api_key", "")
            
            # 检查API密钥是否已配置
            if api_key and api_key.strip():
                config = LLMConfig(
                    api_key=api_key,
                    model=llm_config.get("model"),
                    base_url=llm_config.get("base_url"),
                    temperature=llm_config.get("temperature"),
                    max_tokens=llm_config.get("max_tokens"),
                    timeout=llm_config.get("timeout")
                )
                self.llm_manager.set_client(config)
                self.logger.info(f"已设置LLM客户端: {config.base_url} ({config.model})")
            else:
                self.logger.info("API密钥未配置，请在Web界面中设置")
        
        except Exception as e:
            self.logger.error(f"加载LLM客户端失败: {e}")
    
    def update_llm_config(self, llm_settings: dict):
        """更新LLM配置"""
        try:
            # 更新内存中的配置
            self.config.setdefault("llm", {}).update(llm_settings)
            
            # 更新配置文件中的LLM设置
            for key, value in llm_settings.items():
                self.config_manager.set(f"llm.{key}", value)
            
            # 保存配置到config.json
            self.config_manager.save_config()
            
            # 如果提供了API密钥，重新设置LLM客户端
            if llm_settings.get("api_key"):
                config = LLMConfig(
                    api_key=llm_settings["api_key"],
                    model=llm_settings.get("model") or self.config["llm"]["model"],
                    base_url=llm_settings.get("base_url") or self.config["llm"]["base_url"],
                    temperature=llm_settings.get("temperature") or self.config["llm"]["temperature"],
                    max_tokens=llm_settings.get("max_tokens") or self.config["llm"]["max_tokens"],
                    timeout=llm_settings.get("timeout") or self.config["llm"]["timeout"]
                )
                self.llm_manager.set_client(config)
                self.logger.info(f"已更新LLM客户端: {config.base_url} ({config.model})")
            
            return True
        except Exception as e:
            self.logger.error(f"更新LLM配置失败: {e}")
            return False
    
    async def generate_cards(self, content: str, config: Optional[GenerationConfig] = None) -> list:
        """生成卡片"""
        if config is None:
            config = GenerationConfig(
                template_name="Quizify",  # 默认使用Quizify模板
                prompt_type="cloze",      # 默认使用cloze提示词
                temperature=self.config["llm"]["temperature"],
                max_tokens=self.config["llm"]["max_tokens"],
                card_count=self.config["generation"]["default_card_count"]
            )
        
        try:
            cards = await self.card_generator.generate_cards(content, config)
            self.logger.info(f"成功生成 {len(cards)} 张卡片")
            return cards
        except Exception as e:
            self.logger.error(f"生成卡片失败: {e}")
            raise
    
    async def generate_from_file(self, file_path: str, config: Optional[GenerationConfig] = None) -> list:
        """从文件生成卡片"""
        try:
            cards = await self.batch_generator.generate_from_file(file_path, config)
            self.logger.info(f"从文件生成 {len(cards)} 张卡片")
            return cards
        except Exception as e:
            self.logger.error(f"从文件生成卡片失败: {e}")
            raise
    
    def export_cards(self, cards: list, formats: Optional[list] = None, original_content: str = None, generation_config: Dict = None) -> dict:
        """导出卡片"""
        # 确保 formats 是有效的格式列表
        if formats is None:
            formats = self.config["export"]["default_formats"].copy()  # 使用副本避免修改原始配置
        else:
            # 验证传入的格式参数
            if not isinstance(formats, list):
                formats = self.config["export"]["default_formats"].copy()
            else:
                # 过滤掉无效的格式
                valid_formats = []
                for fmt in formats:
                    if isinstance(fmt, str) and fmt in ['json', 'csv', 'apkg', 'txt', 'html']:
                        valid_formats.append(fmt)
                formats = valid_formats if valid_formats else self.config["export"]["default_formats"].copy()
        
        try:
            export_paths = self.exporter.export_multiple_formats(
                cards, formats, 
                original_content=original_content, generation_config=generation_config
            )
            self.logger.info(f"已导出卡片到: {export_paths}")
            return export_paths
        except Exception as e:
            self.logger.error(f"导出卡片失败: {e}")
            raise
    
    def list_templates(self) -> list:
        """列出可用模板"""
        return self.template_manager.list_templates()
    
    def list_prompts(self, category: str = None, template_name: str = None) -> list:
        """列出可用提示词（可按模板过滤）"""
        return self.prompt_manager.list_prompts(category=category, template_name=template_name)
    
    def list_prompt_names(self, category: str = None, template_name: str = None) -> list:
        """列出可用提示词名称（用于显示，可按模板过滤）"""
        return self.prompt_manager.list_prompt_names(category=category, template_name=template_name)
    
    def get_prompt_content(self, prompt_type: str, template_name: str = None) -> str:
        """获取提示词内容，优先读取用户文件，支持模板子目录优先级"""
        try:
            # 委托给PromptManager，内部按模板子目录/全局顺序查找
            prompt_content = self.prompt_manager.get_prompt(prompt_type, template_name)
            return prompt_content
        except Exception as e:
            self.logger.error(f"获取提示词内容失败: {e}")
            raise
    
    def _get_template_prompt_dir(self, template_name: str = None) -> Path:
        """获取模板提示词目录"""
        base_dir = Path("src/prompts")
        if template_name:
            folder = self.prompt_manager.template_dir_map.get(template_name)
            if folder:
                return base_dir / folder
        return base_dir
    
    def _reload_prompt_manager(self):
        """重新加载提示词管理器"""
        self.prompt_manager = BasePromptManager("src/prompts")
    
    def save_prompt_content(self, prompt_type: str, content: str, template_name: str = None) -> None:
        """保存提示词内容到用户文件；若提供模板名则保存到该模板子目录"""
        try:
            save_dir = self._get_template_prompt_dir(template_name)
            save_dir.mkdir(parents=True, exist_ok=True)
            user_prompt_file = save_dir / f"{prompt_type}_user.md"
            with open(user_prompt_file, 'w', encoding='utf-8') as f:
                f.write(content)
            # 重新加载提示词管理器
            self._reload_prompt_manager()
            self.logger.info(f"提示词内容已保存: {user_prompt_file}")
        except Exception as e:
            self.logger.error(f"保存提示词内容失败: {e}")
            raise
    
    def reset_prompt_content(self, prompt_type: str, template_name: str = None) -> str:
        """重置提示词内容，从原始文件恢复；优先模板目录"""
        try:
            read_dir = self._get_template_prompt_dir(template_name)
            # 读取原始文件
            original_prompt_file = read_dir / f"{prompt_type}.md"
            if not original_prompt_file.exists():
                raise FileNotFoundError(f"原始提示词文件不存在: {original_prompt_file}")
            with open(original_prompt_file, 'r', encoding='utf-8') as f:
                original_content = f.read()
            # 将原始内容写入目标用户文件
            user_prompt_file = read_dir / f"{prompt_type}_user.md"
            with open(user_prompt_file, 'w', encoding='utf-8') as f:
                f.write(original_content)
            # 重新加载提示词管理器
            self._reload_prompt_manager()
            self.logger.info(f"提示词内容已重置为原始版本: {user_prompt_file}")
            return original_content
        except Exception as e:
            self.logger.error(f"重置提示词内容失败: {e}")
            raise
    
    def list_llm_clients(self) -> list:
        """列出可用LLM客户端"""
        if self.llm_manager.client:
            return [f"{self.llm_manager.client.config.base_url} ({self.llm_manager.client.config.model})"]
        return []
    
    def get_export_summary(self, cards: list) -> dict:
        """获取导出摘要"""
        return self.exporter.get_export_summary(cards)
    
    def export_apkg(self, cards: list, filename: str = None, template_name: str = None) -> str:
        """导出为apkg格式"""
        return self.exporter.export_to_apkg(cards, filename, template_name)
    
    def export_apkg_with_custom_template(self, cards: list, template_name: str, filename: str = None) -> str:
        """使用自定义模板导出为apkg格式"""
        return self.exporter.export_to_apkg_with_custom_template(cards, template_name, filename)

async def main():
    """主函数"""
    parser = argparse.ArgumentParser(description="Anki写卡助手")
    parser.add_argument("--content", "-c", help="要生成卡片的内容")
    parser.add_argument("--file", "-f", help="包含内容的文件路径")
    parser.add_argument("--template", "-t", help="使用的模板名称")
    parser.add_argument("--prompt", "-p", help="使用的提示词类型")
    parser.add_argument("--language", help="语言 (zh-CN)")
    parser.add_argument("--difficulty", help="难度 (easy, medium, hard)")
    parser.add_argument("--count", type=int, help="生成卡片数量")
    parser.add_argument("--export", "-e", nargs="+", help="导出格式 (json, csv, html, txt)")
    parser.add_argument("--list-templates", action="store_true", help="列出可用模板")
    parser.add_argument("--list-prompts", action="store_true", help="列出可用提示词")
    parser.add_argument("--list-llms", action="store_true", help="列出可用LLM客户端")
    parser.add_argument("--web", action="store_true", help="启动Web界面")
    parser.add_argument("--debug", action="store_true", help="启用Flask调试与自动重载")
    parser.add_argument("--host", default="0.0.0.0", help="Web服务器主机地址")
    parser.add_argument("--port", type=int, default=5000, help="Web服务器端口")
    
    args = parser.parse_args()
    
    # 初始化助手
    assistant = AnkiCardAssistant()
    
    # 处理列表命令
    if args.list_templates:
        templates = assistant.list_templates()
        print("可用模板:")
        for template in templates:
            print(f"  - {template}")
        return
    
    if args.list_prompts:
        prompts = assistant.list_prompts()
        print("可用提示词:")
        for prompt in prompts:
            print(f"  - {prompt}")
        return
    
    if args.list_llms:
        clients = assistant.list_llm_clients()
        print("可用LLM客户端:")
        for client in clients:
            print(f"  - {client}")
        return
    
    # 启动Web界面
    if args.web:
        try:
            from src.web.app import WebApp
            
            print(f"启动Web服务器: http://{args.host}:{args.port}")
            print("按 Ctrl+C 停止服务器")
            
            # 创建Web应用并启动
            web_app = WebApp(assistant)
            web_app.run(host=args.host, port=args.port, debug=args.debug)
            
        except ImportError as e:
            print(f"Web模块未找到，请安装相关依赖: {e}")
        except KeyboardInterrupt:
            print("\n服务器已停止")
        except Exception as e:
            print(f"启动Web服务器失败: {e}")
        return
    
    # 生成卡片
    if not args.content and not args.file:
        print("请提供内容或文件路径")
        parser.print_help()
        return
    
    # 构建生成配置
    config = GenerationConfig(
        template_name=args.template or "Quizify",  # 默认使用Quizify模板
        prompt_type=args.prompt or "cloze",        # 默认使用cloze提示词
        card_count=args.count or assistant.config["generation"]["default_card_count"]
    )
    
    try:
        # 生成卡片
        if args.file:
            cards = await assistant.generate_from_file(args.file, config)
        else:
            cards = await assistant.generate_cards(args.content, config)
        
        # 导出卡片
        export_paths = assistant.export_cards(cards, args.export)
        print(f"卡片已导出到:")
        for format_type, path in export_paths.items():
            print(f"  {format_type}: {path}")
        
        # 显示摘要
        summary = assistant.get_export_summary(cards)
        print(f"\n生成摘要:")
        print(f"  总卡片数: {summary['total_cards']}")
        print(f"  牌组统计: {summary['deck_stats']}")
        print(f"  模型统计: {summary['model_stats']}")
        
    except Exception as e:
        print(f"错误: {e}")
        sys.exit(1)

if __name__ == "__main__":
    asyncio.run(main())
