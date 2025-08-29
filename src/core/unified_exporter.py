"""
统一导出器模块
合并AnkiExporter和GenAnkiExporter的功能，提供统一的导出接口
"""

import json
import csv
import logging
import hashlib
from typing import Dict, List, Optional, Any
from pathlib import Path
from datetime import datetime


import genanki
from genanki import Model, Deck, Note, Package

from .card_generator import CardData
from ..templates.template_manager import TemplateManager, AnkiTemplate

class UnifiedExporter:
    """统一的Anki导出器，支持多种格式"""
    
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
            "quizify_enhanced_cloze": 1607392322
        }
        
        # 预定义的牌组ID
        self.deck_ids = {}
    
    def _normalize_newlines_for_anki(self, text: Any) -> str:
        """将内容中的换行统一为适合Anki渲染的HTML换行。
        处理场景：
        - 字面量 "\n"（反斜杠+n）未被渲染为换行
        - 实际换行符需要在HTML中显示
        策略：统一替换为 <br>。
        """
        if text is None:
            return ""
        s = str(text)
        # 归一化平台换行
        s = s.replace("\r\n", "\n").replace("\r", "\n")
        # 先将字面量 \n 转为统一占位换行
        # 注意：\\n 表示文本里真的包含反斜杠+n
        if "\\n" in s:
            s = s.replace("\\n", "\n")
        # 将实际换行替换为 <br>
        if "\n" in s:
            s = s.replace("\n", "<br>")
        return s

    def export_multiple_formats(self, cards: List[CardData], formats: List[str], 
                               original_content: str = None, generation_config: Dict = None) -> Dict[str, str]:
        """导出多种格式"""
        export_paths = {}
        
        # 从生成配置中获取模板名称
        template_name = None
        if generation_config and 'template_name' in generation_config:
            template_name = generation_config['template_name']
        
        for format_type in formats:
            try:
                if format_type == 'json':
                    export_paths['json'] = self.export_to_json(cards, original_content=original_content, generation_config=generation_config)
                elif format_type == 'csv':
                    export_paths['csv'] = self.export_to_csv(cards)
                elif format_type == 'apkg':
                    export_paths['apkg'] = self.export_to_apkg(cards, template_name=template_name)
                elif format_type == 'txt':
                    export_paths['txt'] = self.export_to_txt(cards)
                elif format_type == 'html':
                    export_paths['html'] = self.export_to_html(cards)
            except Exception as e:
                self.logger.error(f"导出{format_type}格式失败: {e}")
        
        return export_paths
    
    def export_to_json(self, cards: List[CardData], filename: str = None, 
                      original_content: str = None, generation_config: Dict = None) -> str:
        """导出为JSON格式"""
        if not filename:
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            filename = f"anki_cards_{timestamp}.json"
        
        output_path = self.output_dir / filename
        
        # 构建完整的导出数据，包含元数据
        export_data = {
            "metadata": {
                "timestamp": datetime.now().isoformat(),
                "card_count": len(cards),
                "deck_name": cards[0].deck if cards else "默认牌组",
                "content_preview": original_content[:200] + "..." if original_content and len(original_content) > 200 else original_content,
                "generation_config": generation_config or {}
            },
            "cards": []
        }
        
        # 转换为Anki导入格式
        for card in cards:
            anki_card = {
                "modelName": card.model,
                "fields": card.fields,
                "tags": card.tags,
                "deckName": card.deck,
                "options": {
                    "closeAfterAdding": True,
                    "closeAfterAddingNote": True
                }
            }
            export_data["cards"].append(anki_card)
        
        # 写入JSON文件
        with open(output_path, 'w', encoding='utf-8') as f:
            json.dump(export_data, f, ensure_ascii=False, indent=2)
        
        self.logger.info(f"已导出 {len(cards)} 张卡片到: {output_path}")
        return str(output_path)
    
    def export_to_csv(self, cards: List[CardData], filename: str = None) -> str:
        """导出为CSV格式"""
        if not filename:
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            filename = f"anki_cards_{timestamp}.csv"
        
        output_path = self.output_dir / filename
        
        # 获取所有字段名
        all_fields = set()
        for card in cards:
            all_fields.update(card.fields.keys())
        
        field_names = sorted(list(all_fields))
        
        # 写入CSV文件
        with open(output_path, 'w', newline='', encoding='utf-8') as f:
            writer = csv.writer(f)
            
            # 写入表头
            writer.writerow(['#separator:tab', '#html:true', '#tags column:4'])
            
            # 写入字段名
            writer.writerow(field_names)
            
            # 写入卡片数据
            for card in cards:
                row = [card.fields.get(field, '') for field in field_names]
                writer.writerow(row)
        
        self.logger.info(f"已导出 {len(cards)} 张卡片到: {output_path}")
        return str(output_path)
    
    def export_to_txt(self, cards: List[CardData], filename: str = None) -> str:
        """导出为TXT格式"""
        if not filename:
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            filename = f"anki_cards_{timestamp}.txt"
        
        output_path = self.output_dir / filename
        
        with open(output_path, 'w', encoding='utf-8') as f:
            for i, card in enumerate(cards, 1):
                f.write(f"=== 卡片 {i} ===\n")
                f.write(f"牌组: {card.deck}\n")
                f.write(f"模型: {card.model}\n")
                f.write(f"标签: {', '.join(card.tags)}\n")
                f.write(f"正面: {card.fields.get('Front', card.fields.get('Text', ''))}\n")
                f.write(f"背面: {card.fields.get('Back', card.fields.get('Back Extra', ''))}\n")
                f.write("\n")
        
        self.logger.info(f"已导出 {len(cards)} 张卡片到: {output_path}")
        return str(output_path)
    
    def export_to_html(self, cards: List[CardData], filename: str = None) -> str:
        """导出为HTML格式"""
        if not filename:
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            filename = f"anki_cards_{timestamp}.html"
        
        output_path = self.output_dir / filename
        
        html_content = """
        <!DOCTYPE html>
        <html>
        <head>
            <meta charset="utf-8">
            <title>Anki卡片预览</title>
            <style>
                body { font-family: Arial, sans-serif; margin: 20px; }
                .card { border: 1px solid #ddd; margin: 10px 0; padding: 15px; border-radius: 5px; }
                .front { background-color: #f9f9f9; padding: 10px; margin-bottom: 10px; }
                .back { background-color: #e8f4f8; padding: 10px; }
                .meta { font-size: 12px; color: #666; margin-bottom: 10px; }
            </style>
        </head>
        <body>
            <h1>Anki卡片预览</h1>
        """
        
        for i, card in enumerate(cards, 1):
            front_content = card.fields.get('Front', card.fields.get('Text', ''))
            back_content = card.fields.get('Back', card.fields.get('Back Extra', ''))
            
            html_content += f"""
            <div class="card">
                <div class="meta">
                    卡片 {i} | 牌组: {card.deck} | 模型: {card.model} | 标签: {', '.join(card.tags)}
                </div>
                <div class="front">
                    <strong>正面:</strong><br>
                    {front_content}
                </div>
                <div class="back">
                    <strong>背面:</strong><br>
                    {back_content}
                </div>
            </div>
            """
        
        html_content += """
        </body>
        </html>
        """
        
        with open(output_path, 'w', encoding='utf-8') as f:
            f.write(html_content)
        
        self.logger.info(f"已导出 {len(cards)} 张卡片到: {output_path}")
        return str(output_path)
    
    def export_to_apkg(self, cards: List[CardData], filename: str = None, template_name: str = None) -> str:
        """导出为apkg格式"""
        if not filename:
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            filename = f"anki_cards_{timestamp}.apkg"
        
        output_path = self.output_dir / filename
        
        # 添加调试信息
        self.logger.info(f"开始导出apkg文件: {filename}")
        self.logger.info(f"卡片数量: {len(cards)}")
        self.logger.info(f"指定模板名称: {template_name}")
        self.logger.info(f"模板管理器可用: {self.template_manager is not None}")
        
        if self.template_manager:
            available_templates = self.template_manager.list_templates()
            self.logger.info(f"可用模板: {available_templates}")
        
        # 按牌组分组卡片
        deck_groups = {}
        for card in cards:
            if card.deck not in deck_groups:
                deck_groups[card.deck] = []
            deck_groups[card.deck].append(card)
        
        # 创建牌组和笔记
        decks = []
        for deck_name, deck_cards in deck_groups.items():
            deck = Deck(
                deck_id=self._get_deck_id(deck_name),
                name=deck_name
            )
            
            for card in deck_cards:
                # 优先使用指定的模板名称，如果没有则使用卡片的模型名称
                effective_template_name = template_name or card.model
                
                # 尝试获取模板
                if self.template_manager:
                    template = self.template_manager.get_template(effective_template_name)
                    if template:
                        # 使用模板创建模型和笔记
                        model = self._create_model_from_template(template)
                        note = self._create_note_from_template(card, model, template)
                        self.logger.debug(f"使用模板 {template.name} 创建卡片")
                    else:
                        # 模板不存在，使用默认模型
                        model = self._get_model_for_card(card)
                        note = self._create_note(card, model)
                        self.logger.debug(f"模板 {effective_template_name} 不存在，使用默认模型")
                else:
                    # 没有模板管理器，使用默认模型
                    model = self._get_model_for_card(card)
                    note = self._create_note(card, model)
                    self.logger.debug("没有模板管理器，使用默认模型")
                
                deck.add_note(note)
            
            decks.append(deck)
        
        # 创建包并导出
        package = Package(decks)
        package.write_to_file(str(output_path))
        
        self.logger.info(f"已导出 {len(cards)} 张卡片到: {output_path}")
        return str(output_path)
    
    def export_to_apkg_with_custom_template(self, cards: List[CardData], template_name: str, filename: str = None) -> str:
        """使用自定义模板导出为apkg格式"""
        if not filename:
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            filename = f"anki_cards_{timestamp}.apkg"
        
        output_path = self.output_dir / filename
        
        # 获取模板
        if not self.template_manager:
            raise ValueError("模板管理器未初始化")
        
        template = self.template_manager.get_template(template_name)
        if not template:
            raise ValueError(f"无法找到模板: {template_name}")
        
        # 按牌组分组卡片
        deck_groups = {}
        for card in cards:
            if card.deck not in deck_groups:
                deck_groups[card.deck] = []
            deck_groups[card.deck].append(card)
        
        # 创建牌组和笔记
        decks = []
        for deck_name, deck_cards in deck_groups.items():
            deck = Deck(
                deck_id=self._get_deck_id(deck_name),
                name=deck_name
            )
            
            for card in deck_cards:
                model = self._create_model_from_template(template)
                note = self._create_note_from_template(card, model, template)
                deck.add_note(note)
            
            decks.append(deck)
        
        # 创建包并导出
        package = Package(decks)
        package.write_to_file(str(output_path))
        
        self.logger.info(f"已使用自定义模板导出 {len(cards)} 张卡片到: {output_path}")
        return str(output_path)
    
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
    
    def _get_model_for_card(self, card: CardData) -> Model:
        """根据卡片获取对应的模型"""
        model_name = card.model.lower()
        
        if 'cloze' in model_name:
            return self._create_cloze_model(card.model)
        elif 'basic' in model_name:
            return self._create_basic_model(card.model)
        else:
            return self._create_basic_model(card.model)
    
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
    
    def _create_model_from_template(self, template: AnkiTemplate) -> Model:
        """从模板创建模型"""
        # 将TemplateField转换为genanki需要的格式
        fields = []
        for field in template.fields:
            fields.append({'name': field.name})
        
        # 创建模板列表
        templates = [
            {
                'name': '卡片 1',
                'qfmt': template.front_template,
                'afmt': template.back_template,
            }
        ]
        
        # 检查是否为填空模板
        is_cloze = template.is_cloze or "{{cloze:" in template.front_template
        
        model = Model(
            model_id=self._get_model_id(template.name),
            name=template.name,
            fields=fields,
            templates=templates,
            css=template.css,
            model_type=1 if is_cloze else 0  # 1表示填空模型，0表示基础模型
        )
        
        # 调试信息
        self.logger.debug(f"创建模型 {template.name}，字段数量: {len(fields)}")
        for field in fields:
            self.logger.debug(f"  字段: {field['name']}")
        
        return model
    
    def _create_note(self, card: CardData, model: Model) -> Note:
        """创建笔记"""
        # 根据模型类型创建不同的笔记
        if 'cloze' in model.name.lower():
            return Note(
                model=model,
                fields=[
                    self._normalize_newlines_for_anki(card.fields.get('Text', '')),
                    self._normalize_newlines_for_anki(card.fields.get('Back Extra', ''))
                ]
            )
        else:
            return Note(
                model=model,
                fields=[
                    self._normalize_newlines_for_anki(card.fields.get('Front', '')),
                    self._normalize_newlines_for_anki(card.fields.get('Back', ''))
                ]
            )
    
    def _create_note_from_template(self, card: CardData, model: Model, template: AnkiTemplate) -> Note:
        """从模板创建笔记"""
        # 根据模板字段创建笔记
        fields = []
        for field in template.fields:
            field_value = ""
            
            # 根据字段名获取对应的卡片数据
            if field.name == 'Front':
                field_value = card.fields.get('Front', card.front)
            elif field.name == 'Back':
                field_value = card.fields.get('Back', card.back)
            elif field.name == 'Text':
                # 对于填空模板，Text字段包含填空内容
                field_value = card.fields.get('Text', card.front)
            elif field.name == 'Content':
                # 增强填空模板的Content字段
                field_value = card.fields.get('Content', card.front)
            elif field.name == 'Back Extra':
                field_value = card.fields.get('Back Extra', card.back)
            elif field.name == 'Cloze99':
                # AnkiDroid兼容字段，通常为空
                field_value = ""
            elif field.name == 'Deck':
                field_value = card.deck
            elif field.name == 'Tags':
                field_value = ' '.join(card.tags) if isinstance(card.tags, (list, tuple)) else str(card.tags)
            else:
                # 对于其他字段，尝试从card.fields中获取
                field_value = card.fields.get(field.name, field.default_value)
            
            # 确保字段值不为None
            if field_value is None:
                field_value = field.default_value or ""
            
            # 统一处理换行，避免 "\n" 在 Anki 中不换行
            fields.append(self._normalize_newlines_for_anki(field_value))
        
        # 调试信息
        self.logger.debug(f"创建笔记，模板: {template.name}，字段数量: {len(fields)}")
        for i, (field, field_value) in enumerate(zip(template.fields, fields)):
            self.logger.debug(f"  字段 {field.name}: {field_value[:50]}{'...' if len(field_value) > 50 else ''}")
        
        return Note(model=model, fields=fields)
    
    def get_export_summary(self, cards: List[CardData]) -> Dict[str, Any]:
        """获取导出摘要"""
        if not cards:
            return {
                'total_cards': 0,
                'deck_stats': {},
                'model_stats': {}
            }
        
        # 统计牌组
        deck_stats = {}
        for card in cards:
            deck_stats[card.deck] = deck_stats.get(card.deck, 0) + 1
        
        # 统计模型
        model_stats = {}
        for card in cards:
            model_stats[card.model] = model_stats.get(card.model, 0) + 1
        
        return {
            'total_cards': len(cards),
            'deck_stats': deck_stats,
            'model_stats': model_stats
        }
