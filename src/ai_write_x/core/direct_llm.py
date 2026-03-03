"""
自定义 LLM 类 - 完全绕过 litellm，直接使用 OpenAI SDK

这个模块提供了一个自定义的 LLM 类，继承自 CrewAI 的 LLM 类，
但覆盖了 call 方法，直接使用 OpenAI 官方 SDK 进行 API 调用。

支持流式输出和进度回调。
"""

import json
import sys
from typing import Any, Dict, List, Optional, Union, Callable

from openai import OpenAI
from crewai import LLM

from src.ai_write_x.core.llm_client import VisionModelDetector
from src.ai_write_x.utils import log


# 全局流式输出回调
_stream_callback: Optional[Callable[[str], None]] = None


def set_stream_callback(callback: Optional[Callable[[str], None]]):
    """设置全局流式输出回调"""
    global _stream_callback
    _stream_callback = callback


def get_stream_callback() -> Optional[Callable[[str], None]]:
    """获取全局流式输出回调"""
    return _stream_callback


class OpenAIDirectLLM(LLM):
    """
    直接使用 OpenAI SDK 的 LLM 类
    
    继承自 CrewAI 的 LLM 类，但覆盖 call 方法，
    直接使用 OpenAI 官方 SDK 进行 API 调用，完全绕过 litellm。
    
    支持流式输出，实时显示生成进度。
    """
    
    def __init__(
        self,
        model: str,
        api_key: str,
        base_url: str,
        temperature: float = 0.7,
        max_tokens: int = 8192,
        timeout: Optional[float] = None,
        stream: bool = True,  # 默认启用流式输出
        **kwargs
    ):
        """
        初始化直接使用 OpenAI SDK 的 LLM
        
        Args:
            model: 模型名称（原始名称，如 glm-4.6）
            api_key: API 密钥
            base_url: API 基础 URL
            temperature: 温度参数
            max_tokens: 最大 token 数
            timeout: 超时时间
            stream: 是否启用流式输出
            **kwargs: 其他参数传递给父类
        """
        # 调用父类初始化
        super().__init__(
            model=model,
            api_key=api_key,
            base_url=base_url,
            temperature=temperature,
            max_tokens=max_tokens,
            timeout=timeout,
            **kwargs
        )
        
        # 保存原始模型名（用户配置的）
        self._original_model = model
        self._stream = stream
        
        # 创建 OpenAI 客户端
        self._openai_client = OpenAI(
            api_key=api_key,
            base_url=base_url,
            timeout=timeout if timeout else 120.0
        )
        
        # 检测是否为视觉模型
        self._is_vision = VisionModelDetector.is_vision_model(model)
        
        log.print_log(
            f"OpenAIDirectLLM 初始化: model={model}, base_url={base_url}, vision={self._is_vision}",
            "info"
        )
    
    @property
    def is_vision_model(self) -> bool:
        """是否为视觉模型"""
        return self._is_vision
    
    def _stream_call(
        self,
        messages: List[Dict[str, str]],
        tools: Optional[List[dict]] = None,
        **kwargs
    ) -> str:
        """
        流式调用 OpenAI API
        
        实时输出生成的内容，让用户看到进度。
        """
        # 构建请求参数
        params = {
            "model": self._original_model,
            "messages": messages,
            "temperature": self.temperature,
            "stream": True,  # 启用流式输出
        }
        
        if tools:
            params["tools"] = tools
            
        if kwargs:
            for key, value in kwargs.items():
                if key not in params:
                    params[key] = value
        
        full_content = ""
        tool_calls_data = []
        chunk_count = 0
        last_status_len = 0
        
        try:
            log.print_log("AI正在生成内容...", "status")
            log.print_log(f"[DEBUG] 调用参数: model={self._original_model}, max_tokens=auto (server default)", "debug")
            
            # 流式获取响应
            stream = self._openai_client.chat.completions.create(**params)
            log.print_log("[DEBUG] API 连接成功，开始接收流式数据...", "debug")
            
            chunk_index = 0
            for chunk in stream:
                chunk_index += 1
                # 调试：打印每个 chunk 的结构
                if chunk_index <= 3:
                    log.print_log(f"[DEBUG] Chunk {chunk_index}: {chunk}", "debug")
                
                # 检查是否有内容
                if chunk.choices and len(chunk.choices) > 0:
                    delta = chunk.choices[0].delta
                    
                    # 处理文本内容
                    if delta.content:
                        content = delta.content
                        full_content += content
                        chunk_count += 1
                        
                        # 每50个chunk输出一次进度状态（避免过多日志）
                        if chunk_count % 50 == 0:
                            # 显示已生成字数
                            status_msg = f"AI生成中... ({len(full_content)}字)"
                            log.print_log(status_msg, "status")
                        
                        # 调用全局回调（用于UI显示）
                        callback = get_stream_callback()
                        if callback:
                            callback(content)
                    
                    # 处理工具调用
                    if delta.tool_calls:
                        for tc in delta.tool_calls:
                            if tc.index >= len(tool_calls_data):
                                tool_calls_data.append({
                                    "id": "",
                                    "type": "function",
                                    "function": {"name": "", "arguments": ""}
                                })
                            if tc.id:
                                tool_calls_data[tc.index]["id"] = tc.id
                            if tc.function:
                                if tc.function.name:
                                    tool_calls_data[tc.index]["function"]["name"] = tc.function.name
                                if tc.function.arguments:
                                    tool_calls_data[tc.index]["function"]["arguments"] += tc.function.arguments
            
            # 调试：循环结束后的状态
            log.print_log(f"[DEBUG] 流式结束: 共 {chunk_index} 个 chunk, {chunk_count} 个有效内容, 内容长度 {len(full_content)}", "debug")
            
            # 生成完成状态
            if full_content:
                log.print_log(f"AI生成完成 ({len(full_content)}字)", "status")
            
            # 如果有工具调用，返回工具调用数据
            if tool_calls_data:
                log.print_log(f"检测到工具调用: {len(tool_calls_data)} 个", "debug")
                return {"tool_calls": tool_calls_data}
            
            # 检查是否返回空内容 - 抛出异常以便重试
            if not full_content or not full_content.strip():
                log.print_log("错误: LLM 返回空内容，将触发重试", "error")
                raise ValueError(
                    f"模型 '{self._original_model}' 返回空内容。"
                    "这可能是因为:\n"
                    "1. 该模型在当前 API 上不可用\n"
                    "2. API 服务端问题\n\n"
                    "建议: 在设置中切换到其他模型(如 deepseek-v3 或 kimi-k2)后重试"
                )
            
            return full_content
            
        except Exception as e:
            error_msg = str(e)
            log.print_log(f"AI生成失败: {error_msg}", "error")
            
            # 打印更详细的错误信息
            if hasattr(e, '__dict__'):
                log.print_log(f"错误详情: {e.__dict__}", "error")
            
            raise e
    
    def _non_stream_call(
        self,
        messages: List[Dict[str, str]],
        tools: Optional[List[dict]] = None,
        **kwargs
    ) -> str:
        """
        非流式调用 OpenAI API
        """
        params = {
            "model": self._original_model,
            "messages": messages,
            "temperature": self.temperature,
        }
        
        if tools:
            params["tools"] = tools
            
        if kwargs:
            for key, value in kwargs.items():
                if key not in params:
                    params[key] = value
        
        log.print_log("AI正在生成内容...", "status")
        
        response = self._openai_client.chat.completions.create(**params)
        message = response.choices[0].message
        
        # 检查是否有工具调用
        if message.tool_calls:
            return {"tool_calls": message.tool_calls}
        
        content = message.content or ""
        
        # 输出生成完成状态
        log.print_log(f"AI生成完成 ({len(content)}字)", "status")
        
        # 调用全局回调
        callback = get_stream_callback()
        if callback:
            callback(content)
        
        return content
    
    def call(
        self,
        messages: Union[str, List[Dict[str, str]]],
        tools: Optional[List[dict]] = None,
        callbacks: Optional[List[Any]] = None,
        available_functions: Optional[Dict[str, Any]] = None,
        **kwargs
    ) -> Union[str, Any]:
        """
        直接使用 OpenAI SDK 调用 LLM
        
        完全绕过 litellm，直接使用 OpenAI 官方 SDK。
        支持流式输出，实时显示生成进度。
        
        Args:
            messages: 输入消息（字符串或消息列表）
            tools: 工具列表（用于 function calling）
            callbacks: 回调函数列表
            available_functions: 可用函数映射
            
        Returns:
            LLM 响应文本或工具调用结果
        """
        # 如果是字符串，转换为消息列表
        if isinstance(messages, str):
            messages = [{"role": "user", "content": messages}]
            
        # 强制注入 Anti-AI 风格模仿系统词汇 (Style Mimicry Injection)
        from src.ai_write_x.core.anti_ai import AntiAIEngine
        anti_ai_prompt = AntiAIEngine.get_style_mimicry_prompt()
        # 确保不会重复添加
        if not any(anti_ai_prompt in m.get("content", "") for m in messages):
            # 将提示追加到最后一个系统消息，如果没有则直接追加系统消息
            system_msg = next((m for m in reversed(messages) if m.get("role") == "system"), None)
            if system_msg:
                system_msg["content"] += f"\n\n{anti_ai_prompt}"
            else:
                messages.append({"role": "system", "content": anti_ai_prompt})
        
        # 处理 O1 模型的系统消息
        if "o1" in self._original_model.lower():
            for message in messages:
                if message.get("role") == "system":
                    message["role"] = "assistant"
        
        # 设置回调
        if callbacks:
            self.set_callbacks(callbacks)
        
        # 添加带指数避让和上下文压缩的重试机制
        max_retries = 4
        last_error = None
        
        for attempt in range(max_retries + 1):
            try:
                # 根据配置选择流式或非流式调用
                if self._stream:
                    result = self._stream_call(messages, tools, **kwargs)
                else:
                    result = self._non_stream_call(messages, tools, **kwargs)
                
                # 检查结果是否为空
                if result is None or (isinstance(result, str) and not result.strip()):
                    raise ValueError("LLM 返回空响应")
                
                # 处理工具调用结果
                if isinstance(result, dict) and "tool_calls" in result:
                    tool_calls = result["tool_calls"]
                    if available_functions:
                        for tool_call in tool_calls:
                            func_name = tool_call.function.name if hasattr(tool_call, 'function') else tool_call["function"]["name"]
                            if func_name in available_functions:
                                func_args_str = tool_call.function.arguments if hasattr(tool_call, 'function') else tool_call["function"]["arguments"]
                                func_args = json.loads(func_args_str)
                                return available_functions[func_name](**func_args)
                    return tool_calls
                
                return result
                
            except Exception as e:
                last_error = e
                error_msg = str(e)
                log.print_log(f"OpenAI API 调用失败 (尝试 {attempt + 1}/{max_retries + 1}): {error_msg}", "error")
                
                # 检查是否是上下文长度超出 -> 触发动态上下文压缩
                if "context" in error_msg.lower() and "length" in error_msg.lower():
                    if len(messages) > 3:
                        log.print_log("上下文超限，尝试动态压缩消息历史以恢复生成...", "warning")
                        # 保留最重要的部分：系统设定[0]、早期上下文[1]和最近的交互[-2:]
                        compressed_messages = [messages[0]]
                        if len(messages) > 4:
                            compressed_messages.append(messages[1])
                        compressed_messages.extend(messages[-2:])
                        messages = compressed_messages
                        continue
                    else:
                        from crewai.utilities.exceptions import LLMContextLengthExceededException
                        raise LLMContextLengthExceededException(
                            f"上下文首尾两端内容超限且无法通过截断历史恢复: {error_msg}"
                        )
                
                # 检查是否是 API 限流 -> 触发全抖动指数退避(Exponential Backoff with Jitter)
                if "rate" in error_msg.lower() or "limit" in error_msg.lower():
                    import time
                    import random
                    # 计算基础退避时间，加入随机 Jitter 以打散重试风暴
                    wait_time = (2 ** attempt) + random.uniform(0.5, 2.5)
                    log.print_log(f"API 限流，将在 {wait_time:.2f} 秒后带有 Jitter 机制自动重试...", "warning")
                    time.sleep(wait_time)
                    continue
                
                # 如果还有重试机会应对一般网络抖动，继续重试
                if attempt < max_retries:
                    import time
                    import random
                    wait_time = (1.5 ** attempt) + random.uniform(0, 1)
                    time.sleep(wait_time)
                    continue
                else:
                    raise
        
        # 不应该到达这里
        raise last_error or Exception("LLM 调用重试次数耗尽，未知错误")
    
    def supports_function_calling(self) -> bool:
        """是否支持 function calling"""
        return True
    
    def supports_stop_words(self) -> bool:
        """是否支持 stop words"""
        return True
    
    def get_context_window_size(self) -> int:
        """获取上下文窗口大小"""
        model_lower = self._original_model.lower()
        
        if "gpt-4" in model_lower or "gpt4" in model_lower:
            return 128000
        elif "gpt-3.5" in model_lower:
            return 16385
        elif "claude" in model_lower:
            return 200000
        elif "glm-4" in model_lower:
            return 128000
        elif "deepseek" in model_lower:
            return 64000
        else:
            return 32768


def create_direct_llm(
    model: str,
    api_key: str,
    base_url: str,
    temperature: float = 0.7,
    max_tokens: int = 8192,
    stream: bool = True,
    **kwargs
) -> OpenAIDirectLLM:
    """
    创建直接使用 OpenAI SDK 的 LLM 实例
    
    Args:
        model: 模型名称
        api_key: API 密钥
        base_url: API 基础 URL
        temperature: 温度参数
        max_tokens: 最大 token 数
        stream: 是否启用流式输出
        **kwargs: 其他参数
        
    Returns:
        OpenAIDirectLLM 实例
    """
    return OpenAIDirectLLM(
        model=model,
        api_key=api_key,
        base_url=base_url,
        temperature=temperature,
        max_tokens=max_tokens,
        stream=stream,
        **kwargs
    )