from datetime import datetime
from pathlib import Path

from fastapi import APIRouter, HTTPException, File, UploadFile
from fastapi.responses import HTMLResponse, Response
import uuid
from pydantic import BaseModel
from typing import List, Optional
import json

from src.ai_write_x.config.config import Config
from src.ai_write_x.utils.path_manager import PathManager
from src.ai_write_x.tools.wx_publisher import pub2wx
from src.ai_write_x.utils import utils
from src.ai_write_x.utils import log
from src.ai_write_x.core.adaptive_template_engine import ContentAnalyzer, ModularTemplateBuilder, ComponentType, DesignScheme

from bs4 import BeautifulSoup
import re

def html_to_markdown(html_content: str) -> str:
    """
    将提取的 HTML 核心内容还原为干净的 Markdown
    用于给 AI 设计师提供更高质量、更具结构感的输入
    """
    if not html_content:
        return ""
    
    soup = BeautifulSoup(html_content, "html.parser")
    md_lines = []
    
    # 我们只遍历顶层元素或直接子元素，避免 find_all 引起的重复提取
    # 如果 html_content 本身就是碎片的集合，soup 可能包装了一个 <html><body>
    target = soup.body if soup.body else soup
    
    for el in target.find_all(['p', 'img', 'h2', 'h3', 'h4', 'blockquote', 'ul', 'ol'], recursive=False):
        if el.name == 'h2':
            md_lines.append(f"## {el.get_text().strip()}")
        elif el.name == 'h3':
            md_lines.append(f"### {el.get_text().strip()}")
        elif el.name == 'h4':
            md_lines.append(f"#### {el.get_text().strip()}")
        elif el.name == 'p':
            # 如果段落里包含图片，我们尝试提取图片并放在段落前后，或者转为 md 图片
            # 这里的逻辑是：我们要的是干净的 Markdown
            content_parts = []
            for child in el.children:
                if child.name == 'img':
                    alt = child.get('alt', 'image')
                    src = child.get('src', '')
                    if src:
                        content_parts.append(f"![{alt}]({src})")
                elif child.name == 'br':
                    content_parts.append("\n")
                else:
                    content_parts.append(child.get_text().strip())
            
            text = " ".join([p for p in content_parts if p])
            if text:
                md_lines.append(text)
        elif el.name == 'img':
            alt = el.get('alt', 'image')
            src = el.get('src', '')
            if src:
                md_lines.append(f"![{alt}]({src})")
        elif el.name == 'blockquote':
            md_lines.append(f"> {el.get_text().strip()}")
        elif el.name == 'ul' or el.name == 'ol':
            for li in el.find_all('li'):
                md_lines.append(f"- {li.get_text().strip()}")
        
        md_lines.append("") # 换行
        
    return "\n".join(md_lines).strip()


router = APIRouter(prefix="/api/articles", tags=["articles"])

# ==================== 后期补图日志缓冲区 ====================
import threading
import time as _time

_img_gen_log_buffer = []  # [{type, message, timestamp}, ...]
_img_gen_log_lock = threading.Lock()


def _clear_img_gen_logs():
    """清空日志缓冲区"""
    with _img_gen_log_lock:
        _img_gen_log_buffer.clear()


def _push_img_gen_log(msg_type, message):
    """添加一条日志到缓冲区"""
    with _img_gen_log_lock:
        _img_gen_log_buffer.append({
            "type": msg_type,
            "message": message,
            "timestamp": _time.time()
        })


@router.get("/logs")
async def get_img_gen_logs(since: int = 0, limit: int = 50):
    """获取后期补图日志（供前端轮询）"""
    with _img_gen_log_lock:
        logs = _img_gen_log_buffer[since:since + limit]
        next_index = min(since + limit, len(_img_gen_log_buffer))
    return {"logs": logs, "nextIndex": next_index}


class ArticleContentUpdate(BaseModel):
    content: str


class PublishRequest(BaseModel):
    article_paths: List[str]
    account_indices: List[int]
    platform: str = "wechat"


@router.get("/")
async def list_articles():
    """获取文章列表"""
    try:
        articles_dir = PathManager.get_article_dir()
        articles = []

        patterns = ["*.html", "*.md", "*.txt"]
        article_files = []

        for pattern in patterns:
            article_files.extend(articles_dir.glob(pattern))

        for file_path in article_files:
            stat = file_path.stat()
            title = file_path.stem.replace("_", "|")
            status = get_publish_status(title)

            articles.append(
                {
                    "name": file_path.stem,
                    "path": str(file_path),
                    "title": title,
                    "format": file_path.suffix[1:].upper(),
                    "size": f"{stat.st_size / 1024:.2f} KB",
                    "create_time": datetime.fromtimestamp(stat.st_ctime).strftime(
                        "%Y-%m-%d %H:%M:%S"
                    ),
                    "status": status,
                }
            )

        articles.sort(key=lambda x: x["create_time"], reverse=True)
        return {"status": "success", "data": articles}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/content")
async def get_article_content(path: str):
    """获取文章内容 - 使用查询参数"""
    file_path = Path(path)
    if not file_path.exists():
        raise HTTPException(status_code=404, detail="文章不存在")

    content = file_path.read_text(encoding="utf-8")
    return Response(content=content, media_type="text/plain; charset=utf-8")


@router.put("/content")
async def update_article_content(path: str, update: ArticleContentUpdate):
    """更新文章内容"""
    file_path = Path(path)
    if not file_path.exists():
        raise HTTPException(status_code=404, detail="文章不存在")

    file_path.write_text(update.content, encoding="utf-8")
    return {"status": "success", "message": "文章已保存"}


@router.get("/preview")
async def preview_article(path: str):
    """安全预览文章 - 使用查询参数"""
    file_path = Path(path)
    if not file_path.exists():
        return HTMLResponse("<p>文章不存在</p>")

    content = file_path.read_text(encoding="utf-8")
    return HTMLResponse(
        content, headers={"Content-Security-Policy": "default-src 'self' 'unsafe-inline'"}
    )


@router.delete("/{article_path:path}")
async def delete_article(article_path: str):
    """删除文章"""
    file_path = Path(article_path)
    if file_path.exists():
        file_path.unlink()
        return {"status": "success", "message": "文章已删除"}
    raise HTTPException(status_code=404, detail="文章不存在")


@router.post("/publish")
async def publish_articles(request: PublishRequest):
    """发布文章到平台"""
    try:
        config = Config.get_instance()
        credentials = config.wechat_credentials

        if not credentials:
            raise HTTPException(status_code=400, detail="未配置微信账号")

        success_count = 0
        fail_count = 0
        error_details = []
        warning_details = []
        format_publish = config.format_publish
        
        # 记录成功发布的文章路径（用于自动删除）
        published_article_paths = set()

        for article_path in request.article_paths:
            file_path = Path(article_path)
            if not file_path.exists():
                fail_count += 1
                error_details.append(f"{article_path}: 文件不存在")
                continue

            content = file_path.read_text(encoding="utf-8")

            ext = file_path.suffix.lower()

            try:
                if ext == ".html":
                    title, digest = utils.extract_html(content)
                elif ext == ".md":
                    title, digest = utils.extract_markdown_content(content)
                elif ext == ".txt":
                    title, digest = utils.extract_text_content(content)
                else:
                    fail_count += 1
                    error_details.append(f"{article_path}: 不支持的文件格式 {ext}")
                    continue
            except Exception as e:
                fail_count += 1
                error_details.append(f"{article_path}: 内容提取失败 - {str(e)}")
                continue

            if title is None:
                fail_count += 1
                error_details.append(f"{article_path}: 标题提取失败，无法发布")
                continue

            for account_index in request.account_indices:
                if account_index >= len(credentials):
                    continue

                cred = credentials[account_index]
                try:
                    article_to_publish = content
                    if ext != ".html" and format_publish:
                        article_to_publish = utils.get_format_article(ext, content)

                    message, _, success = pub2wx(
                        title=title,
                        digest=digest,
                        article=article_to_publish,
                        appid=cred["appid"],
                        appsecret=cred["appsecret"],
                        author=cred.get("author", ""),
                        cover_path=utils.get_cover_path(article_path),
                    )

                    if success:
                        success_count += 1
                        # 记录成功发布的文章路径
                        published_article_paths.add(article_path)
                        # 如果message包含权限回收提示,添加到warning_details
                        if message and "草稿箱" in message:
                            warning_details.append(f"{cred.get('author', '未命名')}: {message}")

                        save_publish_record(
                            article_path=article_path,
                            platform="wechat",
                            account_info={
                                "appid": cred["appid"],
                                "author": cred.get("author", ""),
                                "account_type": "wechat_official",
                            },
                            success=True,
                            error=message if "草稿箱" in message else None,
                        )
                    else:
                        fail_count += 1
                        save_publish_record(
                            article_path=article_path,
                            platform="wechat",
                            account_info={
                                "appid": cred["appid"],
                                "author": cred.get("author", ""),
                                "account_type": "wechat_official",
                            },
                            success=False,
                            error=message,
                        )

                except Exception as e:
                    fail_count += 1
                    error_msg = str(e)
                    save_publish_record(
                        article_path=article_path,
                        platform="wechat",
                        account_info={
                            "appid": cred["appid"],
                            "author": cred.get("author", ""),
                            "account_type": "wechat_official",
                        },
                        success=False,
                        error=error_msg,
                    )
                    error_details.append(f"{cred.get('author', '未命名')}: {error_msg}")

        # 自动删除成功发布的文章
        deleted_articles = []
        auto_delete_enabled = Config.get_instance().config.get("auto_delete_published", False)
        
        if auto_delete_enabled:
            for article_path in published_article_paths:
                try:
                    file_path = Path(article_path)
                    if file_path.exists():
                        file_path.unlink()
                        deleted_articles.append(article_path)
                        log.print_log(f"已自动删除发布的文章: {article_path}", "info")
                except Exception as e:
                    log.print_log(f"删除文章失败: {article_path}, 错误: {e}", "warning")

        return {
            "status": "success" if success_count > 0 else "error",
            "success_count": success_count,
            "fail_count": fail_count,
            "warning_details": warning_details,
            "error_details": error_details,
            "deleted_articles": deleted_articles,
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


def get_publish_status(title: str) -> str:
    """获取文章发布状态"""
    records_file = PathManager.get_article_dir() / "publish_records.json"
    if not records_file.exists():
        return "unpublished"

    try:
        records = json.loads(records_file.read_text(encoding="utf-8"))
        article_records = records.get(title, [])

        if not article_records:
            return "unpublished"

        latest = max(article_records, key=lambda x: x.get("timestamp", ""))
        return "published" if latest.get("success") else "failed"
    except Exception:
        return "unpublished"


def save_publish_record(
    article_path: str, platform: str, account_info: dict, success: bool, error: Optional[str]
):
    """保存发布记录 - 新的通用格式"""
    records_file = PathManager.get_article_dir() / "publish_records.json"

    title = Path(article_path).stem.replace("_", "|")

    records = {}
    if records_file.exists():
        try:
            records = json.loads(records_file.read_text(encoding="utf-8"))
        except Exception:
            pass

    if title not in records:
        records[title] = []

    records[title].append(
        {
            "timestamp": datetime.now().isoformat(),
            "platform": platform,
            "success": success,
            "error": error,
            "account_info": account_info,
        }
    )

    records_file.write_text(json.dumps(records, ensure_ascii=False, indent=2), encoding="utf-8")


@router.get("/platforms")
async def get_supported_platforms():
    """获取支持的发布平台列表"""
    config = Config.get_instance()

    platforms = []

    # 微信公众号
    wechat_credentials = config.wechat_credentials or []
    if wechat_credentials:
        platforms.append(
            {
                "id": "wechat",
                "name": "微信公众号",
                "icon": "wechat",
                "accounts": [
                    {
                        "index": idx,
                        "author": cred.get("author", "未命名"),
                        "appid": cred["appid"],
                        "full_info": f"{cred.get('author', '未命名')} ({cred['appid']})",
                    }
                    for idx, cred in enumerate(wechat_credentials)
                ],
            }
        )

    # 未来可扩展其他平台
    # if config.other_platform_credentials:
    #     platforms.append({...})

    return {"status": "success", "data": platforms}


@router.get("/publish-history/{article_path:path}")
async def get_publish_history(article_path: str):
    """获取文章发布历史"""
    records_file = PathManager.get_article_dir() / "publish_records.json"

    title = Path(article_path).stem.replace("_", "|")

    if not records_file.exists():
        return {"status": "success", "data": {"article_path": article_path, "records": []}}

    try:
        records = json.loads(records_file.read_text(encoding="utf-8"))
        article_records = records.get(title, [])

        sorted_records = sorted(article_records, key=lambda x: x.get("timestamp", ""), reverse=True)

        return {
            "status": "success",
            "data": {"article_path": article_path, "records": sorted_records},
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


class ArticleDesign(BaseModel):
    article: str
    html: str
    css: str
    cover: Optional[str] = ""


@router.post("/design")
async def save_article_design(design: ArticleDesign):
    """保存文章设计(包括封面)"""
    try:
        article_path = Path(design.article)
        design_path = article_path.with_suffix(".design.json")

        design_data = {"html": design.html, "css": design.css, "cover": design.cover}  # 保存封面

        with open(design_path, "w", encoding="utf-8") as f:
            json.dump(design_data, f, ensure_ascii=False, indent=2)

        return {"success": True, "message": "设计已保存"}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/design")
async def load_article_design(article: str):
    """加载文章设计(包括封面)"""
    try:
        article_path = Path(article)
        design_path = article_path.with_suffix(".design.json")

        if not design_path.exists():
            return {"html": "", "css": "", "cover": ""}

        with open(design_path, "r", encoding="utf-8") as f:
            design_data = json.load(f)

        return {
            "html": design_data.get("html", ""),
            "css": design_data.get("css", ""),
            "cover": design_data.get("cover", ""),
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/upload-image")
async def upload_image(image: UploadFile = File(...)):
    """上传图片并返回路径"""
    try:
        # 获取图片保存目录
        image_dir = PathManager.get_image_dir()

        # 生成唯一文件名
        file_ext = Path(image.filename).suffix or ".jpg"
        unique_filename = f"{uuid.uuid4().hex}{file_ext}"
        file_path = image_dir / unique_filename

        # 保存图片
        with open(file_path, "wb") as f:
            content = await image.read()
            f.write(content)

        # 返回相对路径(用于 HTML src 属性)
        relative_path = f"/images/{unique_filename}"

        return {"status": "success", "path": relative_path, "filename": unique_filename}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/images")
async def get_images():
    """获取已上传的图片列表"""
    try:
        image_dir = PathManager.get_image_dir()
        images = []

        # 支持的图片格式
        image_extensions = {".jpg", ".jpeg", ".png", ".gif", ".webp"}

        for file_path in image_dir.iterdir():
            if file_path.is_file() and file_path.suffix.lower() in image_extensions:
                stat = file_path.stat()
                images.append({
                    "filename": file_path.name,
                    "path": f"/images/{file_path.name}",
                    "size": stat.st_size,
                    "size_display": f"{stat.st_size / 1024:.1f} KB" if stat.st_size < 1024 * 1024 else f"{stat.st_size / 1024 / 1024:.1f} MB",
                    "create_time": datetime.fromtimestamp(stat.st_ctime).strftime("%Y-%m-%d %H:%M"),
                })

        images.sort(key=lambda x: x["create_time"], reverse=True)
        return {"status": "success", "data": images}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.delete("/images/{filename}")
async def delete_image(filename: str):
    """删除指定图片"""
    try:
        image_dir = PathManager.get_image_dir()
        file_path = image_dir / filename

        # 安全检查：确保文件在 image_dir 内
        if not file_path.resolve().parent == image_dir.resolve():
            raise HTTPException(status_code=400, detail="非法路径")

        if not file_path.exists():
            raise HTTPException(status_code=404, detail="图片不存在")

        file_path.unlink()
        return {"status": "success", "message": f"图片 {filename} 已删除"}
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


class GenerateImagesRequest(BaseModel):
    path: str


@router.post("/generate-images")
async def generate_images_for_article(request: GenerateImagesRequest):
    """后期一键补图：扫描文章中的图片占位符并调用图片API生成图片
    
    支持三种占位符格式：
    1. [IMG_PROMPT: prompt | ratio]  — markdown 原始标记
    2. <div class="img-placeholder" data-img-prompt="..."> — HTML 有提示词占位
    3. <div class="img-placeholder"> (不含 data-img-prompt) — HTML 无提示词占位
    """
    from src.ai_write_x.core.visual_assets import VisualAssetsManager
    from src.ai_write_x.utils import comm as _comm
    
    # 清空日志缓冲区，准备新一轮日志
    _clear_img_gen_logs()
    
    # 拦截 comm.send_update，让日志同时写入缓冲区
    _original_send_update = _comm.send_update
    def _intercepted_send_update(msg_type, msg):
        _push_img_gen_log(msg_type, msg)
        _original_send_update(msg_type, msg)
    _comm.send_update = _intercepted_send_update
    
    try:
        res = VisualAssetsManager.auto_fix_article_images(request.path)
        if res.get("status") == "error":
            raise HTTPException(status_code=500, detail=res.get("message"))
        return res
    finally:
        # 无论成功失败，都恢复原始 send_update
        _comm.send_update = _original_send_update



class ReTemplateRequest(BaseModel):
    path: str


def _apply_automatic_highlighting(content: str, title: str) -> str:
    """
    自动关键词高亮
    识别核心动词、形容词或专有名词，并包裹 [KEY:] 或 [HL:]
    """
    if not content:
        return content
        
    # 简单的分词/关键词提取逻辑 (基于长度和常见强调词)
    import re
    keywords = re.findall(r'[\u4e00-\u9fa5]{4,8}', title) # 从标题提取长词
    if not keywords:
        keywords = ["重点", "关键", "由于", "但是", "核心", "特别", "注意", "专家", "研究", "非常", "重大"]
        
    # 限制高亮数量，防止花哨
    limit = 6
    count = 0
    
    processed_content = content
    
    # 1. 对标题中的关键词进行 HL 高亮 (仅限正文中第一次出现)
    for kw in keywords:
        if count >= limit: break
        if kw in processed_content:
            # 使用 HL 涂鸦感
            processed_content = processed_content.replace(kw, f"[HL: {kw}]", 1)
            count += 1
            
    # 2. 对一些语气词或数据词进行 KEY 胶囊化
    data_kws = ["第一", "首个", "爆发", "突破", "领先", "唯一", "震惊", "最新", "宣布"]
    for dkw in data_kws:
        if dkw in processed_content and dkw not in keywords:
            processed_content = processed_content.replace(dkw, f"[KEY: {dkw}]", 1)
            
    return processed_content


@router.post("/re-template")
async def re_template_article(request: ReTemplateRequest):
    """AI 换模板：提取现有文章核心内容并使用 AI 重新设计模板（流式）"""
    from fastapi.responses import StreamingResponse
    from src.ai_write_x.core.ai_template_designer import AITemplateDesigner
    from bs4 import BeautifulSoup

    file_path = Path(request.path)
    if not file_path.exists():
        raise HTTPException(status_code=404, detail="文章不存在")

    content = file_path.read_text(encoding="utf-8")
    ext = file_path.suffix.lower()

    # 1. 提取核心内容
    title = file_path.stem.replace("_", "|")
    core_content = ""
    inner_styles = ""
    
    if ext == ".html":
        soup = BeautifulSoup(content, "html.parser")
        
        # 1. 提取真实标题
        h1_tag = soup.find("h1")
        if h1_tag:
            title = h1_tag.get_text().strip()
            
        # 2. 深度清洗内容：只保留核心语义元素
        # 我们需要递归遍历，提取段落、图片、列表等，但丢弃所有旧的容器样式
        clean_elements = []
        
        # 寻找主内容区域
        main_body = soup.find(["main", "article"]) or soup.find("div", class_="container") or soup.find("body")
        
        if main_body:
            # 只提取核心语义元素，并采用防重机制
            processed_ids = set()
            
            # 使用 find_all 寻找所有目标标签，但通过 processed_ids 深度过滤父子嵌套
            all_elements = main_body.find_all(['p', 'img', 'h2', 'h3', 'blockquote', 'ul', 'ol'])
            
            for el in all_elements:
                if id(el) in processed_ids:
                    continue
                
                # 标记该元素的所有子孙元素为已处理
                for descendant in el.find_all(['p', 'img', 'h2', 'h3', 'blockquote', 'ul', 'ol']):
                    processed_ids.add(id(descendant))
                
                # 跳过 AI 占位符
                if el.name == 'div' and ('img-placeholder' in el.get('class', []) or 'section-icon' in el.get('class', [])):
                    continue
                
                # 清除样式
                if 'style' in el.attrs:
                    del el.attrs['style']
                for sub in el.find_all(True):
                    if 'style' in sub.attrs:
                        del sub.attrs['style']
                
                clean_elements.append(str(el))
        
        core_content_html = "\n".join(clean_elements)
        # 3. 将 HTML 还原为 Markdown，让 AI 更容易识别结构并进行高级排版
        core_content = html_to_markdown(core_content_html)
        
        # 如果还原失败，降级处理
        if not core_content.strip():
            core_content = soup.get_text(separator="\n")
    else:
        # 对 markdown 或 txt 内容做简易清理
        core_content = content.replace("[ 预留配图空间 - AI稍后生成 ]", "")

    # 注入自动高亮语义点 (确保 Stage 3 能够将其渲染为 HTML 标记)
    core_content = _apply_automatic_highlighting(core_content, title)

    designer = AITemplateDesigner()

    async def event_generator(core_content_arg=core_content):
        yield json.dumps({"type": "log", "message": "🤖 AI 设计师已感知任务，正在唤醒可视化引擎..."}) + "\n"
        yield json.dumps({"type": "log", "message": "🧬 正在提取原文深度语义结构..."}) + "\n"
        
        # 将参数绑定到本地可变或独立命名的变量，避免 UnboundLocalError
        core_content = core_content_arg
        try:
            yield json.dumps({"type": "log", "message": "🎨 正在制定全局设计蓝图与视觉色调..."}) + "\n"
            
            # 直接使用 async for 迭代异步生成器
            # AdaptiveTemplateEngine 已经处理了所有的 5 阶强化逻辑
            async for item in designer.stream_unique_template(title, core_content):
                # 直接转发所有引擎事件 (logs, thoughts, chunks, full_html)
                yield json.dumps(item) + "\n"
                
        except Exception as e:
            log.print_log(f"流式模板生成异常: {e}", "error")
            yield json.dumps({"type": "log", "message": f"❌ 严重错误: {str(e)}"}) + "\n"
            yield json.dumps({"type": "done"}) + "\n"

        except Exception as e:
            log.print_log(f"流式模板生成异常: {e}", "error")
            yield json.dumps({"type": "log", "message": f"❌ 严重错误: {str(e)}"}) + "\n"
            yield json.dumps({"type": "done"}) + "\n"

    return StreamingResponse(
        event_generator(), 
        media_type="application/x-ndjson",
        headers={
            "Cache-Control": "no-cache",
            "Connection": "keep-alive",
            "X-Accel-Buffering": "no"
        }
    )

@router.get("/{article_name}/source")
async def get_article_source(article_name: str):
    """
    获取文章的源文本（通常在生成时保存的 .source.txt 中）
    如果找不到，则尝试直接返回空字符串。
    """
    try:
        articles_dir = PathManager.get_article_dir()
        source_path = articles_dir / f"{article_name}.source.txt"
        
        if source_path.exists():
            content = source_path.read_text(encoding="utf-8")
            return {"status": "success", "content": content}
        
        # 兜底：如果没有找到对应的 source.txt，返回提示
        return {"status": "success", "content": "【系统提示：找不到该文章的原始参考文本】"}
        
    except Exception as e:
        log.print_log(f"获取文章源文件失败: {str(e)}", "error")
        raise HTTPException(status_code=500, detail=str(e))
