"""
Anki导出器模块
负责将生成的卡片导出为Anki可导入的格式
"""

import json
import csv
import logging
from typing import Dict, List, Optional, Any
from pathlib import Path
from datetime import datetime
import zipfile
import tempfile
import shutil

from .card_generator import CardData
from .genanki_exporter import GenAnkiExporter

class AnkiExporter:
    """Anki导出器"""
    
    def __init__(self, output_dir: str = "output"):
        self.output_dir = Path(output_dir)
        self.output_dir.mkdir(exist_ok=True)
        self.logger = logging.getLogger(__name__)
        self.genanki_exporter = GenAnkiExporter(output_dir)
    
    def export_to_json(self, cards: List[CardData], filename: str = None) -> str:
        """导出为JSON格式"""
        if not filename:
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            filename = f"anki_cards_{timestamp}.json"
        
        output_path = self.output_dir / filename
        
        # 转换为Anki导入格式
        anki_data = []
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
            anki_data.append(anki_card)
        
        # 写入JSON文件
        with open(output_path, 'w', encoding='utf-8') as f:
            json.dump(anki_data, f, ensure_ascii=False, indent=2)
        
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
            header = ['#separator:tab', '#html:true', '#tags column:4']
            writer.writerow(header)
            
            # 写入字段名
            writer.writerow(field_names)
            
            # 写入卡片数据
            for card in cards:
                row = []
                for field in field_names:
                    value = card.fields.get(field, '')
                    row.append(value)
                writer.writerow(row)
        
        self.logger.info(f"已导出 {len(cards)} 张卡片到: {output_path}")
        return str(output_path)
    
    def export_to_apkg(self, cards: List[CardData], filename: str = None) -> str:
        """导出为.apkg格式（Anki包）"""
        return self.genanki_exporter.export_to_apkg(cards, filename)
    
    def _create_anki_package_structure(self, temp_path: Path, cards: List[CardData]):
        """创建Anki包结构"""
        # 创建collection.anki2数据库文件（简化版本）
        collection_data = self._create_collection_data(cards)
        
        # 写入collection.anki2
        collection_path = temp_path / "collection.anki2"
        with open(collection_path, 'w', encoding='utf-8') as f:
            json.dump(collection_data, f, ensure_ascii=False, indent=2)
        
        # 创建media目录
        media_dir = temp_path / "media"
        media_dir.mkdir(exist_ok=True)
        
        # 创建media索引文件
        media_index = {}
        media_index_path = media_dir / "media.json"
        with open(media_index_path, 'w', encoding='utf-8') as f:
            json.dump(media_index, f, ensure_ascii=False, indent=2)
    
    def _create_collection_data(self, cards: List[CardData]) -> Dict[str, Any]:
        """创建集合数据"""
        # 按模型分组卡片
        models = {}
        decks = {}
        
        for card in cards:
            # 创建模型
            if card.model not in models:
                models[card.model] = {
                    "name": card.model,
                    "type": 0,  # 0 = 标准模型
                    "flds": [{"name": field, "ord": i} for i, field in enumerate(card.fields.keys())],
                    "tmpls": [{
                        "name": "卡片 1",
                        "qfmt": "{{Front}}",
                        "afmt": "{{FrontSide}}\n\n<hr id=answer>\n\n{{Back}}"
                    }]
                }
            
            # 创建牌组
            if card.deck not in decks:
                decks[card.deck] = {
                    "name": card.deck,
                    "desc": f"由Anki写卡助手生成的牌组 - {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}",
                    "cards": []
                }
            
            # 添加卡片到牌组
            decks[card.deck]["cards"].append({
                "model": card.model,
                "fields": card.fields,
                "tags": card.tags
            })
        
        return {
            "models": models,
            "decks": decks,
            "created": datetime.now().isoformat(),
            "modified": datetime.now().isoformat()
        }
    
    def export_to_text(self, cards: List[CardData], filename: str = None) -> str:
        """导出为纯文本格式"""
        if not filename:
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            filename = f"anki_cards_{timestamp}.txt"
        
        output_path = self.output_dir / filename
        
        with open(output_path, 'w', encoding='utf-8') as f:
            f.write(f"Anki卡片导出 - {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n")
            f.write("=" * 50 + "\n\n")
            
            for i, card in enumerate(cards, 1):
                f.write(f"卡片 {i}\n")
                f.write("-" * 20 + "\n")
                f.write(f"牌组: {card.deck}\n")
                f.write(f"模型: {card.model}\n")
                f.write(f"标签: {', '.join(card.tags)}\n")
                f.write(f"正面: {card.front}\n")
                f.write(f"背面: {card.back}\n")
                f.write("\n")
        
        self.logger.info(f"已导出 {len(cards)} 张卡片到: {output_path}")
        return str(output_path)
    
    def export_to_apkg_with_custom_template(self, cards: List[CardData], 
                                           template_path: str,
                                           filename: str = None) -> str:
        """使用自定义模板导出为.apkg格式"""
        return self.genanki_exporter.export_with_custom_template(cards, template_path, filename)
    
    def export_to_html(self, cards: List[CardData], filename: str = None) -> str:
        """导出为HTML格式"""
        if not filename:
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            filename = f"anki_cards_{timestamp}.html"
        
        output_path = self.output_dir / filename
        
        html_content = f"""
<!DOCTYPE html>
<html lang="zh-CN">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>Anki卡片预览</title>
    <style>
        body {{
            font-family: Arial, sans-serif;
            max-width: 800px;
            margin: 0 auto;
            padding: 20px;
            background-color: #f5f5f5;
        }}
        .card {{
            background: white;
            border-radius: 8px;
            padding: 20px;
            margin-bottom: 20px;
            box-shadow: 0 2px 4px rgba(0,0,0,0.1);
        }}
        .card-header {{
            border-bottom: 1px solid #eee;
            padding-bottom: 10px;
            margin-bottom: 15px;
        }}
        .card-title {{
            font-size: 18px;
            font-weight: bold;
            color: #333;
        }}
        .card-meta {{
            font-size: 12px;
            color: #666;
            margin-top: 5px;
        }}
        .card-front, .card-back {{
            margin: 10px 0;
        }}
        .card-front {{
            background-color: #f8f9fa;
            padding: 15px;
            border-radius: 4px;
        }}
        .card-back {{
            background-color: #e9ecef;
            padding: 15px;
            border-radius: 4px;
        }}
        .tags {{
            margin-top: 10px;
        }}
        .tag {{
            display: inline-block;
            background-color: #007bff;
            color: white;
            padding: 2px 8px;
            border-radius: 12px;
            font-size: 11px;
            margin-right: 5px;
        }}
    </style>
</head>
<body>
    <h1>Anki卡片预览</h1>
    <p>生成时间: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}</p>
    <p>卡片数量: {len(cards)}</p>
"""
        
        for i, card in enumerate(cards, 1):
            html_content += f"""
    <div class="card">
        <div class="card-header">
            <div class="card-title">卡片 {i}</div>
            <div class="card-meta">
                牌组: {card.deck} | 模型: {card.model}
            </div>
        </div>
        <div class="card-front">
            <strong>正面:</strong><br>
            {card.front}
        </div>
        <div class="card-back">
            <strong>背面:</strong><br>
            {card.back}
        </div>
        <div class="tags">
"""
            for tag in card.tags:
                html_content += f'            <span class="tag">{tag}</span>\n'
            
            html_content += "        </div>\n    </div>\n"
        
        html_content += """
</body>
</html>
"""
        
        with open(output_path, 'w', encoding='utf-8') as f:
            f.write(html_content)
        
        self.logger.info(f"已导出 {len(cards)} 张卡片到: {output_path}")
        return str(output_path)
    
    def export_multiple_formats(self, cards: List[CardData], formats: List[str] = None) -> Dict[str, str]:
        """导出多种格式"""
        if formats is None:
            formats = ['json', 'csv', 'apkg', 'html']
        
        export_paths = {}
        
        for format_type in formats:
            try:
                if format_type == 'json':
                    export_paths['json'] = self.export_to_json(cards)
                elif format_type == 'csv':
                    export_paths['csv'] = self.export_to_csv(cards)
                elif format_type == 'apkg':
                    export_paths['apkg'] = self.export_to_apkg(cards)
                elif format_type == 'txt':
                    export_paths['txt'] = self.export_to_text(cards)
                elif format_type == 'html':
                    export_paths['html'] = self.export_to_html(cards)
                else:
                    self.logger.warning(f"不支持的导出格式: {format_type}")
            except Exception as e:
                self.logger.error(f"导出 {format_type} 格式失败: {e}")
        
        return export_paths
    
    def get_export_summary(self, cards: List[CardData]) -> Dict[str, Any]:
        """获取导出摘要"""
        # 按牌组统计
        deck_stats = {}
        for card in cards:
            if card.deck not in deck_stats:
                deck_stats[card.deck] = 0
            deck_stats[card.deck] += 1
        
        # 按模型统计
        model_stats = {}
        for card in cards:
            if card.model not in model_stats:
                model_stats[card.model] = 0
            model_stats[card.model] += 1
        
        # 收集所有标签
        all_tags = set()
        for card in cards:
            all_tags.update(card.tags)
        
        return {
            "total_cards": len(cards),
            "deck_stats": deck_stats,
            "model_stats": model_stats,
            "unique_tags": list(all_tags),
            "export_time": datetime.now().isoformat()
        }
