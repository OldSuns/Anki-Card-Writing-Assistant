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


class ExportConstants:
    """导出常量"""
    
    # 预定义的模型ID
    MODEL_IDS = {
        "basic": 1607392319,
        "basic_reversed": 1607392320,
        "cloze": 1607392321,
        "quizify_enhanced_cloze": 1607392322
    }
    
    # 文件格式映射
    FORMAT_METHODS = {
        'json': 'export_to_json',
        'csv': 'export_to_csv',
        'apkg': 'export_to_apkg',
        'txt': 'export_to_txt',
        'html': 'export_to_html'
    }
    
    # HTML模板
    HTML_TEMPLATE = """<!DOCTYPE html>
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
    {content}
</body>
</html>"""

    # CSS样式
    BASIC_CSS = """
.card {
    font-family: arial;
    font-size: 20px;
    text-align: center;
    color: black;
    background-color: white;
}"""

    CLOZE_CSS = """
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
}"""


class TextProcessor:
    """文本处理器"""
    
    @staticmethod
    def normalize_newlines_for_anki(text: Any) -> str:
        """将内容中的换行统一为适合Anki渲染的HTML换行"""
        if text is None:
            return ""
        s = str(text)
        # 归一化平台换行
        s = s.replace("\r\n", "\n").replace("\r", "\n")
        # 处理字面量 \n
        if "\\n" in s:
            s = s.replace("\\n", "\n")
        # 将实际换行替换为 <br>
        if "\n" in s:
            s = s.replace("\n", "<br>")
        return s


class ModelFactory:
    """模型工厂类"""
    
    def __init__(self, logger: logging.Logger):
        self.logger = logger
        self._model_cache = {}
    
    def get_model_id(self, model_name: str) -> int:
        """获取模型ID"""
        if model_name in ExportConstants.MODEL_IDS:
            return ExportConstants.MODEL_IDS[model_name]
        
        hash_obj = hashlib.md5(model_name.encode())
        return int(hash_obj.hexdigest()[:8], 16)
    
    def create_basic_model(self, model_name: str = "Basic") -> Model:
        """创建基础模型"""
        if model_name in self._model_cache:
            return self._model_cache[model_name]
        
        model = Model(
            model_id=self.get_model_id(model_name),
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
            css=ExportConstants.BASIC_CSS
        )
        
        self._model_cache[model_name] = model
        return model
    
    def create_cloze_model(self, model_name: str = "Cloze") -> Model:
        """创建填空题模型"""
        if model_name in self._model_cache:
            return self._model_cache[model_name]
        
        model = Model(
            model_id=self.get_model_id(model_name),
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
            css=ExportConstants.CLOZE_CSS
        )
        
        self._model_cache[model_name] = model
        return model
    
    def create_model_from_template(self, template: AnkiTemplate) -> Model:
        """从模板创建模型"""
        if template.name in self._model_cache:
            return self._model_cache[template.name]
        
        # 将TemplateField转换为genanki需要的格式
        fields = [{'name': field.name} for field in template.fields]
        
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
            model_id=self.get_model_id(template.name),
            name=template.name,
            fields=fields,
            templates=templates,
            css=template.css,
            model_type=1 if is_cloze else 0  # 1表示填空模型，0表示基础模型
        )
        
        self._model_cache[template.name] = model
        self.logger.debug(f"创建模型 {template.name}，字段数量: {len(fields)}")
        
        return model
    
    def get_model_for_card(self, card: CardData) -> Model:
        """根据卡片获取对应的模型"""
        model_name = card.model.lower()
        
        if 'cloze' in model_name:
            return self.create_cloze_model(card.model)
        else:
            return self.create_basic_model(card.model)


class NoteFactory:
    """笔记工厂类"""
    
    def __init__(self, text_processor: TextProcessor, logger: logging.Logger):
        self.text_processor = text_processor
        self.logger = logger
    
    def create_note(self, card: CardData, model: Model) -> Note:
        """创建笔记"""
        if 'cloze' in model.name.lower():
            return Note(
                model=model,
                fields=[
                    self.text_processor.normalize_newlines_for_anki(card.fields.get('Text', '')),
                    self.text_processor.normalize_newlines_for_anki(card.fields.get('Back Extra', ''))
                ]
            )
        else:
            return Note(
                model=model,
                fields=[
                    self.text_processor.normalize_newlines_for_anki(card.fields.get('Front', '')),
                    self.text_processor.normalize_newlines_for_anki(card.fields.get('Back', ''))
                ]
            )
    
    def create_note_from_template(self, card: CardData, model: Model, template: AnkiTemplate) -> Note:
        """从模板创建笔记"""
        fields = []
        
        # 字段映射策略
        field_mapping = {
            'Front': lambda c: c.fields.get('Front', c.front),
            'Back': lambda c: c.fields.get('Back', c.back),
            'Text': lambda c: c.fields.get('Text', c.front),
            'Content': lambda c: c.fields.get('Content', c.front),
            'Back Extra': lambda c: c.fields.get('Back Extra', c.back),
            'Cloze99': lambda c: "",
            'Deck': lambda c: c.deck,
            'Tags': lambda c: ' '.join(c.tags) if isinstance(c.tags, (list, tuple)) else str(c.tags)
        }
        
        for field in template.fields:
            field_value = ""
            
            if field.name in field_mapping:
                field_value = field_mapping[field.name](card)
            else:
                # 对于其他字段，尝试从card.fields中获取
                field_value = card.fields.get(field.name, field.default_value)
            
            # 确保字段值不为None
            if field_value is None:
                field_value = field.default_value or ""
            
            fields.append(self.text_processor.normalize_newlines_for_anki(field_value))
        
        self.logger.debug(f"创建笔记，模板: {template.name}，字段数量: {len(fields)}")
        return Note(model=model, fields=fields)


class FileExporter:
    """文件导出器"""
    
    def __init__(self, output_dir: Path, text_processor: TextProcessor, logger: logging.Logger):
        self.output_dir = output_dir
        self.text_processor = text_processor
        self.logger = logger
    
    def export_to_json(self, cards: List[CardData], filename: str = None, 
                      original_content: str = None, generation_config: Dict = None, timestamp: str = None) -> str:
        """导出为JSON格式"""
        if filename is None:
            if timestamp:
                filename = f"anki_cards_{timestamp}.json"
            else:
                filename = f"anki_cards_{datetime.now().strftime('%Y%m%d_%H%M%S')}.json"
        output_path = self.output_dir / filename
        
        export_data = {
            "metadata": {
                "timestamp": datetime.now().isoformat(),
                "card_count": len(cards),
                "deck_name": cards[0].deck if cards else "默认牌组",
                "content_preview": self._get_content_preview(original_content),
                "generation_config": generation_config or {}
            },
            "cards": [self._format_card_for_json(card) for card in cards]
        }
        
        with open(output_path, 'w', encoding='utf-8') as f:
            json.dump(export_data, f, ensure_ascii=False, indent=2)
        
        self.logger.info(f"已导出 {len(cards)} 张卡片到: {output_path}")
        return str(output_path)
    
    def export_to_csv(self, cards: List[CardData], filename: str = None, timestamp: str = None) -> str:
        """导出为CSV格式"""
        if filename is None:
            if timestamp:
                filename = f"anki_cards_{timestamp}.csv"
            else:
                filename = f"anki_cards_{datetime.now().strftime('%Y%m%d_%H%M%S')}.csv"
        output_path = self.output_dir / filename
        
        # 获取所有字段名并排序
        all_fields = set()
        for card in cards:
            all_fields.update(card.fields.keys())
        field_names = sorted(list(all_fields))
        
        with open(output_path, 'w', newline='', encoding='utf-8') as f:
            writer = csv.writer(f)
            writer.writerow(['#separator:tab', '#html:true', '#tags column:4'])
            writer.writerow(field_names)
            
            for card in cards:
                row = [card.fields.get(field, '') for field in field_names]
                writer.writerow(row)
        
        self.logger.info(f"已导出 {len(cards)} 张卡片到: {output_path}")
        return str(output_path)
    
    def export_to_txt(self, cards: List[CardData], filename: str = None, timestamp: str = None) -> str:
        """导出为TXT格式"""
        if filename is None:
            if timestamp:
                filename = f"anki_cards_{timestamp}.txt"
            else:
                filename = f"anki_cards_{datetime.now().strftime('%Y%m%d_%H%M%S')}.txt"
        output_path = self.output_dir / filename
        
        with open(output_path, 'w', encoding='utf-8') as f:
            for i, card in enumerate(cards, 1):
                f.write(f"=== 卡片 {i} ===\n")
                f.write(f"牌组: {card.deck}\n")
                f.write(f"模型: {card.model}\n")
                f.write(f"标签: {', '.join(card.tags)}\n")
                f.write(f"正面: {card.fields.get('Front', card.fields.get('Text', ''))}\n")
                f.write(f"背面: {card.fields.get('Back', card.fields.get('Back Extra', ''))}\n\n")
        
        self.logger.info(f"已导出 {len(cards)} 张卡片到: {output_path}")
        return str(output_path)
    
    def export_to_html(self, cards: List[CardData], filename: str = None, timestamp: str = None) -> str:
        """导出为HTML格式"""
        if filename is None:
            if timestamp:
                filename = f"anki_cards_{timestamp}.html"
            else:
                filename = f"anki_cards_{datetime.now().strftime('%Y%m%d_%H%M%S')}.html"
        output_path = self.output_dir / filename
        
        card_html = []
        for i, card in enumerate(cards, 1):
            front_content = card.fields.get('Front', card.fields.get('Text', ''))
            back_content = card.fields.get('Back', card.fields.get('Back Extra', ''))
            
            card_html.append(f"""
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
            """)
        
        html_content = ExportConstants.HTML_TEMPLATE.format(content=''.join(card_html))
        
        with open(output_path, 'w', encoding='utf-8') as f:
            f.write(html_content)
        
        self.logger.info(f"已导出 {len(cards)} 张卡片到: {output_path}")
        return str(output_path)
    
    def _get_content_preview(self, original_content: str) -> str:
        """获取内容预览"""
        if not original_content:
            return None
        return original_content[:200] + "..." if len(original_content) > 200 else original_content
    
    def _format_card_for_json(self, card: CardData) -> Dict:
        """格式化卡片用于JSON导出"""
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


class UnifiedExporter:
    """统一的Anki导出器，支持多种格式"""
    
    def __init__(self, output_dir: str = "output", template_manager: TemplateManager = None):
        self.output_dir = Path(output_dir)
        self.output_dir.mkdir(exist_ok=True)
        self.logger = logging.getLogger(__name__)
        self.template_manager = template_manager
        
        # 初始化组件
        self.text_processor = TextProcessor()
        self.model_factory = ModelFactory(self.logger)
        self.note_factory = NoteFactory(self.text_processor, self.logger)
        self.file_exporter = FileExporter(self.output_dir, self.text_processor, self.logger)
        
        # 牌组ID缓存
        self.deck_ids = {}

    def export_multiple_formats(self, cards: List[CardData], formats: List[str], 
                               original_content: str = None, generation_config: Dict = None) -> Dict[str, str]:
        """导出多种格式"""
        export_paths = {}
        template_name = generation_config.get('template_name') if generation_config else None
        
        # 统一生成时间戳，确保同一批次的所有文件使用相同的时间戳
        timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
        
        for format_type in formats:
            try:
                if format_type in ExportConstants.FORMAT_METHODS:
                    method_name = ExportConstants.FORMAT_METHODS[format_type]
                    method = getattr(self, method_name)
                    
                    if format_type == 'json':
                        export_paths[format_type] = method(cards, timestamp=timestamp, original_content=original_content, generation_config=generation_config)
                    elif format_type == 'apkg':
                        export_paths[format_type] = method(cards, timestamp=timestamp, template_name=template_name)
                    else:
                        export_paths[format_type] = method(cards, timestamp=timestamp)
                        
            except Exception as e:
                self.logger.error(f"导出{format_type}格式失败: {e}")
        
        return export_paths

    def export_to_json(self, cards: List[CardData], filename: str = None, 
                      original_content: str = None, generation_config: Dict = None, timestamp: str = None) -> str:
        """导出为JSON格式"""
        return self.file_exporter.export_to_json(cards, filename, original_content, generation_config, timestamp)
    
    def export_to_csv(self, cards: List[CardData], filename: str = None, timestamp: str = None) -> str:
        """导出为CSV格式"""
        return self.file_exporter.export_to_csv(cards, filename, timestamp)
    
    def export_to_txt(self, cards: List[CardData], filename: str = None, timestamp: str = None) -> str:
        """导出为TXT格式"""
        return self.file_exporter.export_to_txt(cards, filename, timestamp)
    
    def export_to_html(self, cards: List[CardData], filename: str = None, timestamp: str = None) -> str:
        """导出为HTML格式"""
        return self.file_exporter.export_to_html(cards, filename, timestamp)
    
    def export_to_apkg(self, cards: List[CardData], filename: str = None, template_name: str = None, timestamp: str = None) -> str:
        """导出为apkg格式"""
        if filename is None:
            if timestamp:
                filename = f"anki_cards_{timestamp}.apkg"
            else:
                filename = f"anki_cards_{datetime.now().strftime('%Y%m%d_%H%M%S')}.apkg"
        output_path = self.output_dir / filename
        
        self.logger.info(f"开始导出apkg文件: {filename}, 卡片数量: {len(cards)}, 模板: {template_name}")
        
        # 按牌组分组卡片并创建包
        decks = self._create_decks_from_cards(cards, template_name)
        package = Package(decks)
        package.write_to_file(str(output_path))
        
        self.logger.info(f"已导出 {len(cards)} 张卡片到: {output_path}")
        return str(output_path)
    
    def export_to_apkg_with_custom_template(self, cards: List[CardData], template_name: str, filename: str = None, timestamp: str = None) -> str:
        """使用自定义模板导出为apkg格式"""
        if not self.template_manager:
            raise ValueError("模板管理器未初始化")
        
        template = self.template_manager.get_template(template_name)
        if not template:
            raise ValueError(f"无法找到模板: {template_name}")
        
        return self.export_to_apkg(cards, filename, template_name, timestamp)
    
    def _create_decks_from_cards(self, cards: List[CardData], template_name: str = None) -> List[Deck]:
        """从卡片创建牌组"""
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
                effective_template_name = template_name or card.model
                model, note = self._create_model_and_note(card, effective_template_name)
                deck.add_note(note)
            
            decks.append(deck)
        
        return decks
    
    def _create_model_and_note(self, card: CardData, template_name: str):
        """创建模型和笔记"""
        # 尝试使用模板创建
        if self.template_manager:
            template = self.template_manager.get_template(template_name)
            if template:
                model = self.model_factory.create_model_from_template(template)
                note = self.note_factory.create_note_from_template(card, model, template)
                return model, note
        
        # 使用默认模型
        model = self.model_factory.get_model_for_card(card)
        note = self.note_factory.create_note(card, model)
        return model, note
    
    def _get_deck_id(self, deck_name: str) -> int:
        """获取牌组ID"""
        if deck_name not in self.deck_ids:
            hash_obj = hashlib.md5(deck_name.encode())
            self.deck_ids[deck_name] = int(hash_obj.hexdigest()[:8], 16)
        return self.deck_ids[deck_name]
    
    def get_export_summary(self, cards: List[CardData]) -> Dict[str, Any]:
        """获取导出摘要"""
        if not cards:
            return {'total_cards': 0, 'deck_stats': {}, 'model_stats': {}}
        
        # 使用字典推导式统计
        deck_stats = {}
        model_stats = {}
        
        for card in cards:
            deck_stats[card.deck] = deck_stats.get(card.deck, 0) + 1
            model_stats[card.model] = model_stats.get(card.model, 0) + 1
        
        return {
            'total_cards': len(cards),
            'deck_stats': deck_stats,
            'model_stats': model_stats
        }
