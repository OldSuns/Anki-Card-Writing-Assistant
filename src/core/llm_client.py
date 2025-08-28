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
    max_tokens: int = 20000
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
            # 最多尝试两次：首次为空则重试一次
            attempts = 2
            raw = ""
            for i in range(attempts):
                response = await self.client.chat.completions.create(
                    model=self.config.model,
                    messages=[{"role": "user", "content": prompt}],
                    response_format={"type": "json_object"},
                    temperature=kwargs.get('temperature', self.config.temperature),
                    max_tokens=kwargs.get('max_tokens', self.config.max_tokens),
                    timeout=kwargs.get('timeout', self.config.timeout)
                )
                raw = response.choices[0].message.content or ""
                if raw.strip():
                    break
                self.logger.warning("LLM返回内容为空，准备重试一次...")
            
            if not raw.strip():
                raise ValueError("LLM返回为空，无法解析为JSON。请稍后重试或减少max_tokens/降低温度。")
            
            # 尝试解析JSON
            try:
                return json.loads(raw)
            except json.JSONDecodeError as primary_err:
                # 回退：尝试从代码块或混入文本中提取纯JSON
                cleaned = self._extract_json_block(raw)
                try:
                    return json.loads(cleaned)
                except json.JSONDecodeError as secondary_err:
                    # 记录部分内容以便排查
                    preview = raw[:500].replace("\n", " ")
                    self.logger.error(
                        f"JSON解析失败，原始前500字符: {preview} | primary={primary_err} | secondary={secondary_err}"
                    )
                    # 继续抛出原始异常
                    raise primary_err
        except Exception as e:
            self.logger.error(f"LLM结构化生成失败: {e}")
            raise

    def _extract_json_block(self, text: str) -> str:
        """从文本中提取第一个完整的JSON对象字符串。
        支持去除 ```json ... ``` 或 ``` ... ``` 代码围栏，并裁剪到首个 { 与最后一个 } 之间。
        """
        if not text:
            return text
        
        s = text.strip()
        
        # 去除Markdown代码围栏
        if s.startswith("```"):
            try:
                lines = s.splitlines()
                # 去掉起始围栏行
                if lines and lines[0].startswith("```"):
                    lines = lines[1:]
                # 去掉末尾围栏
                if lines and lines[-1].strip().startswith("```"):
                    lines = lines[:-1]
                s = "\n".join(lines).strip()
            except Exception:
                pass
        
        # 裁剪到最外层花括号
        start = s.find('{')
        end = s.rfind('}')
        if start != -1 and end != -1 and end > start:
            return s[start:end+1]
        
        return s

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
