"""
AIWriteX V18.1 - Exception Handler
统一异常处理框架 - 全局错误捕获和处理

功能:
1. 全局捕获: 统一捕获和处理异常
2. 错误分类: 自动分类和优先级处理
3. 恢复机制: 自动恢复和降级策略
4. 报告机制: 错误报告和追踪

使用示例:
    from src.ai_write_x.utils import exception_handler, ErrorCategory
    
    # 方式1: 装饰器
    @exception_handler_decorator(ErrorCategory.API, fallback=None)
    def my_function():
        pass
    
    # 方式2: 上下文管理
    with ExceptionContext() as ctx:
        risky_operation()
    
    # 方式3: 手动处理
    try:
        risky_operation()
    except Exception as e:
        exception_handler.handle(e, context={"operation": "risky"})
"""

import traceback
import sys
from typing import Dict, Any, Callable, Optional
from enum import Enum
from datetime import datetime
from dataclasses import dataclass, field
from functools import wraps


# 统一的日志函数（延迟导入避免循环依赖）
def _log_message(severity: str, message: str):
    """统一的日志输出"""
    try:
        from src.ai_write_x.utils.log import print_log
        print_log(message, severity)
    except Exception:
        print(f"[{severity.upper()}] {message}")


class ErrorSeverity(Enum):
    """错误严重程度"""
    DEBUG = "debug"
    INFO = "info"
    WARNING = "warning"
    ERROR = "error"
    CRITICAL = "critical"


class ErrorCategory(Enum):
    """错误分类"""
    NETWORK = "network"         # 网络错误
    DATABASE = "database"       # 数据库错误
    API = "api"                 # API错误
    VALIDATION = "validation"   # 验证错误
    SYSTEM = "system"          # 系统错误
    BUSINESS = "business"      # 业务错误
    UNKNOWN = "unknown"        # 未知错误


@dataclass
class ErrorRecord:
    """错误记录"""
    error_type: str
    message: str
    severity: ErrorSeverity
    category: ErrorCategory
    timestamp: datetime
    traceback_str: str = ""
    context: Dict[str, Any] = field(default_factory=dict)


class ExceptionHandler:
    """
    异常处理器 - 统一处理系统中的所有异常
    
    单例模式，全局只有一个实例
    """
    
    _instance = None
    
    def __new__(cls):
        if cls._instance is None:
            cls._instance = super().__new__(cls)
            cls._instance._initialized = False
        return cls._instance
    
    def __init__(self):
        if self._initialized:
            return
            
        self._initialized = True
        self._handlers: Dict[ErrorCategory, Callable] = {}
        self._fallback_handlers: Dict[ErrorCategory, Callable] = {}
        self._error_history: list = []
        self._max_history = 100
        
        _log_message("info", "异常处理器初始化完成")
    
    def register_handler(
        self,
        category: ErrorCategory,
        handler: Callable,
        fallback: Optional[Callable] = None
    ):
        """注册错误处理器"""
        self._handlers[category] = handler
        if fallback:
            self._fallback_handlers[category] = fallback
        
        _log_message("debug", f"注册错误处理器: {category.value}")
    
    def handle(self, exception: Exception, context: Dict = None) -> Any:
        """
        处理异常
        
        Args:
            exception: 异常对象
            context: 上下文信息
            
        Returns:
            处理结果
        """
        # 分类错误
        category = self._classify_error(exception)
        severity = self._determine_severity(exception, category)
        
        # 记录错误
        error_record = ErrorRecord(
            error_type=type(exception).__name__,
            message=str(exception),
            severity=severity,
            category=category,
            timestamp=datetime.now(),
            traceback_str=traceback.format_exc(),
            context=context or {}
        )
        
        self._record_error(error_record)
        
        # 尝试处理
        try:
            if category in self._handlers:
                result = self._handlers[category](exception, context)
                _log_message("info", f"错误已处理: {category.value}")
                return result
        except Exception as e:
            _log_message("error", f"处理器失败: {e}")
        
        # 使用降级策略
        if category in self._fallback_handlers:
            _log_message("warning", f"使用降级策略: {category.value}")
            return self._fallback_handlers[category](exception, context)
        
        # 默认处理
        return self._default_handle(error_record)
    
    def _classify_error(self, exception: Exception) -> ErrorCategory:
        """分类错误"""
        error_name = type(exception).__name__.lower()
        error_msg = str(exception).lower()
        
        if any(kw in error_name for kw in ['network', 'connection', 'timeout', 'ssl']):
            return ErrorCategory.NETWORK
        elif any(kw in error_name for kw in ['database', 'sql', 'db', 'sqlite']):
            return ErrorCategory.DATABASE
        elif any(kw in error_name for kw in ['api', 'http', 'request', 'response']):
            return ErrorCategory.API
        elif any(kw in error_name for kw in ['validation', 'value', 'type', 'key']):
            return ErrorCategory.VALIDATION
        elif any(kw in error_name for kw in ['system', 'runtime', 'memory', 'os']):
            return ErrorCategory.SYSTEM
        elif any(kw in error_name for kw in ['business', 'domain', 'logic']):
            return ErrorCategory.BUSINESS
        else:
            return ErrorCategory.UNKNOWN
    
    def _determine_severity(
        self,
        exception: Exception,
        category: ErrorCategory
    ) -> ErrorSeverity:
        """确定错误严重程度"""
        error_name = type(exception).__name__
        
        if error_name in ['SystemExit', 'KeyboardInterrupt']:
            return ErrorSeverity.CRITICAL
        elif category == ErrorCategory.DATABASE:
            return ErrorSeverity.ERROR
        elif category == ErrorCategory.NETWORK:
            return ErrorSeverity.WARNING
        elif category == ErrorCategory.VALIDATION:
            return ErrorSeverity.INFO
        else:
            return ErrorSeverity.ERROR
    
    def _record_error(self, record: ErrorRecord):
        """记录错误"""
        self._error_history.append(record)
        if len(self._error_history) > self._max_history:
            self._error_history = self._error_history[-self._max_history:]
        
        # 日志记录
        log_message = f"[{record.category.value}] {record.error_type}: {record.message[:100]}"
        
        if record.severity == ErrorSeverity.CRITICAL:
            _log_message("error", f"[CRITICAL] {log_message}")
        elif record.severity == ErrorSeverity.ERROR:
            _log_message("error", log_message)
        elif record.severity == ErrorSeverity.WARNING:
            _log_message("warning", log_message)
        else:
            _log_message("info", log_message)
    
    def _default_handle(self, record: ErrorRecord) -> Dict:
        """默认错误处理"""
        return {
            "success": False,
            "error": {
                "type": record.error_type,
                "message": record.message,
                "category": record.category.value,
                "timestamp": record.timestamp.isoformat()
            }
        }
    
    def get_error_stats(self) -> Dict:
        """获取错误统计"""
        from collections import Counter
        
        category_counts = Counter(e.category.value for e in self._error_history)
        severity_counts = Counter(e.severity.value for e in self._error_history)
        
        return {
            "total_errors": len(self._error_history),
            "by_category": dict(category_counts),
            "by_severity": dict(severity_counts),
            "recent_errors": [
                {
                    "type": e.error_type,
                    "message": e.message[:100],
                    "timestamp": e.timestamp.isoformat()
                }
                for e in self._error_history[-5:]
            ]
        }


def safe_execute(
    func: Callable,
    *args,
    fallback: Any = None,
    context: Dict = None,
    **kwargs
) -> Any:
    """
    安全执行函数
    
    Args:
        func: 要执行的函数
        fallback: 失败时的返回值
        context: 上下文信息
        
    Returns:
        函数返回值或fallback值
    """
    try:
        return func(*args, **kwargs)
    except Exception as e:
        handler = ExceptionHandler()
        result = handler.handle(e, context or {"function": func.__name__})
        return fallback if fallback is not None else result


def exception_handler_decorator(
    category: ErrorCategory = ErrorCategory.UNKNOWN,
    fallback: Any = None
):
    """异常处理装饰器"""
    def decorator(func: Callable):
        @wraps(func)
        def wrapper(*args, **kwargs):
            try:
                return func(*args, **kwargs)
            except Exception as e:
                handler = ExceptionHandler()
                context = {"function": func.__name__, "args": str(args)}
                result = handler.handle(e, context)
                return fallback if fallback is not None else result
        return wrapper
    return decorator


# 全局异常处理器实例
exception_handler = ExceptionHandler()


# 上下文管理器类
class ExceptionContext:
    """异常处理上下文管理器"""
    
    def __init__(self, context: Dict = None, suppress: bool = False):
        self.context = context or {}
        self.suppress = suppress
        self.exception = None
    
    def __enter__(self):
        return self
    
    def __exit__(self, exc_type, exc_val, exc_tb):
        if exc_val:
            self.exception = exc_val
            handler = ExceptionHandler()
            handler.handle(exc_val, self.context)
            return self.suppress  # 是否抑制异常
        return False