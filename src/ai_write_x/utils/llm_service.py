# -*- coding: utf-8 -*-
"""
LLM 服务层
提供简化的异步LLM调用接口
"""

from typing import Dict, List, Optional, Any
import asyncio
from concurrent.futures import ThreadPoolExecutor

from src.ai_write_x.core.llm_client import LLMClient
from src.ai_write_x.utils import log


class LLMService:
    """
    LLM服务类
    提供同步和异步的LLM调用接口
    """
    
    _instance = None
    _executor = ThreadPoolExecutor(max_workers=3)
    
    def __new__(cls):
        if cls._instance is None:
            cls._instance = super().__new__(cls)
            cls._instance._client = None
        return cls._instance
    
    @property
    def client(self) -> LLMClient:
        """获取LLMClient实例（懒加载）"""
        if self._client is None:
            self._client = LLMClient()
        return self._client
    
    def complete(self, 
                 prompt: str,
                 model: Optional[str] = None,
                 max_tokens: int = 4096,
                 temperature: float = 0.7,
                 system_prompt: Optional[str] = None) -> Dict[str, Any]:
        """
        同步调用LLM
        
        Args:
            prompt: 用户提示词
            model: 模型名称（可选）
            max_tokens: 最大token数
            temperature: 温度参数
            system_prompt: 系统提示词（可选）
            
        Returns:
            包含content和metadata的字典
        """
        try:
            # 构建消息列表
            messages = []
            if system_prompt:
                messages.append({"role": "system", "content": system_prompt})
            messages.append({"role": "user", "content": prompt})
            
            # 调用LLM
            response_text = self.client.chat(
                messages=messages,
                model=model,
                temperature=temperature,
                max_tokens=max_tokens
            )
            
            return {
                "content": response_text,
                "success": True,
                "model": model or self.client.current_model
            }
            
        except Exception as e:
            log.print_log(f"[LLMService] 调用失败: {e}", "error")
            return {
                "content": "",
                "success": False,
                "error": str(e)
            }
    
    async def acomplete(self,
                       prompt: str,
                       model: Optional[str] = None,
                       max_tokens: int = 4096,
                       temperature: float = 0.7,
                       system_prompt: Optional[str] = None) -> Dict[str, Any]:
        """
        异步调用LLM
        
        Args:
            prompt: 用户提示词
            model: 模型名称（可选）
            max_tokens: 最大token数
            temperature: 温度参数
            system_prompt: 系统提示词（可选）
            
        Returns:
            包含content客观结果的字典
        """
        loop = asyncio.get_event_loop()
        
        # 在线程池中执行同步调用
        result = await loop.run_in_executor(
            self._executor,
            lambda: self.complete(
                prompt=prompt,
                model=model,
                max_tokens=max_tokens,
                temperature=temperature,
                system_prompt=system_prompt
            )
        )
        
        return result

    async def astream(self,
                     prompt: str,
                     model: Optional[str] = None,
                     max_tokens: int = 4096,
                     temperature: float = 0.7,
                     system_prompt: Optional[str] = None):
        """
        异步流式调用LLM
        
        Yields:
            文本片段
        """
        messages = []
        if system_prompt:
            messages.append({"role": "system", "content": system_prompt})
        messages.append({"role": "user", "content": prompt})
        
        async for chunk in self.client.stream_chat_async(
            messages=messages,
            model=model,
            temperature=temperature,
            max_tokens=max_tokens
        ):
            yield chunk
    
    def chat(self,
             messages: List[Dict[str, str]],
             model: Optional[str] = None,
             max_tokens: int = 4096,
             temperature: float = 0.7) -> str:
        """
        多轮对话（同步）
        
        Args:
            messages: 消息列表，格式 [{"role": "user", "content": "..."}, ...]
            model: 模型名称（可选）
            max_tokens: 最大token数
            temperature: 温度参数
            
        Returns:
            助手回复文本
        """
        try:
            return self.client.chat(
                messages=messages,
                model=model,
                temperature=temperature,
                max_tokens=max_tokens
            )
        except Exception as e:
            log.print_log(f"[LLMService] 对话失败: {e}", "error")
            return ""
    
    async def achat(self,
                   messages: List[Dict[str, str]],
                   model: Optional[str] = None,
                   max_tokens: int = 4096,
                   temperature: float = 0.7) -> str:
        """
        多轮对话（异步）
        
        Args:
            messages: 消息列表
            model: 模型名称（可选）
            max_tokens: 最大token数
            temperature: 温度参数
            
        Returns:
            助手回复文本
        """
        loop = asyncio.get_event_loop()
        
        result = await loop.run_in_executor(
            self._executor,
            lambda: self.chat(
                messages=messages,
                model=model,
                max_tokens=max_tokens,
                temperature=temperature
            )
        )
        
        return result


# 便捷函数
def get_llm_service() -> LLMService:
    """获取LLMService单例"""
    return LLMService()


async def quick_complete(prompt: str, 
                        model: Optional[str] = None,
                        max_tokens: int = 4096,
                        temperature: float = 0.7) -> str:
    """
    快速异步调用LLM
    
    Args:
        prompt: 提示词
        model: 模型名称（可选）
        max_tokens: 最大token数
        temperature: 温度参数
        
    Returns:
        回复文本
    """
    service = LLMService()
    result = await service.acomplete(
        prompt=prompt,
        model=model,
        max_tokens=max_tokens,
        temperature=temperature
    )
    return result.get("content", "")
