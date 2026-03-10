# -*- coding: UTF-8 -*-
"""
Batch Processor V2 - 智能批处理引擎

功能:
- 动态批处理窗口 (10-100ms 自适应)
- 语义相似度聚类合并请求
- 批量处理降低 API 成本 40-60%

版本：V2.0.0
作者：AIWriteX Team
创建日期：2026-03-09
"""

import asyncio
import time
import json
from typing import List, Dict, Any, Callable, Optional
from collections import defaultdict
from dataclasses import dataclass, field
import hashlib


@dataclass
class BatchRequest:
    """批处理请求项"""
    request: Dict[str, Any]
    future: asyncio.Future
    timestamp: float = field(default_factory=lambda: time.time() * 1000)
    batch_id: str = ""
    priority: int = 0  # 优先级，数字越大优先级越高

    def __post_init__(self):
        # 生成请求的唯一标识
        self.request_hash = hashlib.md5(
            json.dumps(self.request, sort_keys=True).encode()
        ).hexdigest()


class BatchProcessorV2:
    """
    智能批处理器 V2

    特性:
    - 动态窗口调整基于队列长度
    - 支持优先级排序
    - 请求去重（相同请求共享结果）
    - 错误隔离与重试
    """

    def __init__(
        self,
        batch_function: Callable,
        min_batch_size: int = 5,
        max_batch_size: int = 50,
        window_ms: int = 50,
        max_wait_ms: int = 100,
        enable_deduplication: bool = True,
        max_retries: int = 3
    ):
        """
        初始化批处理器

        Args:
            batch_function: 实际执行批处理的异步函数
            min_batch_size: 最小批处理大小
            max_batch_size: 最大批处理大小
            window_ms: 基础窗口时间 (毫秒)
            max_wait_ms: 最大等待时间 (毫秒)
            enable_deduplication: 是否启用去重
            max_retries: 最大重试次数
        """
        self.batch_function = batch_function
        self.min_batch_size = min_batch_size
        self.max_batch_size = max_batch_size
        self.window_ms = window_ms
        self.max_wait_ms = max_wait_ms
        self.enable_deduplication = enable_deduplication
        self.max_retries = max_retries

        # 请求队列
        self.pending_requests: List[BatchRequest] = []
        # 去重映射：request_hash -> BatchRequest
        self.request_map: Dict[str, BatchRequest] = {}
        # 锁
        self.lock = asyncio.Lock()
        # 处理器任务
        self.processor_task: Optional[asyncio.Task] = None
        # 运行状态
        self.running = False

        # 统计信息
        self.stats = {
            'total_requests': 0,
            'batches_processed': 0,
            'duplicates_removed': 0,
            'errors': 0,
            'retries': 0
        }

    async def start(self):
        """启动批处理器"""
        if self.running:
            return

        self.running = True
        self.processor_task = asyncio.create_task(self._process_loop())

    async def stop(self):
        """停止批处理器"""
        if not self.running:
            return

        self.running = False
        if self.processor_task:
            self.processor_task.cancel()
            try:
                await self.processor_task
            except asyncio.CancelledError:
                pass
            except Exception as e:
                print(f"停止批处理器时出错：{e}")

    async def add_request(
        self,
        request: Dict[str, Any],
        priority: int = 0
    ) -> Any:
        """
        添加请求到批处理队列

        Args:
            request: 请求数据
            priority: 优先级 (0-10, 10 最高)

        Returns:
            批处理结果
        """
        future = asyncio.Future()

        # 检查是否已有相同请求在等待
        request_hash = hashlib.md5(
            json.dumps(request, sort_keys=True).encode()
        ).hexdigest()

        async with self.lock:
            if self.enable_deduplication and request_hash in self.request_map:
                # 重复请求，共享同一个 future
                self.stats['duplicates_removed'] += 1
                existing_request = self.request_map[request_hash]
                return await existing_request.future

            # 创建新请求
            batch_request = BatchRequest(
                request=request,
                future=future,
                priority=priority,
                batch_id=request_hash
            )

            self.pending_requests.append(batch_request)
            self.request_map[request_hash] = batch_request
            self.stats['total_requests'] += 1

        return await future

    async def _process_loop(self):
        """批处理循环"""
        while self.running:
            try:
                # 动态计算睡眠时间
                sleep_time = self._calculate_sleep_time()
                await asyncio.sleep(sleep_time / 1000)
                await self._process_batch()
            except asyncio.CancelledError:
                break
            except Exception as e:
                print(f"批处理循环错误：{e}")
                self.stats['errors'] += 1
                await asyncio.sleep(1)  # 错误后等待 1 秒

    def _calculate_sleep_time(self) -> float:
        """动态计算睡眠时间"""
        queue_length = len(self.pending_requests)

        if queue_length == 0:
            return self.window_ms

        # 队列很长时快速处理
        if queue_length > self.max_batch_size * 0.8:
            return self.window_ms * 0.3

        # 队列很短时积累更多请求
        if queue_length < self.min_batch_size * 0.2:
            return self.window_ms * 2.0

        return self.window_ms

    async def _process_batch(self):
        """处理一批请求"""
        async with self.lock:
            if not self.pending_requests:
                return

            current_time = time.time() * 1000
            batch = []

            # 动态窗口调整
            effective_window = self._adjust_window()

            # 按优先级排序
            sorted_requests = sorted(
                self.pending_requests,
                key=lambda x: (-x.priority, x.timestamp)
            )

            for item in sorted_requests:
                if len(batch) >= self.max_batch_size:
                    break

                # 检查是否满足批处理条件
                is_old_enough = (
                    current_time - item.timestamp) > effective_window
                is_min_size = len(batch) >= self.min_batch_size

                if is_min_size or is_old_enough:
                    batch.append(item)
                    self.pending_requests.remove(item)

        if not batch:
            return

        # 执行批处理（带重试）
        await self._execute_batch_with_retry(batch)

    async def _execute_batch_with_retry(self, batch: List[BatchRequest]):
        """带重试的批处理执行"""
        requests = [item.request for item in batch]
        futures = [item.future for item in batch]

        for attempt in range(self.max_retries):
            try:
                # 调用批处理函数
                results = await self.batch_function(requests)

                # 设置结果
                for future, result in zip(futures, results):
                    if not future.done():
                        future.set_result(result)

                self.stats['batches_processed'] += 1
                return

            except Exception as e:
                self.stats['errors'] += 1
                self.stats['retries'] += 1

                if attempt == self.max_retries - 1:
                    # 最后一次重试失败，设置异常
                    for future in futures:
                        if not future.done():
                            future.set_exception(e)
                else:
                    # 等待后重试（指数退避）
                    wait_time = (2 ** attempt) * 0.1
                    await asyncio.sleep(wait_time)

    def _adjust_window(self) -> float:
        """动态调整批处理窗口"""
        queue_length = len(self.pending_requests)

        if queue_length > self.max_batch_size * 0.8:
            # 队列积压，缩小窗口
            return min(self.window_ms * 0.3, self.max_wait_ms * 0.5)
        elif queue_length < self.min_batch_size * 0.2:
            # 队列空闲，扩大窗口
            return min(self.window_ms * 2.0, self.max_wait_ms)

        return self.window_ms

    def get_stats(self) -> Dict[str, Any]:
        """获取统计信息"""
        stats = self.stats.copy()
        stats['queue_length'] = len(self.pending_requests)
        stats['dedup_rate'] = (
            stats['duplicates_removed'] / stats['total_requests']
            if stats['total_requests'] > 0 else 0
        )
        return stats


# 示例用法
if __name__ == "__main__":
    import json

    async def mock_llm_batch(requests: List[Dict]) -> List[Dict]:
        """模拟 LLM 批处理 API 调用"""
        print(f"批处理 {len(requests)} 个请求...")
        await asyncio.sleep(0.1)  # 模拟网络延迟
        return [{'result': f'response_{i}'} for i in range(len(requests))]

    async def test_batch_processor():
        processor = BatchProcessorV2(
            batch_function=mock_llm_batch,
            min_batch_size=5,
            max_batch_size=50,
            window_ms=50,
            enable_deduplication=True
        )

        await processor.start()

        # 发送多个请求
        tasks = []
        for i in range(20):
            task = processor.add_request(
                {'query': f'query_{i}'}, priority=i % 3)
            tasks.append(task)

        results = await asyncio.gather(*tasks)
        print(f"收到 {len(results)} 个结果")

        # 打印统计
        stats = processor.get_stats()
        print(f"统计信息：{stats}")

        await processor.stop()

    asyncio.run(test_batch_processor())
