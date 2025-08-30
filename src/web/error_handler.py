"""
Web应用错误处理模块
提供统一的错误处理装饰器和工具
"""

import logging
import functools
from flask import jsonify
from typing import Callable, Any, Tuple


class ErrorHandler:
    """错误处理器类"""
    
    def __init__(self):
        self.logger = logging.getLogger(__name__)
    
    def create_error_response(self, error_message: str, status_code: int = 500) -> Tuple[Any, int]:
        """创建统一的错误响应"""
        return jsonify({
            'success': False,
            'error': error_message
        }), status_code
    
    def log_and_respond(self, func_name: str, error: Exception, status_code: int = 500) -> Tuple[Any, int]:
        """记录错误并返回响应"""
        self.logger.error(f"{func_name} 失败: {error}")
        return self.create_error_response(str(error), status_code)


# 全局错误处理器实例
error_handler = ErrorHandler()


def handle_api_error(func: Callable) -> Callable:
    """API错误处理装饰器"""
    @functools.wraps(func)
    def wrapper(*args, **kwargs) -> Any:
        try:
            return func(*args, **kwargs)
        except Exception as e:
            return error_handler.log_and_respond(func.__name__, e)
    return wrapper


def handle_file_error(func: Callable) -> Callable:
    """文件操作错误处理装饰器"""
    @functools.wraps(func)
    def wrapper(*args, **kwargs) -> Any:
        try:
            return func(*args, **kwargs)
        except FileNotFoundError as e:
            error_handler.logger.error(f"文件不存在: {e}")
            return error_handler.create_error_response('文件不存在或已过期', 404)
        except Exception as e:
            return error_handler.log_and_respond(func.__name__, e)
    return wrapper


def handle_specific_errors(*error_types: type, status_code: int = 500, message: str = None):
    """处理特定类型错误的装饰器工厂"""
    def decorator(func: Callable) -> Callable:
        @functools.wraps(func)
        def wrapper(*args, **kwargs) -> Any:
            try:
                return func(*args, **kwargs)
            except error_types as e:
                error_message = message or str(e)
                return error_handler.log_and_respond(func.__name__, e, status_code)
            except Exception as e:
                return error_handler.log_and_respond(func.__name__, e)
        return wrapper
    return decorator
