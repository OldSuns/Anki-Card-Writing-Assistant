"""
配置管理器模块
负责管理应用配置的加载、保存和访问
"""

import json
import logging
from pathlib import Path
from typing import Any, Dict, List


class ConfigDefaults:
    """配置默认值常量"""
    
    DEFAULT_CONFIG = {
        "llm": {
            "api_key": "",
            "model": "gpt-3.5-turbo",
            "base_url": "https://api.openai.com/v1",
            "temperature": 0.7,
            "max_tokens": 20000,
            "timeout": 60
        },
        "generation": {
            "default_template": "Quizify",
            "default_prompt_type": "multiple_choice",
            "default_card_count": 5,
            "default_difficulty": "medium"
        },
        "export": {
            "output_directory": "output",
            "default_formats": ["json", "apkg"]
        },
        "templates": {
            "directory": "src/templates"
        }
    }
    
    REQUIRED_KEYS = [
        "llm.api_key",
        "llm.model",
        "llm.base_url",
        "generation.default_template",
        "export.output_directory"
    ]


class ConfigUtils:
    """配置工具类 - 合并原来的验证器、文件处理器和访问器功能"""
    
    def __init__(self, logger: logging.Logger):
        self.logger = logger
    
    # 验证功能
    def validate_config(self, config: Dict[str, Any]) -> bool:
        """验证配置有效性"""
        try:
            for key in ConfigDefaults.REQUIRED_KEYS:
                if not self._get_nested_value(config, key):
                    self.logger.warning("缺少必需的配置项: %s", key)
                    return False
            return True
        except Exception as e:
            self.logger.error("验证配置失败: %s", e)
            return False
    
    # 文件操作功能
    def load_from_file(self, config_file: Path) -> Dict[str, Any]:
        """从文件加载配置"""
        try:
            if config_file.exists():
                with open(config_file, 'r', encoding='utf-8') as f:
                    config = json.load(f)
                self.logger.info("配置已从 %s 加载", config_file)
                return config
            else:
                self.logger.warning("配置文件 %s 不存在，使用默认配置", config_file)
                return {}
        except Exception as e:
            self.logger.error("加载配置文件失败: %s", e)
            return {}
    
    def save_to_file(self, config: Dict[str, Any], config_file: Path) -> bool:
        """保存配置到文件"""
        try:
            config_file.parent.mkdir(parents=True, exist_ok=True)
            with open(config_file, 'w', encoding='utf-8') as f:
                json.dump(config, f, indent=2, ensure_ascii=False)
            self.logger.info("配置已保存到 %s", config_file)
            return True
        except Exception as e:
            self.logger.error("保存配置文件失败: %s", e)
            return False
    
    # 配置访问功能
    def get_nested_value(self, config: Dict[str, Any], key: str, default: Any = None) -> Any:
        """获取嵌套配置值（支持点号分隔的嵌套键）"""
        return self._get_nested_value(config, key) or default
    
    def set_nested_value(self, config: Dict[str, Any], key: str, value: Any) -> bool:
        """设置嵌套配置值（支持点号分隔的嵌套键）"""
        try:
            keys = key.split('.')
            current_config = config
            for k in keys[:-1]:
                if k not in current_config:
                    current_config[k] = {}
                current_config = current_config[k]
            current_config[keys[-1]] = value
            return True
        except Exception as e:
            self.logger.error("设置配置值失败: %s", e)
            return False
    
    def update_config(self, config: Dict[str, Any], new_config: Dict[str, Any]) -> bool:
        """更新配置"""
        try:
            config.update(new_config)
            self.logger.info("配置已更新")
            return True
        except Exception as e:
            self.logger.error("更新配置失败: %s", e)
            return False
    
    def get_config_section(self, config: Dict[str, Any], section: str) -> Dict[str, Any]:
        """获取配置段"""
        return config.get(section, {})
    
    def _get_nested_value(self, config: Dict[str, Any], key: str) -> Any:
        """获取嵌套配置值的内部实现"""
        try:
            keys = key.split('.')
            value = config
            for k in keys:
                value = value[k]
            return value
        except (KeyError, TypeError):
            return None


class ConfigManager:
    """配置管理器 - 简化后的主类"""

    def __init__(self, config_file: str = "config.json"):
        self.logger = logging.getLogger(__name__)
        self.config_file = Path(config_file)
        
        # 初始化工具类
        self.utils = ConfigUtils(self.logger)
        
        # 加载配置
        self._config = self._load_config()

    def _load_config(self) -> Dict[str, Any]:
        """加载配置"""
        config = self.utils.load_from_file(self.config_file)
        
        if not config:
            self.logger.info("使用默认配置")
            config = ConfigDefaults.DEFAULT_CONFIG.copy()
            self.save_config()
        
        return config

    def get_config(self) -> Dict[str, Any]:
        """获取完整配置"""
        return self._config.copy()

    def get(self, key: str, default: Any = None) -> Any:
        """获取配置值（支持点号分隔的嵌套键）"""
        return self.utils.get_nested_value(self._config, key, default)

    def set(self, key: str, value: Any) -> bool:
        """设置配置值（支持点号分隔的嵌套键）"""
        return self.utils.set_nested_value(self._config, key, value)

    def save_config(self) -> bool:
        """保存配置到文件"""
        return self.utils.save_to_file(self._config, self.config_file)

    def update_config(self, new_config: Dict[str, Any]) -> bool:
        """更新配置"""
        if self.utils.update_config(self._config, new_config):
            return self.save_config()
        return False

    def reset_config(self) -> bool:
        """重置为默认配置"""
        try:
            self._config = ConfigDefaults.DEFAULT_CONFIG.copy()
            self.save_config()
            self.logger.info("配置已重置为默认值")
            return True
        except Exception as e:
            self.logger.error("重置配置失败: %s", e)
            return False

    def validate_config(self) -> bool:
        """验证配置有效性"""
        return self.utils.validate_config(self._config)

    # 便捷方法 - 获取特定配置段
    def get_llm_config(self) -> Dict[str, Any]:
        """获取LLM配置"""
        return self.utils.get_config_section(self._config, "llm")

    def get_generation_config(self) -> Dict[str, Any]:
        """获取生成配置"""
        return self.utils.get_config_section(self._config, "generation")

    def get_export_config(self) -> Dict[str, Any]:
        """获取导出配置"""
        return self.utils.get_config_section(self._config, "export")

    def get_templates_config(self) -> Dict[str, Any]:
        """获取模板配置"""
        return self.utils.get_config_section(self._config, "templates")
    
    # 批量操作方法
    def get_multiple(self, keys: List[str]) -> Dict[str, Any]:
        """批量获取配置值"""
        return {key: self.get(key) for key in keys}
    
    def set_multiple(self, key_value_pairs: Dict[str, Any]) -> bool:
        """批量设置配置值"""
        try:
            for key, value in key_value_pairs.items():
                if not self.set(key, value):
                    return False
            return True
        except Exception as e:
            self.logger.error("批量设置配置失败: %s", e)
            return False
    
    # 配置备份和恢复
    def backup_config(self, backup_file: str = None) -> bool:
        """备份当前配置"""
        if backup_file is None:
            backup_file = f"{self.config_file.stem}_backup.json"
        
        backup_path = self.config_file.parent / backup_file
        return self.utils.save_to_file(self._config, backup_path)
    
    def restore_config(self, backup_file: str) -> bool:
        """从备份恢复配置"""
        backup_path = self.config_file.parent / backup_file
        if not backup_path.exists():
            self.logger.error("备份文件不存在: %s", backup_path)
            return False
        
        backup_config = self.utils.load_from_file(backup_path)
        if backup_config:
            self._config = backup_config
            return self.save_config()
        return False
