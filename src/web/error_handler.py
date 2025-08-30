"""
Web应用错误处理模块
提供统一的错误处理装饰器和工具
"""

import logging
import functools
from flask import jsonify
from typing import Callable, Any, Tuple, Dict, Type, Union


class ErrorHandler:
    """统一错误处理器类"""
    
    def __init__(self):
        self.logger = logging.getLogger(__name__)
        
        # 预定义的错误映射
        self.error_mappings = {
            FileNotFoundError: (404, '文件不存在或已过期'),
            PermissionError: (403, '权限不足'),
            ValueError: (400, '参数值错误'),
            TypeError: (400, '参数类型错误'),
            KeyError: (400, '缺少必要参数'),
            ConnectionError: (500, '网络连接错误'),
            TimeoutError: (500, '请求超时'),
            RuntimeError: (500, '运行时错误'),
        }
    
    def create_error_response(self, error_message: str, status_code: int = 500) -> Tuple[Any, int]:
        """创建统一的错误响应"""
        return jsonify({
            'success': False,
            'error': error_message
        }), status_code
    
    def get_error_info(self, error: Exception) -> Tuple[int, str]:
        """根据异常类型获取错误信息"""
        error_type = type(error)
        if error_type in self.error_mappings:
            status_code, default_message = self.error_mappings[error_type]
            # 如果异常有自定义消息，使用异常消息，否则使用默认消息
            message = str(error) if str(error) else default_message
            return status_code, message
        else:
            # 未知错误类型
            return 500, str(error) if str(error) else '未知错误'
    
    def log_and_respond(self, func_name: str, error: Exception, 
                       custom_status_code: int = None, 
                       custom_message: str = None) -> Tuple[Any, int]:
        """记录错误并返回响应"""
        if custom_status_code and custom_message:
            status_code, message = custom_status_code, custom_message
        else:
            status_code, message = self.get_error_info(error)
        
        self.logger.error(f"{func_name} 失败: {message}")
        return self.create_error_response(message, status_code)


# 全局错误处理器实例
error_handler = ErrorHandler()


def handle_errors(*error_types: Type[Exception], status_code: int = None, message: str = None):
    """通用错误处理装饰器工厂"""
    def decorator(func: Callable) -> Callable:
        @functools.wraps(func)
        def wrapper(*args, **kwargs) -> Any:
            try:
                return func(*args, **kwargs)
            except error_types as e:
                return error_handler.log_and_respond(
                    func.__name__, e, status_code, message
                )
            except Exception as e:
                return error_handler.log_and_respond(func.__name__, e)
        return wrapper
    
    # 如果没有指定错误类型，处理所有异常
    if not error_types:
        error_types = (Exception,)
    
    return decorator


def handle_api_error(func: Callable) -> Callable:
    """API错误处理装饰器"""
    return handle_errors()(func)


def handle_file_error(func: Callable) -> Callable:
    """文件操作错误处理装饰器"""
    return handle_errors(
        FileNotFoundError, PermissionError, OSError
    )(func)


def handle_validation_error(func: Callable) -> Callable:
    """验证错误处理装饰器"""
    return handle_errors(
        ValueError, TypeError, KeyError,
        status_code=400
    )(func)


def handle_network_error(func: Callable) -> Callable:
    """网络错误处理装饰器"""
    return handle_errors(
        ConnectionError, TimeoutError,
        status_code=500,
        message="网络请求失败，请检查网络连接"
    )(func)


class ErrorContext:
    """错误上下文管理器，用于统一处理代码块中的异常"""
    
    def __init__(self, operation_name: str, 
                 default_status_code: int = 500,
                 error_mappings: Dict[Type[Exception], Tuple[int, str]] = None):
        self.operation_name = operation_name
        self.default_status_code = default_status_code
        self.error_mappings = error_mappings or {}
        self.logger = logging.getLogger(__name__)
    
    def __enter__(self):
        return self
    
    def __exit__(self, exc_type, exc_val, exc_tb):
        if exc_type is not None:
            # 有异常发生
            if exc_type in self.error_mappings:
                status_code, message = self.error_mappings[exc_type]
            else:
                status_code, message = self.default_status_code, str(exc_val)
            
            self.logger.error(f"{self.operation_name} 失败: {message}")
            # 返回 True 表示异常已被处理
            return True
        return False
    
    def get_error_response(self, exc_type, exc_val) -> Tuple[Any, int]:
        """获取错误响应"""
        if exc_type in self.error_mappings:
            status_code, message = self.error_mappings[exc_type]
        else:
            status_code, message = self.default_status_code, str(exc_val)
        
        return error_handler.create_error_response(message, status_code)
