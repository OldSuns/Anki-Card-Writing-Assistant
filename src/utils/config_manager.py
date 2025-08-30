"""
配置管理器模块
负责管理应用配置的加载、保存和访问
"""

import json
import logging
from pathlib import Path
from typing import Any, Dict


class ConfigManager:
    """配置管理器"""

    def __init__(self, config_file: str = "config.json"):
        self.config_file = Path(config_file)
        self.logger = logging.getLogger(__name__)
        self._config = {}
        self._load_config()

    def _load_config(self):
        """加载配置文件"""
        try:
            if self.config_file.exists():
                with open(self.config_file, 'r', encoding='utf-8') as f:
                    self._config = json.load(f)
                self.logger.info("配置已从 %s 加载", self.config_file)
            else:
                self.logger.warning("配置文件 %s 不存在，使用默认配置", self.config_file)
                self._create_default_config()
        except Exception as e:
            self.logger.error("加载配置文件失败: %s", e)
            self._create_default_config()

    def _create_default_config(self):
        """创建默认配置"""
        self._config = {
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
        self.save_config()

    def get_config(self) -> Dict[str, Any]:
        """获取完整配置"""
        return self._config.copy()

    def get(self, key: str, default: Any = None) -> Any:
        """获取配置值（支持点号分隔的嵌套键）"""
        try:
            keys = key.split('.')
            value = self._config
            for k in keys:
                value = value[k]
            return value
        except (KeyError, TypeError):
            return default

    def set(self, key: str, value: Any):
        """设置配置值（支持点号分隔的嵌套键）"""
        try:
            keys = key.split('.')
            config = self._config
            for k in keys[:-1]:
                if k not in config:
                    config[k] = {}
                config = config[k]
            config[keys[-1]] = value
        except Exception as e:
            self.logger.error("设置配置值失败: %s", e)

    def save_config(self):
        """保存配置到文件"""
        try:
            # 确保输出目录存在
            self.config_file.parent.mkdir(parents=True, exist_ok=True)
            with open(self.config_file, 'w', encoding='utf-8') as f:
                json.dump(self._config, f, indent=2, ensure_ascii=False)
            self.logger.info("配置已保存到 %s", self.config_file)
        except Exception as e:
            self.logger.error("保存配置文件失败: %s", e)

    def update_config(self, new_config: Dict[str, Any]):
        """更新配置"""
        try:
            self._config.update(new_config)
            self.save_config()
            self.logger.info("配置已更新")
        except Exception as e:
            self.logger.error("更新配置失败: %s", e)

    def reset_config(self):
        """重置为默认配置"""
        try:
            self._create_default_config()
            self.logger.info("配置已重置为默认值")
        except Exception as e:
            self.logger.error("重置配置失败: %s", e)

    def get_llm_config(self) -> Dict[str, Any]:
        """获取LLM配置"""
        return self._config.get("llm", {})

    def get_generation_config(self) -> Dict[str, Any]:
        """获取生成配置"""
        return self._config.get("generation", {})

    def get_export_config(self) -> Dict[str, Any]:
        """获取导出配置"""
        return self._config.get("export", {})

    def validate_config(self) -> bool:
        """验证配置有效性"""
        try:
            required_keys = [
                "llm.api_key",
                "llm.model",
                "llm.base_url",
                "generation.default_template",
                "export.output_directory"
            ]
            for key in required_keys:
                if not self.get(key):
                    self.logger.warning("缺少必需的配置项: %s", key)
                    return False
            return True
        except Exception as e:
            self.logger.error("验证配置失败: %s", e)
            return False
