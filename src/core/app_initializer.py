"""应用初始化器模块"""

import logging
from pathlib import Path
from typing import Dict, Any

from src.core.card_generator import CardGenerator, BatchCardGenerator
from src.core.unified_exporter import UnifiedExporter
from src.core.llm_manager import LLMClientManager
from src.templates.template_manager import TemplateManager
from src.prompts.base_prompts import BasePromptManager
from src.utils.file_processor import FileProcessor
from src.utils.config_manager import ConfigManager
from src.utils.logger_config import LoggerConfig


class AppInitializer:
    """应用初始化器"""
    
    def __init__(self, config_path: str = None):
        self.config_path = config_path or "config.json"
        self.logger = None
        
    def initialize_logging(self) -> None:
        """初始化日志系统"""
        logger_config = LoggerConfig()
        logger_config.setup_logging()
        self.logger = logging.getLogger(__name__)
        
    def initialize_config(self) -> ConfigManager:
        """初始化配置管理器"""
        return ConfigManager(self.config_path)
        
    def initialize_components(self, config: Dict[str, Any]) -> Dict[str, Any]:
        """初始化所有组件"""
        components = {}
        
        # 初始化LLM客户端管理器
        components['llm_client_manager'] = LLMClientManager()
        components['llm_client_manager'].load_from_config(config.get("llm", {}))
        
        # 初始化模板管理器
        components['template_manager'] = TemplateManager(
            config["templates"]["directory"]
        )
        
        # 初始化提示词管理器
        components['prompt_manager'] = BasePromptManager("src/prompts")
        
        # 初始化文件处理器
        components['file_processor'] = FileProcessor()
        
        # 初始化卡片生成器
        components['card_generator'] = CardGenerator(
            components['llm_client_manager'].client,
            components['template_manager'],
            components['prompt_manager']
        )
        
        # 初始化批量生成器
        components['batch_generator'] = BatchCardGenerator(
            components['card_generator']
        )
        
        # 初始化导出器
        components['exporter'] = UnifiedExporter(
            config["export"]["output_directory"],
            components['template_manager']
        )
        
        if self.logger:
            self.logger.info("所有组件初始化完成")
            
        return components


class ComponentManager:
    """组件管理器 - 管理应用组件的生命周期"""
    
    def __init__(self, components: Dict[str, Any]):
        self.components = components
        self.logger = logging.getLogger(__name__)
    
    def get_component(self, name: str) -> Any:
        """获取组件"""
        return self.components.get(name)
    
    def update_llm_config(self, llm_settings: Dict[str, Any]) -> bool:
        """更新LLM配置"""
        llm_manager = self.get_component('llm_client_manager')
        if llm_manager:
            return llm_manager.update_config(llm_settings)
        return False
    
    def reload_prompt_manager(self) -> None:
        """重新加载提示词管理器"""
        try:
            self.components['prompt_manager'] = BasePromptManager("src/prompts")
            
            # 更新依赖提示词管理器的组件
            self.components['card_generator'] = CardGenerator(
                self.components['llm_client_manager'].client,
                self.components['template_manager'],
                self.components['prompt_manager']
            )
            
            self.components['batch_generator'] = BatchCardGenerator(
                self.components['card_generator']
            )
            
            self.logger.info("提示词管理器重新加载完成")
            
        except Exception as e:
            self.logger.error("重新加载提示词管理器失败: %s", e)
            raise