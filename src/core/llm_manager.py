"""LLM客户端管理模块"""

import logging
from typing import Dict, Optional, Any
from src.core.llm_client import LLMManager, LLMConfig


class LLMClientManager:
    """LLM客户端管理器"""
    
    def __init__(self):
        self.llm_manager = LLMManager()
        self.logger = logging.getLogger(__name__)
        self._current_config = None
    
    def load_from_config(self, llm_config: Dict[str, Any]) -> bool:
        """从配置字典加载LLM客户端"""
        try:
            api_key = llm_config.get("api_key", "")
            
            # 检查API密钥是否已配置
            if not api_key or not api_key.strip():
                self.logger.info("API密钥未配置，请在Web界面中设置")
                return False
            
            config = LLMConfig(
                api_key=api_key,
                model=llm_config.get("model"),
                base_url=llm_config.get("base_url"),
                temperature=llm_config.get("temperature"),
                max_tokens=llm_config.get("max_tokens"),
                timeout=llm_config.get("timeout")
            )
            
            self.llm_manager.set_client(config)
            self._current_config = config
            
            self.logger.info(
                "已设置LLM客户端: %s (%s)",
                config.base_url,
                config.model
            )
            return True
            
        except Exception as e:
            self.logger.error("加载LLM客户端失败: %s", e)
            return False
    
    def update_config(self, llm_settings: Dict[str, Any]) -> bool:
        """更新LLM配置"""
        try:
            # 如果提供了API密钥，重新设置LLM客户端
            if llm_settings.get("api_key"):
                # 合并当前配置和新设置
                merged_config = self._merge_config(llm_settings)
                
                config = LLMConfig(
                    api_key=merged_config["api_key"],
                    model=merged_config.get("model"),
                    base_url=merged_config.get("base_url"),
                    temperature=merged_config.get("temperature"),
                    max_tokens=merged_config.get("max_tokens"),
                    timeout=merged_config.get("timeout")
                )
                
                self.llm_manager.set_client(config)
                self._current_config = config
                
                self.logger.info(
                    "已更新LLM客户端: %s (%s)",
                    config.base_url,
                    config.model
                )
            
            return True
            
        except Exception as e:
            self.logger.error("更新LLM配置失败: %s", e)
            return False
    
    def _merge_config(self, new_settings: Dict[str, Any]) -> Dict[str, Any]:
        """合并配置"""
        if self._current_config:
            merged = {
                "api_key": self._current_config.api_key,
                "model": self._current_config.model,
                "base_url": self._current_config.base_url,
                "temperature": self._current_config.temperature,
                "max_tokens": self._current_config.max_tokens,
                "timeout": self._current_config.timeout
            }
        else:
            merged = {}
        
        # 更新新设置
        merged.update(new_settings)
        return merged
    
    def get_client_info(self) -> list:
        """获取客户端信息"""
        if self.llm_manager.client and self._current_config:
            return [
                f"{self._current_config.base_url} "
                f"({self._current_config.model})"
            ]
        return []
    
    @property
    def client(self):
        """获取LLM客户端"""
        return self.llm_manager