"""
统一LLM调用层 - 使用OpenAI官方库

功能：
1. 完全使用OpenAI官方SDK，不依赖litellm
2. 自动检测视觉模型（VL/vision/gpt-4o/gpt-4-vision等标识）
3. 支持动态切换文本模型和视觉模型
4. 与CrewAI集成

模型命名规则：
- 文本模型：直接使用模型名称（如 glm-4-flash, deepseek-chat）
- 视觉模型：模型名称包含 VL/vision/gpt-4o/gpt-4-vision/claude-3 等标识
"""

import base64
import re
from typing import Any, Dict, List, Optional, Union
from openai import OpenAI

from src.ai_write_x.config.config import Config
from src.ai_write_x.utils import log


class VisionModelDetector:
    """视觉模型检测器"""
    
    # 视觉模型标识符（不区分大小写）
    VISION_PATTERNS = [
        r'vl',           # VL-xxx, glm-4v-plus-vl
        r'vision',       # gpt-4-vision, vision-model
        r'gpt-4o',       # GPT-4o系列
        r'gpt-4-turbo',  # GPT-4 Turbo (支持视觉)
        r'claude-3',     # Claude 3系列
        r'gemini',       # Gemini系列
        r'qwen-vl',      # 通义千问视觉
        r'glm-4v',       # 智谱GLM视觉
        r'doubao-vision', # 豆包视觉
        r'minimax-vision', # MiniMax视觉
        r'cogvlm',       # CogVLM
        r'yi-vl',        # 零一万物视觉
        r'idefics',      # Idefics
        r'llava',        # LLaVA
    ]
    
    @classmethod
    def is_vision_model(cls, model_name: str) -> bool:
        """检测是否为视觉模型"""
        if not model_name:
            return False
        model_lower = model_name.lower()
        for pattern in cls.VISION_PATTERNS:
            if re.search(pattern, model_lower):
                return True
        return False
    
    @classmethod
    def get_vision_keywords(cls) -> List[str]:
        """获取视觉模型关键词列表（用于UI提示）"""
        return ['VL', 'vision', 'GPT-4o', 'GPT-4-turbo', 'Claude-3', 
                'Gemini', 'Qwen-VL', 'GLM-4V', 'CogVLM', 'LLaVA']


class LLMClient:
    """
    统一LLM调用客户端
    
    使用OpenAI官方SDK，支持任意OpenAI兼容API
    """
    
    _instance = None
    _lock = __import__('threading').RLock()
    
    def __new__(cls):
        if cls._instance is None:
            with cls._lock:
                if cls._instance is None:
                    cls._instance = super().__new__(cls)
                    cls._instance._initialized = False
        return cls._instance
    
    def __init__(self):
        if self._initialized:
            return
        self._initialized = True
        self._client_cache: Dict[str, OpenAI] = {}
        self._config = Config.get_instance()
        
        # 模型配置缓存
        self._text_model: Optional[str] = None
        self._vision_model: Optional[str] = None
        self._auto_vision_switch = True
        
    def _get_client(self, api_key: str, base_url: str) -> OpenAI:
        """获取或创建OpenAI客户端 (带高级连接池优化以减小满载时的内存峰值)"""
        import httpx
        cache_key = f"{api_key[:8]}_{base_url}"
        if cache_key not in self._client_cache:
            # 使用自定义 httpx 客户端提升高并发流式处理的连接回收率及内存表现
            http_client = httpx.Client(
                limits=httpx.Limits(max_keepalive_connections=50, max_connections=100),
                timeout=httpx.Timeout(120.0)
            )
            self._client_cache[cache_key] = OpenAI(
                api_key=api_key,
                base_url=base_url,
                http_client=http_client
            )
        return self._client_cache[cache_key]
    
    def _get_current_client(self) -> OpenAI:
        """获取当前配置的主客户端"""
        return self._get_client(
            api_key=self._config.api_key,
            base_url=self._config.api_apibase
        )

    def _get_fallback_clients(self) -> List[tuple]:
        """动态获取所有可用的备用提供程序 (Fallback Providers)"""
        # 如果 Config 支持 multi-api 结构，自动构建回退链
        fallbacks = []
        try:
            apis = self._config.get("api", {})
            current_type = self._config.get("api", {}).get("api_type", "")
            for provider_type, data in apis.items():
                if provider_type != "api_type" and provider_type != current_type and isinstance(data, dict):
                    if "api_key" in data and "base_url" in data:
                        model = data.get("model", "gpt-3.5-turbo") # 退避默认兜底模型
                        fallbacks.append((data["api_key"], data["base_url"], model, provider_type))
        except Exception:
            pass # 配置结构不支持则跳过
        return fallbacks
    
    @property
    def current_model(self) -> str:
        """获取当前模型名称"""
        return self._config.api_model
    
    @property
    def is_current_model_vision(self) -> bool:
        """检查当前模型是否为视觉模型"""
        return VisionModelDetector.is_vision_model(self.current_model)
    
    def set_text_model(self, model: str):
        """设置文本模型（用于后续切换）"""
        self._text_model = model
        
    def set_vision_model(self, model: str):
        """设置视觉模型"""
        self._vision_model = model
        
    def get_text_model(self) -> str:
        """获取文本模型"""
        if self._text_model:
            return self._text_model
        # 如果当前模型不是视觉模型，则作为文本模型
        if not self.is_current_model_vision:
            return self.current_model
        # 否则返回默认
        return self.current_model
    
    def get_vision_model(self) -> Optional[str]:
        """获取视觉模型"""
        if self._vision_model:
            return self._vision_model
            
        # 优先从配置获取视觉模型
        cfg_vision = Config.get_instance().api_vision_model
        if cfg_vision:
            return cfg_vision
            
        # 如果当前模型本身就是视觉模型（如 gpt-4o），直接返回
        if self.is_current_model_vision:
            return self.current_model
        return None
    
    def chat(
        self,
        messages: List[Dict[str, Any]],
        model: Optional[str] = None,
        temperature: float = 0.7,
        max_tokens: int = 4096,
        timeout: Optional[float] = None,
        **kwargs
    ) -> str:
        """
        发送聊天请求（支持多提供商自动故障转移）
        
        Args:
            messages: 消息列表
            model: 模型名称（可选，默认使用配置中的模型）
            temperature: 温度参数
            max_tokens: 最大token数
            timeout: 超时时间（秒）
            **kwargs: 其他参数
            
        Returns:
            助手回复文本
        """
        client = self._get_current_client()
        model_name = model or self.current_model
        
        try:
            response = client.chat.completions.create(
                model=model_name,
                messages=messages,
                temperature=temperature,
                timeout=timeout,
                **kwargs
            )
            return response.choices[0].message.content
        except Exception as primary_e:
            log.print_log(f"主LLM调用失败 [{model_name}]: {primary_e}", "error")
            
            # 多提供商故障转移 (Multi-Provider Fallback)
            fallbacks = self._get_fallback_clients()
            if fallbacks:
                for fallback_key, fallback_base, fallback_model, provider_name in fallbacks:
                    log.print_log(f"正在尝试备用提供商: {provider_name} ({fallback_model})", "warning")
                    try:
                        fallback_client = self._get_client(fallback_key, fallback_base)
                        response = fallback_client.chat.completions.create(
                            model=fallback_model,
                            messages=messages,
                            temperature=temperature,
                            **kwargs
                        )
                        log.print_log(f"备用提供商 {provider_name} 调用成功!", "success")
                        return response.choices[0].message.content
                    except Exception as fallback_e:
                        log.print_log(f"备用提供商 {provider_name} 调用也失败: {fallback_e}", "error")
                        continue
            
            raise Exception(f"所有LLM提供商均调用失败。主端点报错: {primary_e}")
    
    def chat_with_vision(
        self,
        text: str,
        image_data: Union[str, bytes, List[str], List[bytes]],
        model: Optional[str] = None,
        temperature: float = 0.7,
        max_tokens: int = 131452,
        **kwargs
    ) -> str:
        """
        发送带图片的聊天请求（视觉模型）
        
        Args:
            text: 文本内容
            image_data: 图片数据（URL、base64字符串或bytes）
            model: 模型名称（可选，自动检测视觉模型）
            temperature: 温度参数
            max_tokens: 最大token数
            
        Returns:
            助手回复文本
        """
        # 确定使用的模型
        vision_model = model or self.get_vision_model()
        if not vision_model:
            # 尝试使用当前模型（如果是视觉模型）
            if self.is_current_model_vision:
                vision_model = self.current_model
            else:
                raise ValueError("未配置视觉模型，请设置视觉模型或使用支持视觉的模型")
        
        # 构建消息内容
        content = [{"type": "text", "text": text}]
        
        # 处理图片数据
        if isinstance(image_data, (list, tuple)):
            images = image_data
        else:
            images = [image_data]
        
        for img in images:
            if isinstance(img, bytes):
                # bytes转base64
                img_url = {
                    "type": "image_url",
                    "image_url": {
                        "url": f"data:image/jpeg;base64,{base64.b64encode(img).decode()}"
                    }
                }
            elif isinstance(img, str):
                if img.startswith(('http://', 'https://')):
                    # URL
                    img_url = {
                        "type": "image_url",
                        "image_url": {"url": img}
                    }
                elif img.startswith('data:'):
                    # 已经是base64格式
                    img_url = {
                        "type": "image_url",
                        "image_url": {"url": img}
                    }
                else:
                    # 假设是base64字符串
                    img_url = {
                        "type": "image_url",
                        "image_url": {
                            "url": f"data:image/jpeg;base64,{img}"
                        }
                    }
            else:
                continue
            content.append(img_url)
        
        messages = [{"role": "user", "content": content}]
        
        return self.chat(
            messages=messages,
            model=vision_model,
            temperature=temperature,
            **kwargs
        )
    
    def analyze_image(
        self,
        image_data: Union[str, bytes],
        prompt: str = "请详细描述这张图片的内容",
        model: Optional[str] = None
    ) -> str:
        """
        分析图片（便捷方法）
        
        Args:
            image_data: 图片数据
            prompt: 分析提示词
            model: 模型名称
            
        Returns:
            图片分析结果
        """
        return self.chat_with_vision(
            text=prompt,
            image_data=image_data,
            model=model
        )
    
    async def stream_chat_async(
        self,
        messages: List[Dict[str, Any]],
        model: Optional[str] = None,
        temperature: float = 0.7,
        max_tokens: int = 4096,
        **kwargs
    ):
        """
        异步流式聊天
        
        Yields:
            文本片段
        """
        import httpx
        from openai import AsyncOpenAI
        
        model_name = model or self.current_model
        
        # 使用 AsyncOpenAI 客户端进行真正的异步流式处理
        async_client = AsyncOpenAI(
            api_key=self._config.api_key,
            base_url=self._config.api_apibase
        )
        
        try:
            stream = await async_client.chat.completions.create(
                model=model_name,
                messages=messages,
                temperature=temperature,
                stream=True,
                **kwargs
            )
            async for chunk in stream:
                if chunk.choices and chunk.choices[0].delta.content:
                    yield chunk.choices[0].delta.content
        except Exception as e:
            log.print_log(f"LLM异步流式调用失败: {e}", "error")
            raise
        finally:
            await async_client.close()

    def stream_chat(
        self,
        messages: List[Dict[str, Any]],
        model: Optional[str] = None,
        temperature: float = 0.7,
        max_tokens: int = 4096,
        **kwargs
    ):
        """
        同步流式聊天 (包装异步实现)
        
        Yields:
            文本片段
        """
        import asyncio
        
        # 内部异步生成器包装
        async def _run():
            async for chunk in self.stream_chat_async(
                messages=messages,
                model=model,
                temperature=temperature,
                max_tokens=max_tokens,
                **kwargs
            ):
                yield chunk

        # 在同步环境中运行异步迭代器
        try:
            # 尝试获取当前事件循环，如果没有则创建一个新的
            try:
                loop = asyncio.get_event_loop()
            except RuntimeError:
                loop = asyncio.new_event_loop()
                asyncio.set_event_loop(loop)
            
            gen = _run()
            
            while True:
                try:
                    # 迭代异步生成器
                    chunk = loop.run_until_complete(gen.__anext__())
                    yield chunk
                except StopAsyncIteration:
                    break
        except Exception as e:
            log.print_log(f"LLM同步流式调用失败: {e}", "error")
            raise

    def count_tokens(self, text: str) -> int:
        """估算token数量（简单估算）"""
        # 中文约1.5字符/token，英文约4字符/token
        chinese_chars = len(re.findall(r'[\u4e00-\u9fff]', text))
        other_chars = len(text) - chinese_chars
        return int(chinese_chars / 1.5 + other_chars / 4)


class CrewAILLMAdapter:
    """
    CrewAI LLM适配器
    
    将我们的LLMClient适配为CrewAI需要的LLM接口
    """
    
    def __init__(
        self,
        model: str,
        api_key: str,
        base_url: str,
        temperature: float = 0.7,
        max_tokens: int = 8192
    ):
        self.model = model
        self.api_key = api_key
        self.base_url = base_url
        self.temperature = temperature
        self.max_tokens = max_tokens
        
        # 创建OpenAI客户端
        self._client = OpenAI(api_key=api_key, base_url=base_url)
        
        # 检测是否为视觉模型
        self._is_vision = VisionModelDetector.is_vision_model(model)
        
        log.print_log(
            f"LLM适配器初始化: model={model}, base_url={base_url}, vision={self._is_vision}",
            "info"
        )
    
    @property
    def is_vision_model(self) -> bool:
        return self._is_vision
    
    def call(
        self,
        messages: List[Dict[str, Any]],
        tools: Optional[List] = None,
        **kwargs
    ) -> str:
        """
        调用LLM（兼容CrewAI接口）
        """
        params = {
            "model": self.model,
            "messages": messages,
            "temperature": self.temperature,
        }
        
        # 添加工具支持
        if tools:
            params["tools"] = tools
        
        # 合并其他参数
        params.update(kwargs)
        
        try:
            response = self._client.chat.completions.create(**params)
            return response.choices[0].message.content
        except Exception as e:
            log.print_log(f"LLM调用失败: {e}", "error")
            raise
    
    def __call__(self, *args, **kwargs):
        """支持直接调用"""
        return self.call(*args, **kwargs)
    
    def __repr__(self):
        return f"CrewAILLMAdapter(model={self.model})"


def create_llm_for_crewai(
    model: Optional[str] = None,
    api_key: Optional[str] = None,
    base_url: Optional[str] = None,
    **kwargs
) -> CrewAILLMAdapter:
    """
    为CrewAI创建LLM适配器
    
    Args:
        model: 模型名称（可选，使用配置中的值）
        api_key: API密钥（可选）
        base_url: API基础URL（可选）
        **kwargs: 其他参数
        
    Returns:
        CrewAILLMAdapter实例
    """
    config = Config.get_instance()
    
    model = model or config.api_model
    api_key = api_key or config.api_key
    base_url = base_url or config.api_apibase
    
    return CrewAILLMAdapter(
        model=model,
        api_key=api_key,
        base_url=base_url,
        **kwargs
    )


# 全局客户端实例
def get_llm_client() -> LLMClient:
    """获取全局LLM客户端实例"""
    return LLMClient()
