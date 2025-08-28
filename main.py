#!/usr/bin/env python3
"""
Anki写卡助手主程序
基于大语言模型的Anki记忆卡片生成工具
"""

import asyncio
import argparse
import json
import logging
import sys
from pathlib import Path
from typing import Optional

# 添加src目录到Python路径
sys.path.insert(0, str(Path(__file__).parent / "src"))

from src.core.llm_client import LLMManager, LLMConfig
from src.core.card_generator import CardGenerator, BatchCardGenerator, GenerationConfig
from src.core.anki_exporter import AnkiExporter
from src.templates.template_manager import TemplateManager
from src.prompts.base_prompts import BasePromptManager
from src.utils.config_manager import ConfigManager

class AnkiCardAssistant:
    """Anki写卡助手主类"""
    
    def __init__(self, config_path: str = None):
        # 不再依赖config目录，使用内存中的默认配置
        self.config = self._get_default_config()
        
        # 如果提供了config_path，尝试加载配置（向后兼容）
        if config_path:
            try:
                self.config_manager = ConfigManager(config_path)
                loaded_config = self.config_manager.get_config()
                # 合并配置
                self._merge_config(loaded_config)
            except Exception as e:
                print(f"警告：无法加载配置文件 {config_path}: {e}")
                print("使用默认配置")
        
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
        self.card_generator = CardGenerator(
            self.llm_manager, 
            self.template_manager, 
            self.prompt_manager
        )
        self.batch_generator = BatchCardGenerator(self.card_generator)
        self.exporter = AnkiExporter(self.config["export"]["output_directory"])
        
        # 加载LLM客户端
        self._load_llm_clients()
        
        self.logger.info("Anki写卡助手初始化完成")
    
    def _get_default_config(self):
        """获取默认配置"""
        return {
            "app": {
                "name": "Anki写卡助手",
                "version": "1.0.0",
                "description": "基于大语言模型的Anki记忆卡片生成工具",
                "author": "Anki Card Writing Assistant Team"
            },
            "ui": {
                "theme": "light",
                "language": "zh-CN",
                "window_size": {"width": 1200, "height": 800},
                "show_preview": True
            },
            "llm": {
                "api_key": "",
                "base_url": "https://api.openai.com/v1",
                "model": "gpt-3.5-turbo",
                "temperature": 0.7,
                "max_tokens": 2000,
                "timeout": 30,
                "retry_attempts": 3,
                "retry_delay": 1
            },
            "generation": {
                "default_template": "Quizify",
                "default_prompt_type": "standard_qa",
                "default_language": "zh-CN",
                "default_difficulty": "medium",
                "default_card_count": 1,
                "batch_size": 10,
                "max_content_length": 10000
            },
            "export": {
                "default_formats": ["json", "csv", "html", "apkg"],
                "output_directory": "output",
                "filename_template": "anki_cards_{timestamp}",
                "include_timestamp": True
            },
            "templates": {
                "directory": "Card Template",
                "auto_load": True,
                "custom_templates_enabled": True
            },
            "prompts": {
                "auto_load": True,
                "custom_prompts_enabled": True,
                "default_categories": ["standard", "cloze", "medical", "programming", "language"]
            },
            "logging": {
                "level": "INFO",
                "file_enabled": True,
                "file_path": "logs/app.log",
                "max_file_size": "10MB",
                "backup_count": 5,
                "console_enabled": True
            },
            "security": {
                "api_key_encryption": True,
                "config_file_permissions": "600",
                "log_file_permissions": "644"
            },
            "performance": {
                "max_concurrent_requests": 5,
                "request_delay": 0.1,
                "cache_enabled": True,
                "cache_size": 100,
                "cache_ttl": 3600
            },
            "features": {
                "card_preview": True,
                "batch_processing": True,
                "template_editor": True,
                "prompt_editor": True,
                "export_preview": True,
                "statistics": True
            }
        }
    
    def _merge_config(self, loaded_config):
        """合并配置"""
        def merge_dict(target, source):
            for key, value in source.items():
                if key in target and isinstance(target[key], dict) and isinstance(value, dict):
                    merge_dict(target[key], value)
                else:
                    target[key] = value
        
        merge_dict(self.config, loaded_config)
    
    # ---------- 持久化用户设置 ----------
    def get_user_settings_path(self) -> Path:
        """获取用户设置文件路径"""
        from src.utils.config_manager import ConfigManager as _CM
        # 复用ConfigManager的用户目录逻辑
        cm = _CM("dummy.json")
        user_dir = cm.get_user_config_dir()
        return user_dir / "settings.json"

    def load_user_settings(self):
        """加载用户设置并合并到内存配置"""
        settings_path = self.get_user_settings_path()
        if settings_path.exists():
            with open(settings_path, 'r', encoding='utf-8') as f:
                user_settings = json.load(f)
            # 仅允许覆盖的键：llm
            allowed = {
                "llm": user_settings.get("llm", {})
            }
            self._merge_config(allowed)

    def save_user_settings(self):
        """将当前设置持久化到用户文件"""
        settings_path = self.get_user_settings_path()
        settings_path.parent.mkdir(parents=True, exist_ok=True)
        payload = {
            "llm": {
                "api_key": self.config.get("llm", {}).get("api_key", ""),
                "base_url": self.config.get("llm", {}).get("base_url", "https://api.openai.com/v1"),
                "model": self.config.get("llm", {}).get("model", "gpt-3.5-turbo"),
                "temperature": self.config.get("llm", {}).get("temperature", 0.7),
                "max_tokens": self.config.get("llm", {}).get("max_tokens", 2000),
                "timeout": self.config.get("llm", {}).get("timeout", 30)
            }
        }
        with open(settings_path, 'w', encoding='utf-8') as f:
            json.dump(payload, f, ensure_ascii=False, indent=2)
    
    def _setup_logging(self):
        """设置日志系统"""
        log_config = self.config["logging"]
        
        # 创建日志目录
        log_path = Path(log_config["file_path"])
        log_path.parent.mkdir(exist_ok=True)
        
        # 配置日志格式
        log_format = "%(asctime)s - %(name)s - %(levelname)s - %(message)s"
        
        # 配置根日志器
        logging.basicConfig(
            level=getattr(logging, log_config["level"]),
            format=log_format,
            handlers=[]
        )
        
        # 添加控制台处理器
        if log_config["console_enabled"]:
            console_handler = logging.StreamHandler()
            console_handler.setFormatter(logging.Formatter(log_format))
            logging.getLogger().addHandler(console_handler)
        
        # 添加文件处理器
        if log_config["file_enabled"]:
            from logging.handlers import RotatingFileHandler
            file_handler = RotatingFileHandler(
                log_path,
                maxBytes=10*1024*1024,  # 10MB
                backupCount=log_config["backup_count"]
            )
            file_handler.setFormatter(logging.Formatter(log_format))
            logging.getLogger().addHandler(file_handler)
    
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
                    model=llm_config.get("model", "gpt-3.5-turbo"),
                    base_url=llm_config.get("base_url", "https://api.openai.com/v1"),
                    temperature=llm_config.get("temperature", 0.7),
                    max_tokens=llm_config.get("max_tokens", 2000),
                    timeout=llm_config.get("timeout", 30)
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
            
            # 如果提供了API密钥，重新设置LLM客户端
            if llm_settings.get("api_key"):
                config = LLMConfig(
                    api_key=llm_settings["api_key"],
                    model=llm_settings.get("model", "gpt-3.5-turbo"),
                    base_url=llm_settings.get("base_url", "https://api.openai.com/v1"),
                    temperature=llm_settings.get("temperature", 0.7),
                    max_tokens=llm_settings.get("max_tokens", 2000),
                    timeout=llm_settings.get("timeout", 30)
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
                template_name=self.config["generation"]["default_template"],
                prompt_type=self.config["generation"]["default_prompt_type"],
                llm_client="default",  # 不再需要指定具体的LLM客户端
                temperature=self.config["llm"]["temperature"],
                max_tokens=self.config["llm"]["max_tokens"],
                language=self.config["generation"]["default_language"],
                difficulty=self.config["generation"]["default_difficulty"],
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
    
    def export_cards(self, cards: list, formats: Optional[list] = None) -> dict:
        """导出卡片"""
        if formats is None:
            formats = self.config["export"]["default_formats"]
        
        try:
            export_paths = self.exporter.export_multiple_formats(cards, formats)
            self.logger.info(f"已导出卡片到: {export_paths}")
            return export_paths
        except Exception as e:
            self.logger.error(f"导出卡片失败: {e}")
            raise
    
    def list_templates(self) -> list:
        """列出可用模板"""
        return self.template_manager.list_templates()
    
    def list_prompts(self, category: str = None) -> list:
        """列出可用提示词"""
        return self.prompt_manager.list_prompts(category=category)
    
    def list_prompt_names(self, category: str = None) -> list:
        """列出可用提示词名称（用于显示）"""
        return self.prompt_manager.list_prompt_names(category=category)
    
    def get_prompt_content(self, prompt_type: str) -> str:
        """获取提示词内容，优先读取用户文件"""
        try:
            # 首先尝试读取用户文件
            user_prompt_file = Path("src/prompts") / f"{prompt_type}_user.md"
            if user_prompt_file.exists():
                with open(user_prompt_file, 'r', encoding='utf-8') as f:
                    content = f.read()
                self.logger.info(f"从用户文件读取提示词: {prompt_type}_user.md")
                return content
            
            # 如果用户文件不存在，读取原始文件
            original_prompt_file = Path("src/prompts") / f"{prompt_type}.md"
            if original_prompt_file.exists():
                with open(original_prompt_file, 'r', encoding='utf-8') as f:
                    content = f.read()
                self.logger.info(f"从原始文件读取提示词: {prompt_type}.md")
                return content
            
            # 如果都不存在，从提示词管理器获取
            prompt_content = self.prompt_manager.get_prompt(prompt_type)
            return prompt_content
            
        except Exception as e:
            self.logger.error(f"获取提示词内容失败: {e}")
            raise
    
    def save_prompt_content(self, prompt_type: str, content: str) -> None:
        """保存提示词内容到用户文件"""
        try:
            # 保存到用户文件（添加_user后缀）
            user_prompt_file = Path("src/prompts") / f"{prompt_type}_user.md"
            
            # 确保prompts目录存在
            user_prompt_file.parent.mkdir(exist_ok=True)
            
            # 写入内容到用户文件
            with open(user_prompt_file, 'w', encoding='utf-8') as f:
                f.write(content)
            
            # 重新加载提示词管理器
            self.prompt_manager = BasePromptManager("src/prompts")
            
            self.logger.info(f"提示词内容已保存到用户文件: {prompt_type}_user.md")
        except Exception as e:
            self.logger.error(f"保存提示词内容失败: {e}")
            raise
    
    def reset_prompt_content(self, prompt_type: str) -> str:
        """重置提示词内容，从原始文件恢复"""
        try:
            # 读取原始文件内容
            original_prompt_file = Path("src/prompts") / f"{prompt_type}.md"
            if not original_prompt_file.exists():
                raise FileNotFoundError(f"原始提示词文件不存在: {prompt_type}.md")
            
            with open(original_prompt_file, 'r', encoding='utf-8') as f:
                original_content = f.read()
            
            # 将原始内容写入用户文件（覆盖用户修改）
            user_prompt_file = Path("src/prompts") / f"{prompt_type}_user.md"
            with open(user_prompt_file, 'w', encoding='utf-8') as f:
                f.write(original_content)
            
            # 重新加载提示词管理器
            self.prompt_manager = BasePromptManager("src/prompts")
            
            self.logger.info(f"提示词内容已重置为原始版本: {prompt_type}")
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
    
    def export_apkg(self, cards: list, filename: str = None) -> str:
        """导出为apkg格式"""
        return self.exporter.export_to_apkg(cards, filename)
    
    def export_apkg_with_custom_template(self, cards: list, template_path: str, filename: str = None) -> str:
        """使用自定义模板导出为apkg格式"""
        return self.exporter.export_to_apkg_with_custom_template(cards, template_path, filename)

async def main():
    """主函数"""
    parser = argparse.ArgumentParser(description="Anki写卡助手")
    parser.add_argument("--content", "-c", help="要生成卡片的内容")
    parser.add_argument("--file", "-f", help="包含内容的文件路径")
    parser.add_argument("--template", "-t", help="使用的模板名称")
    parser.add_argument("--prompt", "-p", help="使用的提示词类型")
    parser.add_argument("--llm", "-l", help="LLM客户端（已弃用，统一使用配置的客户端）")
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
        template_name=args.template or assistant.config["generation"]["default_template"],
        prompt_type=args.prompt or assistant.config["generation"]["default_prompt_type"],
        llm_client="default",  # 不再需要指定具体的LLM客户端
        language=args.language or assistant.config["generation"]["default_language"],
        difficulty=args.difficulty or assistant.config["generation"]["default_difficulty"],
        card_count=args.count or assistant.config["generation"]["default_card_count"]
    )
    
    try:
        # 生成卡片
        if args.file:
            cards = await assistant.generate_from_file(args.file, config)
        else:
            cards = await assistant.generate_cards(args.content, config)
        
        # 导出卡片
        if args.export:
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
