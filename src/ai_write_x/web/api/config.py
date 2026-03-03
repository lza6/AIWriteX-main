#!/usr/bin/env python
# -*- coding: UTF-8 -*-

import json
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
    测试微信公众号凭证
    
    验证：
    1. AppID格式是否正确
    2. 能否获取access_token
    3. 账号是否已认证
    4. IP白名单是否配置
    """
    import re
    
    result = {
        "status": "error",
        "message": "",
        "details": {}
    }
    
    # 1. 验证AppID格式
    if not cred.appid or not cred.appsecret:
        result["message"] = "AppID和AppSecret不能为空"
        return result
    
    # AppID通常是wx开头的16位字符串
    if not re.match(r'^wx[a-z0-9]{16}$', cred.appid):
        result["message"] = "AppID格式不正确（应为wx开头的18位字符串）"
        return result
    
    # AppSecret通常是32位字符串
    if len(cred.appsecret) != 32:
        result["message"] = "AppSecret格式不正确（应为32位字符串）"
        return result
    
    # 2. 尝试获取access_token
    token_url = f"https://api.weixin.qq.com/cgi-bin/token?grant_type=client_credential&appid={cred.appid}&secret={cred.appsecret}"
    
    try:
        response = requests.get(token_url, timeout=10)
        data = response.json()
        
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
            
            # 特殊提示IP白名单问题
            if error_code == 40164:
                result["message"] = f"IP白名单未配置！请在公众号后台→设置与开发→基本配置→IP白名单中添加服务器IP"
            
            return result
        
        access_token = data.get("access_token")
        if not access_token:
            result["message"] = "获取access_token失败，响应格式异常"
            return result
        
        result["details"]["access_token_valid"] = True
        result["details"]["expires_in"] = data.get("expires_in", 7200)
        
        # 3. 获取账号基本信息
        try:
            info_url = f"https://api.weixin.qq.com/cgi-bin/account/getaccountbasicinfo?access_token={access_token}"
            info_response = requests.get(info_url, timeout=10)
            info_data = info_response.json()
            
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
                else:
                    result["status"] = "warning"
                    result["message"] = f"验证成功！账号「{result['details']['nickname']}」未认证，仅支持保存到草稿箱"
                    
        except Exception as e:
            # 获取账号信息失败，但token获取成功
            result["status"] = "success"
            result["message"] = "验证成功！AppID和AppSecret有效"
            result["details"]["is_verified"] = False
        
        return result
        
    except requests.exceptions.Timeout:
        result["message"] = "连接超时，请检查网络连接"
        return result
    except requests.exceptions.ConnectionError:
        result["message"] = "网络连接失败，请检查网络设置"
        return result
    except Exception as e:
        result["message"] = f"验证失败: {str(e)}"
        return result


@router.get("/wechat/server-ip")
async def get_server_ip():
    """获取当前服务器的出口IP（用于配置微信IP白名单）"""
    import aiohttp
    
    try:
        # 使用多个IP查询服务，提高可靠性
        ip_services = [
            "https://api.ipify.org?format=json",
            "https://api.ip.sb/jsonip",
            "https://ipinfo.io/json"
        ]
        
        async with aiohttp.ClientSession() as session:
            for service in ip_services:
                try:
                    async with session.get(service, timeout=aiohttp.ClientTimeout(total=5)) as response:
                        if response.status == 200:
                            data = await response.json()
                            ip = data.get("ip") or data.get("IP")
                            if ip:
                                return {
                                    "status": "success",
                                    "ip": ip,
                                    "message": f"请将此IP添加到微信公众号后台的IP白名单中"
                                }
                except Exception:
                    continue
        
        return {"status": "error", "message": "无法获取服务器IP，请手动查询"}
    except Exception as e:
        return {"status": "error", "message": f"获取IP失败: {str(e)}"}
