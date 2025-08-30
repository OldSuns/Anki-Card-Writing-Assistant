"""
卡片生成器模块
负责根据模板和LLM生成内容创建Anki卡片
"""

import logging
import re
from typing import Dict, List, Optional, Any
from dataclasses import dataclass

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

    def to_dict(self) -> Dict[str, Any]:
        """将卡片数据转换为可JSON序列化的字典"""
        return {
            "front": self.front,
            "back": self.back,
            "deck": self.deck,
            "tags": list(self.tags) if isinstance(self.tags, (list, tuple)) else [],
            "model": self.model,
            "fields": dict(self.fields) if isinstance(self.fields, dict) else {},
            "cloze_data": self.cloze_data
        }


@dataclass
class GenerationConfig:
    """生成配置"""
    template_name: str
    prompt_type: str
    temperature: float = 0.7
    max_tokens: int = 20000
    card_count: int = 1
    custom_deck_name: Optional[str] = None
    difficulty: str = "medium"  # 添加难度参数：easy, medium, hard


class CardGenerationHelper:
    """卡片生成辅助类"""
    
    # 难度映射
    DIFFICULTY_MAP = {
        "easy": "简单",
        "medium": "中等", 
        "hard": "困难"
    }
    
    @staticmethod
    def get_effective_prompt_type(config: GenerationConfig) -> str:
        """获取有效的提示词类型"""
        if (config.template_name == "Quizify Enhanced Cloze" and
                config.prompt_type == "cloze"):
            return "enhanced_cloze"
        return config.prompt_type
    
    @staticmethod
    def build_prompt(base_prompt: str, content: str, config: GenerationConfig) -> str:
        """构建完整提示词"""
        difficulty_text = CardGenerationHelper.DIFFICULTY_MAP.get(config.difficulty, "中等")

        prompt_parts = [
            base_prompt,
            f"\n\n内容：\n{content}",
            "\n\n要求：",
            f"- 生成 {config.card_count} 张卡片",
            f"- 难度级别：{difficulty_text}",
            f"- 使用模板：{config.template_name}"
        ]

        # 如果用户指定了deck名称，添加到提示词中
        if config.custom_deck_name:
            prompt_parts.append(f"- 牌组名称：{config.custom_deck_name}")

        return "\n".join(prompt_parts)
    
    @staticmethod
    def get_standard_card_schema() -> Dict:
        """获取标准卡片输出结构"""
        return {
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
    
    @staticmethod
    def get_cloze_card_schema() -> Dict:
        """获取填空卡片输出结构"""
        return {
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
                        "required": ["content", "tags", "deck"]
                    }
                }
            },
            "required": ["cards"]
        }


class CardFieldBuilder:
    """卡片字段构建器"""
    
    @staticmethod
    def build_fields(template, cloze_content: str, card_data: Dict, deck_name: str) -> Dict[str, str]:
        """构建卡片字段"""
        template_name = getattr(template, 'name', '')
        is_cloze = getattr(template, 'is_cloze', False)
        is_quizify = template_name == 'Quizify'
        
        tags_str = " ".join(card_data.get("tags", []))
        
        if is_cloze:
            return CardFieldBuilder._build_cloze_fields(template_name, cloze_content, card_data, deck_name, tags_str)
        elif is_quizify:
            return CardFieldBuilder._build_quizify_fields(cloze_content, card_data, deck_name, tags_str)
        else:
            return CardFieldBuilder._build_standard_fields(cloze_content, deck_name, tags_str)
    
    @staticmethod
    def _build_cloze_fields(template_name: str, content: str, card_data: Dict, deck_name: str, tags_str: str) -> Dict[str, str]:
        """构建填空卡片字段"""
        if template_name == "Quizify Enhanced Cloze":
            return {
                "Content": content,
                "Back Extra": card_data.get("back", ""),
                "Deck": deck_name,
                "Tags": tags_str,
                "Cloze99": ""  # AnkiDroid兼容字段
            }
        else:
            return {
                "Text": content,
                "Back Extra": card_data.get("back", ""),
                "Deck": deck_name,
                "Tags": tags_str
            }
    
    @staticmethod
    def _build_quizify_fields(content: str, card_data: Dict, deck_name: str, tags_str: str) -> Dict[str, str]:
        """构建Quizify模板字段"""
        return {
            "Front": content,
            "Back": card_data.get("back", ""),
            "Deck": deck_name,
            "Tags": tags_str
        }
    
    @staticmethod
    def _build_standard_fields(content: str, deck_name: str, tags_str: str) -> Dict[str, str]:
        """构建标准字段"""
        return {
            "Front": content,
            "Back": content,
            "Deck": deck_name,
            "Tags": tags_str
        }


class ClozeProcessor:
    """填空处理器"""
    
    @staticmethod
    def process_cloze_content(content: str, clozes: List[Dict]) -> str:
        """处理填空内容，将文本转换为Anki填空格式"""
        if not clozes:
            return content
            
        processed_content = content
        # 按位置排序填空，从后往前处理避免位置偏移
        sorted_clozes = sorted(clozes, key=lambda x: x.get("position", 0), reverse=True)

        for cloze in sorted_clozes:
            text = cloze["text"]
            cloze_id = cloze["id"]
            hint = cloze.get("hint", "")

            # 构建填空格式
            cloze_format = f"{{{{c{cloze_id}::{text}::{hint}}}}}" if hint else f"{{{{c{cloze_id}::{text}}}}}"
            # 替换文本
            processed_content = processed_content.replace(text, cloze_format, 1)

        return processed_content
    
    @staticmethod
    def validate_cloze_format(content: str) -> bool:
        """验证填空格式：支持增强填空 {{...}} 和更多内容块"""
        # 增强填空基本占位
        if re.search(r'\{\{[^{}]+\}\}', content):
            return True
        # 更多内容块
        if '[[更多内容::' in content:
            return True
        return False


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

            # 根据模板名称确定提示词类型
            effective_prompt_type = CardGenerationHelper.get_effective_prompt_type(config)

            # 获取提示词
            prompt = self.prompt_manager.get_prompt(
                effective_prompt_type,
                template_name=template.name
            )

            # 构建完整提示词
            full_prompt = CardGenerationHelper.build_prompt(prompt, content, config)

            # 根据提示词类型选择生成方法
            if effective_prompt_type in ['cloze', 'enhanced_cloze']:
                cards = await self._generate_cloze_cards(full_prompt, template, config)
            else:
                cards = await self._generate_standard_cards(full_prompt, template, config)

            self.logger.info("成功生成 %d 张卡片", len(cards))
            return cards

        except Exception as e:
            self.logger.error("生成卡片失败: %s", e)
            raise

    async def _generate_standard_cards(self, prompt: str, template, config: GenerationConfig) -> List[CardData]:
        """生成标准卡片"""
        schema = CardGenerationHelper.get_standard_card_schema()

        # 生成结构化内容
        response = await self.llm_manager.generate_structured(
            prompt, schema,
            temperature=config.temperature,
            max_tokens=config.max_tokens
        )

        # 转换为CardData对象
        cards = []
        for card_data in response.get("cards", []):
            deck_name = config.custom_deck_name or card_data["deck"]
            
            card = CardData(
                front=card_data["front"],
                back=card_data["back"],
                deck=deck_name,
                tags=card_data["tags"],
                model=template.name,
                fields={
                    "Front": card_data["front"],
                    "Back": card_data["back"],
                    "Deck": deck_name,
                    "Tags": " ".join(card_data["tags"])
                }
            )
            cards.append(card)

        return cards

    async def _generate_cloze_cards(self, prompt: str, template, config: GenerationConfig) -> List[CardData]:
        """生成填空卡片（兼容增强填空 {{ }} / 注释 / 更多内容 格式，以及旧式 clozes 数组）"""
        schema = CardGenerationHelper.get_cloze_card_schema()

        # 生成结构化内容
        response = await self.llm_manager.generate_structured(
            prompt, schema,
            temperature=config.temperature,
            max_tokens=config.max_tokens
        )

        # 转换为CardData对象
        cards = []
        for card_data in response.get("cards", []):
            card = self._create_cloze_card(card_data, template, config)
            cards.append(card)

        return cards

    def _create_cloze_card(self, card_data: Dict, template, config: GenerationConfig) -> CardData:
        """创建填空卡片"""
        content = card_data["content"]
        clozes = card_data.get("clozes")

        # 处理填空内容
        if clozes:
            cloze_content = ClozeProcessor.process_cloze_content(content, clozes)
            cloze_meta = {"clozes": clozes, "original_content": content}
        else:
            cloze_content = content
            cloze_meta = None

        # 使用用户指定的deck名称或AI生成的名称
        deck_name = config.custom_deck_name or card_data["deck"]

        # 构建字段
        fields = CardFieldBuilder.build_fields(template, cloze_content, card_data, deck_name)

        # 确定front和back内容
        template_name = getattr(template, 'name', '')
        is_quizify = template_name == 'Quizify'
        is_cloze = getattr(template, 'is_cloze', False)
        
        front_content = cloze_content
        back_content = "" if is_quizify and not is_cloze else cloze_content

        return CardData(
            front=front_content,
            back=back_content,
            deck=deck_name,
            tags=card_data["tags"],
            model=template.name,
            fields=fields,
            cloze_data=cloze_meta
        )

    def validate_card(self, card: CardData) -> bool:
        """验证卡片数据"""
        if not card.front or not card.back:
            return False

        if not card.deck:
            return False

        # 检查填空格式（如果是填空卡片）
        if card.cloze_data and not ClozeProcessor.validate_cloze_format(card.front):
            return False

        return True

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


class ContentSplitter:
    """内容分割器"""
    
    @staticmethod
    def split_text_content(content: str) -> List[str]:
        """分割文本内容"""
        paragraphs = content.split('\n\n')
        return [p.strip() for p in paragraphs if p.strip()]
    
    @staticmethod
    def split_markdown_content(content: str) -> List[str]:
        """分割Markdown内容"""
        sections = re.split(r'^#{1,6}\s+', content, flags=re.MULTILINE)
        return [s.strip() for s in sections if s.strip()]


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
                self.logger.info("处理第 %d/%d 个内容", i + 1, len(contents))
                cards = await self.card_generator.generate_cards(content, config)

                # 验证返回的是卡片对象列表
                if cards and not isinstance(cards[0], CardData):
                    self.logger.error(
                        "card_generator.generate_cards 返回的不是卡片对象列表，而是: %s",
                        type(cards[0])
                    )
                    continue

                all_cards.extend(cards)
            except Exception as e:
                self.logger.error("处理第 %d 个内容失败: %s", i + 1, e)
                continue

        self.logger.info("批量生成完成，共生成 %d 张卡片", len(all_cards))
        return all_cards

    async def generate_from_file(self, file_path: str, config: GenerationConfig) -> List[CardData]:
        """从文件生成卡片"""
        try:
            with open(file_path, 'r', encoding='utf-8') as f:
                content = f.read()

            # 根据文件类型分割内容
            if file_path.endswith('.txt'):
                contents = ContentSplitter.split_text_content(content)
            elif file_path.endswith('.md'):
                contents = ContentSplitter.split_markdown_content(content)
            else:
                contents = [content]

            # 生成卡片
            cards = await self.generate_batch(contents, config)

            # 验证返回的是卡片对象列表
            if cards and not isinstance(cards[0], CardData):
                self.logger.error(
                    "generate_batch 返回的不是卡片对象列表，而是: %s",
                    type(cards[0])
                )
                raise ValueError(f"generate_batch 返回了错误的数据类型: {type(cards[0])}")

            return cards

        except (FileNotFoundError, PermissionError) as e:
            self.logger.error("文件访问失败: %s", e)
            raise
        except Exception as e:
            self.logger.error("从文件生成卡片失败: %s", e)
            raise
