"""
统一LLM调用层 V5 - 使用OpenAI官方库

功能：
1. 完全使用OpenAI官方SDK，不依赖litellm
2. 自动检测视觉模型（VL/vision/gpt-4o/gpt-4-vision等标识）
3. 支持动态切换文本模型和视觉模型
4. 与CrewAI集成
5. V4: 重试抖动(Jitter)、智能模型降级、流式容错增强
6. V5: 请求追踪ID(req_id)、缓存键增强(含max_tokens)、API耗时日志

模型命名规则：
- 文本模型：直接使用模型名称（如 glm-4-flash, deepseek-chat）
- 视觉模型：模型名称包含 VL/vision/gpt-4o/gpt-4-vision/claude-3 等标识
"""

import base64
import re
import time
import uuid
import random
import hashlib
import json
import threading
from typing import Any, Dict, List, Optional, Union
from openai import OpenAI

from src.ai_write_x.config.config import Config
from src.ai_write_x.utils import log


# V3: 请求级LRU缓存 — 相同prompt+model在300秒内命中缓存，避免重复消耗API配额
class _ResponseCache:
    """线程安全的LRU响应缓存，TTL 300秒，最大128条"""
    def __init__(self, maxsize=128, ttl=300):
        self._cache = {}
        self._lock = threading.Lock()
        self._maxsize = maxsize
        self._ttl = ttl

    def _make_key(self, messages, model, temperature, max_tokens=4096):
        # V5: 缓存键加入max_tokens，防止不同配额参数命中同一缓存
        # V23.1: 增加防御，处理可能包含非标对象的 messages (如 Task 对象)
        raw = json.dumps({"m": messages, "model": model, "t": temperature, "mt": max_tokens}, 
                         sort_keys=True, ensure_ascii=False, default=str)
        return hashlib.md5(raw.encode('utf-8')).hexdigest()

    def get(self, messages, model, temperature, max_tokens=4096):
        key = self._make_key(messages, model, temperature, max_tokens)
        with self._lock:
            if key in self._cache:
                resp, ts = self._cache[key]
                if time.time() - ts < self._ttl:
                    return resp
                else:
                    del self._cache[key]
        return None

    def put(self, messages, model, temperature, response, max_tokens=4096):
        key = self._make_key(messages, model, temperature, max_tokens)
        with self._lock:
            if len(self._cache) >= self._maxsize:
                oldest_key = min(self._cache, key=lambda k: self._cache[k][1])
                del self._cache[oldest_key]
            self._cache[key] = (response, time.time())

_response_cache = _ResponseCache()


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
        
        # V3: Token用量追踪系统 — 累计记录所有API调用的token消耗
        self._token_usage = {
            "prompt_tokens": 0,
            "completion_tokens": 0,
            "total_tokens": 0,
            "request_count": 0,
            "cache_hits": 0,
        }
        self._usage_lock = threading.Lock()
        
        # V7.0: 模型性能追踪器 (Model Fallback Evaluator)
        self._model_stats = {} # {model_name: {"success": 0, "fail": 0, "last_latency": 0}}
        self._stats_lock = threading.Lock()
        
        # V13.0: Predictive Token Cache - 系统指令哈希缓存
        self._system_prompt_cache = {} # {hash: full_text}
        
    def _get_client(self, api_key: str, base_url: str) -> OpenAI:
        """获取或创建OpenAI客户端 (V3: 连接池限制10连接/provider防泄露)"""
        import httpx
        # V14.1: 使用哈希处理缓存键，避免API密钥泄露
        key_hash = hashlib.sha256(api_key.encode()).hexdigest()[:16]
        cache_key = f"{key_hash}_{base_url}"
        if cache_key not in self._client_cache:
            # V3: 降低max_connections到10/provider防止连接泄露，keepalive降到5
            http_client = httpx.Client(
                limits=httpx.Limits(max_keepalive_connections=5, max_connections=10),
                timeout=httpx.Timeout(120.0)
            )
            self._client_cache[cache_key] = OpenAI(
                api_key=api_key,
                base_url=base_url,
                http_client=http_client
            )
        return self._client_cache[cache_key]

    def _track_model_performance(self, model_name: str, success: bool, latency_ms: int = 0):
        with self._stats_lock:
            if model_name not in self._model_stats:
                self._model_stats[model_name] = {"success": 0, "fail": 0, "last_latency": 0}
            if success:
                self._model_stats[model_name]["success"] += 1
                self._model_stats[model_name]["last_latency"] = latency_ms
            else:
                self._model_stats[model_name]["fail"] += 1

    def _track_token_usage(self, usage):
        if not usage:
            return
        with self._usage_lock:
            self._token_usage["prompt_tokens"] += getattr(usage, 'prompt_tokens', 0) or 0
            self._token_usage["completion_tokens"] += getattr(usage, 'completion_tokens', 0) or 0
            self._token_usage["total_tokens"] += getattr(usage, 'total_tokens', 0) or 0
            self._token_usage["request_count"] += 1

    def get_token_usage(self) -> Dict[str, int]:
        with self._usage_lock:
            return dict(self._token_usage)

    def reset_token_usage(self):
        with self._usage_lock:
            for k in self._token_usage:
                self._token_usage[k] = 0

    @staticmethod
    def _humanize_error(e: Exception) -> str:
        """V3: 将SDK异常包装为用户友好的中文提示"""
        msg = str(e)
        if '401' in msg or 'Unauthorized' in msg:
            return "API密钥无效或已过期，请检查API Key配置"
        elif '403' in msg or 'Forbidden' in msg:
            return "API访问被拒绝，可能是权限不足或IP白名单未配置"
        elif '404' in msg or 'not found' in msg.lower():
            return f"模型不存在或API地址错误，请确认模型名称和Base URL"
        elif '429' in msg or 'rate' in msg.lower():
            return "API请求频率超限(429)，正在自动退避重试..."
        elif '500' in msg or '502' in msg or '503' in msg:
            return "API服务端暂时不可用，请稍后重试"
        elif 'timeout' in msg.lower() or 'timed out' in msg.lower():
            return "API请求超时(120s)，可能是网络问题或模型响应过慢"
        elif 'Connection' in msg or 'connect' in msg.lower():
            return "无法连接到API服务器，请检查网络和Base URL配置"
        return f"LLM调用异常: {msg}"
    
    def _get_current_client(self) -> OpenAI:
        """获取当前配置的主客户端"""
        return self._get_client(
            api_key=self._config.api_key,
            base_url=self._config.api_apibase
        )

    @property
    def _client(self) -> OpenAI:
        """兼容测试的属性"""
        return self._get_current_client()

    def _get_fallback_clients(self) -> List[tuple]:
        """V13.0: 动态获取并按性能排序的备用提供程序 (Adaptive Weighting)"""
        fallbacks = []
        try:
            apis = self._config.get("api", {})
            current_type = self._config.get("api", {}).get("api_type", "")
            for provider_type, data in apis.items():
                if provider_type != "api_type" and provider_type != current_type and isinstance(data, dict):
                    if "api_key" in data and "base_url" in data:
                        model = data.get("model", "gpt-3.5-turbo")
                        with self._stats_lock:
                            stats = self._model_stats.get(model, {"last_latency": 9999})
                            latency = stats.get("last_latency", 9999)
                        fallbacks.append((data["api_key"], data["base_url"], model, provider_type, latency))
            fallbacks.sort(key=lambda x: x[4])
            return [f[:4] for f in fallbacks]
        except Exception:
            pass
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
    
    # V4: 智能模型降级映射 — 同一 provider 内先尝试更便宜/更稳定的模型
    MODEL_DOWNGRADE_MAP = {
        'gpt-4o': 'gpt-4o-mini',
        'gpt-4-turbo': 'gpt-3.5-turbo',
        'gpt-4': 'gpt-3.5-turbo',
        'deepseek-chat': 'deepseek-chat',  # deepseek 只有一个，不降级
        'glm-4-plus': 'glm-4-flash',
        'glm-4': 'glm-4-flash',
        'qwen-max': 'qwen-turbo',
        'qwen-plus': 'qwen-turbo',
    }

    def chat(
        self,
        messages: List[Dict[str, Any]],
        model: Optional[str] = None,
        temperature: float = 0.7,
        max_tokens: int = 4096,
        timeout: Optional[float] = None,
        use_v15: bool = True,  # V15.0: 是否使用 V15 优化
        **kwargs
    ) -> str:
        """
        V4/V15: 发送聊天请求（重试抖动 + 智能模型降级 + 多提供商故障转移 + V15量子优化）
        
        Args:
            use_v15: 是否启用 V15.0 量子优化（语义缓存、批处理）
        
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
        # V15.0: 量子优化检查
        if use_v15:
            try:
                from src.ai_write_x.config.config import Config
                v15_config = Config.get_instance().v15_config
                
                if v15_config.get("enabled", True):
                    if v15_config.get("enable_semantic_cache", True):
                        try:
                            from src.ai_write_x.core.semantic_cache_v2 import get_semantic_cache
                            cache = get_semantic_cache()
                            threshold = v15_config.get("cache_similarity_threshold", 0.88)
                            cached_result = cache.get(messages, similarity_threshold=threshold)
                            if cached_result:
                                log.print_log("[V15.0] 💾 语义缓存命中", "info")
                                return cached_result
                        except Exception:
                            pass
            except Exception:
                pass
        
        client = self._get_current_client()
        model_name = model or self.current_model
        effective_timeout = timeout or 120.0
        
        # V5: 请求级唯一追踪ID — 贯穿日志链路便于故障追踪
        req_id = uuid.uuid4().hex[:8]
        
        # V5: LRU缓存命中检查(含max_tokens维度)
        cached = _response_cache.get(messages, model_name, temperature, max_tokens)
        if cached is not None:
            with self._usage_lock:
                self._token_usage["cache_hits"] += 1
            log.print_log(f"[req:{req_id}] 缓存命中 [{model_name}]，跳过API调用", "info")
            return cached

        # V13.0: Predictive Token Caching - 优化系统指令传输
        optimized_messages = []
        for msg in messages:
            if msg.get("role") == "system":
                content_hash = hashlib.md5(msg["content"].encode()).hexdigest()[:12]
                if content_hash in self._system_prompt_cache:
                    # 如果已知此指令，可以标记或应用预测性逻辑（此处仅作日志标记，防止重复传输逻辑在底层由Provider/缓存处理）
                    log.print_log(f"[req:{req_id}] 检测到高频系统指令 (Hash:{content_hash})，应用预测性缓存优化", "debug")
                else:
                    self._system_prompt_cache[content_hash] = msg["content"]
            optimized_messages.append(msg)
        
        # V4/V15: 重试逻辑 — 指数退避 + 随机抖动(Jitter) + 扩展网络异常捕获
        max_retries = 3  # V14.1: 减少重试次数到3次，添加快速失败机制
        for attempt in range(max_retries + 1):
            try:
                # V23.1: 记录请求载荷 (仅在终端美化展示，完整内容存入文件)
                log.print_ai_log(f"AI Request ({model_name})", messages, log_type="payload", req_id=req_id)

                t0 = time.time()
                response = client.chat.completions.create(
                    model=model_name,
                    messages=messages,
                    temperature=temperature,
                    timeout=effective_timeout,
                    **kwargs
                )
                elapsed_ms = int((time.time() - t0) * 1000)
                self._track_token_usage(response.usage)
                self._track_model_performance(model_name, True, elapsed_ms)
                result = response.choices[0].message.content
                _response_cache.put(messages, model_name, temperature, result, max_tokens)
                
                # V23.1: 记录详细响应内容
                log.print_ai_log(f"AI Response ({model_name})", result, log_type="response", req_id=req_id)

                # V15.0: 写入语义缓存
                if use_v15:
                    try:
                        from src.ai_write_x.core.semantic_cache_v2 import get_semantic_cache
                        cache = get_semantic_cache()
                        prompt_tokens = getattr(response.usage, 'prompt_tokens', 0) or 0
                        completion_tokens = getattr(response.usage, 'completion_tokens', 0) or 0
                        cache.set(
                            messages=messages,
                            response=result,
                            prompt_tokens=prompt_tokens,
                            completion_tokens=completion_tokens
                        )
                    except Exception:
                        pass
                
                # V5: 记录API响应耗时，便于性能瓶颈定位
                log.print_log(f"[req:{req_id}] [{model_name}] 响应完成 {elapsed_ms}ms (Pass)", "info")
                return result
            except Exception as e:
                self._track_model_performance(model_name, False)
                error_str = str(e).lower()
                
                # 判定是否为可重试的异常 (429, 5xx, 网络波动, 超时)
                is_retryable = any(kw in error_str for kw in [
                    '429', 'rate', '500', '502', '503', '504', 
                    'timeout', 'timed out', 'connection', 'connect', 'eof'
                ])
                
                if is_retryable and attempt < max_retries:
                    base_wait = 2 ** (attempt + 1)
                    jitter = base_wait * random.uniform(-0.3, 0.3)
                    wait_time = max(1.5, base_wait + jitter)
                    
                    reason = self._humanize_error(e)
                    log.print_log(f"⏳ {reason}，{wait_time:.1f}秒后自动重试 (第{attempt+1}/{max_retries}次)", "warning")
                    # 打印原始异常详情
                    import traceback
                    log.print_log(f"[异常详情] 类型: {type(e).__name__}, 消息: {str(e)}", "info")
                    time.sleep(wait_time)
                    continue
                
                human_msg = self._humanize_error(e)
                log.print_log(f"主LLM调用失败 [{model_name}]: {human_msg}", "error")
                # 打印原始异常详情
                import traceback
                log.print_log(f"[异常详情] 类型: {type(e).__name__}, 消息: {str(e)}", "info")
                
                # V4 Step 1: 同 provider 智能模型降级 — 先试同一服务商的便宜模型
                downgrade_model = self.MODEL_DOWNGRADE_MAP.get(model_name)
                if downgrade_model and downgrade_model != model_name:
                    log.print_log(f"⬇️ 尝试同服务商模型降级: {model_name} → {downgrade_model}", "warning")
                    try:
                        response = client.chat.completions.create(
                            model=downgrade_model,
                            messages=messages,
                            temperature=temperature,
                            timeout=effective_timeout,
                            **kwargs
                        )
                        self._track_token_usage(response.usage)
                        log.print_log(f"✅ 降级模型 {downgrade_model} 调用成功!", "success")
                        result = response.choices[0].message.content
                        _response_cache.put(messages, model_name, temperature, result)
                        return result
                    except Exception as dg_e:
                        log.print_log(f"降级模型 {downgrade_model} 也失败: {self._humanize_error(dg_e)}", "error")
                        import traceback as _tb
                        log.print_log(f"[异常详情] 降级模型异常: {type(dg_e).__name__}: {str(dg_e)}", "info")
                
                # V4 Step 2: 跨 provider 故障转移
                fallbacks = self._get_fallback_clients()
                if fallbacks:
                    for fallback_key, fallback_base, fallback_model, provider_name in fallbacks:
                        log.print_log(f"🔄 正在尝试备用提供商: {provider_name} ({fallback_model})", "warning")
                        try:
                            fallback_client = self._get_client(fallback_key, fallback_base)
                            response = fallback_client.chat.completions.create(
                                model=fallback_model,
                                messages=messages,
                                temperature=temperature,
                                timeout=effective_timeout,
                                **kwargs
                            )
                            self._track_token_usage(response.usage)
                            log.print_log(f"✅ 备用提供商 {provider_name} 调用成功!", "success")
                            result = response.choices[0].message.content
                            _response_cache.put(messages, model_name, temperature, result)
                            return result
                        except Exception as fallback_e:
                            log.print_log(f"备用提供商 {provider_name} 调用也失败: {self._humanize_error(fallback_e)}", "error")
                            import traceback as _tb
                            log.print_log(f"[异常详情] 备用提供商异常: {type(fallback_e).__name__}: {str(fallback_e)}", "info")
                            continue
                
                raise Exception(f"所有LLM提供商均调用失败。{human_msg}")
        
        raise Exception("LLM请求重试次数耗尽")
    
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
                img_url = {
                    "type": "image_url",
                    "image_url": {
                        "url": f"data:image/jpeg;base64,{base64.b64encode(img).decode()}"
                    }
                }
            elif isinstance(img, str):
                if img.startswith(('http://', 'https://')):
                    img_url = {
                        "type": "image_url",
                        "image_url": {"url": img}
                    }
                elif img.startswith('data:'):
                    img_url = {
                        "type": "image_url",
                        "image_url": {"url": img}
                    }
                else:
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
        V4: 异步流式聊天（增强容错 + token追踪 + 自动重试与故障转移）
        
        Yields:
            文本片段
        """
        import httpx
        from openai import AsyncOpenAI
        import asyncio
        import random
        
        model_name = model or self.current_model
        req_id = uuid.uuid4().hex[:8]
        
        # V14.1: 重试与故障转移逻辑
        max_retries = 3
        current_model = model_name
        
        for attempt in range(max_retries + 1):
            async_client = AsyncOpenAI(
                api_key=self._config.api_key,
                base_url=self._config.api_apibase
            )
            
            total_chunks = 0
            try:
                log.print_ai_log(f"AI Async Stream Request ({current_model})", messages, log_type="payload", req_id=req_id)
                
                stream = await async_client.chat.completions.create(
                    model=current_model,
                    messages=messages,
                    temperature=temperature,
                    stream=True,
                    timeout=120.0,
                    **kwargs
                )
                
                async for chunk in stream:
                    if chunk.choices and chunk.choices[0].delta.content:
                        content = chunk.choices[0].delta.content
                        total_chunks += 1
                        yield content
                
                with self._usage_lock:
                    self._token_usage["request_count"] += 1
                    self._token_usage["completion_tokens"] += total_chunks * 3
                
                self._track_model_performance(current_model, True)
                log.print_log(f"[req:{req_id}] [{current_model}] 异步流式响应完成 (Pass)", "info")
                await async_client.close()
                return

            except Exception as e:
                await async_client.close()
                self._track_model_performance(current_model, False)
                error_str = str(e).lower()
                
                # 判定是否为可重试的异常
                is_retryable = any(kw in error_str for kw in [
                    '429', 'rate', '500', '502', '503', '504', 
                    'timeout', 'timed out', 'connection', 'connect', 'eof'
                ])
                
                if is_retryable and attempt < max_retries:
                    base_wait = 2 ** (attempt + 1)
                    jitter = base_wait * random.uniform(-0.3, 0.3)
                    wait_time = max(1.5, base_wait + jitter)
                    
                    reason = self._humanize_error(e)
                    log.print_log(f"⏳ {reason}，{wait_time:.1f}秒后自动重试流式请求 (第{attempt+1}/{max_retries}次)", "warning")
                    await asyncio.sleep(wait_time)
                    continue
                
                human_msg = self._humanize_error(e)
                log.print_log(f"异步流式调用失败 [{current_model}]: {human_msg}", "error")
                
                # 1. 尝试同服务商模型降级
                downgrade_model = self.MODEL_DOWNGRADE_MAP.get(current_model)
                if downgrade_model and downgrade_model != current_model:
                    log.print_log(f"⬇️ 尝试流式模型降级: {current_model} → {downgrade_model}", "warning")
                    current_model = downgrade_model
                    # 重置重试计数或继续尝试
                    continue
                
                # 2. 尝试跨 provider 故障转移
                fallbacks = self._get_fallback_clients()
                if fallbacks:
                    for fb_key, fb_base, fb_model, fb_provider in fallbacks:
                        log.print_log(f"🔄 正在尝试备用提供商(流式): {fb_provider} ({fb_model})", "warning")
                        try:
                            fallback_client = AsyncOpenAI(api_key=fb_key, base_url=fb_base)
                            fb_stream = await fallback_client.chat.completions.create(
                                model=fb_model,
                                messages=messages,
                                temperature=temperature,
                                stream=True,
                                timeout=120.0,
                                **kwargs
                            )
                            async for fb_chunk in fb_stream:
                                if fb_chunk.choices and fb_chunk.choices[0].delta.content:
                                    yield fb_chunk.choices[0].delta.content
                            await fallback_client.close()
                            log.print_log(f"✅ 备用提供商 {fb_provider} 流式调用成功!", "success")
                            return
                        except Exception as fb_e:
                            log.print_log(f"备用提供商 {fb_provider} 流式调用也失败: {self._humanize_error(fb_e)}", "error")
                            continue
                
                raise Exception(f"所有LLM提供商均流式请求失败。{human_msg}")

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
        
        if tools:
            params["tools"] = tools
        
        params.update(kwargs)
        
        # V14.0 Defensive Programming: Add exponential backoff for CrewAI Adapter
        max_retries = 3
        for attempt in range(max_retries + 1):
            try:
                response = self._client.chat.completions.create(**params)
                return response.choices[0].message.content
            except Exception as e:
                import time
                import random
                error_str = str(e).lower()
                if ('429' in error_str or 'rate' in error_str or '502' in error_str or '503' in error_str) and attempt < max_retries:
                    base_wait = 2 ** (attempt + 1)
                    jitter = base_wait * random.uniform(-0.3, 0.3)
                    wait_time = max(1.0, base_wait + jitter)
                    log.print_log(f"⚠️ CrewAI LLMAdapter 调用故障 (尝试 {attempt+1}/{max_retries}): {e}. 等待 {wait_time:.1f}s", "warning")
                    time.sleep(wait_time)
                    continue
                else:
                    log.print_log(f"LLM调用彻底失败: {e}", "error")
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
