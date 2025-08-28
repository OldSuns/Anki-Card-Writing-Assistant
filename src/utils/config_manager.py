import json
import logging
from pathlib import Path
from typing import Dict, Any, Optional
import os

class ConfigManager:
    """配置管理器"""
    
    def __init__(self, config_path: Optional[str] = None):
        # 优先使用项目根目录的config.json，除非明确指定其他路径
        if config_path is None:
            self.config_path = Path("config.json")
        else:
            self.config_path = Path(config_path)
        
        self.config: Dict[str, Any] = {}
        self.logger = logging.getLogger(__name__)
        self._load_config()
    
    def _load_config(self):
        """加载配置文件"""
        try:
            if self.config_path.exists():
                with open(self.config_path, 'r', encoding='utf-8') as f:
                    self.config = json.load(f)
                self.logger.info(f"已加载配置文件: {self.config_path}")
            else:
                self.logger.warning(f"配置文件不存在: {self.config_path}")
                self._create_default_config()
        except Exception as e:
            self.logger.error(f"加载配置文件失败: {e}")
            self._create_default_config()
    
    def _create_default_config(self):
        """创建默认配置文件 - 从config.json.example复制模板"""
        try:
            # 尝试从config.json.example读取配置模板
            template_config_path = Path("config.json.example")
            if template_config_path.exists():
                with open(template_config_path, 'r', encoding='utf-8') as f:
                    template_config = json.load(f)
                
                # 创建config.json文件
                config_json_path = Path("config.json")
                with open(config_json_path, 'w', encoding='utf-8') as f:
                    json.dump(template_config, f, ensure_ascii=False, indent=2)
                
                # 加载到内存
                self.config = template_config
                self.logger.info("已从config.json.example创建并加载默认配置到config.json")
                return
        except Exception as e:
            self.logger.warning(f"从config.json.example创建配置失败: {e}")
        
        # 如果无法从config.json.example读取，创建最基础的配置
        self.config = {
            "llm": {
                "api_key": "",
                "base_url": "https://api.openai.com/v1",
                "model": "gpt-3.5-turbo",
                "temperature": 0.7,
                "max_tokens": 20000,
                "timeout": 30
            },
            "generation": {
                "default_difficulty": "medium",
                "default_card_count": 1
            },
            "export": {
                "default_formats": ["json", "apkg"],
                "output_directory": "output"
            },
            "templates": {
                "directory": "Card Template"
            }
        }
        
        # 同时创建config.json文件
        try:
            with open("config.json", 'w', encoding='utf-8') as f:
                json.dump(self.config, f, ensure_ascii=False, indent=2)
            self.logger.info("已创建基础配置文件config.json")
        except Exception as e:
            self.logger.error(f"创建config.json文件失败: {e}")
    
    def get_config(self) -> Dict[str, Any]:
        """获取配置"""
        return self.config
    
    def get(self, key: str, default: Any = None) -> Any:
        """获取配置项"""
        keys = key.split('.')
        value = self.config
        
        for k in keys:
            if isinstance(value, dict) and k in value:
                value = value[k]
            else:
                return default
        
        return value
    
    def set(self, key: str, value: Any):
        """设置配置项"""
        keys = key.split('.')
        config = self.config
        
        # 创建嵌套字典结构
        for k in keys[:-1]:
            if k not in config:
                config[k] = {}
            config = config[k]
        
        config[keys[-1]] = value
        self.logger.info(f"已设置配置项: {key} = {value}")
    
    def save_config(self, path: Optional[str] = None):
        """保存配置到文件"""
        save_path = Path(path) if path else self.config_path
        
        try:
            save_path.parent.mkdir(parents=True, exist_ok=True)
            with open(save_path, 'w', encoding='utf-8') as f:
                json.dump(self.config, f, ensure_ascii=False, indent=2)
            self.logger.info(f"配置已保存到: {save_path}")
        except Exception as e:
            self.logger.error(f"保存配置失败: {e}")
            raise
    
    def reload_config(self):
        """重新加载配置"""
        self._load_config()
    
    def validate_config(self) -> bool:
        """验证配置"""
        required_keys = [
            "llm.api_key",
            "llm.model"
        ]
        
        for key in required_keys:
            if self.get(key) is None:
                self.logger.error(f"缺少必需的配置项: {key}")
                return False
        
        return True
    
    def get_api_keys(self) -> Dict[str, Any]:
        """获取API密钥配置"""
        api_keys_path = Path("config/api_keys.json")
        if api_keys_path.exists():
            try:
                with open(api_keys_path, 'r', encoding='utf-8') as f:
                    return json.load(f)
            except Exception as e:
                self.logger.error(f"加载API密钥配置失败: {e}")
        
        return {}
    
    def save_api_keys(self, api_keys: Dict[str, Any]):
        """保存API密钥配置"""
        api_keys_path = Path("config/api_keys.json")
        try:
            api_keys_path.parent.mkdir(parents=True, exist_ok=True)
            with open(api_keys_path, 'w', encoding='utf-8') as f:
                json.dump(api_keys, f, ensure_ascii=False, indent=2)
            self.logger.info("API密钥配置已保存")
        except Exception as e:
            self.logger.error(f"保存API密钥配置失败: {e}")
            raise
    
    @staticmethod
    def get_user_config_dir() -> Path:
        """获取用户配置目录（静态方法，不触发配置文件加载）"""
        if os.name == 'nt':  # Windows
            config_dir = Path.home() / "AppData" / "Local" / "AnkiCardAssistant"
        elif os.name == 'posix':  # macOS/Linux
            config_dir = Path.home() / ".config" / "ankicardassistant"
        else:
            config_dir = Path.home() / ".ankicardassistant"
        
        config_dir.mkdir(parents=True, exist_ok=True)
        return config_dir
    
    @staticmethod
    def get_user_data_dir() -> Path:
        """获取用户数据目录（静态方法，不触发配置文件加载）"""
        if os.name == 'nt':  # Windows
            data_dir = Path.home() / "AppData" / "Local" / "AnkiCardAssistant" / "data"
        elif os.name == 'posix':  # macOS/Linux
            data_dir = Path.home() / ".local" / "share" / "ankicardassistant"
        else:
            data_dir = Path.home() / ".ankicardassistant" / "data"
        
        data_dir.mkdir(parents=True, exist_ok=True)
        return data_dir
