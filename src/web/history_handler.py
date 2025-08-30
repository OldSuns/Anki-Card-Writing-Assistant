"""
历史记录处理模块
提供历史记录的解析、格式化和管理功能
"""

import json
import logging
import re
from datetime import datetime
from pathlib import Path
from typing import Dict, List, Any, Optional


class HistoryConstants:
    """历史记录处理常量"""
    SUPPORTED_EXTENSIONS = ['json', 'csv', 'html', 'txt', 'apkg']
    DEFAULT_DECK_NAME = '未知牌组'
    DEFAULT_CONTENT_PREVIEW = '从卡片数据生成'
    FILENAME_PATTERN = r'anki_cards_(\d{8})_(\d{6})'
    DATE_FORMAT = "%Y%m%d_%H%M%S"
    DISPLAY_DATE_FORMAT = "%Y-%m-%d %H:%M:%S"


class TimestampParser:
    """时间戳解析器"""
    
    @staticmethod
    def parse_from_filename(filename: str) -> Optional[datetime]:
        """从文件名解析时间戳"""
        if "_" not in filename:
            return None
            
        # 文件名格式: anki_cards_20250828_231020
        parts = filename.split("_")
        if len(parts) < 3:
            return None
            
        date_str = parts[-2]  # 20250828
        time_str = parts[-1]  # 231020
        
        # 解析日期和时间
        if len(date_str) == 8 and len(time_str) == 6:
            try:
                year = int(date_str[:4])
                month = int(date_str[4:6])
                day = int(date_str[6:8])
                hour = int(time_str[:2])
                minute = int(time_str[2:4])
                second = int(time_str[4:6])
                
                return datetime(year, month, day, hour, minute, second)
            except ValueError:
                pass
                
        # 回退到原始解析方式
        try:
            timestamp_str = f"{date_str}_{time_str}"
            return datetime.strptime(timestamp_str, HistoryConstants.DATE_FORMAT)
        except ValueError:
            return None


class ContentProcessor:
    """内容处理器"""
    
    @staticmethod
    def clean_html_content(content: str) -> str:
        """清理HTML标签和特殊字符"""
        clean_content = re.sub(r'<[^>]+>', '', content)
        clean_content = re.sub(r'\{\{[^}]+\}\}', '', clean_content)
        return clean_content
        
    @staticmethod
    def format_content_preview(content_preview, max_length: int = 100) -> str:
        """安全地格式化内容预览"""
        if content_preview is None:
            return ''
            
        content_str = str(content_preview)
        if len(content_str) > max_length:
            return content_str[:max_length] + '...'
        return content_str

    @staticmethod
    def extract_deck_name_from_card(card: Dict[str, Any]) -> str:
        """从卡片中提取牌组名称"""
        return (
            card.get('deckName') or
            card.get('deck') or
            card.get('fields', {}).get('Deck') or
            HistoryConstants.DEFAULT_DECK_NAME
        )

    @staticmethod
    def generate_content_preview_from_card(card: Dict[str, Any]) -> str:
        """从卡片生成内容预览"""
        front_content = ''
        if 'fields' in card and isinstance(card['fields'], dict):
            front_content = card['fields'].get('Front', '')
        elif 'front' in card:
            front_content = card['front']
            
        if front_content:
            clean_content = ContentProcessor.clean_html_content(front_content)
            return ContentProcessor.format_content_preview(clean_content, 100)
        return HistoryConstants.DEFAULT_CONTENT_PREVIEW


class CardDataProcessor:
    """卡片数据处理器"""
    
    @staticmethod
    def process_single_card(card, card_index: int) -> Dict[str, Any]:
        """处理单个卡片数据，统一格式"""
        if not isinstance(card, dict):
            return {
                'index': card_index,
                'front': '无效卡片数据',
                'back': '',
                'deck': '',
                'tags': [],
                'fields': {},
                'modelName': '',
                'deckName': ''
            }
            
        processed_card = {
            'index': card_index,
            'front': '',
            'back': '',
            'deck': '',
            'tags': [],
            'fields': card.get('fields', {}),
            'modelName': card.get('modelName', ''),
            'deckName': card.get('deckName', '')
        }
        
        # 获取正面内容
        if 'front' in card:
            processed_card['front'] = card['front']
        elif 'fields' in card and isinstance(card['fields'], dict):
            processed_card['front'] = card['fields'].get('Front', '')
            
        # 获取背面内容
        if 'back' in card:
            processed_card['back'] = card['back']
        elif 'fields' in card and isinstance(card['fields'], dict):
            processed_card['back'] = card['fields'].get('Back', '')
            
        # 获取牌组名称
        if 'deck' in card:
            processed_card['deck'] = card['deck']
        elif 'fields' in card and isinstance(card['fields'], dict):
            processed_card['deck'] = card['fields'].get('Deck', '')
            
        # 获取标签
        if 'tags' in card and isinstance(card['tags'], list):
            processed_card['tags'] = card['tags']
        elif 'fields' in card and isinstance(card['fields'], dict) and card['fields'].get('Tags'):
            processed_card['tags'] = card['fields']['Tags'].split()
            
        return processed_card

    @staticmethod
    def process_cards_list(cards_list: List, start_index: int = 1) -> List[Dict[str, Any]]:
        """处理卡片列表"""
        processed_cards = []
        for i, card in enumerate(cards_list):
            processed_card = CardDataProcessor.process_single_card(card, start_index + i)
            processed_cards.append(processed_card)
        return processed_cards


class RecordBuilder:
    """记录构建器"""
    
    @staticmethod
    def build_from_metadata(filename: str, timestamp: datetime, card_data: Dict) -> Dict[str, Any]:
        """从包含metadata的数据构建记录"""
        metadata = card_data.get('metadata', {})
        cards_list = card_data.get('cards', [])
        
        return {
            'id': filename,
            'timestamp': metadata.get('timestamp', timestamp.isoformat()),
            'timestamp_display': timestamp.strftime(HistoryConstants.DISPLAY_DATE_FORMAT),
            'card_count': metadata.get('card_count', len(cards_list)),
            'deck_name': metadata.get('deck_name', HistoryConstants.DEFAULT_DECK_NAME),
            'content_preview': ContentProcessor.format_content_preview(metadata.get('content_preview', '')),
            'files': {}
        }
        
    @staticmethod
    def build_from_card_list(filename: str, timestamp: datetime, cards_list: List) -> Dict[str, Any]:
        """从卡片列表构建记录"""
        deck_name = HistoryConstants.DEFAULT_DECK_NAME
        content_preview = HistoryConstants.DEFAULT_CONTENT_PREVIEW
        
        if cards_list and isinstance(cards_list[0], dict):
            first_card = cards_list[0]
            deck_name = ContentProcessor.extract_deck_name_from_card(first_card)
            content_preview = ContentProcessor.generate_content_preview_from_card(first_card)
            
        return {
            'id': filename,
            'timestamp': timestamp.isoformat(),
            'timestamp_display': timestamp.strftime(HistoryConstants.DISPLAY_DATE_FORMAT),
            'card_count': len(cards_list),
            'deck_name': deck_name,
            'content_preview': content_preview,
            'files': {}
        }

    @staticmethod
    def build_unknown_format(filename: str, timestamp: datetime) -> Dict[str, Any]:
        """构建未知格式的记录"""
        return {
            'id': filename,
            'timestamp': timestamp.isoformat(),
            'timestamp_display': timestamp.strftime(HistoryConstants.DISPLAY_DATE_FORMAT),
            'card_count': 0,
            'deck_name': HistoryConstants.DEFAULT_DECK_NAME,
            'content_preview': '',
            'files': {}
        }


class HistoryHandler:
    """历史记录处理器"""
    
    def __init__(self, output_directory: str):
        self.output_dir = Path(output_directory)
        self.logger = logging.getLogger(__name__)
        self.timestamp_parser = TimestampParser()
        self.content_processor = ContentProcessor()
        self.card_processor = CardDataProcessor()
        self.record_builder = RecordBuilder()
        
    def get_history_records(self) -> List[Dict[str, Any]]:
        """获取所有历史记录"""
        if not self.output_dir.exists():
            return []
            
        history_records = []
        for file_path in self.output_dir.glob("anki_cards_*.json"):
            try:
                record = self._parse_history_file(file_path)
                if record:
                    history_records.append(record)
            except Exception as e:
                self.logger.warning(f"解析历史记录文件失败 {file_path}: {e}")
                continue
                
        # 按时间倒序排列
        history_records.sort(key=lambda x: x['timestamp'], reverse=True)
        return history_records
        
    def get_history_detail(self, record_id: str) -> Optional[Dict[str, Any]]:
        """获取历史记录详情"""
        json_file = self.output_dir / f"{record_id}.json"
        
        if not json_file.exists():
            return None
            
        with open(json_file, 'r', encoding='utf-8') as f:
            card_data = json.load(f)
            
        return self._process_card_data_for_detail(card_data)
        
    def get_history_card(self, record_id: str, card_index: int) -> Optional[Dict[str, Any]]:
        """获取历史记录中的特定卡片"""
        json_file = self.output_dir / f"{record_id}.json"
        
        if not json_file.exists():
            return None
            
        with open(json_file, 'r', encoding='utf-8') as f:
            card_data = json.load(f)
            
        # 处理卡片数据
        cards_list = self._extract_cards_list(card_data)
            
        if not cards_list or card_index < 1 or card_index > len(cards_list):
            return None
            
        # 处理指定卡片
        card = cards_list[card_index - 1]  # 转换为0基索引
        processed_card = self.card_processor.process_single_card(card, card_index)
        
        return {
            'card': processed_card,
            'current_index': card_index,
            'total_cards': len(cards_list),
            'has_previous': card_index > 1,
            'has_next': card_index < len(cards_list)
        }
        
    def delete_history_record(self, record_id: str) -> List[str]:
        """删除历史记录，返回删除的文件列表"""
        deleted_files = []
        
        for ext in HistoryConstants.SUPPORTED_EXTENSIONS:
            file_path = self.output_dir / f"{record_id}.{ext}"
            if file_path.exists():
                file_path.unlink()
                deleted_files.append(file_path.name)
                
        return deleted_files
        
    def _parse_history_file(self, file_path: Path) -> Optional[Dict[str, Any]]:
        """解析单个历史记录文件"""
        filename = file_path.stem
        
        # 解析时间戳
        timestamp = self.timestamp_parser.parse_from_filename(filename)
        if not timestamp:
            return None
            
        # 读取JSON文件获取详细信息
        with open(file_path, 'r', encoding='utf-8') as f:
            card_data = json.load(f)
            
        # 构建历史记录
        record = self._build_history_record(filename, timestamp, card_data)
        
        # 检查相关文件是否存在
        self._check_related_files(record, file_path.stem)
        
        return record
            
    def _build_history_record(self, filename: str, timestamp: datetime, card_data: Any) -> Dict[str, Any]:
        """构建历史记录对象"""
        if isinstance(card_data, dict) and 'metadata' in card_data:
            return self.record_builder.build_from_metadata(filename, timestamp, card_data)
        elif isinstance(card_data, list):
            return self.record_builder.build_from_card_list(filename, timestamp, card_data)
        else:
            return self.record_builder.build_unknown_format(filename, timestamp)
                
    def _check_related_files(self, record: Dict[str, Any], base_name: str):
        """检查相关文件是否存在"""
        for ext in HistoryConstants.SUPPORTED_EXTENSIONS:
            ext_file = self.output_dir / f"{base_name}.{ext}"
            if ext_file.exists():
                record['files'][ext] = {
                    'exists': True,
                    'size': ext_file.stat().st_size,
                    'filename': ext_file.name
                }
            else:
                record['files'][ext] = {'exists': False}
                
    def _process_card_data_for_detail(self, card_data: Any) -> Dict[str, Any]:
        """处理卡片数据用于详情显示"""
        if isinstance(card_data, dict) and 'metadata' in card_data:
            return self._process_metadata_format(card_data)
        elif isinstance(card_data, list):
            return self._process_list_format(card_data)
        else:
            return self._get_unknown_format_detail()
            
    def _process_metadata_format(self, card_data: Dict) -> Dict[str, Any]:
        """处理包含metadata的格式"""
        cards_list = card_data.get('cards', [])
        processed_cards = self.card_processor.process_cards_list(cards_list)
            
        return {
            'timestamp': card_data['metadata'].get('timestamp'),
            'deck_name': card_data['metadata'].get('deck_name', HistoryConstants.DEFAULT_DECK_NAME),
            'card_count': card_data['metadata'].get('card_count', len(processed_cards)),
            'content_preview': self.content_processor.format_content_preview(
                card_data['metadata'].get('content_preview', '')
            ),
            'generation_config': card_data['metadata'].get('generation_config', {}),
            'cards': processed_cards,
            'current_card_index': 0,
            'total_cards': len(processed_cards)
        }
        
    def _process_list_format(self, card_data: List) -> Dict[str, Any]:
        """处理列表格式的卡片数据"""
        processed_cards = self.card_processor.process_cards_list(card_data)
        
        deck_name = HistoryConstants.DEFAULT_DECK_NAME
        content_preview = HistoryConstants.DEFAULT_CONTENT_PREVIEW
        
        if processed_cards:
            first_card = processed_cards[0]
            deck_name = self.content_processor.extract_deck_name_from_card(first_card)
            
            # 尝试从卡片内容生成预览
            front_content = first_card.get('front', '')
            if front_content:
                clean_content = self.content_processor.clean_html_content(front_content)
                content_preview = self.content_processor.format_content_preview(clean_content, 200)
                
        return {
            'timestamp': None,
            'deck_name': deck_name,
            'card_count': len(processed_cards),
            'content_preview': content_preview,
            'generation_config': {},
            'cards': processed_cards,
            'current_card_index': 0,
            'total_cards': len(processed_cards)
        }

    def _get_unknown_format_detail(self) -> Dict[str, Any]:
        """获取未知格式的详情"""
        return {
            'timestamp': None,
            'deck_name': HistoryConstants.DEFAULT_DECK_NAME,
            'card_count': 0,
            'content_preview': '',
            'generation_config': {},
            'cards': [],
            'current_card_index': 0,
            'total_cards': 0
        }

    def _extract_cards_list(self, card_data: Any) -> List:
        """提取卡片列表"""
        if isinstance(card_data, dict) and 'metadata' in card_data:
            return card_data.get('cards', [])
        elif isinstance(card_data, list):
            return card_data
        return []