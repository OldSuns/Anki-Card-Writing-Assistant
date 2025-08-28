"""
GenAnki导出器模块
使用genanki库生成.apkg文件
"""

import logging
import hashlib
from pathlib import Path
from typing import Dict, List, Optional, Any
from datetime import datetime

import genanki
from genanki import Model, Deck, Note, Package

from .card_generator import CardData

class GenAnkiExporter:
    """使用genanki的Anki导出器"""
    
    def __init__(self, output_dir: str = "output"):
        self.output_dir = Path(output_dir)
        self.output_dir.mkdir(exist_ok=True)
        self.logger = logging.getLogger(__name__)
        
        # 预定义的模型ID
        self.model_ids = {
            "basic": 1607392319,
            "basic_reversed": 1607392320,
            "cloze": 1607392321,
            "enhanced_cloze": 1607392322
        }
        
        # 预定义的牌组ID
        self.deck_ids = {}
    
    def _get_model_id(self, model_name: str) -> int:
        """获取模型ID"""
        if model_name in self.model_ids:
            return self.model_ids[model_name]
        
        hash_obj = hashlib.md5(model_name.encode())
        return int(hash_obj.hexdigest()[:8], 16)
    
    def _get_deck_id(self, deck_name: str) -> int:
        """获取牌组ID"""
        if deck_name not in self.deck_ids:
            hash_obj = hashlib.md5(deck_name.encode())
            self.deck_ids[deck_name] = int(hash_obj.hexdigest()[:8], 16)
        return self.deck_ids[deck_name]
    
    def _create_basic_model(self, model_name: str = "Basic") -> Model:
        """创建基础模型"""
        return Model(
            model_id=self._get_model_id(model_name),
            name=model_name,
            fields=[
                {'name': 'Front'},
                {'name': 'Back'},
            ],
            templates=[
                {
                    'name': '卡片 1',
                    'qfmt': '{{Front}}',
                    'afmt': '{{FrontSide}}\n\n<hr id=answer>\n\n{{Back}}',
                }
            ],
            css="""
            .card {
                font-family: arial;
                font-size: 20px;
                text-align: center;
                color: black;
                background-color: white;
            }
            """
        )
    
    def _create_cloze_model(self, model_name: str = "Cloze") -> Model:
        """创建填空题模型"""
        return Model(
            model_id=self._get_model_id(model_name),
            name=model_name,
            fields=[
                {'name': 'Text'},
                {'name': 'Back Extra'},
            ],
            templates=[
                {
                    'name': 'Cloze',
                    'qfmt': '{{cloze:Text}}',
                    'afmt': '{{cloze:Text}}<br>{{Back Extra}}',
                }
            ],
            css="""
            .card {
                font-family: arial;
                font-size: 20px;
                text-align: center;
                color: black;
                background-color: white;
            }
            .cloze {
                font-weight: bold;
                color: blue;
            }
            """
        )
    
    def _get_model(self, model_name: str) -> Model:
        """根据模型名称获取对应的genanki模型"""
        model_name_lower = model_name.lower()
        
        if "cloze" in model_name_lower:
            return self._create_cloze_model(model_name)
        else:
            return self._create_basic_model(model_name)
    
    def _create_note(self, card: CardData, model: Model) -> Note:
        """根据卡片数据创建genanki笔记"""
        if card.model.lower().find("cloze") != -1:
            return Note(
                model=model,
                fields=[
                    card.fields.get('Text', card.front),
                    card.fields.get('Back Extra', card.back)
                ],
                tags=card.tags
            )
        else:
            return Note(
                model=model,
                fields=[
                    card.fields.get('Front', card.front),
                    card.fields.get('Back', card.back)
                ],
                tags=card.tags
            )
    
    def export_to_apkg(self, cards: List[CardData], filename: str = None) -> str:
        """导出为.apkg格式"""
        if not filename:
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            filename = f"anki_cards_{timestamp}.apkg"
        
        output_path = self.output_dir / filename
        
        try:
            # 按牌组分组卡片
            deck_cards = {}
            for card in cards:
                if card.deck not in deck_cards:
                    deck_cards[card.deck] = []
                deck_cards[card.deck].append(card)
            
            # 创建牌组和笔记
            decks = []
            models = []
            
            for deck_name, deck_card_list in deck_cards.items():
                # 按模型分组
                model_cards = {}
                for card in deck_card_list:
                    if card.model not in model_cards:
                        model_cards[card.model] = []
                    model_cards[card.model].append(card)
                
                # 为每个模型创建笔记
                all_notes = []
                for model_name, model_card_list in model_cards.items():
                    model = self._get_model(model_name)
                    models.append(model)
                    
                    for card in model_card_list:
                        note = self._create_note(card, model)
                        all_notes.append(note)
                
                # 创建牌组
                deck = Deck(
                    deck_id=self._get_deck_id(deck_name),
                    name=deck_name,
                    description=f"由Anki写卡助手生成 - {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}"
                )
                
                for note in all_notes:
                    deck.add_note(note)
                
                decks.append(deck)
            
            # 创建包
            package = Package(decks)
            
            # 写入文件
            package.write_to_file(str(output_path))
            
            self.logger.info(f"已导出 {len(cards)} 张卡片到: {output_path}")
            return str(output_path)
            
        except Exception as e:
            self.logger.error(f"导出apkg文件失败: {e}")
            raise
    
    def export_with_custom_template(self, cards: List[CardData], 
                                   template_path: str,
                                   filename: str = None) -> str:
        """使用自定义模板导出"""
        if not filename:
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            filename = f"anki_cards_custom_{timestamp}.apkg"
        
        output_path = self.output_dir / filename
        
        try:
            # 读取自定义模板
            template_dir = Path(template_path)
            if not template_dir.exists():
                raise ValueError(f"模板路径不存在: {template_path}")
            
            # 读取CSS文件
            css_file = template_dir / "quizify.css"
            css_content = ""
            if css_file.exists():
                with open(css_file, 'r', encoding='utf-8') as f:
                    css_content = f.read()
            
            # 读取HTML模板
            front_template = ""
            back_template = ""
            
            front_file = template_dir / "front1.html"
            if front_file.exists():
                with open(front_file, 'r', encoding='utf-8') as f:
                    front_template = f.read()
            
            back_file = template_dir / "back1.html"
            if back_file.exists():
                with open(back_file, 'r', encoding='utf-8') as f:
                    back_template = f.read()
            
            # 创建自定义模型
            custom_model = Model(
                model_id=self._get_model_id("Custom Template"),
                name="Custom Template",
                fields=[
                    {'name': 'Front'},
                    {'name': 'Back'},
                ],
                templates=[
                    {
                        'name': 'Custom Card',
                        'qfmt': front_template,
                        'afmt': back_template,
                    }
                ],
                css=css_content
            )
            
            # 创建牌组
            deck = Deck(
                deck_id=self._get_deck_id("Custom Deck"),
                name="Custom Template Deck",
                description=f"使用自定义模板生成 - {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}"
            )
            
            # 添加笔记
            for card in cards:
                note = Note(
                    model=custom_model,
                    fields=[card.front, card.back],
                    tags=card.tags
                )
                deck.add_note(note)
            
            # 创建包
            package = Package([deck])
            package.write_to_file(str(output_path))
            
            self.logger.info(f"已使用自定义模板导出 {len(cards)} 张卡片到: {output_path}")
            return str(output_path)
            
        except Exception as e:
            self.logger.error(f"使用自定义模板导出失败: {e}")
            raise
