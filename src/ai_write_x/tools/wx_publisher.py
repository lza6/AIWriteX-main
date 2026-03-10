from dataclasses import dataclass
from enum import Enum
from typing import Optional
from datetime import datetime, timedelta
import requests
from io import BytesIO
from http import HTTPStatus
from urllib.parse import urlparse, unquote
from pathlib import PurePosixPath
from dashscope import ImageSynthesis
import os
import mimetypes
import json
import time
import re
from bs4 import BeautifulSoup  # ✅ 新增：导入 BeautifulSoup

from src.ai_write_x.utils import utils
from src.ai_write_x.config.config import Config
from src.ai_write_x.utils import log
from src.ai_write_x.utils.path_manager import PathManager


# ... (PublishStatus, PublishResult 类保持不变) ...
class PublishStatus(Enum):
    PENDING = "pending"
    PUBLISHED = "published"
    FAILED = "failed"
    DRAFT = "draft"
    SCHEDULED = "scheduled"


@dataclass
class PublishResult:
    publishId: str
    status: PublishStatus
    publishedAt: datetime
    platform: str
    url: Optional[str] = None


class WeixinPublisher:
    BASE_URL = "https://api.weixin.qq.com/cgi-bin"

    # ... (__init__, is_verified, _ensure_access_token 等方法保持不变) ...
    def __init__(self, app_id: str, app_secret: str, author: str):
        # 获取配置数据，只能使用确定的配置，微信配置是循环发布的，需要传递
        config = Config.get_instance()

        self.access_token_data = None
        self.app_id = app_id
        self.app_secret = app_secret
        self.author = author
        self.img_api_type = config.img_api_type  # 只有一种模型，统一从配置读取
        self.img_api_key = config.img_api_key
        self.img_api_model = config.img_api_model
        # 获取ComfyUI配置
        self.comfyui_config = config.config.get("img_api", {}).get("comfyui", {})
        
        # V13.0: 稳定性增强配置
        self.max_retries = 3
        self.backoff_factor = 2 # 指数退避倍数
        self.adaptive_pause = 0 # 自适应休眠时长

    def _request_with_retry(self, method: str, url: str, **kwargs):
        """V13.0: 自适应 API 请求引擎 - 支持自动重试、指数退避、限频处理"""
        import time
        last_exception = None
        
        for i in range(self.max_retries + 1):
            if self.adaptive_pause > 0:
                time.sleep(self.adaptive_pause)
                self.adaptive_pause = max(0, self.adaptive_pause - 1) # 逐渐衰减
                
            try:
                if method.upper() == "GET":
                    response = requests.get(url, **kwargs)
                else:
                    response = requests.post(url, **kwargs)
                
                response.raise_for_status()
                data = response.json()
                
                errcode = data.get("errcode", 0)
                
                if errcode == 0:
                    return data
                
                # 处理限频 (45009: reach limit)
                if errcode == 45009:
                    log.print_log(f"微信API触发限频(45009)，正在执行自适应休眠...", "warning")
                    self.adaptive_pause = 5 * (i + 1)
                    continue
                    
                # 处理Token失效 (40001/42001)
                if errcode in [40001, 42001]:
                    log.print_log("微信Access Token失效，正在静默刷新...", "info")
                    self.access_token_data = None
                    # 更新 kwargs 中的 token
                    if "params" in kwargs and "access_token" in kwargs["params"]:
                        kwargs["params"]["access_token"] = self._ensure_access_token()
                    elif "access_token=" in url:
                        url = re.sub(r'access_token=[^&]+', f'access_token={self._ensure_access_token()}', url)
                    continue
                
                # 其他错误不重试
                if i == self.max_retries:
                    return data
                    
            except requests.exceptions.RequestException as e:
                last_exception = e
                wait_time = self.backoff_factor ** i
                log.print_log(f"网络请求异常: {e}, {wait_time}s 后重试 ({i+1}/{self.max_retries})", "warning")
                time.sleep(wait_time)
        
        # 最终失败返回伪造响应或抛出
        if last_exception:
            return {"errcode": -1, "errmsg": str(last_exception)}
        return {"errcode": -1, "errmsg": "Unknown error during retry"}

    @property
    def is_verified(self):
        if not hasattr(self, "_is_verified"):
            url = f"{self.BASE_URL}/account/getaccountbasicinfo?access_token={self._ensure_access_token()}"  # noqa 501
            response = requests.get(url, timeout=5)

            try:
                response.raise_for_status()
                data = response.json()
                wx_verify = data.get("wx_verify_info", {})
                self._is_verified = bool(wx_verify.get("qualification_verify", False))
            except (requests.RequestException, ValueError, KeyError):
                self._is_verified = False

        return self._is_verified

    def _ensure_access_token(self):
        # 检查现有token是否有效
        if self.access_token_data and self.access_token_data[
            "expires_at"
        ] > datetime.now() + timedelta(
            minutes=1
        ):  # 预留1分钟余量
            return self.access_token_data["access_token"]

        # 获取新token
        url = f"{self.BASE_URL}/token?grant_type=client_credential&appid={self.app_id}&secret={self.app_secret}"  # noqa 501

        try:
            response = requests.get(url)
            response.raise_for_status()
            data = response.json()
            access_token = data.get("access_token")
            expires_in = data.get("expires_in")

            if not access_token:
                log.print_log(f"获取access_token失败: {data}")
                return None

            self.access_token_data = {
                "access_token": access_token,
                "expires_in": expires_in,
                "expires_at": datetime.now() + timedelta(seconds=expires_in),
            }
            return access_token
        except requests.exceptions.RequestException as e:
            log.print_log(f"获取微信access_token失败: {e}")

        return None  # 获取不到就返回None，失败交给后面的流程处理

    def _upload_draft(self, article, title, digest, media_id):
        token = self._ensure_access_token()
        url = f"{self.BASE_URL}/draft/add?access_token={token}"

        articles = [
            {
                "title": title[:64],
                "author": self.author,
                "digest": digest[:120],
                "content": article,
                "thumb_media_id": media_id,
                "need_open_comment": 1,
                "only_fans_can_comment": 0,
            },
        ]
        
        try:
            data = {"articles": articles}
            headers = {"Content-Type": "application/json"}
            json_data = json.dumps(data, ensure_ascii=False).encode("utf-8")
            
            result = self._request_with_retry("POST", url, data=json_data, headers=headers)
            
            if result.get("errcode", 0) != 0:
                return None, f"上传草稿失败: {result.get('errmsg')}"
            return {"media_id": result.get("media_id")}, None
        except Exception as e:
            return None, f"上传微信草稿失败: {e}"

    def _generate_img_by_ali(self, prompt, size="1024*1024"):
        image_dir = PathManager.get_image_dir()
        img_url = None
        log.print_log(f"[图像生成] 开始使用阿里云通义万相生成图片...")
        log.print_log(f"[图像生成] 模型: {self.img_api_model}, 尺寸: {size}")
        log.print_log(f"[图像生成] 提示词: {prompt[:100]}...")
        
        try:
            log.print_log("[图像生成] 正在调用阿里云API...")
            rsp = ImageSynthesis.call(
                api_key=self.img_api_key,
                model=self.img_api_model,
                prompt=prompt,
                negative_prompt="低分辨率、错误、最差质量、低质量、残缺、多余的手指、比例不良",
                n=1,
                size=size,
            )
            if rsp.status_code == HTTPStatus.OK:
                log.print_log(f"[图像生成] API调用成功，正在下载图片...")
                # 实际上只有一张图片，为了节约，不同时生成多张
                for result in rsp.output.results:
                    file_name = PurePosixPath(unquote(urlparse(result.url).path)).parts[-1]
                    # 拼接绝对路径和文件名
                    file_path = os.path.join(image_dir, file_name)
                    with open(file_path, "wb+") as f:
                        f.write(requests.get(result.url).content)
                img_url = rsp.output.results[0].url
                log.print_log(f"[图像生成] 图片保存成功: {file_path}")
            else:
                log.print_log(
                    "[图像生成] 失败! status_code: %s, code: %s, message: %s"
                    % (rsp.status_code, rsp.code, rsp.message), "error"
                )
        except Exception as e:
            log.print_log(f"[图像生成] 阿里云API调用异常: {e}", "error")

        return img_url

    def _generate_img_by_modelscope(self, prompt, size="1024*1024"):
        image_dir = PathManager.get_image_dir()
        img_url = None
        log.print_log(f"[图像生成] 开始使用魔搭社区(ModelScope)生成图片...")
        log.print_log(f"[图像生成] 模型: {self.img_api_model}, 尺寸: {size}")
        
        try:
            log.print_log("[图像生成] 正在调用 ModelScope API...")
            from openai import OpenAI
            client = OpenAI(
                api_key=self.img_api_key,
                base_url="https://api-inference.modelscope.cn/v1/"
            )
            response = client.images.generate(
                model=self.img_api_model,
                prompt=prompt,
                n=1,
                size=size
            )
            
            if response.data and len(response.data) > 0:
                img_download_url = response.data[0].url
                
                # Download
                file_name = f"modelscope_{int(time.time()*1000)}.png"
                file_path = os.path.join(image_dir, file_name)
                with open(file_path, "wb+") as f:
                    f.write(requests.get(img_download_url).content)
                img_url = file_path
                log.print_log(f"[图像生成] 图片保存成功: {file_path}")
            else:
                log.print_log("[图像生成] ModelScope API调用失败或返回空数据", "error")
        except Exception as e:
            log.print_log(f"[图像生成] ModelScope API调用异常: {e}", "error")

        return img_url

    def _generate_img_by_comfyui(self, prompt, size="1024*1024"):
        """使用ComfyUI API生成图片"""
        import json
        import time
        import uuid
        
        image_dir = PathManager.get_image_dir()
        img_url = None
        
        log.print_log(f"[图像生成] 开始使用ComfyUI生成图片...")
        
        try:
            # 获取ComfyUI配置
            api_base = self.comfyui_config.get("api_base", "")
            model = self.comfyui_config.get("model", "")
            
            # 解析尺寸
            width, height = map(int, size.split("*")) if "*" in size else (1024, 1024)
            log.print_log(f"[图像生成] API地址: {api_base}, 模型: {model or '默认'}, 尺寸: {width}x{height}")
            log.print_log(f"[图像生成] 提示词: {prompt[:100]}...")
            
            # ComfyUI API端点
            prompt_endpoint = f"{api_base}/prompt"
            
            # 构建简单的文生图工作流
            # 使用默认的SDXL模型
            workflow = {
                "prompt_id": str(uuid.uuid4()),
                "prompt": {
                    "1": {
                        "inputs": {
                            "text": prompt,
                            "clip": ["3", 0]
                        },
                        "class_type": "CLIPTextEncode"
                    },
                    "3": {
                        "inputs": {
                            "seed": int(time.time() * 1000) % 1000000000,
                            "steps": 20,
                            "cfg": 8,
                            "sampler_name": "euler",
                            "scheduler": "normal",
                            "positive": ["1", 0],
                            "negative": ["4", 0],
                            "model": ["5", 0],
                            "latent_image": ["6", 0]
                        },
                        "class_type": "KSampler"
                    },
                    "4": {
                        "inputs": {
                            "text": "low quality, worst quality, bad anatomy, bad hands, missing fingers, extra fingers",
                            "clip": ["3", 0]
                        },
                        "class_type": "CLIPTextEncode"
                    },
                    "5": {
                        "inputs": {
                            "model_name": model if model else "sdxl1.0.safetensors"
                        },
                        "class_type": "CheckpointLoaderSimple"
                    },
                    "6": {
                        "inputs": {
                            "width": width,
                            "height": height,
                            "batch_size": 1
                        },
                        "class_type": "EmptyLatentImage"
                    },
                    "7": {
                        "inputs": {
                            "samples": ["3", 0],
                            "vae": ["5", 2]
                        },
                        "class_type": "VAEDecode"
                    },
                    "8": {
                        "inputs": {
                            "filename_prefix": "comfyui_",
                            "images": ["7", 0]
                        },
                        "class_type": "SaveImage"
                    }
                }
            }
            
            # 发送请求到ComfyUI
            headers = {"Content-Type": "application/json"}
            if self.comfyui_config.get("api_key"):
                headers["Authorization"] = f"Bearer {self.comfyui_config['api_key']}"
            
            log.print_log("[图像生成] 正在发送请求到ComfyUI...")
            response = requests.post(prompt_endpoint, json=workflow, headers=headers, timeout=60)
            
            if response.status_code == 200:
                result = response.json()
                prompt_id = result.get("prompt_id")
                log.print_log(f"[图像生成] 任务已提交，prompt_id: {prompt_id}")
                
                if prompt_id:
                    # 等待图片生成完成
                    history_endpoint = f"{api_base}/history/{prompt_id}"
                    max_wait = 120  # 最多等待120秒
                    elapsed = 0
                    log.print_log("[图像生成] 等待图片生成中...")
                    while elapsed < max_wait:
                        time.sleep(2)
                        history_response = requests.get(history_endpoint, timeout=10)
                        if history_response.status_code == 200:
                            history_data = history_response.json()
                            if prompt_id in history_data:
                                # 获取生成的图片
                                prompt_data = history_data[prompt_id]
                                if "outputs" in prompt_data:
                                    for node_id, node_output in prompt_data["outputs"].items():
                                        if "images" in node_output:
                                            for img in node_output["images"]:
                                                # 下载图片
                                                img_filename = img["filename"]
                                                img_subfolder = img.get("subfolder", "")
                                                view_endpoint = f"{api_base}/view"
                                                if img_subfolder:
                                                    view_endpoint += f"?filename={img_filename}&subfolder={img_subfolder}"
                                                else:
                                                    view_endpoint += f"?filename={img_filename}"
                                                
                                                img_response = requests.get(view_endpoint, timeout=30)
                                                if img_response.status_code == 200:
                                                    # 保存图片
                                                    file_name = f"comfyui_{int(time.time()*1000)}.png"
                                                    file_path = os.path.join(image_dir, file_name)
                                                    with open(file_path, "wb") as f:
                                                        f.write(img_response.content)
                                                    img_url = file_path
                                                    log.print_log(f"[图像生成] 图片保存成功: {file_path}")
                                                    break
                                            if img_url:
                                                break
                                    if img_url:
                                        break
                        elapsed += 2
                    
                    if not img_url:
                        log.print_log("[图像生成] ComfyUI图片生成超时 (等待超过120秒)", "error")
                else:
                    log.print_log(f"[图像生成] ComfyUI返回无效响应: {result}", "error")
            else:
                log.print_log(f"[图像生成] ComfyUI API请求失败: {response.status_code} - {response.text}", "error")
                
        except requests.exceptions.ConnectionError:
            log.print_log("[图像生成] 无法连接到ComfyUI服务，请确保ComfyUI正在运行", "error")
        except Exception as e:
            log.print_log(f"[图像生成] ComfyUI调用异常: {e}", "error")

        return img_url

    def generate_img(self, prompt, size="1024*1024"):
        log.print_log(f"[图像生成] ========== 开始生成图片 ==========")
        log.print_log(f"[图像生成] 图像API类型: {self.img_api_type}")
        
        img_url = None
        if self.img_api_type == "ali":
            img_url = self._generate_img_by_ali(prompt, size)
        elif self.img_api_type == "modelscope":
            img_url = self._generate_img_by_modelscope(prompt, size)
        elif self.img_api_type == "comfyui":
            img_url = self._generate_img_by_comfyui(prompt, size)
        elif self.img_api_type == "picsum":
            log.print_log(f"[图像生成] 使用Picsum随机图片服务...")
            image_dir = str(PathManager.get_image_dir())
            width_height = size.split("*")
            download_url = f"https://picsum.photos/{width_height[0]}/{width_height[1]}?random=1"
            log.print_log(f"[图像生成] 下载地址: {download_url}")
            img_url = utils.download_and_save_image(download_url, image_dir)
            if img_url:
                log.print_log(f"[图像生成] 图片保存成功: {img_url}")
            else:
                log.print_log("[图像生成] Picsum图片下载失败", "error")

        if img_url:
            log.print_log(f"[图像生成] ========== 图片生成成功 ==========")
        else:
            log.print_log(f"[图像生成] ========== 图片生成失败 ==========", "error")
            
        return img_url

    def upload_image(self, image_url):
        from src.ai_write_x.utils.utils import resolve_image_path  # 导入新函数

        log.print_log(f"[upload_image] 开始上传, 输入URL: {image_url}", "debug")

        if not image_url:
            log.print_log("[upload_image] 图片URL为空,使用默认封面", "warning")
            return "SwCSRjrdGJNaWioRQUHzgF68BHFkSlb_f5xlTquvsOSA6Yy0ZRjFo0aW9eS3JJu_", None, None

        ret = None, None, None
        try:
            # 先解析图片路径
            resolved_path = resolve_image_path(image_url)
            log.print_log(f"[upload_image] 解析后的路径: {resolved_path}", "debug")

            if resolved_path.startswith(("http://", "https://")):
                # 处理网络图片
                log.print_log(f"[upload_image] 检测到网络图片,开始下载: {resolved_path}", "info")
                image_response = requests.get(resolved_path, stream=True)
                image_response.raise_for_status()
                image_buffer = BytesIO(image_response.content)

                mime_type = image_response.headers.get("Content-Type")
                if not mime_type:
                    mime_type = "image/jpeg"
                file_ext = mimetypes.guess_extension(mime_type)
                file_name = "image" + file_ext if file_ext else "image.jpg"
                log.print_log(f"[upload_image] 网络图片下载完成: {file_name}, mime={mime_type}", "info")
            else:
                # 处理本地图片
                log.print_log(f"[upload_image] 检测到本地图片: {resolved_path}", "info")
                if not os.path.exists(resolved_path):
                    log.print_log(f"[upload_image] 本地图片不存在: {resolved_path}", "error")
                    ret = None, None, f"本地图片未找到: {resolved_path}"
                    return ret
                
                file_size = os.path.getsize(resolved_path)
                log.print_log(f"[upload_image] 本地图片存在,大小: {file_size} bytes", "info")

                with open(resolved_path, "rb") as f:
                    image_buffer = BytesIO(f.read())

                mime_type, _ = mimetypes.guess_type(resolved_path)
                if not mime_type:
                    mime_type = "image/jpeg"
                file_name = os.path.basename(resolved_path)

            token = self._ensure_access_token()
            if self.is_verified:
                url = f"{self.BASE_URL}/media/upload?access_token={token}&type=image"
            else:
                url = f"{self.BASE_URL}/material/add_material?access_token={token}&type=image"

            files = {"media": (file_name, image_buffer, mime_type)}
            result = self._request_with_retry("POST", url, files=files)

            # 调试日志：记录完整响应
            log.print_log(f"[图片上传] 微信API响应: {result}", "debug")

            if result is None:
                ret = None, None, "图片上传失败: API返回空响应"
            elif result.get("errcode", 0) != 0:
                errmsg = result.get('errmsg') or result.get('errMsg') or f"未知错误(代码: {result.get('errcode')})"
                ret = None, None, f"图片上传失败: {errmsg}"
            elif "media_id" not in result:
                ret = None, None, f"图片上传失败: 响应中缺少 media_id, 完整响应: {result}"
            else:
                ret = result.get("media_id"), result.get("url"), None

        except Exception as e:
            import traceback
            log.print_log(f"[图片上传] 异常详情: {traceback.format_exc()}", "error")
            ret = None, None, f"图片上传失败: {e}"

        return ret

    def add_draft(self, article, title, digest, media_id):
        ret = None, None
        try:
            # 上传草稿
            draft, err_msg = self._upload_draft(article, title, digest, media_id)
            if draft is not None:
                ret = (
                    PublishResult(
                        publishId=draft["media_id"],
                        status=PublishStatus.DRAFT,
                        publishedAt=datetime.now(),
                        platform="wechat",
                        url=f"https://mp.weixin.qq.com/s/{draft['media_id']}",
                    ),
                    None,
                )
            else:
                ret = None, err_msg
        except Exception as e:
            ret = None, f"微信添加草稿失败: {e}"

        return ret

    def publish(self, media_id: str):
        url = f"{self.BASE_URL}/freepublish/submit"
        params = {"access_token": self._ensure_access_token()}
        data = {"media_id": media_id}

        try:
            result = self._request_with_retry("POST", url, params=params, json=data)

            if result.get("errcode", 0) != 0:
                return None, f"草稿发布失败: {result.get('errmsg')}"
            return (
                PublishResult(
                    publishId=result.get("publish_id") or result.get("media_id"),
                    status=PublishStatus.PUBLISHED,
                    publishedAt=datetime.now(),
                    platform="wechat",
                    url="",  # 需要通过轮询获取
                ),
                None,
            )
        except Exception as e:
            return None, f"发布草稿文章失败：{e}"

    # 轮询获取文章链接
    def poll_article_url(self, publish_id, max_retries=10, interval=2):
        url = f"{self.BASE_URL}/freepublish/get?access_token={self._ensure_access_token()}"
        params = {"publish_id": publish_id}

        for i in range(max_retries):
            # 轮询不使用 _request_with_retry 的内部重试，因为外部已经有循环
            response = requests.post(url, json=params).json() 
            if response.get("article_id"):
                return response.get("article_detail")["item"][0]["article_url"]
            
            # 如果触发限频，等待长一点
            if response.get("errcode") == 45009:
                time.sleep(interval * 2)
            else:
                time.sleep(interval)

        return None

    # ---------------------以下接口需要微信认证[个人用户不可用]-------------------------
    # 单独发布只能通过绑定到菜单的形式访问到，无法显示到公众号文章列表
    def create_menu(self, article_url):
        menu_data = {
            "button": [
                {
                    "type": "view",
                    "name": "最新文章",
                    "url": article_url,
                }
            ]
        }
        menu_url = f"{self.BASE_URL}/menu/create?access_token={self._ensure_access_token()}"
        try:
            result = self._request_with_retry("POST", menu_url, json=menu_data)
            if result.get("errcode", 0) != 0:
                return f"创建菜单失败: {result.get('errmsg')}"
            return ""
        except Exception as e:
            return f"创建菜单失败:{e}"

    # 上传图文消息素材【订阅号与服务号认证后均可用】
    def media_uploadnews(self, article, title, digest, media_id):
        token = self._ensure_access_token()
        url = f"{self.BASE_URL}/media/uploadnews?access_token={token}"

        articles = [
            {
                "thumb_media_id": media_id,
                "author": self.author,
                "title": title[:64],
                "content": article,
                "digest": digest[:120],
                "show_cover_pic": 1,
                "need_open_comment": 1,
                "only_fans_can_comment": 0,
            }
        ]

        try:
            data = {"articles": articles}
            headers = {"Content-Type": "application/json"}
            json_data = json.dumps(data, ensure_ascii=False).encode("utf-8")
            
            result = self._request_with_retry("POST", url, data=json_data, headers=headers)
            
            if result.get("errcode", 0) != 0:
                return None, f"上传图文素材失败: {result.get('errmsg')}"
            return result.get("media_id"), None
        except Exception as e:
            return None, f"上传微信图文素材失败: {e}"

    # 根据标签进行群发【订阅号与服务号认证后均可用】
    def message_mass_sendall(self, media_id, is_to_all=True, tag_id=0):
        if is_to_all:
            data_filter = {"is_to_all": is_to_all}
        else:
            if tag_id == 0:
                return "根据标签进行群发失败：未勾选群发，且tag_id=0无效"
            data_filter = {"is_to_all": is_to_all, "tag_id": tag_id}
            
        data = {
            "filter": data_filter,
            "mpnews": {"media_id": media_id},
            "msgtype": "mpnews",
            "send_ignore_reprint": 1,
        }
        url = f"{self.BASE_URL}/message/mass/sendall?access_token={self._ensure_access_token()}"

        try:
            result = self._request_with_retry("POST", url, json=data)
            if result.get("errcode", 0) != 0:
                return f"根据标签进行群发失败: {result.get('errmsg')}"
            return None
        except Exception as e:
            return f"群发消息失败：{e}"

    def _replace_div_with_section(self, content):
        """
        强制将所有 <div> 标签转换为 <section>
        微信公众号后台对 section 的兼容性更好，且能避免部分 div 样式丢失问题。
        """
        if not content:
            return ""

        try:
            # 使用 html.parser 解析
            soup = BeautifulSoup(content, "html.parser")

            # 查找所有 div 标签并直接修改其 name 属性
            # 这比正则替换更安全，不会误伤文本内容
            for tag in soup.find_all("div"):
                tag.name = "section"

            # 只要把 tag.name 改了，输出时就会变成 <section>...</section>
            return str(soup)

        except Exception as e:
            log.print_log(f"Div转Section失败(bs4): {e}")
            return content

    def _compress_html(self, content, use_compress=True):
        """
        智能压缩HTML（正则版）：
        只负责“清洗”工作：去除换行符和标签间的幽灵空格，防止微信排版错乱。
        """
        if not use_compress or not content:
            return content

        # 1. 移除注释
        content = re.sub(r"<!--.*?-->", "", content, flags=re.DOTALL)

        # 2. 核心修复：只移除“标签 > 后的【换行符+缩进空格】”
        # 逻辑：编辑器里的换行+缩进是多余的，删掉。
        content = re.sub(r">[\n\r]+\s*", ">", content)

        # 3. 移除标签结尾 < 前面的换行和缩进
        content = re.sub(r"\s+<", "<", content)

        # 4. 移除标签之间的纯空白
        content = re.sub(r">\s+<", "><", content)

        # 5. 清理剩余换行符
        content = content.replace("\n", "").replace("\r", "")

        return content

    def _inject_indent(self, content):
        """
        智能注入首行缩进（BS4 终极版）：
        给正文段落添加 text-indent: 2em。
        升级：
        1. 向上查找5层祖先，彻底排除卡片、提示框、嵌套布局。
        2. 增加 box-shadow (阴影) 检测，这是识别卡片的关键。
        3. 排除短文本和特殊符号开头的段落（如注释、列表）。
        """
        if not content:
            return ""

        try:
            soup = BeautifulSoup(content, "html.parser")

            for p in soup.find_all("p"):
                # --- 文本内容检查 (新功能) ---
                text = p.get_text().strip()

                # 1. 空段落或极短段落跳过 (通常是标题、按钮文字或装饰性文字)
                if not text or len(text) < 30:
                    continue

                # 2. 特殊符号开头跳过 (代码注释、伪列表、引用)
                # 您的截图中 "//" 开头的注释就会在这里被豁免
                if text.startswith(
                    ("/", "●", "-", ">", "•", "*", "1.", "2.", "3.", "4.", "5.", "#")
                ):
                    continue

                should_skip = False

                # --- 🛡️ 深度豁免扫描 (查自己 + 往上查5代) ---
                # 检查列表包含：当前标签 p，以及它的父级...
                check_list = [p] + list(p.parents)[:5]

                for node in check_list:
                    if not hasattr(node, "name"):
                        continue

                    # 1.【结构豁免】列表、引用、表格、代码块、按钮
                    if node.name in [
                        "li",
                        "blockquote",
                        "th",
                        "td",
                        "figcaption",
                        "pre",
                        "code",
                        "dt",
                        "dd",
                        "button",
                        "a",
                    ]:
                        should_skip = True
                        break

                    # 获取样式
                    style = node.get("style", "").lower()

                    # 2.【对齐豁免】
                    if "text-align" in style and ("center" in style or "right" in style):
                        should_skip = True
                        break

                    # 3.【布局豁免】Flex / Grid / Inline-Block
                    if "display" in style and (
                        "flex" in style or "grid" in style or "inline-block" in style
                    ):
                        should_skip = True
                        break

                    # 4.【装饰豁免】有背景色、边框、**阴影(关键)**
                    # 只要祖先里有 box-shadow，说明这是个卡片，坚决不缩进
                    if "background" in style or "border" in style or "box-shadow" in style:
                        should_skip = True
                        break

                if should_skip:
                    continue

                # 5.【自身检查】
                p_style = p.get("style", "").lower()
                if "text-indent" in p_style:
                    continue

                # --- 注入样式 ---
                current_style = p.get("style", "")
                new_style = f"text-indent: 2em; {current_style}".strip()
                p["style"] = new_style

            return str(soup)

        except Exception as e:
            log.print_log(f"HTML样式注入失败(bs4): {e}，将使用原始排版")
            return content


def pub2wx(title, digest, article, appid, appsecret, author, cover_path=None):
    publisher = WeixinPublisher(appid, appsecret, author)
    config = Config.get_instance()

    # 1. 结构标准化：强制 Div -> Section
    # 这是处理的第一步，确保所有容器都是微信友好的 <section>
    article = publisher._replace_div_with_section(article)

    # 2. 样式注入：首行缩进
    # 在 div 变成 section 之后再注入样式，虽然主要针对 p 标签，但层级结构可能变了，所以放在结构调整后
    article = publisher._inject_indent(article)

    # 3. 再处理正文图片URL替换 (bs4 处理后的 html 结构标准，利于正则提取)
    cropped_image_path = ""
    final_image_path = None  # 最终要上传的图片路径

    if cover_path:
        # 如果明确指定了封面路径，使用指定的封面
        resolved_cover_path = utils.resolve_image_path(cover_path)
        cropped_image_path = utils.crop_cover_image(resolved_cover_path, (900, 384))

        if cropped_image_path:
            final_image_path = cropped_image_path
        else:
            final_image_path = resolved_cover_path
    else:
        # 默认策略：优先从正文中随机提取图片作为封面
        import random
        
        article_images = utils.extract_image_urls(article)
        if article_images:
            # 从正文中随机选择一张图片作为封面
            random_cover_url = random.choice(article_images)
            log.print_log(f"从正文随机选取图片作为封面: {random_cover_url}")
            
            # 解析图片路径
            resolved_cover_path = utils.resolve_image_path(random_cover_url)
            if not utils.is_local_path(resolved_cover_path):
                # 如果是网络图片，先下载到本地
                resolved_cover_path = utils.download_and_save_image(
                    resolved_cover_path,
                    str(PathManager.get_image_dir()),
                )
            
            if resolved_cover_path and os.path.exists(resolved_cover_path):
                # 对图片进行安全裁剪 (900x384)
                temp_crop = utils.crop_cover_image(resolved_cover_path, (900, 384))
                if temp_crop:
                    final_image_path = temp_crop
                    cropped_image_path = temp_crop
                else:
                    final_image_path = resolved_cover_path
            else:
                log.print_log("正文图片处理失败，尝试生成封面...", "warning")
                final_image_path = None
        else:
            log.print_log("正文无图片，需要生成封面...", "info")
            final_image_path = None
        
        # 如果正文没有可用图片，尝试自动生成
        if final_image_path is None:
            image_url = publisher.generate_img(
                "主题:" + title.split("|")[-1] + ",内容:" + digest,
                "900*384",
            )
            
            if image_url:
                final_image_path = utils.resolve_image_path(image_url)
                log.print_log(f"成功生成封面图片: {final_image_path}", "success")
            else:
                # 生成也失败，使用默认图片
                log.print_log("生成封面失败，使用默认图片", "warning")
                default_image = utils.get_res_path(
                    os.path.join("branding", "app_icon_1024.png"), 
                    os.path.dirname(__file__) + "/../assets/"
                )
                final_image_path = utils.resolve_image_path(default_image)

    # 先提取文章中的所有图片URL（供后续使用）
    image_urls = utils.extract_image_urls(article)
    
    # 封面图片上传
    log.print_log(f"[发布] 准备上传封面图片: {final_image_path}", "info")
    if not os.path.exists(final_image_path):
        log.print_log(f"[发布] 封面图片文件不存在: {final_image_path}", "error")
    else:
        file_size = os.path.getsize(final_image_path)
        log.print_log(f"[发布] 封面图片文件大小: {file_size} bytes", "info")
    
    media_id, uploaded_url, err_msg = publisher.upload_image(final_image_path)
    log.print_log(f"[发布] 封面上传结果: media_id={media_id}, url={uploaded_url}, err={err_msg}", "debug")

    # 如果使用了临时裁剪文件，上传后删除
    if cover_path and cropped_image_path and cropped_image_path != cover_path:
        try:
            os.remove(cropped_image_path)
        except Exception:
            pass

    if media_id is None:
        log.print_log(f"封面图片上传失败: {err_msg}", "warning")
        log.print_log("尝试从正文提取其他图片作为封面...", "info")
        
        # 尝试从正文提取其他图片
        fallback_media_id = None
        for other_url in image_urls:
            other_resolved = utils.resolve_image_path(other_url)
            if utils.is_local_path(other_resolved) and os.path.exists(other_resolved):
                log.print_log(f"尝试使用正文图片作为封面: {other_resolved}", "info")
                other_media_id, _, other_err = publisher.upload_image(other_resolved)
                if other_media_id:
                    fallback_media_id = other_media_id
                    log.print_log("成功使用正文图片作为封面", "success")
                    break
        
        if fallback_media_id:
            media_id = fallback_media_id
        else:
            # 如果没有可用的封面图片，提示用户并提供手动上传选项
            log.print_log("无法自动获取有效封面图片，请在微信公众号后台手动上传封面", "error")
            return "无法获取有效封面图片，发布失败。请在微信公众号后台手动上传封面", article, False

    # 这里需要将文章中的图片url替换为上传到微信返回的图片url
    try:
        for image_url in image_urls:
            # 先解析图片路径
            resolved_path = utils.resolve_image_path(image_url)

            # 判断解析后的路径类型
            if utils.is_local_path(resolved_path):
                # 本地路径处理
                if os.path.exists(resolved_path):
                    _, url, err_msg = publisher.upload_image(resolved_path)
                    if url:
                        article = article.replace(image_url, url)
                    else:
                        log.print_log(f"本地图片上传失败: {image_url}, 错误: {err_msg}")
                else:
                    log.print_log(f"本地图片文件不存在: {resolved_path}")
            else:
                # 网络URL处理
                local_filename = utils.download_and_save_image(
                    resolved_path,
                    str(PathManager.get_image_dir()),
                )
                if local_filename:
                    _, url, err_msg = publisher.upload_image(local_filename)
                    if url:
                        article = article.replace(image_url, url)
                    else:
                        log.print_log(f"网络图片上传失败: {image_url}, 错误: {err_msg}")
                else:
                    log.print_log(f"下载图片失败:{image_url}")
    except Exception as e:
        log.print_log(f"上传配图出错,影响阅读,可继续发布文章:{e}")

    # 4. 在上传给微信前，把所有换行符、缩进空格统统干掉，解决“幽灵空隙”
    article = publisher._compress_html(article)

    # 检查是否仅保存到草稿箱
    if config.get_draft_only_by_appid(appid):
        add_draft_result, err_msg = publisher.add_draft(article, title, digest, media_id)
        if add_draft_result is None:
            return f"{err_msg}，无法保存草稿", article, False
        return "已保存到微信公众号草稿箱，请在公众号后台手动发布", article, True

    # 账号是否认证
    if not publisher.is_verified:
        add_draft_result, err_msg = publisher.add_draft(article, title, digest, media_id)
        if add_draft_result is None:
            # 添加草稿失败，不再继续执行
            return f"{err_msg}，无法发布文章", article, False

        publish_result, err_msg = publisher.publish(add_draft_result.publishId)
        if publish_result is None:
            if "api unauthorized" in err_msg:  # type: ignore
                return (
                    "自动发布失败，【自2025年7月15日起，个人主体账号、未认证企业账号及不支持认证的账号的发布权限被回收，需到公众号管理后台->草稿箱->发表】",
                    article,
                    True,  # 此类目前认为是发布成功
                )
            else:
                return f"{err_msg}，无法继续发布文章", article, False
    else:
        # 显示到列表
        media_id, ret = publisher.media_uploadnews(article, title, digest, media_id)
        if media_id is None:
            if "api unauthorized" in ret:  # type: ignore
                return (
                    "账号虽认证（非企业账号），但无发布权限，发布失败，无法自动发布文章",
                    article,
                    False,
                )
            else:
                return f"{ret}，无法显示到公众号文章列表（公众号未认证）", article, False

        """
        article_url = publisher.poll_article_url(publish_result.publishId)
        if article_url is not None:
            # 该接口需要认证,将文章添加到菜单中去，用户可以通过菜单“最新文章”获取到
            ret = publisher.create_menu(article_url)
            if not ret:
                log.print_log(f"{ret}（公众号未认证，发布已成功）")
        else:
            log.print_log("无法获取到文章URL，无法创建菜单（可忽略，发布已成功）")
        """

        # 是否设置为群发
        """
        微信官方说明：https://developers.weixin.qq.com/doc/service/guide/product/message/Batch_Sends.html

        关于群发时设置 is_to_all 为 true 使其进入服务号在微信客户端的历史消息列表的说明：
        设置 is_to_all 为 true 且成功群发，会使得此次群发进入历史消息列表。
        为防止异常，认证服务号在一天内，只能设置 is_to_all 为 true 且成功群发一次，或者在公众平台官网群发一次。以避免一天内有2条群发进入历史消息列表。
        类似地，服务号在一个月内，设置 is_to_all 为 true 且成功群发的次数，加上公众平台官网群发的次数，最多只能是4次。
        服务号设置 is_to_all 为 false 时是可以多次群发的，但每个用户一个月内只会收到最多4条，且这些群发不会进入历史消息列表。
        """
        if config.get_call_sendall_by_appid(appid):
            ret = publisher.message_mass_sendall(
                media_id,
                config.get_sendall_by_appid(appid),
                config.get_tagid_by_appid(appid),
            )
            if ret is not None:
                if "api unauthorized" in ret:
                    return (
                        "没有群发权限，无法显示到公众号文章列表（发布已成功）",
                        article,
                        True,
                    )
                else:
                    return (
                        f"{ret}，无法显示到公众号文章列表（发布已成功）",
                        article,
                        True,
                    )

    return "成功发布文章到微信公众号", article, True
