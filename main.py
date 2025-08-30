#!/usr/bin/env python3
"""
Anki写卡助手主程序
优化版本 - 模块化架构，清晰的职责分离
"""

import asyncio
import argparse
import logging
import sys
from pathlib import Path
from typing import Dict, Any

# 添加src目录到Python路径
sys.path.insert(0, str(Path(__file__).parent / "src"))

from src import __version__
from src.core.app_initializer import AppInitializer, ComponentManager
from src.core.business_services import ExportService, PromptService, CardGenerationService


class AnkiCardAssistant:
    """Anki写卡助手主类 - 简化版本"""

    def __init__(self, config_path: str = None):
        # 初始化应用
        self.initializer = AppInitializer(config_path)
        self.initializer.initialize_logging()
        
        # 加载配置
        self.config_manager = self.initializer.initialize_config()
        self.config = self.config_manager.get_config()
        
        # 初始化组件
        components = self.initializer.initialize_components(self.config)
        self.component_manager = ComponentManager(components)
        
        # 初始化服务
        self._initialize_services()
        
        self.logger = logging.getLogger(__name__)
        self.logger.info("Anki写卡助手初始化完成")

    def _initialize_services(self):
        """初始化业务服务"""
        # 导出服务
        self.export_service = ExportService(
            self.component_manager.get_component('exporter'),
            self.config
        )
        
        # 提示词服务
        self.prompt_service = PromptService(
            self.component_manager.get_component('prompt_manager'),
            self.component_manager
        )
        
        # 卡片生成服务
        self.card_generation_service = CardGenerationService(
            self.component_manager.get_component('card_generator'),
            self.component_manager.get_component('batch_generator'),
            self.config
        )

    # 配置管理方法
    def save_user_settings(self):
        """保存用户设置"""
        self.config_manager.save_config()

    def update_llm_config(self, llm_settings: dict) -> bool:
        """更新LLM配置"""
        try:
            # 更新内存中的配置
            self.config.setdefault("llm", {}).update(llm_settings)
            
            # 更新配置文件中的LLM设置
            for key, value in llm_settings.items():
                self.config_manager.set(f"llm.{key}", value)
            
            # 保存配置到config.json
            self.config_manager.save_config()
            
            # 更新组件中的LLM配置
            return self.component_manager.update_llm_config(llm_settings)
            
        except Exception as e:
            self.logger.error("更新LLM配置失败: %s", e)
            return False

    # 卡片生成方法（委托给服务）
    async def generate_cards(self, content: str, config=None) -> list:
        """生成卡片"""
        return await self.card_generation_service.generate_cards(content, config)

    async def generate_from_file(self, file_path: str, config=None) -> list:
        """从文件生成卡片"""
        return await self.card_generation_service.generate_from_file(file_path, config)

    # 导出方法（委托给服务）
    def export_cards(self, cards: list, formats=None, **kwargs) -> dict:
        """导出卡片"""
        return self.export_service.export_cards(cards, formats, **kwargs)

    def export_apkg(self, cards: list, filename: str = None, template_name: str = None) -> str:
        """导出为apkg格式"""
        return self.export_service.export_apkg(cards, filename, template_name)

    def export_apkg_with_custom_template(self, cards: list, template_name: str, filename: str = None) -> str:
        """使用自定义模板导出为apkg格式"""
        return self.export_service.export_apkg_with_custom_template(cards, template_name, filename)

    def get_export_summary(self, cards: list) -> dict:
        """获取导出摘要"""
        return self.export_service.get_export_summary(cards)

    # 模板和提示词方法（委托给服务）
    def list_templates(self) -> list:
        """列出可用模板"""
        template_manager = self.component_manager.get_component('template_manager')
        return template_manager.list_templates()

    def list_prompts(self, category: str = None, template_name: str = None) -> list:
        """列出可用提示词"""
        return self.prompt_service.list_prompts(category, template_name)

    def list_prompt_names(self, category: str = None, template_name: str = None) -> list:
        """列出可用提示词名称"""
        return self.prompt_service.list_prompt_names(category, template_name)

    def get_prompt_content(self, prompt_type: str, template_name: str = None) -> str:
        """获取提示词内容"""
        return self.prompt_service.get_prompt_content(prompt_type, template_name)

    def save_prompt_content(self, prompt_type: str, content: str, template_name: str = None) -> None:
        """保存提示词内容"""
        self.prompt_service.save_prompt_content(prompt_type, content, template_name)

    def reset_prompt_content(self, prompt_type: str, template_name: str = None) -> str:
        """重置提示词内容"""
        return self.prompt_service.reset_prompt_content(prompt_type, template_name)

    # LLM客户端方法
    def list_llm_clients(self) -> list:
        """列出可用LLM客户端"""
        llm_manager = self.component_manager.get_component('llm_client_manager')
        return llm_manager.get_client_info()

    @property
    def llm_manager(self):
        """获取LLM管理器（向后兼容）"""
        return self.component_manager.get_component('llm_client_manager').client


class WebAppLauncher:
    """Web应用启动器"""
    
    @staticmethod
    def parse_arguments():
        """解析命令行参数"""
        parser = argparse.ArgumentParser(description=f"Anki写卡助手 v{__version__} - Web界面")
        parser.add_argument("--debug", action="store_true",
                          help="启用Flask调试与自动重载")
        parser.add_argument("--host", default="0.0.0.0", help="Web服务器主机地址")
        parser.add_argument("--port", type=int, default=5000, help="Web服务器端口")
        parser.add_argument("--version", action="version", version=f"%(prog)s {__version__}")
        return parser.parse_args()
    
    @staticmethod
    def launch_web_app(assistant: AnkiCardAssistant, args):
        """启动Web应用"""
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


async def main():
    """主函数 - 启动Web界面"""
    # 解析命令行参数
    args = WebAppLauncher.parse_arguments()
    
    # 初始化助手
    assistant = AnkiCardAssistant()
    
    # 启动Web界面
    WebAppLauncher.launch_web_app(assistant, args)


if __name__ == "__main__":
    asyncio.run(main())
