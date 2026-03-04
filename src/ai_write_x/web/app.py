#!/usr/bin/env python
# -*- coding: UTF-8 -*-

import time
import asyncio
from pathlib import Path
from contextlib import asynccontextmanager

from fastapi import FastAPI, Request
from fastapi.staticfiles import StaticFiles
from fastapi.responses import HTMLResponse
from fastapi.templating import Jinja2Templates
from fastapi.middleware.gzip import GZipMiddleware

import uvicorn

from src.ai_write_x.version import get_version
from src.ai_write_x.version import get_version_with_prefix 
from src.ai_write_x.utils.path_manager import PathManager
from src.ai_write_x.config.config import Config
from src.ai_write_x.utils import utils

# 导入状态管理
from .state import app_state

# 导入API路由
from .api.config import router as config_router
from .api.templates import router as templates_router
from .api.articles import router as articles_router
from .api.generate import router as generate_router
from .api.spider import router as spider_router
from .api.quality import router as quality_router
from .api.knowledge import router as knowledge_router
from .api.mcp import router as mcp_router
from .api.newshub import router as newshub_router

# 添加全局状态
app_shutdown_event = asyncio.Event()


@asynccontextmanager
async def lifespan(app: FastAPI):
    try:
        import queue
        from src.ai_write_x.utils import comm, log

        # 初始化主进程日志队列
        app_state.log_queue = queue.Queue()
        app_state.is_running = True

        # 初始化 UI 模式
        log.init_ui_mode()

        # 连接 comm 到队列
        comm.set_log_queue(app_state.log_queue)

        # 其他初始化...
        app_state.config = Config.get_instance()
        if not app_state.config.load_config():
            log.print_log("配置加载失败，使用默认配置", "warning")
            
        # 启动清道夫引擎 (V3 Phase 4)
        from src.ai_write_x.core.scavenger import ScavengerEngine
        app_state.scavenger = ScavengerEngine()
        asyncio.create_task(app_state.scavenger.start_daemon())

    except Exception as e:
        log.print_log(f"Web服务启动失败: {str(e)}", "error")

    yield

    # 关闭时执行
    app_state.is_running = False
    
    if hasattr(app_state, 'scavenger') and app_state.scavenger:
        app_state.scavenger.stop_daemon()
        
    log.print_log("AIWriteX Web服务正在关闭", "info")


# 创建FastAPI应用，使用lifespan
app = FastAPI(
    title="AIWriteX Web API",
    version=get_version(),
    description="智能内容创作平台Web接口",
    lifespan=lifespan,
)

# 获取Web模块路径
# 获取Web模块路径
if utils.get_is_release_ver():
    web_path = Path(utils.get_res_path("web"))
else:
    web_path = Path(__file__).parent

static_path = web_path / "static"
templates_path = web_path / "templates"

# 挂载静态文件
app.mount("/static", StaticFiles(directory=str(static_path)), name="static")
app.mount("/images", StaticFiles(directory=PathManager.get_image_dir()), name="images")

app.add_middleware(GZipMiddleware, minimum_size=1000)

# 模板引擎
templates = Jinja2Templates(directory=str(templates_path))

# 注册API路由
app.include_router(config_router)
app.include_router(templates_router)
app.include_router(articles_router)
app.include_router(generate_router)
app.include_router(spider_router)
app.include_router(quality_router)
app.include_router(knowledge_router)
app.include_router(mcp_router)
app.include_router(newshub_router)


# 全局允许的客户端令牌集合
allowed_tokens = set()

@app.middleware("http")
async def verify_client_token(request: Request, call_next):
    # 静态资源、健康检查和主页（带Token进入）跳过验证
    path = request.url.path
    if path.startswith("/static") or path.startswith("/images") or path == "/health":
        return await call_next(request)
    
    # 获取查询参数中的token（用于首次加载同步到allowed_tokens）
    url_token = request.query_params.get("token")
    if path == "/" and url_token:
        allowed_tokens.add(url_token)
        # 将token存入cookie，方便后续JS读取或通过JS设置到全局
        response = await call_next(request)
        response.set_cookie(key="app_client_token", value=url_token, httponly=False) # JS需要读取
        return response

    # 验证 header 中的 token
    header_token = request.headers.get("X-App-Client-Token")
    if header_token in allowed_tokens:
        return await call_next(request)
        
    # 如果是访问主页但没带token，或者接口没带token且不在白名单，拒绝
    from fastapi.responses import JSONResponse
    return JSONResponse(
        status_code=403,
        content={"detail": "Access Denied: Standard browser access is disabled. Please use AIWriteX Client."}
    )

@app.get("/", response_class=HTMLResponse)
async def read_root(request: Request):
    """返回主界面"""
    return templates.TemplateResponse(
        "index.html", {"request": request, "version": get_version_with_prefix()}  # 传递版本号
    )


@app.get("/health")
async def health_check():
    """健康检查接口"""
    return {"status": "healthy", "timestamp": time.time()}


# 添加关闭接口
@app.post("/shutdown")
async def shutdown():
    """关闭服务器"""
    app_shutdown_event.set()
    return {"status": "shutting down"}


if __name__ == "__main__":
    uvicorn.run(app, host="127.0.0.1", port=7000, log_level="info")
