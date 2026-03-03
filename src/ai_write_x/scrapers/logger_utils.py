import logging
from datetime import datetime
from colorama import Fore, Back, Style, init

# 初始化colorama
init(autoreset=True)


class ColoredFormatter(logging.Formatter):
    """彩色日志格式器"""

    def format(self, record):
        # 获取原始消息
        message = record.getMessage()

        # 根据消息类型添加颜色和图标
        if "[成功]" in message:
            colored_msg = f"{Fore.GREEN}✓ {message}{Style.RESET_ALL}"
        elif "[错误]" in message:
            colored_msg = f"{Fore.RED}✗ {message}{Style.RESET_ALL}"
        elif "[警告]" in message:
            colored_msg = f"{Fore.YELLOW}⚠ {message}{Style.RESET_ALL}"
        elif "[跳过]" in message:
            colored_msg = f"{Fore.BLUE}⊘ {message}{Style.RESET_ALL}"
        elif "[信息]" in message:
            colored_msg = f"{Fore.WHITE}ℹ {message}{Style.RESET_ALL}"
        elif "[进度]" in message:
            colored_msg = f"{Fore.CYAN}⟳ {message}{Style.RESET_ALL}"
        elif "[标题]" in message:
            colored_msg = f"{Back.MAGENTA}{Fore.WHITE} {message.replace('[标题] ', '').center(56)} {Style.RESET_ALL}"
        else:
            colored_msg = message

        # 创建新的记录副本
        record.msg = colored_msg
        record.args = ()

        return super().format(record)


class ColoredLogger:
    """彩色日志输出工具类"""

    def __init__(self, name="ArticleSpider"):
        self.logger = logging.getLogger(name)
        self.logger.setLevel(logging.INFO)

        # 避免重复添加handler
        if not self.logger.handlers:
            # 创建控制台处理器
            console_handler = logging.StreamHandler()
            console_handler.setLevel(logging.INFO)
            console_handler.setFormatter(ColoredFormatter())

            # 创建文件处理器
            file_handler = logging.FileHandler("spider.log", encoding="utf-8")
            file_handler.setLevel(logging.INFO)
            file_handler.setFormatter(
                logging.Formatter(
                    "%(asctime)s - %(name)s - %(levelname)s - %(message)s"
                )
            )

            # 添加处理器到logger
            self.logger.addHandler(console_handler)
            self.logger.addHandler(file_handler)

    def success(self, message):
        """成功信息 - 绿色"""
        self.logger.info(f"[成功] {message}")

    def error(self, message):
        """错误信息 - 红色"""
        self.logger.error(f"[错误] {message}")

    def warning(self, message):
        """警告信息 - 黄色"""
        self.logger.warning(f"[警告] {message}")

    def skip(self, message):
        """跳过信息 - 蓝色"""
        self.logger.info(f"[跳过] {message}")

    def info(self, message):
        """普通信息 - 白色"""
        self.logger.info(f"[信息] {message}")

    def progress(self, message):
        """进度信息 - 青色"""
        self.logger.info(f"[进度] {message}")

    def header(self, message):
        """标题信息 - 洋红色背景"""
        print(f"{Back.MAGENTA}{Fore.WHITE}{'='*60}{Style.RESET_ALL}")
        self.logger.info(f"[标题] {message}")
        print(f"{Back.MAGENTA}{Fore.WHITE}{'='*60}{Style.RESET_ALL}")

    def separator(self):
        """分隔线"""
        print(f"{Fore.LIGHTBLACK_EX}{'-'*60}{Style.RESET_ALL}")


# 创建全局logger实例
logger = ColoredLogger()
