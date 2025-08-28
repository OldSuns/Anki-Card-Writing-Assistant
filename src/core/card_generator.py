"""
卡片生成器模块
负责根据模板和LLM生成内容创建Anki卡片
"""

import json
import logging
from typing import Dict, List, Optional, Any
from dataclasses import dataclass, asdict
from pathlib import Path
import re
from datetime import datetime

from .llm_client import LLMManager
from ..prompts.base_prompts import BasePromptManager
from ..templates.template_manager import TemplateManager

@dataclass
class CardData:
    """卡片数据结构"""
    front: str
    back: str
    deck: str
    tags: List[str]
    model: str
    fields: Dict[str, str]
    cloze_data: Optional[Dict] = None

@dataclass
class GenerationConfig:
    """生成配置"""
    template_name: str
    prompt_type: str
    llm_client: str
    temperature: float = 0.7
    max_tokens: int = 2000
    language: str = "zh-CN"
    difficulty: str = "medium"
    card_count: int = 1

class CardGenerator:
    """卡片生成器"""
    
    def __init__(self, llm_manager: LLMManager, 
                 template_manager: TemplateManager,
                 prompt_manager: BasePromptManager):
        self.llm_manager = llm_manager
        self.template_manager = template_manager
        self.prompt_manager = prompt_manager
        self.logger = logging.getLogger(__name__)
    
    async def generate_cards(self, content: str, config: GenerationConfig) -> List[CardData]:
        """生成卡片列表"""
        try:
            # 获取模板
            template = self.template_manager.get_template(config.template_name)
            if not template:
                raise ValueError(f"未找到模板: {config.template_name}")
            
            # 获取提示词
            prompt = self.prompt_manager.get_prompt(
                config.prompt_type,
                template=template,
                language=config.language,
                difficulty=config.difficulty
            )
            
            # 构建完整提示词
            full_prompt = self._build_prompt(prompt, content, config)
            
            # 获取LLM客户端
            llm_client = self.llm_manager
            
            # 生成卡片内容
            if template.is_cloze_template():
                cards = await self._generate_cloze_cards(
                    llm_client, full_prompt, template, config
                )
            else:
                cards = await self._generate_standard_cards(
                    llm_client, full_prompt, template, config
                )
            
            self.logger.info(f"成功生成 {len(cards)} 张卡片")
            return cards
            
        except Exception as e:
            self.logger.error(f"生成卡片失败: {e}")
            raise
    
    async def _generate_standard_cards(self, llm_client: LLMManager, 
                                     prompt: str, template, config: GenerationConfig) -> List[CardData]:
        """生成标准卡片"""
        # 定义输出结构
        schema = {
            "type": "object",
            "properties": {
                "cards": {
                    "type": "array",
                    "items": {
                        "type": "object",
                        "properties": {
                            "front": {"type": "string"},
                            "back": {"type": "string"},
                            "tags": {"type": "array", "items": {"type": "string"}},
                            "deck": {"type": "string"}
                        },
                        "required": ["front", "back", "tags", "deck"]
                    }
                }
            },
            "required": ["cards"]
        }
        
        # 生成结构化内容
        response = await llm_client.generate_structured(
            prompt, schema,
            temperature=config.temperature,
            max_tokens=config.max_tokens
        )
        
        # 转换为CardData对象
        cards = []
        for card_data in response.get("cards", []):
            card = CardData(
                front=card_data["front"],
                back=card_data["back"],
                deck=card_data["deck"],
                tags=card_data["tags"],
                model=template.name,
                fields={
                    "Front": card_data["front"],
                    "Back": card_data["back"],
                    "Deck": card_data["deck"],
                    "Tags": " ".join(card_data["tags"])
                }
            )
            cards.append(card)
        
        return cards
    
    async def _generate_cloze_cards(self, llm_client: LLMManager, 
                                  prompt: str, template, config: GenerationConfig) -> List[CardData]:
        """生成填空卡片"""
        # 定义填空卡片输出结构
        schema = {
            "type": "object",
            "properties": {
                "cards": {
                    "type": "array",
                    "items": {
                        "type": "object",
                        "properties": {
                            "content": {"type": "string"},
                            "tags": {"type": "array", "items": {"type": "string"}},
                            "deck": {"type": "string"},
                            "clozes": {
                                "type": "array",
                                "items": {
                                    "type": "object",
                                    "properties": {
                                        "id": {"type": "integer"},
                                        "text": {"type": "string"},
                                        "hint": {"type": "string"}
                                    }
                                }
                            }
                        },
                        "required": ["content", "tags", "deck", "clozes"]
                    }
                }
            },
            "required": ["cards"]
        }
        
        # 生成结构化内容
        response = await llm_client.generate_structured(
            prompt, schema,
            temperature=config.temperature,
            max_tokens=config.max_tokens
        )
        
        # 转换为CardData对象
        cards = []
        for card_data in response.get("cards", []):
            # 处理填空内容
            content = card_data["content"]
            cloze_content = self._process_cloze_content(content, card_data["clozes"])
            
            card = CardData(
                front=cloze_content,
                back=cloze_content,  # 填空卡片的背面通常与正面相同
                deck=card_data["deck"],
                tags=card_data["tags"],
                model=template.name,
                fields={
                    "Content": cloze_content,
                    "Deck": card_data["deck"],
                    "Tags": " ".join(card_data["tags"])
                },
                cloze_data={
                    "clozes": card_data["clozes"],
                    "original_content": content
                }
            )
            cards.append(card)
        
        return cards
    
    def _process_cloze_content(self, content: str, clozes: List[Dict]) -> str:
        """处理填空内容，将文本转换为Anki填空格式"""
        processed_content = content
        
        # 按位置排序填空，从后往前处理避免位置偏移
        sorted_clozes = sorted(clozes, key=lambda x: x.get("position", 0), reverse=True)
        
        for cloze in sorted_clozes:
            text = cloze["text"]
            cloze_id = cloze["id"]
            hint = cloze.get("hint", "")
            
            # 构建填空格式
            if hint:
                cloze_format = f"{{{{c{cloze_id}::{text}::{hint}}}}}"
            else:
                cloze_format = f"{{{{c{cloze_id}::{text}}}}}"
            
            # 替换文本
            processed_content = processed_content.replace(text, cloze_format, 1)
        
        return processed_content
    
    def _build_prompt(self, base_prompt: str, content: str, config: GenerationConfig) -> str:
        """构建完整提示词"""
        prompt_parts = [
            base_prompt,
            f"\n\n内容：\n{content}",
            f"\n\n要求：",
            f"- 生成 {config.card_count} 张卡片",
            f"- 语言：{config.language}",
            f"- 难度：{config.difficulty}",
            f"- 使用模板：{config.template_name}"
        ]
        
        return "\n".join(prompt_parts)
    
    def validate_card(self, card: CardData) -> bool:
        """验证卡片数据"""
        if not card.front or not card.back:
            return False
        
        if not card.deck:
            return False
        
        # 检查填空格式（如果是填空卡片）
        if card.cloze_data:
            if not self._validate_cloze_format(card.front):
                return False
        
        return True
    
    def _validate_cloze_format(self, content: str) -> bool:
        """验证填空格式"""
        # 检查是否有有效的填空格式
        cloze_pattern = r'\{\{c\d+::[^}]+\}\}'
        matches = re.findall(cloze_pattern, content)
        return len(matches) > 0
    
    def format_card_for_export(self, card: CardData) -> Dict[str, Any]:
        """格式化卡片用于导出"""
        return {
            "modelName": card.model,
            "fields": card.fields,
            "tags": card.tags,
            "deckName": card.deck,
            "options": {
                "closeAfterAdding": True,
                "closeAfterAddingNote": True
            }
        }

class BatchCardGenerator:
    """批量卡片生成器"""
    
    def __init__(self, card_generator: CardGenerator):
        self.card_generator = card_generator
        self.logger = logging.getLogger(__name__)
    
    async def generate_batch(self, contents: List[str], config: GenerationConfig) -> List[CardData]:
        """批量生成卡片"""
        all_cards = []
        
        for i, content in enumerate(contents):
            try:
                self.logger.info(f"处理第 {i+1}/{len(contents)} 个内容")
                cards = await self.card_generator.generate_cards(content, config)
                all_cards.extend(cards)
            except Exception as e:
                self.logger.error(f"处理第 {i+1} 个内容失败: {e}")
                continue
        
        self.logger.info(f"批量生成完成，共生成 {len(all_cards)} 张卡片")
        return all_cards
    
    async def generate_from_file(self, file_path: str, config: GenerationConfig) -> List[CardData]:
        """从文件生成卡片"""
        try:
            with open(file_path, 'r', encoding='utf-8') as f:
                content = f.read()
            
            # 根据文件类型分割内容
            if file_path.endswith('.txt'):
                contents = self._split_text_content(content)
            elif file_path.endswith('.md'):
                contents = self._split_markdown_content(content)
            else:
                contents = [content]
            
            return await self.generate_batch(contents, config)
            
        except Exception as e:
            self.logger.error(f"从文件生成卡片失败: {e}")
            raise
    
    def _split_text_content(self, content: str) -> List[str]:
        """分割文本内容"""
        # 按段落分割
        paragraphs = content.split('\n\n')
        return [p.strip() for p in paragraphs if p.strip()]
    
    def _split_markdown_content(self, content: str) -> List[str]:
        """分割Markdown内容"""
        # 按标题分割
        sections = re.split(r'^#{1,6}\s+', content, flags=re.MULTILINE)
        return [s.strip() for s in sections if s.strip()]
