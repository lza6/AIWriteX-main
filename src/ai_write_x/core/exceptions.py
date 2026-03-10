"""
AIWriteX 自定义异常类
用于替代 bare except Exception，分类处理不同类型的错误

异常分类:
- FatalError: 致命异常 - 需要立即停止
- RecoverableError: 可恢复异常 - 可以重试或降级
- Warning: 警告 - 不影响主流程
"""

import asyncio
import traceback
from enum import Enum
from typing import Callable, Optional, Any, Dict, List, Type
from datetime import datetime
from functools import wraps

# ==================== 异常严重级别 ====================
class ErrorSeverity(str, Enum):
    """异常严重级别"""
    FATAL = "fatal"        # 致命 - 立即停止
    CRITICAL = "critical"  # 严重 - 需要人工介入
    ERROR = "error"        # 错误 - 可以恢复
    WARNING = "warning"    # 警告 - 可以忽略
    INFO = "info"          # 信息 - 仅记录


class AIWriteXError(Exception):
    """基础异常类"""
    def __init__(self, message: str, details: dict = None, severity: ErrorSeverity = ErrorSeverity.ERROR):
        super().__init__(message)
        self.message = message
        self.details = details or {}
        self.severity = severity
        self.timestamp = datetime.now()

    def to_dict(self) -> Dict:
        return {
            "error": self.__class__.__name__,
            "message": self.message,
            "severity": self.severity.value,
            "details": self.details,
            "timestamp": self.timestamp.isoformat()
        }


# ==================== 异常导出（兼容旧代码）====================
AIWriteXException = AIWriteXError  # 别名，兼容旧代码


class WorkflowException(AIWriteXError):
    """工作流异常 - 用于工作流执行过程中的错误"""
    def __init__(self, message: str, step: str = None, context: dict = None, **kwargs):
        super().__init__(message, **kwargs)
        self.step = step
        self.context = context or {}
    
    def to_dict(self) -> Dict:
        data = super().to_dict()
        data["step"] = self.step
        data["context"] = self.context
        return data


# ==================== 致命异常 ====================
class FatalError(AIWriteXError):
    """致命异常 - 需要立即停止"""
    def __init__(self, message: str, **kwargs):
        super().__init__(message, severity=ErrorSeverity.FATAL, **kwargs)


# ==================== 可恢复异常 ====================
class RecoverableError(AIWriteXError):
    """可恢复异常 - 可以重试"""
    def __init__(self, message: str, retry_count: int = 0, max_retries: int = 3, **kwargs):
        super().__init__(message, severity=ErrorSeverity.ERROR, **kwargs)
        self.retry_count = retry_count
        self.max_retries = max_retries
    
    @property
    def can_retry(self) -> bool:
        return self.retry_count < self.max_retries


# ==================== 网络相关异常 ====================
class NetworkError(AIWriteXError):
    """网络连接异常"""
    pass


class APITimeoutError(NetworkError):
    """API 请求超时"""
    pass


# ==================== API 相关异常 ====================
class APIError(AIWriteXError):
    """API 调用基础异常"""
    pass


class RateLimitError(APIError):
    """API 限流异常"""
    def __init__(self, message: str, retry_after: int = None, **kwargs):
        super().__init__(message, **kwargs)
        self.retry_after = retry_after


class InvalidAPIKeyError(APIError):
    """API 密钥无效"""
    pass


class ModelNotAvailableError(APIError):
    """模型不可用"""
    pass


class ContentGenerationError(APIError):
    """内容生成失败"""
    pass


# ==================== 数据库相关异常 ====================
class DatabaseError(AIWriteXError):
    """数据库基础异常"""
    pass


class RecordNotFoundError(DatabaseError):
    """记录不存在"""
    pass


class DuplicateRecordError(DatabaseError):
    """记录重复"""
    pass


class MigrationError(DatabaseError):
    """数据库迁移失败"""
    pass


# ==================== 业务逻辑异常 ====================
class ValidationError(AIWriteXError):
    """数据验证失败"""
    pass


class ConfigurationError(AIWriteXError):
    """配置错误"""
    pass


class ResourceNotFoundError(AIWriteXError):
    """资源不存在"""
    pass


class WorkflowError(AIWriteXError):
    """工作流执行错误"""
    pass


# ==================== 文件相关异常 ====================
class FileError(AIWriteXError):
    """文件操作异常"""
    pass


class FileNotFoundError(FileError):
    """文件不存在"""
    pass


class FilePermissionError(FileError):
    """文件权限错误"""
    pass


# ==================== 异常处理工具函数 ====================
def get_error_category(error: Exception) -> str:
    """根据异常类型获取错误分类"""
    error_mapping = {
        NetworkError: "network",
        APITimeoutError: "network",
        RateLimitError: "api_limit",
        InvalidAPIKeyError: "api_auth",
        ModelNotAvailableError: "api_model",
        ContentGenerationError: "generation",
        DatabaseError: "database",
        RecordNotFoundError: "database",
        ValidationError: "validation",
        ConfigurationError: "config",
        FileNotFoundError: "file",
        FilePermissionError: "file",
    }
    
    for error_type, category in error_mapping.items():
        if isinstance(error, error_type):
            return category
    
    # 检查异常消息关键词
    msg = str(error).lower()
    if "timeout" in msg or "timed out" in msg:
        return "network"
    if "rate limit" in msg or "限流" in msg:
        return "api_limit"
    if "api key" in msg or "api_key" in msg or "密钥" in msg:
        return "api_auth"
    if "database" in msg or "db" in msg or "sqlite" in msg:
        return "database"
    if "not found" in msg or "不存在" in msg:
        return "not_found"
    
    return "unknown"


class ExceptionHandler:
    """
    分层异常处理策略
    
    特性:
    - 按严重级别分类处理
    - 异常链保留原始堆栈
    - 可配置的重试策略
    - 降级处理
    """
    
    def __init__(self):
        self.handlers: Dict[Type[Exception], Callable] = {}
        self.fallback_handler: Optional[Callable] = None
    
    def register(
        self,
        exception_type: Type[Exception],
        handler: Callable[[Exception], Any]
    ):
        """注册特定异常处理器"""
        self.handlers[exception_type] = handler
    
    def register_fallback(self, handler: Callable[[Exception], Any]):
        """注册默认处理器"""
        self.fallback_handler = handler
    
    def handle(self, error: Exception) -> Any:
        """处理异常"""
        # 查找具体处理器
        for exc_type, handler in self.handlers.items():
            if isinstance(error, exc_type):
                return handler(error)
        
        # 使用默认处理器
        if self.fallback_handler:
            return self.fallback_handler(error)
        
        # 重新抛出
        raise


class RetryPolicy:
    """
    重试策略
    
    配置:
    - 最大重试次数
    - 指数退避
    - 可重试异常列表
    """
    
    def __init__(
        self,
        max_retries: int = 3,
        base_delay: float = 1.0,
        max_delay: float = 60.0,
        exponential_base: float = 2.0,
        retryable_exceptions: List[Type[Exception]] = None
    ):
        self.max_retries = max_retries
        self.base_delay = base_delay
        self.max_delay = max_delay
        self.exponential_base = exponential_base
        self.retryable_exceptions = retryable_exceptions or [
            NetworkError,
            APITimeoutError,
            RecoverableError,
        ]
    
    def can_retry(self, error: Exception) -> bool:
        """检查是否可以重试"""
        for exc_type in self.retryable_exceptions:
            if isinstance(error, exc_type):
                return True
        return False
    
    def get_delay(self, attempt: int) -> float:
        """计算退避延迟"""
        delay = self.base_delay * (self.exponential_base ** attempt)
        return min(delay, self.max_delay)
    
    async def execute_with_retry(
        self,
        func: Callable,
        *args,
        **kwargs
    ) -> Any:
        """执行带重试的函数"""
        last_error = None
        
        for attempt in range(self.max_retries + 1):
            try:
                return await func(*args, **kwargs) if asyncio.iscoroutinefunction(func) else func(*args, **kwargs)
            except Exception as e:
                last_error = e
                
                if not self.can_retry(e) or attempt >= self.max_retries:
                    break
                
                delay = self.get_delay(attempt)
                print(f"[重试] {attempt + 1}/{self.max_retries}, 等待 {delay:.1f}s: {e}")
                
                if asyncio.iscoroutinefunction(func):
                    await asyncio.sleep(delay)
                else:
                    import time
                    time.sleep(delay)
        
        raise last_error


def safe_execute(
    default_return: Any = None,
    log_errors: bool = True,
    reraise: bool = False
):
    """
    安全执行装饰器
    
    用法:
    @safe_execute(default_return=[], log_errors=True)
    def my_function():
        ...
    """
    def decorator(func: Callable) -> Callable:
        @wraps(func)
        async def async_wrapper(*args, **kwargs):
            try:
                return await func(*args, **kwargs)
            except Exception as e:
                if log_errors:
                    print(f"[安全执行] {func.__name__} 失败: {e}")
                if reraise:
                    raise
                return default_return
        
        @wraps(func)
        def sync_wrapper(*args, **kwargs):
            try:
                return func(*args, **kwargs)
            except Exception as e:
                if log_errors:
                    print(f"[安全执行] {func.__name__} 失败: {e}")
                if reraise:
                    raise
                return default_return
        
        if asyncio.iscoroutinefunction(func):
            return async_wrapper
        return sync_wrapper
    
    return decorator


def format_error_response(error: Exception, include_trace: bool = False) -> dict:
    """格式化错误响应"""
    response = {
        "error": error.__class__.__name__,
        "message": str(error),
        "category": get_error_category(error)
    }
    
    # 添加详细信息
    if isinstance(error, AIWriteXError) and error.details:
        response["details"] = error.details
    
    # 可选：包含堆栈跟踪
    if include_trace:
        import traceback
        response["traceback"] = traceback.format_exc()
    
    return response
