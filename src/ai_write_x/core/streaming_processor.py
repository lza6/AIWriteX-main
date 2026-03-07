# -*- coding: UTF-8 -*-
"""
流式处理引擎 - Streaming Processing Engine
实现实时热点流处理，毫秒级响应

功能特性:
1. 滑动窗口流处理
2. 实时聚合统计
3. 热点检测算法
4. 背压处理
5. 容错恢复
"""

import asyncio
import time
import heapq
import hashlib
import json
from typing import Any, Dict, List, Optional, Callable, Awaitable
from dataclasses import dataclass, field
from datetime import datetime, timedelta
from collections import deque, defaultdict
from enum import Enum
from abc import ABC, abstractmethod
import logging

logger = logging.getLogger(__name__)


class EventPriority(str, Enum):
    """事件优先级"""
    LOW = "low"
    NORMAL = "normal"
    HIGH = "high"
    CRITICAL = "critical"


class StreamStatus(str, Enum):
    """流处理状态"""
    IDLE = "idle"
    RUNNING = "running"
    PAUSED = "paused"
    ERROR = "error"


@dataclass
class StreamEvent:
    """流事件"""
    event_id: str
    event_type: str
    data: Dict[str, Any]
    timestamp: datetime = field(default_factory=datetime.now)
    priority: EventPriority = EventPriority.NORMAL
    source: str = "unknown"
    metadata: Dict[str, Any] = field(default_factory=dict)
    
    def __lt__(self, other):
        """优先级比较"""
        priority_order = {
            EventPriority.CRITICAL: 4,
            EventPriority.HIGH: 3,
            EventPriority.NORMAL: 2,
            EventPriority.LOW: 1
        }
        return priority_order.get(self.priority, 0) > priority_order.get(other.priority, 0)


@dataclass
class HotspotMetric:
    """热点指标"""
    topic: str
    score: float
    velocity: float          # 变化速率
    volume: int             # 事件数量
    first_seen: datetime
    last_updated: datetime
    sources: List[str] = field(default_factory=list)
    keywords: List[str] = field(default_factory=list)


class StreamProcessor(ABC):
    """流处理器抽象基类"""
    
    @abstractmethod
    async def process(self, event: StreamEvent) -> Optional[Any]:
        """处理事件"""
        pass
    
    @abstractmethod
    async def on_error(self, event: StreamEvent, error: Exception):
        """错误处理"""
        pass


class HotspotDetector(StreamProcessor):
    """
    热点检测器
    使用多维度算法检测实时热点:
    1. 音量阈值 - 超过阈值触发
    2. 速度变化 - 短时间内快速增长
    3. 突发检测 - 异常模式识别
    4. 趋势预测 - 基于历史趋势
    """
    
    def __init__(
        self,
        window_size: int = 300,        # 窗口大小(秒)
        threshold_volume: int = 100,     # 音量阈值
        threshold_velocity: float = 2.0,  # 速度阈值
        min_topics: int = 10            # 最小热点数
    ):
        self.window_size = window_size
        self.threshold_volume = threshold_volume
        self.threshold_velocity = threshold_velocity
        self.min_topics = min_topics
        
        # 滑动窗口存储
        self._windows: Dict[str, deque] = defaultdict(
            lambda: deque(maxlen=1000)
        )
        
        # 热点缓存
        self._hotspots: Dict[str, HotspotMetric] = {}
        
        # 历史趋势
        self._history: Dict[str, List[float]] = defaultdict(list)
        
        # 回调函数
        self.on_hotspot_detected: Optional[Callable[[HotspotMetric], Awaitable]] = None
        self.on_hotspot_faded: Optional[Callable[[str], Awaitable]] = None
    
    async def process(self, event: StreamEvent) -> Optional[HotspotMetric]:
        """处理事件并检测热点"""
        # 提取话题
        topic = self._extract_topic(event)
        if not topic:
            return None
        
        # 更新窗口
        self._windows[topic].append(event.timestamp.timestamp())
        
        # 计算指标
        metric = self._calculate_metric(topic)
        
        # 检测热点
        is_hotspot = self._is_hotspot(metric)
        
        if is_hotspot and topic not in self._hotspots:
            # 新热点
            self._hotspots[topic] = metric
            logger.info(f"[热点检测] 检测到新热点: {topic} (score={metric.score:.2f})")
            
            if self.on_hotspot_detected:
                await self.on_hotspot_detected(metric)
        
        elif is_hotspot and topic in self._hotspots:
            # 更新热点
            self._hotspots[topic] = metric
        
        elif not is_hotspot and topic in self._hotspots:
            # 热点消退
            del self._hotspots[topic]
            logger.info(f"[热点检测] 热点消退: {topic}")
            
            if self.on_hotspot_faded:
                await self.on_hotspot_faded(topic)
        
        return metric if is_hotspot else None
    
    async def on_error(self, event: StreamEvent, error: Exception):
        """错误处理"""
        logger.error(f"[热点检测] 事件处理错误: {error}")
    
    def _extract_topic(self, event: StreamEvent) -> Optional[str]:
        """从事件中提取话题"""
        # 优先从data中提取
        if "topic" in event.data:
            return event.data["topic"]
        
        if "title" in event.data:
            # 使用标题作为话题
            return event.data["title"][:50]
        
        if "content" in event.data:
            # 使用内容哈希作为话题ID
            content = event.data["content"]
            return hashlib.md5(content.encode()).hexdigest()[:16]
        
        return None
    
    def _calculate_metric(self, topic: str) -> HotspotMetric:
        """计算热点指标"""
        now = datetime.now()
        window = self._windows[topic]
        
        if not window:
            return HotspotMetric(
                topic=topic,
                score=0.0,
                velocity=0.0,
                volume=0,
                first_seen=now,
                last_updated=now
            )
        
        # 计算音量
        volume = len(window)
        
        # 计算时间跨度
        timestamps = list(window)
        time_span = max(timestamps) - min(timestamps) if len(timestamps) > 1 else 1
        
        # 计算速度 (事件/秒)
        velocity = volume / max(time_span, 1)
        
        # 计算分数
        score = self._calculate_score(volume, velocity, topic)
        
        # 获取首次出现时间
        first_seen = datetime.fromtimestamp(min(timestamps))
        
        return HotspotMetric(
            topic=topic,
            score=score,
            velocity=velocity,
            volume=volume,
            first_seen=first_seen,
            last_updated=now
        )
    
    def _calculate_score(self, volume: int, velocity: float, topic: str) -> float:
        """计算热点分数"""
        # 音量分数 (归一化到 0-40)
        volume_score = min(40, volume / self.threshold_volume * 40)
        
        # 速度分数 (归一化到 0-40)
        velocity_score = min(40, velocity / self.threshold_velocity * 40)
        
        # 趋势分数 (基于历史)
        trend_score = self._calculate_trend_score(topic)
        
        # 突发分数
        burst_score = self._calculate_burst_score(topic)
        
        return volume_score + velocity_score + trend_score + burst_score
    
    def _calculate_trend_score(self, topic: str) -> float:
        """计算趋势分数"""
        history = self._history[topic]
        if len(history) < 2:
            return 10.0
        
        # 简单线性回归斜率
        recent = history[-5:] if len(history) >= 5 else history
        if len(recent) < 2:
            return 10.0
        
        n = len(recent)
        x = list(range(n))
        y = recent
        
        sum_x = sum(x)
        sum_y = sum(y)
        sum_xy = sum(x[i] * y[i] for i in range(n))
        sum_xx = sum(xi * xi for xi in x)
        
        slope = (n * sum_xy - sum_x * sum_y) / (n * sum_xx - sum_x * sum_x + 1e-10)
        
        # 归一化到 0-20
        return min(20, max(0, 10 + slope * 10))
    
    def _calculate_burst_score(self, topic: str) -> float:
        """计算突发分数"""
        # 简化的突发检测
        history = self._history[topic]
        if len(history) < 3:
            return 10.0
        
        recent_avg = sum(history[-3:]) / 3
        if recent_avg == 0:
            return 10.0
        
        current = self._windows[topic].__len__()
        burst_ratio = current / (recent_avg + 1)
        
        # 突发超过3倍给予高分
        return min(20, burst_ratio * 5)
    
    def _is_hotspot(self, metric: HotspotMetric) -> bool:
        """判断是否为热点"""
        # 更新历史
        self._history[metric.topic].append(metric.score)
        if len(self._history[metric.topic]) > 100:
            self._history[metric.topic] = self._history[metric.topic][-100:]
        
        # 多条件判断
        return (
            metric.volume >= self.threshold_volume or
            metric.velocity >= self.threshold_velocity or
            metric.score >= 50
        )
    
    def get_hotspots(self) -> List[HotspotMetric]:
        """获取当前热点列表"""
        return sorted(
            self._hotspots.values(),
            key=lambda x: x.score,
            reverse=True
        )[:self.min_topics]


class StreamAggregator(StreamProcessor):
    """
    流聚合器
    支持:
    1. 时间窗口聚合
    2. 计数聚合
    3. 去重聚合
    4. 百分比聚合
    """
    
    def __init__(self, window_size: int = 60):
        self.window_size = window_size
        self._counters: Dict[str, int] = defaultdict(int)
        self._unique: Dict[str, set] = defaultdict(set)
        self._sums: Dict[str, float] = defaultdict(float)
        self._timestamps: Dict[str, deque] = defaultdict(
            lambda: deque(maxlen=10000)
        )
    
    async def process(self, event: StreamEvent) -> Dict[str, Any]:
        """处理事件并进行聚合"""
        key = event.event_type
        
        # 计数
        self._counters[key] += 1
        
        # 时间戳记录
        self._timestamps[key].append(event.timestamp.timestamp())
        
        # 去重
        if "id" in event.data:
            self._unique[key].add(event.data["id"])
        
        # 数值求和
        for num_field in ["value", "count", "amount", "score"]:
            if num_field in event.data:
                try:
                    self._sums[f"{key}_{num_field}"] += float(event.data[num_field])
                except (ValueError, TypeError):
                    pass
        
        # 清理过期数据
        self._cleanup(key)
        
        return self.get_stats(key)
    
    async def on_error(self, event: StreamEvent, error: Exception):
        """错误处理"""
        logger.error(f"[流聚合] 错误: {error}")
    
    def _cleanup(self, key: str):
        """清理过期数据"""
        cutoff = time.time() - self.window_size
        
        # 清理时间戳
        timestamps = self._timestamps[key]
        while timestamps and timestamps[0] < cutoff:
            timestamps.popleft()
        
        # 重建唯一集合 (简化实现)
        if len(self._unique[key]) > 10000:
            current_time = time.time()
            self._unique[key] = {
                uid for uid in self._unique[key]
                if uid in [str(h) for h in self._timestamps[key]]
            }
    
    def get_stats(self, key: str = None) -> Dict[str, Any]:
        """获取聚合统计"""
        if key:
            return {
                "event_type": key,
                "count": self._counters[key],
                "unique_count": len(self._unique.get(key, set())),
                "sum": self._sums.get(key, 0),
                "avg": self._sums.get(key, 0) / max(self._counters[key], 1),
                "rate": len(self._timestamps[key]) / max(self.window_size, 1)
            }
        
        return {
            key: {
                "count": self._counters[key],
                "unique": len(self._unique.get(key, set())),
                "rate": len(self._timestamps[key]) / max(self.window_size, 1)
            }
            for key in self._counters.keys()
        }


class BackpressureHandler:
    """
    背压处理器
    防止数据流过载
    """
    
    def __init__(
        self,
        max_queue_size: int = 10000,
        overflow_strategy: str = "drop_oldest"  # drop_oldest, drop_newest, block
    ):
        self.max_queue_size = max_queue_size
        self.overflow_strategy = overflow_strategy
        self._queue: asyncio.PriorityQueue = asyncio.PriorityQueue(maxsize=max_queue_size)
        self._dropped = 0
        self._processed = 0
    
    async def enqueue(self, event: StreamEvent) -> bool:
        """入队"""
        try:
            self._queue.put_nowait(event)
            return True
        except asyncio.QueueFull:
            self._dropped += 1
            
            if self.overflow_strategy == "drop_oldest":
                # 丢弃最老的
                try:
                    self._queue.get_nowait()
                    self._queue.put_nowait(event)
                    return True
                except:
                    pass
            
            elif self.overflow_strategy == "block":
                # 阻塞等待
                await self._queue.put(event)
                return True
            
            return False
    
    async def dequeue(self) -> Optional[StreamEvent]:
        """出队"""
        try:
            event = await asyncio.wait_for(
                self._queue.get(),
                timeout=1.0
            )
            self._processed += 1
            return event
        except asyncio.TimeoutError:
            return None
    
    def get_stats(self) -> Dict[str, Any]:
        """获取背压统计"""
        return {
            "queue_size": self._queue.qsize(),
            "max_size": self.max_queue_size,
            "utilization": self._queue.qsize() / max(self.max_queue_size, 1),
            "dropped": self._dropped,
            "processed": self._processed,
            "overflow_strategy": self.overflow_strategy
        }


class StreamingProcessorEngine:
    """
    流处理引擎主类
    整合所有流处理组件
    """
    
    def __init__(self):
        # 状态
        self.status = StreamStatus.IDLE
        
        # 组件
        self.hotspot_detector = HotspotDetector()
        self.aggregator = StreamAggregator()
        self.backpressure = BackpressureHandler()
        
        # 处理器列表
        self._processors: List[StreamProcessor] = [
            self.hotspot_detector,
            self.aggregator
        ]
        
        # 事件队列
        self._event_queue: asyncio.Queue = asyncio.Queue(maxsize=1000)
        
        # 任务
        self._tasks: List[asyncio.Task] = []
        self._running = False
        
        # 统计
        self._stats = {
            "events_received": 0,
            "events_processed": 0,
            "events_dropped": 0,
            "start_time": None,
            "uptime": 0
        }
    
    async def start(self):
        """启动流处理引擎"""
        if self.status == StreamStatus.RUNNING:
            return
        
        self.status = StreamStatus.RUNNING
        self._running = True
        self._stats["start_time"] = datetime.now()
        
        # 启动消费者任务
        consumer = asyncio.create_task(self._consume_events())
        self._tasks.append(consumer)
        
        logger.info("[流处理引擎] 启动成功")
    
    async def stop(self):
        """停止流处理引擎"""
        self._running = False
        self.status = StreamStatus.IDLE
        
        # 取消所有任务
        for task in self._tasks:
            if not task.done():
                task.cancel()
        
        self._tasks.clear()
        
        # 更新统计
        if self._stats["start_time"]:
            self._stats["uptime"] = (
                datetime.now() - self._stats["start_time"]
            ).total_seconds()
        
        logger.info("[流处理引擎] 已停止")
    
    async def emit(
        self,
        event_type: str,
        data: Dict[str, Any],
        priority: EventPriority = EventPriority.NORMAL,
        source: str = "unknown"
    ) -> bool:
        """
        发射事件到流处理引擎
        """
        if self.status != StreamStatus.RUNNING:
            logger.warning("[流处理引擎] 未运行，事件被丢弃")
            return False
        
        event = StreamEvent(
            event_id=hashlib.md5(
                f"{time.time()}{event_type}".encode()
            ).hexdigest()[:16],
            event_type=event_type,
            data=data,
            priority=priority,
            source=source
        )
        
        self._stats["events_received"] += 1
        
        # 背压处理
        if not await self.backpressure.enqueue(event):
            self._stats["events_dropped"] += 1
            logger.warning(f"[流处理引擎] 事件丢弃 (背压): {event_type}")
            return False
        
        return True
    
    async def _consume_events(self):
        """消费事件"""
        while self._running:
            event = await self.backpressure.dequeue()
            
            if event is None:
                await asyncio.sleep(0.01)
                continue
            
            try:
                # 处理器链
                for processor in self._processors:
                    try:
                        await processor.process(event)
                    except Exception as e:
                        await processor.on_error(event, e)
                
                self._stats["events_processed"] += 1
            
            except Exception as e:
                logger.error(f"[流处理引擎] 事件处理错误: {e}")
    
    def get_hotspots(self) -> List[HotspotMetric]:
        """获取当前热点"""
        return self.hotspot_detector.get_hotspots()
    
    def get_aggregates(self) -> Dict[str, Any]:
        """获取聚合统计"""
        return self.aggregator.get_stats()
    
    def get_stats(self) -> Dict[str, Any]:
        """获取引擎统计"""
        stats = self._stats.copy()
        stats["status"] = self.status.value
        stats["backpressure"] = self.backpressure.get_stats()
        stats["hotspot_count"] = len(self.hotspot_detector._hotspots)
        
        if stats["start_time"]:
            stats["uptime"] = (
                datetime.now() - stats["start_time"]
            ).total_seconds()
        
        return stats


# 全局实例
_streaming_engine: Optional[StreamingProcessorEngine] = None


def get_streaming_processor() -> StreamingProcessorEngine:
    """获取流处理引擎实例"""
    global _streaming_engine
    
    if _streaming_engine is None:
        _streaming_engine = StreamingProcessorEngine()
    
    return _streaming_engine


async def emit_hotspot_event(
    event_type: str,
    data: Dict[str, Any],
    priority: EventPriority = EventPriority.NORMAL
) -> bool:
    """便捷函数: 发射热点事件"""
    engine = get_streaming_processor()
    return await engine.emit(event_type, data, priority, source="hotspot")


async def get_current_hotspots() -> List[HotspotMetric]:
    """便捷函数: 获取当前热点"""
    engine = get_streaming_processor()
    return engine.get_hotspots()
