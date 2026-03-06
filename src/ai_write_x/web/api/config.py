#!/usr/bin/env python
# -*- coding: UTF-8 -*-

import json
import time
import asyncio
from typing import Dict, Any
from fastapi import APIRouter, HTTPException
from pydantic import BaseModel
import requests
from packaging import version


from src.ai_write_x.version import get_version
from src.ai_write_x.config.config import Config
from src.ai_write_x.utils import log
from src.ai_write_x.utils.path_manager import PathManager
from src.ai_write_x.core.platform_adapters import PlatformType


router = APIRouter(prefix="/api/config", tags=["config"])


class ConfigUpdateRequest(BaseModel):
    config_data: Dict[str, Any]


@router.get("/")
async def get_config():
    """获取当前配置"""
    try:
        config = Config.get_instance()
        config_dict = config.config

        config_data = {
            "platforms": config_dict.get("platforms", []),
            "publish_platform": config_dict.get("publish_platform", "wechat"),
            "api": config_dict.get("api", {}),
            "img_api": config_dict.get("img_api", {}),
            "wechat": config_dict.get("wechat", {}),
            "use_template": config_dict.get("use_template", True),
            "template_category": config_dict.get("template_category", ""),
            "template": config_dict.get("template", ""),
            "use_compress": config_dict.get("use_compress", True),
            "min_article_len": config_dict.get("min_article_len", 1000),
            "max_article_len": config_dict.get("max_article_len", 2000),
            "auto_publish": config_dict.get("auto_publish", False),
            "article_format": config_dict.get("article_format", "html"),
            "format_publish": config_dict.get("format_publish", True),
            "dimensional_creative": config_dict.get("dimensional_creative", {}),
            "strict_freshness": config_dict.get("strict_freshness", True),
            "aiforge_config": config.aiforge_config,
            "page_design": config_dict.get("page_design"),
        }

        return {"status": "success", "data": config_data}

    except Exception as e:
        log.print_log(f"获取配置失败: {str(e)}", "error")
        raise HTTPException(status_code=500, detail=str(e))


@router.patch("/")
async def update_config_memory(request: ConfigUpdateRequest):
    """仅更新内存中的配置,不保存到文件"""
    try:
        config = Config.get_instance()
        config_data = request.config_data.get("config_data", request.config_data)

        # 深度合并配置到内存
        def deep_merge(target, source):
            for key, value in source.items():
                if key in target and isinstance(target[key], dict) and isinstance(value, dict):
                    deep_merge(target[key], value)
                else:
                    target[key] = value

        with config._lock:
            if "aiforge_config" in config_data:
                aiforge_config_update = config_data.pop("aiforge_config")
                deep_merge(config.aiforge_config, aiforge_config_update)

            # 处理config.yaml的配置
            deep_merge(config.config, config_data)

        return {"status": "success", "message": "配置已更新(仅内存)"}
    except Exception as e:
        log.print_log(f"更新内存配置失败: {str(e)}", "error")
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/")
async def save_config_to_file():
    """保存当前内存配置到文件"""
    try:
        config = Config.get_instance()

        if config.save_config(config.config, config.aiforge_config):
            return {"status": "success", "message": "配置已保存"}
        else:
            raise HTTPException(status_code=500, detail="配置保存失败")
    except Exception as e:
        log.print_log(f"保存配置失败: {str(e)}", "error")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/default")
async def get_default_config():
    """获取默认配置"""
    try:
        config = Config.get_instance()
        return {
            "status": "success",
            "data": {
                **config.default_config,
                "aiforge_config": config.default_aiforge_config,
            },
        }
    except Exception as e:
        log.print_log(f"获取默认配置失败: {str(e)}", "error")
        raise HTTPException(status_code=500, detail=str(e))


def get_ui_config_path():
    """获取 UI 配置文件路径"""
    return PathManager.get_config_dir() / "ui_config.json"


@router.get("/ui-config")
async def get_ui_config():
    """获取 UI 配置"""
    config_file = get_ui_config_path()
    if config_file.exists():
        return json.loads(config_file.read_text(encoding="utf-8"))
    return {"theme": "light", "windowMode": "STANDARD"}


@router.post("/ui-config")
async def save_ui_config(config: dict):
    """保存 UI 配置"""
    config_file = get_ui_config_path()
    config_file.write_text(json.dumps(config, ensure_ascii=False, indent=2), encoding="utf-8")
    return {"success": True}


@router.get("/template-categories")
async def get_template_categories():
    """获取所有模板分类"""
    try:
        from src.ai_write_x.config.config import DEFAULT_TEMPLATE_CATEGORIES

        categories = PathManager.get_all_categories(DEFAULT_TEMPLATE_CATEGORIES)

        return {"status": "success", "data": categories}
    except Exception as e:
        log.print_log(f"获取模板分类失败: {str(e)}", "error")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/templates/{category}")
async def get_templates_by_category(category: str):
    """获取指定分类下的模板列表"""
    try:
        if category == "随机分类":
            return {"status": "success", "data": []}

        templates = PathManager.get_templates_by_category(category)

        return {"status": "success", "data": templates}
    except Exception as e:
        log.print_log(f"获取模板列表失败: {str(e)}", "error")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/platforms")
async def get_platforms():
    """获取所有支持的发布平台"""
    try:
        platforms = [
            {"value": platform_value, "label": PlatformType.get_display_name(platform_value)}
            for platform_value in PlatformType.get_all_platforms()
        ]

        return {"status": "success", "data": platforms}
    except Exception as e:
        log.print_log(f"获取平台列表失败: {str(e)}", "error")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/system-messages")
async def get_system_messages():
    """获取系统消息/帮助信息"""
    config = Config.get_instance()

    # 从配置中读取系统消息
    system_messages = config.config.get("system_messages", [])

    # 如果配置中没有,返回默认消息
    if not system_messages:
        system_messages = [
            {"text": "欢迎使用AIWriteX智能内容创作平台", "type": "info"},
            {"text": "本项目禁止用于商业用途，仅限个人使用", "type": "info"},
            {"text": "技术支持与业务合作，请联系522765228@qq.com", "type": "info"},
            {
                "text": "AIWriteX重新定义AI辅助内容创作的边界，融合搜索+借鉴+AI+创意四重能力，多种超绝玩法，让内容创作充满无限可能",
                "type": "info",
            },
            {"text": "更多AIWriteX功能开发中，敬请期待", "type": "info"},
        ]

    return {"status": "success", "data": system_messages}


@router.get("/page-design")
async def get_page_design_config():
    """获取页面设计配置"""
    config = Config.get_instance()
    page_design = config.get_config().get("page_design")

    # 如果配置不存在,返回None,让前端使用原始HTML
    if not page_design:
        return None

    return page_design


@router.get("/help-manual")
async def get_help_manual():
    """获取使用手册HTML内容"""
    from fastapi.responses import HTMLResponse
    from ..app import templates

    # 渲染模板
    html_content = templates.TemplateResponse(
        "components/help-manual.html", {"request": {}}
    ).body.decode("utf-8")

    return HTMLResponse(content=html_content)


@router.get("/check-updates")
async def check_for_updates():
    """检查更新 - 本地开发版已禁用"""
    current_version = get_version()
    # 本地开发版，不检查更新
    return {
        "status": "success",
        "has_update": False,
        "current_version": current_version,
        "latest_version": current_version,
        "download_url": "",
        "release_notes": "本地开发版",
    }


class URLRequest(BaseModel):
    url: str


@router.post("/open-url")
async def open_external_url(request: URLRequest):
    """打开外部链接"""
    from src.ai_write_x.utils.utils import open_url

    try:
        result = open_url(request.url)
        return {"status": "success", "message": result}
    except Exception as e:
        return {"status": "error", "message": str(e)}


# 自定义API测试请求模型
class CustomAPIConfig(BaseModel):
    name: str = ""
    api_base: str
    api_key: str
    model: str = ""
    provider: str = ""


@router.post("/test-custom-api")
async def test_custom_api(config: CustomAPIConfig):
    """测试自定义API连接"""
    try:
        import aiohttp
        
        # 构建请求
        url = config.api_base.rstrip('/') + "/chat/completions"
        headers = {
            "Authorization": f"Bearer {config.api_key}",
            "Content-Type": "application/json"
        }
        payload = {
            "model": config.model or "gpt-3.5-turbo",
            "messages": [{"role": "user", "content": "Hello"}],
            "max_tokens": 10
        }
        
        # 发送请求
        async with aiohttp.ClientSession() as session:
            async with session.post(url, json=payload, headers=headers, timeout=aiohttp.ClientTimeout(total=30)) as response:
                if response.status == 200:
                    result = await response.json()
                    return {"status": "success", "message": "连接成功!", "response": result}
                else:
                    error_text = await response.text()
                    return {"status": "error", "message": f"请求失败 (HTTP {response.status}): {error_text[:200]}"}
    except Exception as e:
        return {"status": "error", "message": f"连接失败: {str(e)}"}


@router.post("/test-custom-img-api")
async def test_custom_img_api(config: CustomAPIConfig):
    """测试自定义图片API连接 (支持OpenAI格式、异步轮询和本地预览)"""
    try:
        import aiohttp
        import os
        from src.ai_write_x.utils.path_manager import PathManager
        from src.ai_write_x.utils import utils as u
        
        # 构建请求 (OpenAI 格式: images/generations)
        url = config.api_base.rstrip('/')
        if not url.endswith('images/generations') and not url.endswith('image-synthesis'):
             url = url + "/images/generations"
        
        log.print_log(f"[ImageTest] 开始测试连接: {config.name or '未命名'}, URL: {url}", "info")
        log.print_log(f"[ImageTest] 使用模型: {config.model or '默认'}", "info")
             
        headers = {
            "Authorization": f"Bearer {config.api_key}",
            "Content-Type": "application/json"
        }
        
        # 使用一个非常简单的提示词进行测试
        # 针对不同模型动态调整尺寸，大部分API支持 1024x1024
        payload = {
            "prompt": "a cute white cat, high quality, masterpiece",
            "n": 1,
            "size": "1024x1024"
        }
        if hasattr(config, "model") and config.model:
            payload["model"] = config.model
        
        # 对于异步API（阿里/模型答），尝试开启异步模式
        is_modelscope = "modelscope" in url.lower()
        is_ali = "dashscope" in url.lower() or "aliyuncs" in url.lower()
        
        if is_modelscope:
            headers["X-ModelScope-Async-Mode"] = "true"
        if is_ali:
            headers["X-DashScope-Async"] = "enable"

        timeout = aiohttp.ClientTimeout(total=60)
        async with aiohttp.ClientSession() as session:
            async with session.post(url, json=payload, headers=headers, timeout=timeout) as response:
                if response.status != 200:
                    error_text = await response.text()
                    log.print_log(f"[ImageTest] 请求失败 (HTTP {response.status}): {error_text[:200]}", "error")
                    try:
                        error_json = json.loads(error_text)
                        msg = error_json.get("error", {}).get("message", error_text)
                    except:
                        msg = error_text
                    return {"status": "error", "message": f"请求失败 (HTTP {response.status}): {msg[:200]}"}
                
                result = await response.json()
                log.print_log(f"[ImageTest] 初始请求成功, 响应: {str(result)[:200]}...", "info")
                
                # 提取图片 URL 或 任务 ID
                img_url = None
                task_id = result.get("task_id") or (result.get("output", {}) if isinstance(result.get("output"), dict) else {}).get("task_id") or result.get("id")
                
                # 如果没有任务ID，尝试直接获取 URL (同步响应)
                if not task_id:
                    if "data" in result and len(result["data"]) > 0:
                        img_url = result["data"][0].get("url")
                    elif "output" in result and "url" in result["output"]:
                        img_url = result["output"]["url"]
                    
                    if img_url:
                        log.print_log(f"[ImageTest] 同步生成成功: {img_url}", "success")
                
                # 如果有任务ID，进行简单的轮询 (最多轮询 45 秒)
                if task_id and not img_url:
                    log.print_log(f"[ImageTest] 检测到异步任务 ID: {task_id}, 开始轮询...", "info")
                    base_task_url = config.api_base.rstrip('/')
                    if "/images/generations" in base_task_url:
                        base_task_url = base_task_url.replace("/images/generations", "")
                    
                    if is_ali:
                        task_url = f"https://dashscope.aliyuncs.com/api/v1/tasks/{task_id}"
                    else:
                        task_url = f"{base_task_url}/tasks/{task_id}"
                        
                    poll_headers = {"Authorization": f"Bearer {config.api_key}"}
                    if is_modelscope:
                        poll_headers["X-ModelScope-Task-Type"] = "image_generation"
                    
                    for _ in range(12): # 5s * 12 = 60s
                        await asyncio.sleep(5)
                        async with session.get(task_url, headers=poll_headers, timeout=10) as poll_res:
                            if poll_res.status == 200:
                                t_json = await poll_res.json()
                                output = t_json.get("output", {}) if isinstance(t_json.get("output"), dict) else t_json
                                status = t_json.get("task_status") or output.get("task_status") or t_json.get("status") or output.get("status")
                                
                                if status in ("SUCCEEDED", "SUCCEED", "COMPLETED", "success"):
                                    log.print_log(f"[ImageTest] 任务完成, 状态: {status}", "success")
                                    if "output_images" in t_json and len(t_json["output_images"]) > 0:
                                        img_url = t_json["output_images"][0]
                                    elif "results" in output and len(output["results"]) > 0:
                                        img_url = output["results"][0].get("url")
                                    elif "data" in t_json and len(t_json["data"]) > 0:
                                        img_url = t_json["data"][0].get("url")
                                    elif "url" in output:
                                        img_url = output["url"]
                                    break
                                elif status in ("FAILED", "CANCELED", "failed", "error"):
                                    log.print_log(f"[ImageTest] 任务失败, 状态: {status}", "error")
                                    return {"status": "error", "message": f"生成失败: {status}"}
                                else:
                                    log.print_log(f"[ImageTest] 轮询中... 状态: {status}", "info")
                
                if img_url:
                    # 下载图片并返回预览路径
                    log.print_log(f"[ImageTest] 正在下载预览图: {img_url}", "info")
                    image_dir = PathManager.get_image_dir()
                    file_name = f"test_{int(time.time())}.png"
                    file_path = os.path.join(str(image_dir), file_name)
                    
                    async with session.get(img_url, timeout=30) as img_res:
                        if img_res.status == 200:
                            img_data = await img_res.read()
                            with open(file_path, "wb") as f:
                                f.write(img_data)
                            log.print_log(f"[ImageTest] 预览图下载完成: {file_name}", "success")
                            return {
                                "status": "success", 
                                "message": "测试成功! 已生成预览图片。", 
                                "url": f"/images/{file_name}"
                            }
                
                log.print_log(f"[ImageTest] 连接成功但未获取到图片 URL", "warning")
                return {"status": "success", "message": "连接成功 (未获取到图片预览)", "response": result}
                
    except Exception as e:
        log.print_log(f"[ImageTest] 连接发生异常: {str(e)}", "error")
        return {"status": "error", "message": f"连接发生异常: {str(e)}"}


class ComfyUIConfig(BaseModel):
    api_base: str = ""


@router.post("/test-comfyui")
async def test_comfyui(config: ComfyUIConfig):
    """测试ComfyUI连接"""
    try:
        import aiohttp
        
        api_base = config.api_base.rstrip('/')
        test_url1 = f"{api_base}/system_stats"
        test_url2 = f"{api_base}/history"
        
        # 测试ComfyUI的系统端点
        async with aiohttp.ClientSession() as session:
            # 尝试访问系统端点
            async with session.get(test_url1, timeout=aiohttp.ClientTimeout(total=10)) as response:
                if response.status == 200:
                    return {"status": "success", "message": f"连接成功! (请求了: {test_url1}) 可以开始生成图片了。"}
                elif response.status == 404:
                    # 尝试 /history 端点
                    async with session.get(test_url2, timeout=aiohttp.ClientTimeout(total=10)) as response2:
                        if response2.status == 200:
                            return {"status": "success", "message": f"连接成功! (请求了: {test_url2}) 可以开始生成图片了。"}
                        return {"status": "error", "message": f"ComfyUI响应异常 (HTTP {response2.status})\n请求地址: {test_url2}"}
                else:
                    error_text = await response.text()
                    return {"status": "error", "message": f"连接失败 (HTTP {response.status})\n请求地址: {test_url1}\n详情: {error_text[:200]}"}
    except aiohttp.ClientConnectorError:
        return {"status": "error", "message": f"无法连接到目标地址: {api_base}。\n请确认:\n1. ComfyUI本地exe是否已完全启动。\n2. 地址/端口确实为 {api_base} (默认通常是 http://127.0.0.1:8188)。"}
    except Exception as e:
        return {"status": "error", "message": f"连接请求失败 (向 {api_base} 发送请求时出错):\n{str(e)}"}


@router.post("/list-models")
async def list_models(config: CustomAPIConfig):
    """获取API可用模型列表"""
    try:
        import aiohttp
        
        # 尝试多种端点
        url = config.api_base.rstrip('/')
        headers = {
            "Authorization": f"Bearer {config.api_key}",
            "Content-Type": "application/json"
        }
        
        # 尝试不同的模型列表端点
        endpoints = [
            "/v1/models",
            "/models",
            "/api/models"
        ]
        
        async with aiohttp.ClientSession() as session:
            for endpoint in endpoints:
                try:
                    full_url = url + endpoint
                    async with session.get(full_url, headers=headers, timeout=aiohttp.ClientTimeout(total=15)) as response:
                        if response.status == 200:
                            result = await response.json()
                            # 解析不同格式的响应
                            models = []
                            if "data" in result and isinstance(result["data"], list):
                                models = [m.get("id", "") for m in result["data"] if m.get("id")]
                            elif "models" in result and isinstance(result["models"], list):
                                models = [m.get("id", "") or m.get("name", "") for m in result["models"] if m.get("id") or m.get("name")]
                            elif isinstance(result, list):
                                models = [m.get("id", "") or m.get("name", "") for m in result if isinstance(m, dict)]
                            
                            if models:
                                return {"status": "success", "models": models}
                except Exception:
                    continue
            
            return {"status": "error", "message": "无法获取模型列表，请手动输入模型名称"}
    except Exception as e:
        return {"status": "error", "message": f"获取模型列表失败: {str(e)}"}


# 保存自定义API到后端配置
class SaveCustomAPIRequest(BaseModel):
    name: str
    api_base: str
    api_key: str
    model: str = ""


@router.post("/save-custom-api")
async def save_custom_api(request: SaveCustomAPIRequest):
            """保存自定义API到后端配置"""
            try:
                from ai_write_x.config.config import Config
                
                config = Config.get_instance()
                
                # 创建自定义API提供商配置
                provider_name = request.name or "CustomAPI"
                
                # 更新后端配置
                api_config = config.config.get("api", {})
                
                # 添加或更新自定义API提供商
                api_config[provider_name] = {
                    "api_key": [request.api_key],
                    "key_index": 0,
                    "model": [request.model] if request.model else ["gpt-3.5-turbo"],
                    "model_index": 0,
                    "api_base": request.api_base
                }
                
                # 设置为当前使用的API
                api_config["api_type"] = provider_name
                
                # 更新配置
                config.config["api"] = api_config
                
                # 保存到文件
                config.save_config()
                
                return {"status": "success", "message": f"已保存自定义API: {provider_name}", "provider": provider_name}
            except Exception as e:
                return {"status": "error", "message": f"保存失败: {str(e)}"}


# 微信公众号凭证测试
class WechatCredentialTest(BaseModel):
    appid: str
    appsecret: str


@router.post("/test-wechat")
async def test_wechat_credential(cred: WechatCredentialTest):
    """
    测试微信公众号凭证 (v2: 改用aiohttp异步，避免阻塞FastAPI事件循环)
    
    验证：
    1. AppID格式是否正确
    2. 能否获取access_token
    3. 账号是否已认证
    4. IP白名单是否配置
    """
    import re
    import aiohttp
    
    log.print_log(f"[微信验证] 开始验证凭证 AppID={cred.appid[:6]}***", "info")
    
    result = {
        "status": "error",
        "message": "",
        "details": {}
    }
    
    # 1. 验证AppID格式
    if not cred.appid or not cred.appsecret:
        result["message"] = "AppID和AppSecret不能为空"
        log.print_log(f"[微信验证] ❌ 验证失败: {result['message']}", "error")
        return result
    
    # AppID通常是wx开头的16位字符串
    if not re.match(r'^wx[a-z0-9]{16}$', cred.appid):
        result["message"] = "AppID格式不正确（应为wx开头的18位字符串）"
        log.print_log(f"[微信验证] ❌ 验证失败: {result['message']}，实际长度={len(cred.appid)}", "error")
        return result
    
    # AppSecret通常是32位字符串
    if len(cred.appsecret) != 32:
        result["message"] = "AppSecret格式不正确（应为32位字符串）"
        log.print_log(f"[微信验证] ❌ 验证失败: {result['message']}，实际长度={len(cred.appsecret)}", "error")
        return result
    
    log.print_log(f"[微信验证] 格式校验通过，正在请求微信API获取access_token...", "info")
    
    # 2. 尝试获取access_token (v2: 用aiohttp异步请求，不阻塞事件循环)
    token_url = f"https://api.weixin.qq.com/cgi-bin/token?grant_type=client_credential&appid={cred.appid}&secret={cred.appsecret}"
    
    try:
        log.print_log(f"[微信验证] 请求地址: https://api.weixin.qq.com/cgi-bin/token", "info")
        
        async with aiohttp.ClientSession() as session:
            async with session.get(token_url, timeout=aiohttp.ClientTimeout(total=10)) as response:
                data = await response.json(content_type=None)
        
        log.print_log(f"[微信验证] 微信API响应: {data}", "info")
        
        if "errcode" in data:
            error_code = data.get("errcode")
            error_msg = data.get("errmsg", "")
            
            # 常见错误码处理
            error_messages = {
                40001: "AppSecret错误或不属于该公众号",
                40002: "请确保AppSecret正确",
                40013: "AppID无效",
                40125: "AppSecret错误",
                40164: "调用接口的IP地址不在白名单中，请在公众号后台配置IP白名单",
            }
            
            result["details"]["error_code"] = error_code
            result["details"]["error_msg"] = error_msg
            result["message"] = error_messages.get(error_code, f"验证失败: {error_msg}")
            
            # IP白名单错误时从微信错误消息中提取真实IP（最可靠的方法）
            if error_code == 40164:
                import re as _re
                ip_match = _re.search(r'invalid ip ([\d.]+)', error_msg)
                real_ip = ip_match.group(1) if ip_match else None
                
                if real_ip:
                    # 微信告诉我们的IP才是真实出口IP，回写到缓存
                    _ip_cache["ip"] = real_ip
                    _ip_cache["source"] = "微信API检测"
                    _ip_cache["timestamp"] = time.time()
                    result["message"] = f"IP白名单未配置！微信检测到的服务器IP为 {real_ip}，请在公众号后台→设置与开发→基本配置→IP白名单中添加"
                    result["details"]["server_ip"] = real_ip
                    log.print_log(f"[微信验证] 🎯 微信检测到的真实出口IP: {real_ip}", "warning")
                else:
                    result["message"] = f"IP白名单未配置！请在公众号后台→设置与开发→基本配置→IP白名单中添加服务器IP"
            
            log.print_log(f"[微信验证] ❌ 验证失败 (错误码={error_code}): {result['message']}", "error")
            return result
        
        access_token = data.get("access_token")
        if not access_token:
            result["message"] = "获取access_token失败，响应格式异常"
            log.print_log(f"[微信验证] ❌ {result['message']}", "error")
            return result
        
        log.print_log(f"[微信验证] ✅ access_token获取成功，有效期={data.get('expires_in', 7200)}秒", "success")
        result["details"]["access_token_valid"] = True
        result["details"]["expires_in"] = data.get("expires_in", 7200)
        
        # 3. 获取账号基本信息 (v2: 同样用aiohttp异步)
        try:
            info_url = f"https://api.weixin.qq.com/cgi-bin/account/getaccountbasicinfo?access_token={access_token}"
            log.print_log(f"[微信验证] 正在获取账号基本信息...", "info")
            
            async with aiohttp.ClientSession() as session:
                async with session.get(info_url, timeout=aiohttp.ClientTimeout(total=10)) as info_response:
                    info_data = await info_response.json(content_type=None)
            
            if "errcode" not in info_data:
                # 获取账号信息成功
                wx_verify = info_data.get("wx_verify_info", {})
                is_verified = wx_verify.get("qualification_verify", False)
                
                result["details"]["nickname"] = info_data.get("nick_name", "")
                result["details"]["account_type"] = info_data.get("account_type", "")
                result["details"]["is_verified"] = is_verified
                result["details"]["verify_type"] = wx_verify.get("qualification_verify_type", "")
                
                if is_verified:
                    result["status"] = "success"
                    result["message"] = f"验证成功！账号「{result['details']['nickname']}」已认证，支持直接发布"
                    log.print_log(f"[微信验证] ✅ {result['message']}", "success")
                else:
                    result["status"] = "warning"
                    result["message"] = f"验证成功！账号「{result['details']['nickname']}」未认证，仅支持保存到草稿箱"
                    log.print_log(f"[微信验证] ⚠️ {result['message']}", "warning")
            else:
                log.print_log(f"[微信验证] 获取账号信息返回错误: {info_data}，但token有效", "warning")
                result["status"] = "success"
                result["message"] = "验证成功！AppID和AppSecret有效"
                result["details"]["is_verified"] = False
                log.print_log(f"[微信验证] ✅ {result['message']}", "success")
                    
        except Exception as e:
            # 获取账号信息失败，但token获取成功
            log.print_log(f"[微信验证] 获取账号信息异常: {str(e)}，但token有效", "warning")
            result["status"] = "success"
            result["message"] = "验证成功！AppID和AppSecret有效"
            result["details"]["is_verified"] = False
            log.print_log(f"[微信验证] ✅ {result['message']}", "success")
        
        return result
        
    except asyncio.TimeoutError:
        result["message"] = "连接超时，请检查网络连接"
        log.print_log(f"[微信验证] ❌ {result['message']}", "error")
        return result
    except aiohttp.ClientError as e:
        result["message"] = f"网络连接失败: {str(e)}"
        log.print_log(f"[微信验证] ❌ {result['message']}", "error")
        return result
    except Exception as e:
        result["message"] = f"验证失败: {str(e)}"
        log.print_log(f"[微信验证] ❌ {result['message']}", "error")
        return result


# v2: IP缓存 - 5分钟TTL，避免每次切换面板都重新请求外部服务
_ip_cache = {"ip": None, "source": None, "timestamp": 0, "ttl": 300}


@router.get("/wechat/server-ip")
async def get_server_ip():
    """获取当前服务器的出口IP (v2: 并发竞速+缓存)"""
    import aiohttp
    import asyncio
    
    # v2: 检查缓存是否有效
    now = time.time()
    if _ip_cache["ip"] and (now - _ip_cache["timestamp"]) < _ip_cache["ttl"]:
        remaining = int(_ip_cache["ttl"] - (now - _ip_cache["timestamp"]))
        log.print_log(f"[出口IP] 命中缓存: {_ip_cache['ip']} (来源: {_ip_cache['source']}，剩余{remaining}秒)", "info")
        return {
            "status": "success",
            "ip": _ip_cache["ip"],
            "source": _ip_cache["source"],
            "cached": True,
            "message": f"请将此IP添加到微信公众号后台的IP白名单中"
        }
    
    log.print_log(f"[出口IP] 正在并发获取服务器出口IP...", "info")
    
    try:
        # 优先国内服务（与微信走同样的国内线路，确保IP一致）
        ip_services = [
            "https://myip.ipip.net/json",
            "https://api.ipify.org?format=json",
            "https://ipinfo.io/json"
        ]
        
        # v2: 并发竞速 - 同时请求所有服务，取最快成功的结果
        async def fetch_ip(session, service):
            """单个服务的IP获取，返回(ip, service)或抛异常"""
            async with session.get(service, timeout=aiohttp.ClientTimeout(total=5)) as response:
                if response.status == 200:
                    data = await response.json(content_type=None)
                    # 兼容不同服务的响应格式
                    ip = data.get("ip") or data.get("IP")
                    if not ip and "data" in data:
                        ip = data["data"].get("ip") if isinstance(data.get("data"), dict) else None
                    if ip:
                        return ip, service
            raise ValueError(f"{service} 返回无效响应")
        
        async with aiohttp.ClientSession() as session:
            # 创建并发任务
            tasks = [fetch_ip(session, svc) for svc in ip_services]
            
            # 竞速模式: 第一个成功的立即返回，取消其余
            done, pending = await asyncio.wait(
                [asyncio.create_task(t) for t in tasks],
                return_when=asyncio.FIRST_COMPLETED
            )
            
            # 取消尚未完成的任务
            for task in pending:
                task.cancel()
            
            # 从已完成的任务中找第一个成功的
            for task in done:
                try:
                    ip, source = task.result()
                    # v2: 更新缓存
                    _ip_cache["ip"] = ip
                    _ip_cache["source"] = source
                    _ip_cache["timestamp"] = time.time()
                    
                    log.print_log(f"[出口IP] ✅ 获取成功: {ip} (来源: {source})", "success")
                    return {
                        "status": "success",
                        "ip": ip,
                        "source": source,
                        "cached": False,
                        "message": f"请将此IP添加到微信公众号后台的IP白名单中"
                    }
                except Exception:
                    continue
        
        log.print_log(f"[出口IP] ❌ 所有服务均获取失败", "error")
        return {"status": "error", "message": "无法获取服务器IP，请手动查询"}
    except Exception as e:
        log.print_log(f"[出口IP] ❌ 获取IP异常: {str(e)}", "error")
        return {"status": "error", "message": f"获取IP失败: {str(e)}"}
