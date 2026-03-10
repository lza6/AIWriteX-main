import logging
import sys
import re
import time
import traceback
import multiprocessing
import threading
from datetime import datetime

from src.ai_write_x.utils import comm
from src.ai_write_x.utils import utils


class FileLoggingHandler:
    """统一的文件日志处理器"""

    def __init__(self, log_file_path):
        self.log_file_path = log_file_path
        self._lock = threading.Lock()

    def write_log(self, msg_dict):
        """
        写入日志到文件

        Args:
            msg_dict: 包含type, message, timestamp的字典
        """
        try:
            with self._lock:
                timestamp = msg_dict.get("timestamp", time.time())
                msg_type = msg_dict.get("type", "info")
                message = msg_dict.get("message", "")

                # 统一格式化
                log_entry = f"[{datetime.fromtimestamp(timestamp).strftime('%H:%M:%S')}] [{msg_type.upper()}]: {message}"  # noqa 501

                with open(self.log_file_path, "a", encoding="utf-8") as f:
                    f.write(log_entry + "\n")
                    f.flush()
        except Exception:
            # 静默处理文件写入错误
            pass


class LogManager:
    """
    日志管理器 - 负责管理日志系统的运行模式和进程间通信
    完全独立于配置系统，避免循环依赖
    """

    _instance = None
    _lock = threading.Lock()

    def __init__(self):
        if hasattr(self, "_initialized"):
            return
        self._initialized = True

        # 日志系统的核心状态
        self._ui_mode = False  # 默认为命令行模式
        self._process_log_queue = None  # 进程间日志队列
        self._file_handler = None

    def set_file_handler(self, log_file_path):
        """设置文件日志处理器"""

        self._file_handler = FileLoggingHandler(log_file_path)

    def get_file_handler(self):
        """获取文件处理器"""
        return self._file_handler

    @classmethod
    def get_instance(cls):
        """get the single instance of LogManager"""
        with cls._lock:
            if cls._instance is None:
                cls._instance = cls()
            return cls._instance

    def set_ui_mode(self, ui_mode: bool):
        """设置日志系统运行模式"""
        self._ui_mode = ui_mode

    def set_process_log_queue(self, queue):
        """设置进程间日志队列"""
        self._process_log_queue = queue

    def get_ui_mode(self) -> bool:
        """获取当前运行模式"""
        return self._ui_mode

    def get_process_log_queue(self):
        """获取进程间日志队列"""
        return self._process_log_queue


# 全局日志管理器实例
_log_manager = LogManager.get_instance()


def init_ui_mode():
    """初始化为UI模式"""
    _log_manager.set_ui_mode(True)


def init_cli_mode():
    """初始化为命令行模式"""
    _log_manager.set_ui_mode(False)


def set_process_queue(queue):
    """设置进程间日志队列"""
    _log_manager.set_process_log_queue(queue)


def get_process_queue():
    """获取当前进程绑定的日志队列"""
    return _log_manager.get_process_log_queue()


def strip_ansi_codes(text):
    """去除 ANSI 颜色代码"""
    ansi_pattern = r"\x1B(?:[@-Z\\-_]|\[[0-?]*[ -/]*[@-~])"
    return re.sub(ansi_pattern, "", text)


class ProcessLoggingHandler(logging.Handler):
    """进程专用日志处理器"""

    def __init__(self, process_queue: multiprocessing.Queue):
        super().__init__()
        self.process_queue = process_queue

    def emit(self, record):
        try:
            if record.name in ["httpx", "httpcore", "openai"]:
                return

            msg = self.format(record)
            msg = strip_ansi_codes(msg)
            self.process_queue.put(
                {
                    "type": "log",
                    "level": record.levelname,
                    "message": msg,
                    "timestamp": record.created,
                    "logger_name": record.name,
                }
            )
        except Exception:
            pass


class ProcessStreamHandler:
    """进程专用标准输出处理器"""

    def __init__(self, process_queue: multiprocessing.Queue):
        self.process_queue = process_queue
        self.original_stdout = sys.__stdout__
        self._buffer = ""
        self._last_write_time = 0
        self._flush_delay = 0.05  # 减少延迟
        self._timer = None
        self._lock = threading.Lock()
        self._pending_flush = False
        self._max_buffer_size = 10000  # 添加缓冲区大小限制

    def write(self, msg):
        if not msg:
            return

        if not utils.get_is_release_ver() and self.original_stdout:
            try:
                self.original_stdout.write(msg)
                self.original_stdout.flush()
            except Exception:
                pass

        with self._lock:
            current_time = time.time()
            self._buffer += msg
            self._last_write_time = current_time

            if len(self._buffer) > self._max_buffer_size:
                self._force_flush()
                return

            if "[AIForge]" in self._buffer:
                parts = self._buffer.split("[AIForge]")
                for i, part in enumerate(parts[:-1]):
                    if i == 0 and part.strip():
                        clean_msg = strip_ansi_codes(part.strip())
                        self._send_to_queue(clean_msg)
                    elif i > 0:
                        aiforge_msg = f"[AIForge]{part}"
                        clean_msg = strip_ansi_codes(aiforge_msg.strip())
                        if clean_msg:
                            self._send_to_queue(clean_msg)

                last_part = parts[-1]
                if last_part.startswith("[AIForge]") or not last_part.strip():
                    self._buffer = last_part
                else:
                    self._buffer = f"[AIForge]{last_part}"

            if "\\n" in self._buffer:
                if self._timer and self._timer.is_alive():
                    self._timer.cancel()
                    self._timer = None
                self._pending_flush = False

                lines = self._buffer.split("\\n")
                for line in lines[:-1]:
                    if line.strip():
                        clean_msg = strip_ansi_codes(line.strip())
                        self._send_to_queue(clean_msg)

                self._buffer = lines[-1]
            else:
                if not self._pending_flush:
                    self._pending_flush = True
                    self._timer = threading.Timer(self._flush_delay, self._delayed_flush)
                    self._timer.start()

    def _force_flush(self):
        if self._buffer.strip():
            clean_msg = strip_ansi_codes(self._buffer.strip())
            self._send_to_queue({"type": "print", "message": clean_msg, "timestamp": time.time()})
            self._buffer = ""

    def _send_to_queue(self, message):
        try:
            if isinstance(message, str):
                formatted_message = {"type": "print", "message": message, "timestamp": time.time()}
            else:
                formatted_message = message

            self.process_queue.put(formatted_message, timeout=1.0)
        except Exception:
            pass

    def _delayed_flush(self):
        """延迟刷新缓冲区"""
        with self._lock:
            if self._pending_flush:
                self.flush()
                self._pending_flush = False
            self._timer = None

    def flush(self):
        if self._buffer.strip():
            clean_msg = strip_ansi_codes(self._buffer.strip())
            self._send_to_queue({"type": "print", "message": clean_msg, "timestamp": time.time()})
            self._buffer = ""


def setup_process_logging(process_queue: multiprocessing.Queue):
    """在子进程中设置日志系统"""
    sys.stdout = ProcessStreamHandler(process_queue)
    sys.stderr = ProcessStreamHandler(process_queue)

    root_logger = logging.getLogger()
    root_logger.handlers.clear()

    handler = ProcessLoggingHandler(process_queue)
    formatter = logging.Formatter("[%(asctime)s][%(levelname)s][%(name)s]: %(message)s")
    handler.setFormatter(formatter)

    root_logger.addHandler(handler)
    root_logger.setLevel(logging.WARNING)

    logging.getLogger("httpx").setLevel(logging.ERROR)
    logging.getLogger("httpcore").setLevel(logging.ERROR)
    logging.getLogger("openai").setLevel(logging.ERROR)

    crewai_logger = logging.getLogger("crewai")
    crewai_logger.setLevel(logging.WARNING)
    crewai_logger.propagate = True


class QueueLoggingHandler(logging.Handler):
    """线程队列日志处理器（主进程使用）"""

    def __init__(self, queue):
        super().__init__()
        self.queue = queue

    def emit(self, record):
        try:
            if record.name in ["httpx", "httpcore", "openai"]:
                return

            msg = self.format(record)
            msg = strip_ansi_codes(msg)
            self.queue.put({"type": "status", "value": f"LOG: {msg}"})
        except Exception:
            self.handleError(record)


class QueueStreamHandler:
    """线程队列标准输出处理器（主进程使用）"""

    def __init__(self, queue):
        self.queue = queue
        self.original_stdout = sys.__stdout__

    def write(self, msg):
        if msg.strip():
            clean_msg = strip_ansi_codes(msg.rstrip())
            self.queue.put({"type": "status", "value": f"PRINT: {clean_msg}"})

            if not utils.get_is_release_ver() and self.original_stdout is not None:
                try:
                    self.original_stdout.write(msg.rstrip() + "\n")
                    self.original_stdout.flush()
                except UnicodeEncodeError:
                    try:
                        encoded_msg = (
                            msg.rstrip()
                            .encode(self.original_stdout.encoding or "utf-8", errors="replace")
                            .decode(self.original_stdout.encoding or "utf-8")
                        )
                        self.original_stdout.write(encoded_msg + "\n")
                        self.original_stdout.flush()
                    except Exception:
                        safe_msg = msg.rstrip().encode("ascii", errors="ignore").decode("ascii")
                        self.original_stdout.write(safe_msg + "\n")
                        self.original_stdout.flush()

    def flush(self):
        if self.original_stdout is not None:
            self.original_stdout.flush()

    def fileno(self):
        if self.original_stdout is not None:
            try:
                return self.original_stdout.fileno()
            except (AttributeError, IOError):
                pass
        raise IOError("Stream has no fileno")


def setup_logging(log_name, queue):
    """
    配置日志处理器，将 CrewAI 日志发送到队列
    自动从 LogManager 获取 ui_mode 状态

    Args:
        log_name: 日志名称
        queue: 日志队列
    """
    logger = logging.getLogger(log_name)
    logger.setLevel(logging.WARNING)
    handler = QueueLoggingHandler(queue)
    formatter = logging.Formatter("[%(asctime)s][%(levelname)s]: %(message)s")
    handler.setFormatter(formatter)
    logger.addHandler(handler)
    logger.propagate = False
    for h in logger.handlers[:]:
        if isinstance(h, logging.StreamHandler) and h is not handler:
            logger.removeHandler(h)

    ui_mode = _log_manager.get_ui_mode()
    if ui_mode and not hasattr(sys.stdout, "_is_queue_handler"):
        class DualOutputHandler:
            def __init__(self, queue, original_stdout):
                self.queue_handler = QueueStreamHandler(queue)
                self.original_stdout = original_stdout
                self._is_queue_handler = True

            def write(self, msg):
                self.queue_handler.write(msg)

                if not utils.get_is_release_ver() and self.original_stdout:
                    try:
                        self.original_stdout.write(msg)
                        self.original_stdout.flush()
                    except Exception:
                        pass

            def flush(self):
                self.queue_handler.flush()
                if self.original_stdout:
                    try:
                        self.original_stdout.flush()
                    except Exception:
                        pass

            def fileno(self):
                return self.queue_handler.fileno()

        sys.stdout = DualOutputHandler(queue, sys.stdout)


def _rich_print(msg, msg_type):
    """V6新增: 使用 Rich 库进行彩色美化输出"""
    try:
        from rich.console import Console
        from rich.text import Text
        console = Console()
        color_map = {
            "info": "cyan",
            "warning": "yellow",
            "error": "red",
            "status": "green",
            "internal": "magenta",
            "print": "white"
        }
        color = color_map.get(msg_type.lower(), "white")
        timestamp = time.strftime("%H:%M:%S")
        text = Text()
        text.append(f"[{timestamp}] [{msg_type.upper()}] ", style=f"bold {color}")
        text.append(str(msg), style=color)
        console.print(text)
    except ImportError:
        print(utils.format_log_message(str(msg), msg_type))

def print_log(msg, msg_type="status", show_in_ui=True):
    """
    统一日志接口函数 - 不再需要外部传参，自动从 LogManager 获取状态

    Args:
        msg: 日志消息
        msg_type: 消息类型
        show_in_ui: False 表示只输出到终端/文件,不发送到 UI
    """
    if not show_in_ui:
        _rich_print(msg, msg_type)
        return

    ui_mode = _log_manager.get_ui_mode()
    process_log_queue = _log_manager.get_process_log_queue()

    if ui_mode:
        if process_log_queue is not None:
            try:
                process_log_queue.put({"type": msg_type, "message": msg, "timestamp": time.time()})
            except Exception:
                _rich_print(msg, msg_type)
                return
        else:
            try:
                comm.send_update(msg_type, msg)
            except Exception:
                _rich_print(msg, msg_type)
                return

        if not utils.get_is_release_ver():
            try:
                _rich_print(msg, msg_type)
            except Exception:
                pass
    else:
        _rich_print(msg, msg_type)


def print_traceback(what, e):
    """统一错误追踪接口函数"""
    error_traceback = traceback.format_exc()
    tb = e.__traceback__
    filename = tb.tb_frame.f_code.co_filename
    line_number = tb.tb_lineno

    ret = (
        f"{what}发生错误: {str(e)}\n错误位置: {filename}:{line_number}\n错误详情:{error_traceback}"
    )

    # 使用 print_log 统一处理
    print_log(ret, "print")
    return ret


def print_ai_log(title, content, log_type="payload", req_id=None):
    """
    V23.1 新增: 专门用于记录 AI 请求和响应的详细日志
    使用 Rich Panel 展示，支持 JSON 格式化或长文本智能截断
    
    Args:
        title: 日志标题 (如 "AI Request", "AI Response")
        content: 消息原文 (字符串或字典)
        log_type: "payload" (请求载荷) 或 "response" (响应内容)
        req_id: 请求追踪 ID
    """
    try:
        from rich.console import Console
        from rich.panel import Panel
        from rich.syntax import Syntax
        from rich.text import Text
        import json

        def safe_json_default(obj):
            """处理不可序列化的对象"""
            try:
                if hasattr(obj, "to_dict"):
                    return obj.to_dict()
                if hasattr(obj, "__dict__"):
                    return str(obj.__dict__)
                return f"<<Non-serializable: {type(obj).__name__}>>"
            except Exception:
                return f"<<Error-serializable: {type(obj).__name__}>>"

        console = Console()
        
        # 确定边框颜色
        if log_type == "payload":
            border_style = "bold cyan"
            title_styled = f"[bold cyan]▲ {title}[/bold cyan]"
        else:
            border_style = "bold green"
            title_styled = f"[bold green]▼ {title}[/bold green]"
            
        if req_id:
            title_styled += f" [dim](ID: {req_id})[/dim]"

        # 处理内容显示
        rendered_content = ""
        if isinstance(content, (dict, list)):
            # 格式化 JSON (增加防御性处理)
            try:
                json_str = json.dumps(content, indent=4, ensure_ascii=False, default=safe_json_default)
                rendered_content = Syntax(json_str, "json", theme="monokai", background_color="default")
            except Exception as je:
                rendered_content = Text(f"[JSON Serialization Error] {str(je)}\nRaw: {str(content)[:1000]}")
        else:
            # 文本内容处理
            text_str = str(content)
            # 如果内容过长且非 Release 版本，尝试智能截断显示，但文件日志会保留完整
            if len(text_str) > 2000 and utils.get_is_release_ver():
                text_str = text_str[:1000] + "\n\n... [数据过大已在终端截断，完整内容请查阅日志文件] ...\n\n" + text_str[-500:]
            
            rendered_content = Text(text_str)

        # 终端实时美化显示
        panel = Panel(
            rendered_content,
            title=title_styled,
            border_style=border_style,
            expand=False,
            padding=(1, 2)
        )
        console.print(panel)
        
        # 同时记录到文件（如果配置了文件处理器）
        file_handler = _log_manager.get_file_handler()
        if file_handler:
            try:
                # 文件日志也需要序列化防御
                json_content = json.dumps(content, ensure_ascii=False, default=safe_json_default) if isinstance(content, (dict, list)) else content
                raw_msg = f"{title} [{req_id or 'N/A'}]: {json_content}"
            except Exception:
                raw_msg = f"{title} [{req_id or 'N/A'}]: [Serialization Failed] {str(content)[:500]}"
                
            file_handler.write_log({
                "type": "ai_trace",
                "message": raw_msg,
                "timestamp": time.time()
            })
            
    except Exception as e:
        # Fallback to simple print if rich fails
        print(f"[{title}] {content}")
