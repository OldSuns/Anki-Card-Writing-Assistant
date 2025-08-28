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
from ..templates.template_manager import TemplateManager, AnkiTemplate

class GenAnkiExporter:
    """使用genanki的Anki导出器"""
    
    def __init__(self, output_dir: str = "output", template_manager: TemplateManager = None):
        self.output_dir = Path(output_dir)
        self.output_dir.mkdir(exist_ok=True)
        self.logger = logging.getLogger(__name__)
        self.template_manager = template_manager
        
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
            ,
            model_type=Model.CLOZE
        )

    def _create_model_from_template(self, template: AnkiTemplate, model_name: str) -> Model:
        """根据模板创建genanki模型"""
        fields = [{'name': f.name} for f in (template.fields or [])]
        # 如果模板未声明字段，至少提供 Front/Back 兜底
        if not fields:
            fields = [{'name': 'Front'}, {'name': 'Back'}]
        model_type = Model.CLOZE if template.is_cloze_template() else Model.FRONT_BACK
        return Model(
            model_id=self._get_model_id(model_name),
            name=model_name,
            fields=fields,
            templates=[
                {
                    'name': 'Card 1',
                    'qfmt': template.front_template or '{{Front}}',
                    'afmt': template.back_template or '{{FrontSide}}\n\n<hr id=answer>\n\n{{Back}}',
                }
            ],
            css=template.css or "",
            model_type=model_type
        )
    
    def _get_model(self, model_name: str) -> Model:
        """根据模型名称获取对应的genanki模型"""
        # 优先使用模板管理器的模板
        try:
            if self.template_manager is not None:
                tpl = self.template_manager.get_template(model_name)
                if tpl:
                    return self._create_model_from_template(tpl, model_name)
        except Exception as e:
            self.logger.warning(f"根据模板创建模型失败，使用内置模型兜底: {e}")

        # 根据模型名称选择内置模型
        if "cloze" in model_name.lower():
            return self._create_cloze_model(model_name)
        else:
            return self._create_basic_model(model_name)
    
    def _create_note(self, card: CardData, model: Model) -> Note:
        """根据卡片数据创建genanki笔记"""
        # 若模板存在则按模板字段顺序组装
        template = None
        if self.template_manager is not None:
            template = self.template_manager.get_template(card.model)

        def convert_newlines_to_html(text: str) -> str:
            """将换行符转换为HTML的<br>标签"""
            return text.replace('\n', '<br>') if text else ""

        if template and template.fields:
            field_values = []
            for f in template.fields:
                # 常见字段名兜底映射
                default_val = card.front if f.name in ("Front", "Text", "Content") else card.back if f.name in ("Back", "Back Extra") else ""
                field_value = card.fields.get(f.name, default_val)
                # 转换换行符为HTML标签
                field_values.append(convert_newlines_to_html(field_value))
            return Note(model=model, fields=field_values, tags=card.tags)

        # 无模板时按模型类型兜底
        is_cloze = "cloze" in card.model.lower()
        if is_cloze:
            fields = [
                convert_newlines_to_html(card.fields.get('Text', card.front)),
                convert_newlines_to_html(card.fields.get('Back Extra', card.back))
            ]
        else:
            fields = [
                convert_newlines_to_html(card.fields.get('Front', card.front)),
                convert_newlines_to_html(card.fields.get('Back', card.back))
            ]
        
        return Note(model=model, fields=fields, tags=card.tags)
    
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
                deck_cards.setdefault(card.deck, []).append(card)
            
            # 创建牌组和笔记
            decks = []
            models = []
            
            for deck_name, deck_card_list in deck_cards.items():
                # 按模型分组
                model_cards = {}
                for card in deck_card_list:
                    model_cards.setdefault(card.model, []).append(card)
                
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
            
            # 创建包并写入文件
            package = Package(decks)
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
            
            # 读取模板文件
            css_content = self._read_template_file(template_dir / "quizify.css")
            front_template = self._read_template_file(template_dir / "front1.html")
            back_template = self._read_template_file(template_dir / "back1.html")
            
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
                # 转换换行符为HTML标签
                front_content = self._convert_newlines(card.front)
                back_content = self._convert_newlines(card.back)
                
                note = Note(
                    model=custom_model,
                    fields=[front_content, back_content],
                    tags=card.tags
                )
                deck.add_note(note)
            
            # 创建包并写入文件
            package = Package([deck])
            package.write_to_file(str(output_path))
            
            self.logger.info(f"已使用自定义模板导出 {len(cards)} 张卡片到: {output_path}")
            return str(output_path)
            
        except Exception as e:
            self.logger.error(f"使用自定义模板导出失败: {e}")
            raise
    
    def _read_template_file(self, file_path: Path) -> str:
        """读取模板文件内容"""
        if file_path.exists():
            with open(file_path, 'r', encoding='utf-8') as f:
                return f.read()
        return ""
    
    def _convert_newlines(self, text: str) -> str:
        """将换行符转换为HTML的<br>标签"""
        return text.replace('\n', '<br>') if text else ""

    # 为命名一致性提供别名，便于上层统一调用
    def export_to_apkg_with_custom_template(self, cards: List[CardData], 
                                            template_path: str,
                                            filename: str = None) -> str:
        return self.export_with_custom_template(cards, template_path, filename)