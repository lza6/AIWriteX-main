import re
import os
import random
import warnings
from bs4 import BeautifulSoup
import requests
import time
import sys
import shutil
import webbrowser
import markdown
from PIL import Image
import tempfile
import urllib.parse
from pathlib import Path
import json


def copy_file(src_file, dest_file):
    mkdir(os.path.dirname(dest_file))

    if os.path.exists(dest_file):
        return False

    try:
        shutil.copy2(src_file, dest_file)
    except Exception as e:  # noqa 841
        pass


def mkdir(path, clean=False):
    if os.path.exists(path):
        if clean:
            shutil.rmtree(path)
            os.makedirs(path)
    else:
        os.makedirs(path)

    return path


def get_is_release_ver():
    """
    检测是否为打包版本
    注意：Nuitka 打包后 sys.frozen 也会是 True，所以 hasattr(sys, "frozen") 能同时检测两者
    """
    if hasattr(sys, "frozen"):
        return True
    if "__compiled__" in globals():
        return True
    return False


def get_res_path(relative_path, basedir=""):
    """
    获取资源文件的绝对路径
    兼容：IDE运行、PyInstaller打包、Nuitka打包
    Args:
        relative_path: 相对路径，例如 "resources/UI/icon.ico"
        basedir: 开发环境下的基准路径（可选）
    """
    if get_is_release_ver():
        # 1. PyInstaller 专有逻辑 (解压到临时目录 _MEIPASS)
        if hasattr(sys, "_MEIPASS"):
            return os.path.join(sys._MEIPASS, relative_path)

        # 2. Nuitka (Standalone) 或 PyInstaller (Onedir) 逻辑
        # 资源文件位于可执行文件同级目录下
        exe_dir = os.path.dirname(sys.executable)
        return os.path.join(exe_dir, relative_path)

    # 3. 开发环境 (IDE)
    # 默认使用当前文件的目录，或者传入的 basedir
    # 如果 basedir 为空，尝试自动定位到项目根目录（假设 main.py 在根目录）
    if not basedir:
        basedir = os.path.dirname(os.path.abspath(__file__))

    return os.path.join(basedir, relative_path)


def get_random_platform(platforms):
    """
    根据权重随机选择一个启用的平台。
    自动归一化权重,无需用户关心总和是否为1。
    """
    enabled_platforms = [p for p in platforms if p.get("enabled", True)]

    if not enabled_platforms:
        warnings.warn("没有启用的平台，将自动启用所有平台", UserWarning)
        enabled_platforms = platforms
        for p in enabled_platforms:
            p["enabled"] = True

    total_weight = sum(p["weight"] for p in enabled_platforms)

    if total_weight <= 0:
        warnings.warn("启用平台权重总和为0，将平均分配权重", UserWarning)
        avg_weight = 1.0 / len(enabled_platforms)
        for p in enabled_platforms:
            p["weight"] = avg_weight
        total_weight = 1.0

    if abs(total_weight - 1.0) > 0.01:
        for platform in enabled_platforms:
            platform["weight"] = platform["weight"] / total_weight
        total_weight = 1.0

    rand = random.uniform(0, total_weight)
    cumulative_weight = 0
    for platform in enabled_platforms:
        cumulative_weight += platform["weight"]
        if rand <= cumulative_weight:
            return platform["name"]

    return enabled_platforms[0]["name"]


def extract_html(html, max_length=64):
    title = None
    digest = None

    soup = BeautifulSoup(html, "html.parser")
    title_tag = soup.find("title")
    h1_tag = soup.find("h1")

    if title_tag:
        title = " ".join(title_tag.get_text(strip=True).split())
    elif h1_tag:
        title = " ".join(h1_tag.get_text(strip=True).split())

    text = soup.get_text(separator=" ", strip=True)
    text = re.sub(r"\s+", " ", text).strip()

    if text:
        if len(text) > max_length:
            digest = text[:max_length] + "..."
        else:
            digest = text

    return title, digest


def get_latest_file_os(dir_path):
    """使用 os 模块获取目录下最近创建/保存的文件。"""
    files = [
        os.path.join(dir_path, f)
        for f in os.listdir(dir_path)
        if os.path.isfile(os.path.join(dir_path, f))
    ]
    if not files:
        return None

    latest_file = max(files, key=os.path.getmtime)
    return latest_file


def extract_image_urls(html_content, no_repeate=True):
    patterns = [
        r'<img[^>]*?src=["\'](.*?)["\']',  # 匹配 src
        r'<img[^>]*?srcset=["\'](.*?)["\']',  # 匹配 srcset
        r'<img[^>]*?data-(?:src|image)=["\'](.*?)["\']',  # 匹配 data-src/data-image
        r'background(?:-image)?\s*:\s*url$["\']?(.*?)["\']?$',  # 匹配 background
    ]
    urls = []
    for pattern in patterns:
        matches = re.findall(pattern, html_content, re.IGNORECASE)
        urls.extend(
            [url for match in matches for url in (match.split(",") if "," in match else [match])]
        )
    if no_repeate:
        return list(set(urls))
    else:
        return urls


def download_and_save_image(image_url, local_image_folder):
    """
    下载图片并保存到本地。

    Args:
        image_url (str): 图片链接。
        local_image_folder (str): 本地图片保存文件夹。

    Returns:
        str: 本地图片文件路径，如果下载失败则返回 None。
    """
    try:
        if not os.path.exists(local_image_folder):
            os.makedirs(local_image_folder)

        from src.ai_write_x.config.config import Config
        proxy = Config.get_instance().proxy
        proxies = {"http": proxy, "https": proxy} if proxy else None

        response = requests.get(image_url, stream=True, allow_redirects=True, proxies=proxies, timeout=30)
        response.raise_for_status()

        timestamp = str(int(time.time()))
        local_filename = os.path.join(local_image_folder, f"{timestamp}.jpg")
        with open(local_filename, "wb") as file:
            for chunk in response.iter_content(chunk_size=8192):
                file.write(chunk)

        return local_filename
    except Exception:
        return None


def compress_html(content, use_compress=True):
    if use_compress:
        return content

    # 移除注释
    content = re.sub(r"<!--.*?-->", "", content, flags=re.DOTALL)
    # 移除换行和制表符
    content = re.sub(r"[\n\t]+", "", content)
    # 移除多余空格（保留属性分隔空格）
    content = re.sub(r"\s+", " ", content)
    # 移除=、>、<、;、: 前后的空格
    content = re.sub(r"\s*([=><;,:])\s*", r"\1", content)
    # 移除标签间空格
    content = re.sub(r">\s+<", "><", content)
    return content


def decompress_html(compressed_content, use_compress=True):
    """
    格式化 HTML 内容，处理压缩和未压缩 HTML，确保输出的内容适合网页渲染。

    参数：
        compressed_content (str): 输入的 HTML 字符串
        use_compress (bool): 是否作为压缩 HTML 处理（True）或直接返回（False）

    返回：
        str: 格式化后的 HTML 字符串
    """
    if not use_compress or re.search(r"\n\s{2,}", compressed_content):
        return compressed_content.strip()

    try:
        soup = BeautifulSoup(compressed_content, "lxml")

        for element in soup.find_all(text=True):
            if element.strip() == "":  # type: ignore
                element.extract()
            elif element.strip().startswith("<!--") and element.strip().endswith("-->"):  # type: ignore # noqa 501
                element.extract()

        is_fragment = not (
            compressed_content.strip().startswith("<!DOCTYPE")
            or compressed_content.strip().startswith("<html")
        )

        if is_fragment:
            formatted_lines = []
            for child in soup.contents:
                if hasattr(child, "prettify"):
                    formatted_lines.append(child.prettify().strip())  # type: ignore
                else:
                    formatted_lines.append(str(child).strip())
            return "\n".join(line for line in formatted_lines if line)

        return soup.prettify(formatter="minimal").strip()

    except Exception as e:  # noqa 841
        return compressed_content.strip()


def open_url(file_url):
    try:
        if file_url.startswith(("http://", "https://")):
            webbrowser.open(file_url)
        else:
            if not os.path.exists(file_url):
                return "文件不存在！"

            file_path = Path(file_url).resolve()

            if sys.platform == "win32":
                # Windows特殊处理：直接使用文件路径
                import subprocess

                subprocess.run(["start", "", str(file_path)], shell=True)
            elif sys.platform == "darwin":
                html_url = f"file://{urllib.parse.quote(str(file_path))}"
                webbrowser.open(html_url)
            else:
                html_url = file_path.as_uri()
                webbrowser.open(html_url)

        return ""
    except Exception as e:
        return str(e)


def is_valid_url(url):
    try:
        result = urllib.parse.urlparse(url)
        return all([result.scheme in ["http", "https"], result.netloc])
    except Exception as e:  # noqa 841
        return False


def sanitize_filename(filename):
    illegal_chars = r'[<>:"/\\|?*\x00-\x1F]'
    sanitized = re.sub(illegal_chars, "_", filename)
    sanitized = sanitized.strip().strip(".")
    return sanitized or "default_filename"


def is_llm_supported(llm, key_name, env_vars):
    """
    检查CrewAI是否完整支持LLM配置
    排除通过显式配置工作的提供商（如openrouter）
    """
    # OpenRouter 等提供商通过显式配置工作，不依赖ENV_VARS
    if llm.lower() == "openrouter":
        return True

    if llm.lower() not in env_vars:
        return False

    # 检查是否有正确的API密钥配置
    llm_config = env_vars[llm.lower()]
    for config in llm_config:
        if config.get("key_name") == key_name.upper():
            return True

    return False


def remove_code_blocks(content):
    """
    移除所有Markdown代码块标识但保留内容
    处理以下格式：
      ```markdown 内容 ```
      ```html 内容 ```
      ```javascript 内容 ```
      ``` 内容 ```
      `内容`
    """
    content = re.sub(r"```\w*\s*", "", content, flags=re.IGNORECASE)
    content = re.sub(r"`([^`]*)`", r"\1", content)
    content = re.sub(r'<(Reasoning|Critique)>.*?</\1>', '', content, flags=re.IGNORECASE | re.DOTALL)
    content = re.sub(r'<(Reasoning|Critique)>.*', '', content, flags=re.IGNORECASE | re.DOTALL)
    
    pattern = r"""
    [(\[【]            # 起始括号（全角/半角）
    \s*               # 可选空白
    (全文\s*)?        # 可选"全文"前缀
    (约|共|总计|合计)? # 量词
    \s*\d+\s*字       # 核心匹配：数字+"字"
    \s*[)\]】]        # 结束括号
    \s*$              # 确保在行末
    """
    return re.sub(pattern, "", content, flags=re.VERBOSE | re.MULTILINE).strip()


def markdown_to_plaintext(md_text):
    """提取文章文本内容"""
    text = re.sub(r"^#{1,6}\s+", "", md_text, flags=re.MULTILINE)
    text = re.sub(r"(\*\*|\*|~~|__)(.*?)\1", r"\2", text)
    text = re.sub(r"`{1,3}(.*?)`{1,3}", r"\1", text)
    text = re.sub(r"!?$(.*?)$$[^)]*$", r"\1", text)
    text = re.sub(r"^\s*([-*+]|\d+\.)\s+", r"\1 ", text, flags=re.MULTILINE)
    text = re.sub(r"^>\s*", "", text, flags=re.MULTILINE)

    return text.strip()


def extract_markdown_content(content):
    """从Markdown内容中提取标题和摘要"""
    lines = content.strip().split("\n")
    title = None
    digest = ""

    for line in lines:
        line = line.strip()
        if line.startswith("# "):
            title = line[2:].strip()
            break
    
    if title is None:
        for line in lines:
            line = line.strip()
            if line:
                title = line
                break

    content_lines = []
    for line in lines:
        line = line.strip()
        if line and not line.startswith("#"):
            content_lines.append(line)
        if len(content_lines) >= 3:
            break

    digest = " ".join(content_lines)[:100] + "..." if content_lines else "无摘要"

    return title, digest


def extract_text_content(content):
    """从文本内容中提取标题和摘要"""
    lines = content.strip().split("\n")

    title = lines[0].strip() if lines else None

    content_lines = [line.strip() for line in lines[1:] if line.strip()]
    digest = " ".join(content_lines[:3])[:100] + "..." if content_lines else "无摘要"

    return title, digest


def text_to_html(text_content):
    """将纯文本转换为HTML"""
    lines = text_content.split("\n")
    html_lines = []

    for line in lines:
        line = line.strip()
        if line:
            html_lines.append(f"<p>{line}</p>")
        else:
            html_lines.append("<br>")

    return "\n".join(html_lines)


def get_format_article(ext, article):
    """将不同格式的文章转换为HTML"""
    if ext == ".md" or ext == ".markdown":
        md = markdown.Markdown(extensions=["extra", "codehilite"])
        return md.convert(article)
    elif ext == ".txt":
        return text_to_html(article)
    else:
        return article


def is_local_path(url):
    """判断URL是否为本地路径"""
    parsed = urllib.parse.urlparse(url)
    if parsed.scheme in ("http", "https", "ftp"):
        return False

    if url.startswith("/images/") or url.startswith("/static/"):
        return False

    if os.path.isabs(url):
        return True

    if url.startswith("./") or url.startswith("../"):
        return True

    return True


def resolve_image_path(url):
    """将图片URL解析为实际文件系统路径"""
    from src.ai_write_x.utils.path_manager import PathManager

    parsed = urllib.parse.urlparse(url)
    if parsed.scheme in ("http", "https", "ftp"):
        return url

    if url.startswith("/"):
        if url.startswith("/images/"):
            filename = url.replace("/images/", "")
            local_path = PathManager.get_image_dir() / filename
            return str(local_path)
        elif os.path.isabs(url):
            return url

    if os.path.isabs(url):
        return url

    return url


def crop_cover_image(image_path, target_size=(900, 384)):
    """
    将封面图片裁剪为指定尺寸
    先缩放至填满目标尺寸，然后居中裁剪
    """
    try:
        img = Image.open(image_path)
        original_width, original_height = img.size
        target_width, target_height = target_size

        scale_x = target_width / original_width
        scale_y = target_height / original_height
        scale = max(scale_x, scale_y)

        new_width = int(original_width * scale)
        new_height = int(original_height * scale)
        img = img.resize((new_width, new_height), Image.LANCZOS)  # type: ignore

        left = (new_width - target_width) // 2
        top = (new_height - target_height) // 2
        right = left + target_width
        bottom = top + target_height

        img = img.crop((left, top, right, bottom))

        temp_file = tempfile.NamedTemporaryFile(suffix=".jpg", delete=False)
        img.save(temp_file.name, "JPEG", quality=95)
        temp_file.close()

        return temp_file.name

    except Exception:
        return None


def fix_mac_clipboard(value):
    """处理输入框变化，修复macOS重复粘贴问题"""
    if sys.platform == "darwin" and value:
        length = len(value)
        if length > 0 and length % 2 == 0:
            half_length = length // 2
            first_half = value[:half_length]
            second_half = value[half_length:]

            if first_half == second_half:
                return first_half
    return value


def get_gui_icon():
    """获取GUI窗口图标，支持跨平台和多种用途"""
    import sys
    import os
    import base64
    from pathlib import Path

    gui_dir = Path(__file__).parent.parent / "assets"

    # 创建图标资源管理器
    class IconManager:
        def __init__(self):
            self.gui_dir = gui_dir

        def get_icon_path(self, format_type="ico"):
            """获取指定格式的图标路径"""
            icon_files = {"ico": "icon.ico", "png": "icon.png", "icns": "icon.icns"}
            return get_res_path(
                os.path.join("UI", icon_files.get(format_type, "icon.ico")), str(self.gui_dir)
            )

        def get_platform_icon(self):
            """根据平台返回最适合的图标"""
            if sys.platform == "darwin":  # macOS
                # 优先PNG的Base64编码，回退到icns
                png_path = self.get_icon_path("png")
                if os.path.exists(png_path):
                    try:
                        with open(png_path, "rb") as f:
                            return base64.b64encode(f.read())
                    except Exception:
                        pass

                icns_path = self.get_icon_path("icns")
                if os.path.exists(icns_path):
                    return icns_path

            elif sys.platform == "linux":  # Linux
                png_path = self.get_icon_path("png")
                if os.path.exists(png_path):
                    return png_path

            # Windows 或回退方案
            return self.get_icon_path("ico")

    icon_manager = IconManager()
    return icon_manager.get_platform_icon()


def get_file_extension(article_format: str) -> str:
    """根据文章格式获取文件扩展名"""
    format_map = {"HTML": "html", "MARKDOWN": "md", "TXT": "txt", "MD": "md"}

    return format_map.get(article_format.upper(), "txt")


def format_log_message(msg: str, msg_type: str = "info") -> str:
    """
    统一日志格式化接口，检测并避免重复格式化

    Args:
        msg: 原始消息
        msg_type: 消息类型

    Returns:
        格式化后的消息
    """
    timestamp_pattern = r"^\[\d{2}:\d{2}:\d{2}\]"
    if re.match(timestamp_pattern, msg.strip()):
        return msg

    type_pattern = r"\[([A-Z]+)\]:"
    if re.search(type_pattern, msg):
        if not re.match(timestamp_pattern, msg.strip()):
            timestamp = time.strftime("%H:%M:%S")
            return f"[{timestamp}] {msg}"
        return msg

    timestamp = time.strftime("%H:%M:%S")
    return f"[{timestamp}] [{msg_type.upper()}]: {msg}"


def get_cover_path(article_path):
    cover_path = None

    if article_path:
        design_file = Path(article_path).with_suffix(".design.json")
        if design_file.exists():
            try:
                with open(design_file, "r", encoding="utf-8") as f:
                    design_data = json.load(f)
                    cover_path = design_data.get("cover", None)
            except Exception:
                pass

    return cover_path
