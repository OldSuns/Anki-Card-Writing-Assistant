#!/usr/bin/env python3
import asyncio
import argparse
import logging
import sys
import re
from pathlib import Path
from typing import Optional, Dict
from logging.handlers import RotatingFileHandler

# 添加src目录到Python路径
sys.path.insert(0, str(Path(__file__).parent / "src"))

from src.core.llm_client import LLMManager, LLMConfig
from src.core.card_generator import CardGenerator, BatchCardGenerator, GenerationConfig
from src.core.unified_exporter import UnifiedExporter
from src.templates.template_manager import TemplateManager
from src.prompts.base_prompts import BasePromptManager
from src.utils.config_manager import ConfigManager
from src.utils.file_processor import FileProcessor

# 应用常量
LOG_FORMAT = "%(asctime)s - %(name)s - %(levelname)s - %(message)s"
MAX_LOG_SIZE = 10 * 1024 * 1024  # 10MB


class AnkiCardAssistant:
    """Anki写卡助手主类"""

    def __init__(self, config_path: str = None):
        # 使用ConfigManager加载配置
        config_file_path = config_path or "config.json"
        self.config_manager = ConfigManager(config_file_path)
        self.config = self.config_manager.get_config()

        # 设置日志
        self._setup_logging()
        self.logger = logging.getLogger(__name__)

        # 初始化组件
        self.llm_manager = LLMManager()
        self.template_manager = TemplateManager(
            self.config["templates"]["directory"]
        )
        self.prompt_manager = BasePromptManager("src/prompts")
        self.file_processor = FileProcessor()
        self.card_generator = CardGenerator(
            self.llm_manager,
            self.template_manager,
            self.prompt_manager
        )
        self.batch_generator = BatchCardGenerator(self.card_generator)
        self.exporter = UnifiedExporter(
            self.config["export"]["output_directory"],
            self.template_manager
        )

        # 加载LLM客户端
        self._load_llm_clients()

        self.logger.info("Anki写卡助手初始化完成")

    def save_user_settings(self):
        """将当前设置持久化到配置文件"""
        self.config_manager.save_config()

    def _setup_logging(self):
        """设置日志系统"""
        # 创建日志目录
        log_path = Path("logs/app.log")
        log_path.parent.mkdir(exist_ok=True)

        # 配置根日志器
        logging.basicConfig(
            level=logging.INFO,
            format=LOG_FORMAT,
            handlers=[]
        )

        # 定义日志内容清洗（去除ANSI、替换不可显示字符）
        ansi_pattern = re.compile(r'\x1b\[[0-9;]*[A-Za-z]')

        def _sanitize_log_text(text):
            if not isinstance(text, str):
                try:
                    text = str(text)
                except Exception:
                    return "?"
            # 去除 ANSI 转义序列
            text = ansi_pattern.sub('', text)
            # 替换不可显示字符为 '?'
            return ''.join(
                ch if ch.isprintable() or ch in '\t\r\n' else '?'
                for ch in text
            )

        class SafeTextFilter(logging.Filter):
            def filter(self, record):
                try:
                    # 先用 getMessage() 格式化，再覆盖 msg 并清空 args
                    sanitized = _sanitize_log_text(record.getMessage())
                    record.msg = sanitized
                    record.args = ()
                except Exception:
                    pass
                return True

        # 添加处理器
        stream_handler = logging.StreamHandler()
        file_handler = RotatingFileHandler(
            log_path,
            maxBytes=MAX_LOG_SIZE,
            backupCount=5,
            encoding='utf-8'
        )
        # 仅对文件日志添加清洗过滤器
        file_handler.addFilter(SafeTextFilter())

        # 为所有处理器设置格式
        formatter = logging.Formatter(LOG_FORMAT)
        for handler in (stream_handler, file_handler):
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
                self.logger.info(
                    "已设置LLM客户端: %s (%s)",
                    config.base_url,
                    config.model
                )
            else:
                self.logger.info("API密钥未配置，请在Web界面中设置")

        except Exception as e:
            self.logger.error("加载LLM客户端失败: %s", e)

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
                self.logger.info(
                    "已更新LLM客户端: %s (%s)",
                    config.base_url,
                    config.model
                )

            return True
        except Exception as e:
            self.logger.error("更新LLM配置失败: %s", e)
            return False

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

    def list_templates(self) -> list:
        """列出可用模板"""
        return self.template_manager.list_templates()

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
            # 委托给PromptManager，内部按模板子目录/全局顺序查找
            prompt_content = self.prompt_manager.get_prompt(
                prompt_type, template_name
            )
            return prompt_content
        except Exception as e:
            self.logger.error("获取提示词内容失败: %s", e)
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
            self._reload_prompt_manager()
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
            self._reload_prompt_manager()
            self.logger.info("提示词内容已重置为原始版本: %s", user_prompt_file)
            return original_content
        except Exception as e:
            self.logger.error("重置提示词内容失败: %s", e)
            raise

    def list_llm_clients(self) -> list:
        """列出可用LLM客户端"""
        if self.llm_manager.client:
            return [
                f"{self.llm_manager.client.config.base_url} "
                f"({self.llm_manager.client.config.model})"
            ]
        return []

    def get_export_summary(self, cards: list) -> dict:
        """获取导出摘要"""
        return self.exporter.get_export_summary(cards)

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


async def main():
    """主函数 - 启动Web界面"""
    parser = argparse.ArgumentParser(description="Anki写卡助手 - Web界面")
    parser.add_argument("--debug", action="store_true",
                       help="启用Flask调试与自动重载")
    parser.add_argument("--host", default="0.0.0.0", help="Web服务器主机地址")
    parser.add_argument("--port", type=int, default=5000, help="Web服务器端口")

    args = parser.parse_args()

    # 初始化助手
    assistant = AnkiCardAssistant()

    # 启动Web界面
    try:
        from src.web.app import WebApp

        print(f"启动Web服务器: http://{args.host}:{args.port}")
        print("按 Ctrl+C 停止服务器")

        # 创建Web应用并启动
        web_app = WebApp(assistant)
        web_app.run(host=args.host, port=args.port, debug=args.debug)

    except ImportError as e:
        print(f"Web模块未找到，请安装相关依赖: {e}")
        sys.exit(1)
    except KeyboardInterrupt:
        print("\n服务器已停止")
    except Exception as e:
        print(f"启动Web服务器失败: {e}")
        sys.exit(1)


if __name__ == "__main__":
    asyncio.run(main())
