"""
Web应用工具模块
提供通用的工具函数和辅助类
"""

import os
import zipfile
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple
from flask import jsonify


class FileUtils:
    """文件操作工具类"""
    
    @staticmethod
    def ensure_directory_exists(directory: Path) -> bool:
        """确保目录存在"""
        try:
            directory.mkdir(parents=True, exist_ok=True)
            return True
        except Exception:
            return False
    
    @staticmethod
    def safe_filename(filename: str) -> str:
        """生成安全的文件名"""
        # 移除可能的路径前缀
        if filename.startswith('output/'):
            filename = filename[7:]
        elif filename.startswith('output\\'):
            filename = filename[8:]
        
        # Windows路径适配：统一转换为正斜杠
        filename = filename.replace('\\', '/').strip('/')
        
        # 防止路径遍历攻击
        if '..' in filename or filename.startswith('/'):
            return None
        
        return filename
    
    @staticmethod
    def get_file_size(file_path: Path) -> int:
        """获取文件大小"""
        try:
            return file_path.stat().st_size if file_path.exists() else 0
        except Exception:
            return 0
    
    @staticmethod
    def delete_file_safely(file_path: Path) -> bool:
        """安全删除文件"""
        try:
            if file_path.exists():
                file_path.unlink()
                return True
        except Exception:
            pass
        return False


class DateTimeUtils:
    """日期时间工具类"""
    
    @staticmethod
    def generate_timestamp() -> str:
        """生成时间戳字符串"""
        return datetime.now().strftime("%Y%m%d_%H%M%S")
    
    @staticmethod
    def format_display_time(timestamp: datetime) -> str:
        """格式化显示时间"""
        return timestamp.strftime("%Y-%m-%d %H:%M:%S")
    
    @staticmethod
    def parse_filename_timestamp(filename: str) -> Optional[datetime]:
        """从文件名解析时间戳"""
        if "_" not in filename:
            return None
            
        parts = filename.split("_")
        if len(parts) < 3:
            return None
            
        date_str = parts[-2]
        time_str = parts[-1]
        
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
        
        return None


class ValidationUtils:
    """验证工具类"""
    
    @staticmethod
    def is_valid_card_index(index: int, total_cards: int) -> bool:
        """验证卡片索引是否有效"""
        return 1 <= index <= total_cards
    
    @staticmethod
    def is_empty_content(content: str) -> bool:
        """检查内容是否为空"""
        return not content or not content.strip()
    
    @staticmethod
    def validate_file_extension(filename: str, supported_extensions: List[str]) -> bool:
        """验证文件扩展名"""
        if not filename:
            return False
        
        extension = Path(filename).suffix.lower().lstrip('.')
        return extension in supported_extensions


class ArchiveUtils:
    """压缩包工具类"""
    
    @staticmethod
    def create_zip_archive(zip_path: Path, files_to_add: List[Tuple[Path, str]]) -> bool:
        """创建ZIP压缩包
        
        Args:
            zip_path: 压缩包路径
            files_to_add: 要添加的文件列表，每个元素是(文件路径, 压缩包内名称)的元组
            
        Returns:
            bool: 是否成功创建
        """
        try:
            with zipfile.ZipFile(zip_path, 'w', zipfile.ZIP_DEFLATED) as zipf:
                for file_path, archive_name in files_to_add:
                    if file_path.exists():
                        zipf.write(file_path, archive_name)
            return True
        except Exception:
            return False
    
    @staticmethod
    def generate_archive_name(prefix: str = "anki_cards") -> str:
        """生成压缩包名称"""
        timestamp = DateTimeUtils.generate_timestamp()
        return f"{prefix}_{timestamp}.zip"


class ResponseUtils:
    """响应工具类"""
    
    @staticmethod
    def success_response(data: Any = None, message: str = None) -> Dict[str, Any]:
        """创建成功响应"""
        response = {'success': True}
        if data is not None:
            response['data'] = data
        if message:
            response['message'] = message
        return jsonify(response)
    
    @staticmethod
    def error_response(error_msg: str, status_code: int = 500) -> Tuple[Any, int]:
        """创建错误响应"""
        return jsonify({
            'success': False,
            'error': error_msg
        }), status_code
    
    @staticmethod
    def validation_error_response(field: str, message: str) -> Tuple[Any, int]:
        """创建验证错误响应"""
        return ResponseUtils.error_response(f'{field}: {message}', 400)


class LoggingUtils:
    """日志工具类"""
    
    @staticmethod
    def log_operation_start(logger, operation: str, **kwargs):
        """记录操作开始"""
        details = ', '.join(f"{k}={v}" for k, v in kwargs.items())
        logger.info(f"开始{operation}: {details}")
    
    @staticmethod
    def log_operation_success(logger, operation: str, **kwargs):
        """记录操作成功"""
        details = ', '.join(f"{k}={v}" for k, v in kwargs.items())
        logger.info(f"{operation}成功: {details}")
    
    @staticmethod
    def log_operation_error(logger, operation: str, error: Exception, **kwargs):
        """记录操作错误"""
        details = ', '.join(f"{k}={v}" for k, v in kwargs.items())
        logger.error(f"{operation}失败: {error}, 详情: {details}")


class StringUtils:
    """字符串工具类"""
    
    @staticmethod
    def truncate_text(text: str, max_length: int = 100, suffix: str = '...') -> str:
        """截断文本"""
        if not text:
            return ''
        
        text = str(text)
        if len(text) <= max_length:
            return text
        
        return text[:max_length - len(suffix)] + suffix
    
    @staticmethod
    def clean_html_tags(html_content: str) -> str:
        """清理HTML标签"""
        import re
        clean_content = re.sub(r'<[^>]+>', '', html_content)
        clean_content = re.sub(r'\{\{[^}]+\}\}', '', clean_content)
        return clean_content.strip()
    
    @staticmethod
    def normalize_line_endings(text: str) -> str:
        """标准化行结束符"""
        return text.replace('\r\n', '\n').replace('\r', '\n')


class DictUtils:
    """字典工具类"""
    
    @staticmethod
    def safe_get_nested(data: Dict[str, Any], key_path: str, default: Any = None) -> Any:
        """安全获取嵌套字典值"""
        try:
            keys = key_path.split('.')
            value = data
            for key in keys:
                value = value[key]
            return value
        except (KeyError, TypeError, AttributeError):
            return default
    
    @staticmethod
    def merge_dicts(dict1: Dict[str, Any], dict2: Dict[str, Any]) -> Dict[str, Any]:
        """合并字典"""
        result = dict1.copy()
        result.update(dict2)
        return result
    
    @staticmethod
    def filter_none_values(data: Dict[str, Any]) -> Dict[str, Any]:
        """过滤None值"""
        return {k: v for k, v in data.items() if v is not None}