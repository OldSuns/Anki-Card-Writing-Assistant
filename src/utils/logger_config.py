"""日志配置模块"""

import logging
import re
from pathlib import Path
from logging.handlers import RotatingFileHandler
from typing import Optional


class LoggerConfig:
    """日志配置管理器"""
    
    # 常量
    LOG_FORMAT = "%(asctime)s - %(name)s - %(levelname)s - %(message)s"
    MAX_LOG_SIZE = 10 * 1024 * 1024  # 10MB
    DEFAULT_LOG_PATH = "logs/app.log"
    
    def __init__(self, log_path: Optional[str] = None):
        self.log_path = Path(log_path or self.DEFAULT_LOG_PATH)
        self.ansi_pattern = re.compile(r'\x1b\[[0-9;]*[A-Za-z]')
        
    def setup_logging(self, level: int = logging.INFO) -> None:
        """设置日志系统"""
        # 创建日志目录
        self.log_path.parent.mkdir(exist_ok=True)
        
        # 配置根日志器
        logging.basicConfig(
            level=level,
            format=self.LOG_FORMAT,
            handlers=[]
        )
        
        # 添加处理器
        self._add_stream_handler()
        self._add_file_handler()
    
    def _add_stream_handler(self) -> None:
        """添加控制台处理器"""
        stream_handler = logging.StreamHandler()
        formatter = logging.Formatter(self.LOG_FORMAT)
        stream_handler.setFormatter(formatter)
        logging.getLogger().addHandler(stream_handler)
    
    def _add_file_handler(self) -> None:
        """添加文件处理器"""
        file_handler = RotatingFileHandler(
            self.log_path,
            maxBytes=self.MAX_LOG_SIZE,
            backupCount=5,
            encoding='utf-8'
        )
        
        # 为文件日志添加清洗过滤器
        file_handler.addFilter(self._create_safe_text_filter())
        
        formatter = logging.Formatter(self.LOG_FORMAT)
        file_handler.setFormatter(formatter)
        logging.getLogger().addHandler(file_handler)
    
    def _create_safe_text_filter(self) -> logging.Filter:
        """创建安全文本过滤器"""
        class SafeTextFilter(logging.Filter):
            def __init__(self, sanitizer_func):
                super().__init__()
                self.sanitize = sanitizer_func
            
            def filter(self, record):
                try:
                    sanitized = self.sanitize(record.getMessage())
                    record.msg = sanitized
                    record.args = ()
                except Exception:
                    pass
                return True
        
        return SafeTextFilter(self._sanitize_log_text)
    
    def _sanitize_log_text(self, text: str) -> str:
        """清理日志文本"""
        if not isinstance(text, str):
            try:
                text = str(text)
            except Exception:
                return "?"
        
        # 去除 ANSI 转义序列
        text = self.ansi_pattern.sub('', text)
        
        # 替换不可显示字符为 '?'
        return ''.join(
            ch if ch.isprintable() or ch in '\t\r\n' else '?'
            for ch in text
        )