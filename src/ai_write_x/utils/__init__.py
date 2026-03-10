"""
AIWriteX 工具模块 - 统一工具入口

此模块提供统一的工具函数和类，包括:
- 日志系统 (log)
- 异常处理 (exception_handler)
- 通用工具 (utils)
- 路径管理 (path_manager)
"""

# 日志系统 - 统一入口
from src.ai_write_x.utils.log import (
    print_log,
    print_traceback,
    init_ui_mode,
    init_cli_mode,
    LogManager,
    set_process_queue,
    get_process_queue,
    setup_process_logging,
    setup_logging,
    strip_ansi_codes,
    print_ai_log
)

# 异常处理 - 统一入口
from src.ai_write_x.utils.exception_handler import (
    ExceptionHandler,
    ErrorCategory,
    ErrorSeverity,
    safe_execute,
    exception_handler_decorator,
    exception_handler
)

# 保持向后兼容的日志别名
from types import SimpleNamespace
log = SimpleNamespace(
    print_log=print_log,
    print_traceback=print_traceback,
    init_ui_mode=init_ui_mode,
    init_cli_mode=init_cli_mode,
    LogManager=LogManager,
    set_process_queue=set_process_queue,
    get_process_queue=get_process_queue,
    setup_process_logging=setup_process_logging,
    setup_logging=setup_logging,
    strip_ansi_codes=strip_ansi_codes,
    print_ai_log=print_ai_log
)

__all__ = [
    # 日志
    'print_log',
    'print_traceback',
    'init_ui_mode',
    'init_cli_mode',
    'LogManager',
    'set_process_queue',
    'get_process_queue',
    'setup_process_logging',
    'setup_logging',
    'strip_ansi_codes',
    'print_ai_log',
    'log',

    # 异常处理
    'ExceptionHandler',
    'ErrorCategory',
    'ErrorSeverity',
    'safe_execute',
    'exception_handler_decorator',
    'exception_handler'
]
