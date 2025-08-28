"""
Web应用错误处理模块
提供统一的错误处理装饰器
"""

import logging
import functools
from flask import jsonify
from typing import Callable, Any

logger = logging.getLogger(__name__)

def handle_api_error(func: Callable) -> Callable:
    """API错误处理装饰器"""
    @functools.wraps(func)
    def wrapper(*args, **kwargs) -> Any:
        try:
            return func(*args, **kwargs)
        except Exception as e:
            logger.error(f"{func.__name__} 失败: {e}")
            return jsonify({
                'success': False,
                'error': str(e)
            }), 500
    return wrapper

def handle_file_error(func: Callable) -> Callable:
    """文件操作错误处理装饰器"""
    @functools.wraps(func)
    def wrapper(*args, **kwargs) -> Any:
        try:
            return func(*args, **kwargs)
        except FileNotFoundError as e:
            logger.error(f"文件不存在: {e}")
            return jsonify({
                'success': False,
                'error': '文件不存在或已过期'
            }), 404
        except Exception as e:
            logger.error(f"{func.__name__} 失败: {e}")
            return jsonify({
                'success': False,
                'error': str(e)
            }), 500
    return wrapper
