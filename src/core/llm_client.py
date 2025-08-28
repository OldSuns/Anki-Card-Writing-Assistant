"""
大语言模型API客户端模块
使用OpenAI兼容接口统一接入各种LLM服务
"""

import json
import logging
from typing import Dict, List, Optional, Any
import openai
from dataclasses import dataclass

@dataclass
class LLMConfig:
    """LLM配置类"""
    api_key: str
    model: str
    base_url: str
    temperature: float = 0.7
    max_tokens: int = 2000
    timeout: int = 30

class LLMClient:
    """统一的LLM客户端（使用OpenAI兼容接口）"""
    
    def __init__(self, config: LLMConfig):
        self.config = config
        self.logger = logging.getLogger(__name__)
        self.client = openai.AsyncOpenAI(
            api_key=config.api_key,
            base_url=config.base_url
        )
    
    async def generate_text(self, prompt: str, **kwargs) -> str:
        """生成文本"""
        try:
            response = await self.client.chat.completions.create(
                model=self.config.model,
                messages=[{"role": "user", "content": prompt}],
                temperature=kwargs.get('temperature', self.config.temperature),
                max_tokens=kwargs.get('max_tokens', self.config.max_tokens),
                timeout=kwargs.get('timeout', self.config.timeout)
            )
            return response.choices[0].message.content
        except Exception as e:
            self.logger.error(f"LLM API调用失败: {e}")
            raise
    
    async def generate_structured(self, prompt: str, schema: Dict, **kwargs) -> Dict:
        """生成结构化数据"""
        try:
            response = await self.client.chat.completions.create(
                model=self.config.model,
                messages=[{"role": "user", "content": prompt}],
                response_format={"type": "json_object"},
                temperature=kwargs.get('temperature', self.config.temperature),
                max_tokens=kwargs.get('max_tokens', self.config.max_tokens),
                timeout=kwargs.get('timeout', self.config.timeout)
            )
            return json.loads(response.choices[0].message.content)
        except Exception as e:
            self.logger.error(f"LLM结构化生成失败: {e}")
            raise

class LLMManager:
    """LLM管理器"""
    
    def __init__(self):
        self.client: Optional[LLMClient] = None
        self.logger = logging.getLogger(__name__)
    
    def set_client(self, config: LLMConfig):
        """设置LLM客户端"""
        self.client = LLMClient(config)
        self.logger.info(f"设置LLM客户端: {config.base_url} ({config.model})")
    
    def get_client(self) -> LLMClient:
        """获取LLM客户端"""
        if not self.client:
            raise ValueError("LLM客户端未设置，请先配置API密钥")
        return self.client
    
    async def generate_text(self, prompt: str, **kwargs) -> str:
        """生成文本"""
        client = self.get_client()
        return await client.generate_text(prompt, **kwargs)
    
    async def generate_structured(self, prompt: str, schema: Dict, **kwargs) -> Dict:
        """生成结构化数据"""
        client = self.get_client()
        return await client.generate_structured(prompt, schema, **kwargs)
