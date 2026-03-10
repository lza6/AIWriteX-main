"""
AIWriteX V18.1 - Structured Logger (DEPRECATED)
结构化日志系统 - 已统一到 utils/log.py

此文件保留用于向后兼容，所有功能已迁移到主日志系统。
请使用: from src.ai_write_x.utils import log
"""

# 直接导入现有的日志系统，保持完全兼容
from src.ai_write_x.utils.log import (
    print_log,
    print_traceback,
    init_ui_mode,
    init_cli_mode,
    LogManager
)

# 为了保持兼容性，将 print_log 映射为新的接口
def debug(msg: str, **kwargs):
    """调试日志 - 已统一到 print_log"""
    print_log(msg, "debug")

def info(msg: str, **kwargs):
    """信息日志 - 已统一到 print_log"""
    print_log(msg, "info")

def warning(msg: str, **kwargs):
    """警告日志 - 已统一到 print_log"""
    print_log(msg, "warning")

def error(msg: str, **kwargs):
    """错误日志 - 已统一到 print_log"""
    print_log(msg, "error")

def critical(msg: str, **kwargs):
    """严重错误日志 - 已统一到 print_log"""
    print_log(msg, "error")


# 保持向后兼容的类
class StructuredLogger:
    """
    已弃用: 请直接使用 from src.ai_write_x.utils import log
    """
    
    def __init__(self):
        pass
    
    def configure(self, **kwargs):
        """配置已统一到 LogManager"""
        pass
    
    def debug(self, msg: str, **kwargs):
        debug(msg, **kwargs)
    
    def info(self, msg: str, **kwargs):
        info(msg, **kwargs)
    
    def warning(self, msg: str, **kwargs):
        warning(msg, **kwargs)
    
    def error(self, msg: str, **kwargs):
        error(msg, **kwargs)
    
    def critical(self, msg: str, **kwargs):
        critical(msg, **kwargs)


# 全局实例（兼容旧代码）
structured_logger = StructuredLogger()
