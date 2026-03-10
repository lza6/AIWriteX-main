"""
V19工作记忆升级 - 模拟人类认知极限
- 7±2 组块容量限制模拟
- 注意力焦点动态转移
- 认知负荷实时监控
- 干扰抑制机制
"""

import numpy as np
from typing import Dict, List, Optional, Any, Callable, Set, Tuple
from dataclasses import dataclass, field
from datetime import datetime, timedelta
from enum import Enum, auto
from collections import deque
import threading
import time


class AttentionState(Enum):
    """注意力状态"""
    FOCUSED = "focused"        # 高度集中
    DIVIDED = "divided"        # 分散注意
    VIGILANT = "vigilant"      # 警觉状态
    OVERLOADED = "overloaded"  # 过载状态


class CognitiveLoadLevel(Enum):
    """认知负荷等级"""
    LOW = "low"         # 低负荷
    MODERATE = "moderate"  # 中等负荷
    HIGH = "high"       # 高负荷
    CRITICAL = "critical"  # 临界负荷


@dataclass
class MemoryChunk:
    """记忆组块 - 模拟人类工作记忆容量(7±2)"""
    id: str
    content: Any
    priority: float = 1.0
    created_at: datetime = field(default_factory=datetime.now)
    last_accessed: datetime = field(default_factory=datetime.now)
    access_count: int = 0
    associations: Set[str] = field(default_factory=set)
    is_frozen: bool = False  # 冻结状态（不被挤出）
    cognitive_cost: float = 1.0  # 认知消耗

    def access(self):
        """访问组块"""
        self.access_count += 1
        self.last_accessed = datetime.now()

    def get_age_seconds(self) -> float:
        """获取组块存活时间（秒）"""
        return (datetime.now() - self.created_at).total_seconds()

    def get_recency_score(self) -> float:
        """获取近因得分（越新越高）"""
        age = self.get_age_seconds()
        return np.exp(-age / 300)  # 5分钟衰减


@dataclass
class AttentionFocus:
    """注意力焦点"""
    chunk_id: str
    depth: float = 1.0  # 聚焦深度 (0-1)
    breadth: int = 1   # 广度（同时关注的组块数）
    stability: float = 1.0  # 稳定性 (0-1)


@dataclass
class CognitiveMetrics:
    """认知指标"""
    current_load: float = 0.0
    load_level: CognitiveLoadLevel = CognitiveLoadLevel.LOW
    attention_focus: Optional[AttentionFocus] = None
    distraction_count: int = 0
    suppression_count: int = 0
    switch_count: int = 0
    throughput: float = 1.0  # 信息处理吞吐量


class WorkingMemoryV2:
    """
    V19 工作记忆系统
    模拟人类认知极限的智能记忆管理系统
    """

    # 容量常数 - Miller's Law (7±2)
    DEFAULT_CAPACITY = 7
    MIN_CAPACITY = 5
    MAX_CAPACITY = 9

    # 认知负荷阈值
    LOW_THRESHOLD = 0.3
    MODERATE_THRESHOLD = 0.6
    HIGH_THRESHOLD = 0.85
    CRITICAL_THRESHOLD = 0.95

    # 时间常量
    DECAY_HALF_LIFE = 180  # 3分钟半衰期
    ATTENTION_SWITCH_COST = 0.1  # 注意力切换成本
    CHUNK_PROCESSING_TIME = 0.5  # 组块处理时间(秒)

    def __init__(
        self,
        capacity: int = DEFAULT_CAPACITY,
        enable_decay: bool = True,
        enable_interference: bool = True,
        custom_decay_fn: Optional[Callable[[float], float]] = None
    ):
        """
        初始化工作记忆

        Args:
            capacity: 组块容量 (5-9)
            enable_decay: 启用时间衰减
            enable_interference: 启用干扰抑制
            custom_decay_fn: 自定义衰减函数
        """
        self.capacity = max(self.MIN_CAPACITY, min(self.MAX_CAPACITY, capacity))
        self.enable_decay = enable_decay
        self.enable_interference = enable_interference

        # 核心存储
        self._chunks: Dict[str, MemoryChunk] = {}
        self._chunk_order: deque = deque()  # LRU顺序

        # 注意力系统
        self._attention_focus: Optional[AttentionFocus] = None
        self._attention_queue: deque = deque()  # 待处理注意力队列

        # 认知监控
        self._cognitive_metrics = CognitiveMetrics()
        self._load_history: deque = deque(maxlen=100)

        # 干扰抑制
        self._inhibited_ids: Set[str] = set()
        self._inhibition_strength: float = 0.8

        # 衰减函数
        self._decay_fn = custom_decay_fn or (lambda t: np.exp(-t / self.DECAY_HALF_LIFE))

        # 线程安全
        self._lock = threading.RLock()

    @property
    def chunks(self) -> Dict[str, MemoryChunk]:
        """获取所有组块"""
        return self._chunks.copy()

    @property
    def current_load(self) -> float:
        """获取当前认知负荷 (0-1)"""
        return self._cognitive_metrics.current_load

    @property
    def load_level(self) -> CognitiveLoadLevel:
        """获取认知负荷等级"""
        return self._cognitive_metrics.load_level

    @property
    def attention_focus(self) -> Optional[AttentionFocus]:
        """获取当前注意力焦点"""
        return self._attention_focus

    @property
    def metrics(self) -> CognitiveMetrics:
        """获取认知指标"""
        return self._cognitive_metrics

    def add(
        self,
        content: Any,
        chunk_id: Optional[str] = None,
        priority: float = 1.0,
        is_frozen: bool = False,
        cognitive_cost: float = 1.0
    ) -> str:
        """
        添加组块到工作记忆

        Args:
            content: 组块内容
            chunk_id: 组块ID（可选，自动生成）
            priority: 优先级 (0-2)
            is_frozen: 是否冻结（不被挤出）
            cognitive_cost: 认知消耗 (0.5-2.0)

        Returns:
            chunk_id: 添加的组块ID
        """
        with self._lock:
            # 生成ID
            if chunk_id is None:
                chunk_id = f"chunk_{len(self._chunks)}_{int(time.time() * 1000)}"

            # 检查容量，必要时挤出
            if len(self._chunks) >= self.capacity:
                self._evict_lru(is_frozen)

            # 创建组块
            chunk = MemoryChunk(
                id=chunk_id,
                content=content,
                priority=np.clip(priority, 0, 2),
                is_frozen=is_frozen,
                cognitive_cost=np.clip(cognitive_cost, 0.5, 2.0)
            )

            # 存储
            self._chunks[chunk_id] = chunk
            self._chunk_order.append(chunk_id)

            # 更新认知负荷
            self._update_cognitive_load()

            return chunk_id

    def get(self, chunk_id: str, access: bool = True) -> Optional[Any]:
        """
        获取组块内容

        Args:
            chunk_id: 组块ID
            access: 是否记录访问

        Returns:
            组块内容，不存在则返回None
        """
        with self._lock:
            chunk = self._chunks.get(chunk_id)
            if chunk is None:
                return None

            if access:
                chunk.access()
                self._update_chunk_order(chunk_id)

            return chunk.content

    def remove(self, chunk_id: str) -> bool:
        """移除组块"""
        with self._lock:
            if chunk_id not in self._chunks:
                return False

            del self._chunks[chunk_id]
            self._chunk_order = deque(
                [cid for cid in self._chunk_order if cid != chunk_id],
                maxlen=self.capacity
            )

            # 如果是焦点，转移注意力
            if self._attention_focus and self._attention_focus.chunk_id == chunk_id:
                self._shift_attention()

            self._update_cognitive_load()
            return True

    def update(self, chunk_id: str, content: Any, priority: Optional[float] = None) -> bool:
        """更新组块内容"""
        with self._lock:
            chunk = self._chunks.get(chunk_id)
            if chunk is None:
                return False

            chunk.content = content
            if priority is not None:
                chunk.priority = np.clip(priority, 0, 2)

            self._update_cognitive_load()
            return True

    def focus_attention(
        self,
        chunk_id: str,
        depth: float = 1.0,
        breadth: int = 1
    ) -> bool:
        """
        聚焦注意力到指定组块

        Args:
            chunk_id: 目标组块ID
            depth: 聚焦深度 (0-1)
            breadth: 关注广度

        Returns:
            是否成功聚焦
        """
        with self._lock:
            if chunk_id not in self._chunks:
                return False

            # 检查是否过载
            if self._cognitive_metrics.load_level == CognitiveLoadLevel.CRITICAL:
                return False

            # 如果切换焦点
            if self._attention_focus and self._attention_focus.chunk_id != chunk_id:
                self._cognitive_metrics.switch_count += 1

            self._attention_focus = AttentionFocus(
                chunk_id=chunk_id,
                depth=np.clip(depth, 0, 1),
                breadth=max(1, min(breadth, 3)),
                stability=1.0
            )

            self._update_cognitive_metrics()
            return True

    def shift_attention(self, target_id: Optional[str] = None) -> bool:
        """
        转移注意力

        Args:
            target_id: 目标组块ID（可选，自动选择最重要的）

        Returns:
            是否成功转移
        """
        with self._lock:
            return self._shift_attention(target_id)

    def _shift_attention(self, target_id: Optional[str] = None) -> bool:
        """内部转移注意力逻辑"""
        if target_id is None:
            # 自动选择最重要的组块
            if not self._chunks:
                self._attention_focus = None
                return False

            target_id = self._get_most_important_chunk()

        if target_id not in self._chunks:
            return False

        self._attention_focus = AttentionFocus(
            chunk_id=target_id,
            depth=0.8,
            breadth=1,
            stability=0.9
        )
        self._cognitive_metrics.switch_count += 1
        return True

    def inhibit(self, chunk_id: str, strength: float = 0.8) -> bool:
        """
        抑制干扰项

        Args:
            chunk_id: 要抑制的组块ID
            strength: 抑制强度 (0-1)

        Returns:
            是否成功抑制
        """
        with self._lock:
            if chunk_id not in self._chunks:
                return False

            self._inhibited_ids.add(chunk_id)
            self._inhibition_strength = strength
            self._cognitive_metrics.suppression_count += 1
            return True

    def release_inhibition(self, chunk_id: str) -> bool:
        """释放抑制"""
        with self._lock:
            if chunk_id in self._inhibited_ids:
                self._inhibited_ids.discard(chunk_id)
                return True
            return False

    def clear_inhibitions(self) -> None:
        """清除所有抑制"""
        with self._lock:
            self._inhibited_ids.clear()

    def apply_decay(self) -> int:
        """
        应用时间衰减

        Returns:
            被移除的组块数量
        """
        if not self.enable_decay:
            return 0

        with self._lock:
            removed = 0
            current_time = time.time()

            # 遍历所有组块
            for chunk_id in list(self._chunks.keys()):
                chunk = self._chunks[chunk_id]
                if chunk.is_frozen:
                    continue

                # 计算衰减
                age = chunk.get_age_seconds()
                decay = self._decay_fn(age)

                # 如果完全衰减，移除
                if decay < 0.05:
                    self.remove(chunk_id)
                    removed += 1

            return removed

    def get_active_chunks(self, include_inhibited: bool = False) -> List[MemoryChunk]:
        """
        获取活跃组块

        Args:
            include_inhibited: 是否包含被抑制的组块

        Returns:
            活跃组块列表
        """
        with self._lock:
            chunks = []

            for chunk_id in self._chunk_order:
                chunk = self._chunks.get(chunk_id)
                if chunk is None:
                    continue

                if not include_inhibited and chunk_id in self._inhibited_ids:
                    continue

                chunks.append(chunk)

            return chunks

    def get_importance_ranking(self) -> List[Tuple[str, float]]:
        """
        获取组块重要性排名

        Returns:
            [(chunk_id, importance_score), ...]
        """
        with self._lock:
            scores = []

            for chunk in self._chunks.values():
                if chunk.id in self._inhibited_ids:
                    continue

                # 计算综合重要性
                recency = chunk.get_recency_score()
                frequency = np.log1p(chunk.access_count)
                priority = chunk.priority
                cognitive = 1.0 / chunk.cognitive_cost

                # 注意力加成
                attention_boost = 0
                if self._attention_focus and self._attention_focus.chunk_id == chunk.id:
                    attention_boost = self._attention_focus.depth * 0.3

                importance = (recency * 0.3 + frequency * 0.2 +
                            priority * 0.3 + cognitive * 0.2 + attention_boost)

                scores.append((chunk.id, importance))

            return sorted(scores, key=lambda x: x[1], reverse=True)

    def _evict_lru(self, preserve_frozen: bool = True) -> Optional[str]:
        """挤出最不常用的组块"""
        if not self._chunk_order:
            return None

        # 从最旧的开始查找
        for _ in range(len(self._chunk_order)):
            chunk_id = self._chunk_order[0]
            chunk = self._chunks.get(chunk_id)

            if chunk is None:
                self._chunk_order.popleft()
                continue

            # 如果冻结，跳过
            if preserve_frozen and chunk.is_frozen:
                self._chunk_order.rotate(-1)
                continue

            # 移除
            del self._chunks[chunk_id]
            self._chunk_order.popleft()
            return chunk_id

        return None

    def _update_chunk_order(self, chunk_id: str):
        """更新LRU顺序"""
        if chunk_id in self._chunk_order:
            self._chunk_order = deque(
                [cid for cid in self._chunk_order if cid != chunk_id],
                maxlen=self.capacity
            )
        self._chunk_order.append(chunk_id)

    def _get_most_important_chunk(self) -> Optional[str]:
        """获取最重要的组块"""
        ranking = self.get_importance_ranking()
        return ranking[0][0] if ranking else None

    def _update_cognitive_load(self):
        """更新认知负荷"""
        if not self._chunks:
            self._cognitive_metrics.current_load = 0.0
            self._cognitive_metrics.load_level = CognitiveLoadLevel.LOW
            return

        # 计算负荷：基于组块数量和认知消耗
        chunk_load = len(self._chunks) / self.capacity
        cost_load = sum(c.cognitive_cost for c in self._chunks.values()) / self.capacity
        inhibition_load = len(self._inhibited_ids) / max(1, len(self._chunks))

        # 综合负荷
        load = (chunk_load * 0.5 + cost_load * 0.35 + inhibition_load * 0.15)
        load = np.clip(load, 0, 1)

        self._cognitive_metrics.current_load = load

        # 更新负荷等级
        if load < self.LOW_THRESHOLD:
            level = CognitiveLoadLevel.LOW
        elif load < self.MODERATE_THRESHOLD:
            level = CognitiveLoadLevel.MODERATE
        elif load < self.HIGH_THRESHOLD:
            level = CognitiveLoadLevel.HIGH
        else:
            level = CognitiveLoadLevel.CRITICAL

        self._cognitive_metrics.load_level = level
        self._load_history.append(load)

    def _update_cognitive_metrics(self):
        """更新认知指标"""
        metrics = self._cognitive_metrics

        # 注意力稳定性
        if metrics.attention_focus:
            # 根据负荷调整稳定性
            load_factor = 1 - metrics.current_load
            metrics.attention_focus.stability *= load_factor

        # 吞吐量（高负荷时降低）
        if metrics.load_level == CognitiveLoadLevel.CRITICAL:
            metrics.throughput = 0.3
        elif metrics.load_level == CognitiveLoadLevel.HIGH:
            metrics.throughput = 0.6
        elif metrics.load_level == CognitiveLoadLevel.MODERATE:
            metrics.throughput = 0.8
        else:
            metrics.throughput = 1.0

    def get_status(self) -> Dict[str, Any]:
        """获取工作记忆状态"""
        with self._lock:
            return {
                "capacity": self.capacity,
                "current_size": len(self._chunks),
                "load": self._cognitive_metrics.current_load,
                "load_level": self._cognitive_metrics.load_level.value,
                "attention_focus": {
                    "chunk_id": self._attention_focus.chunk_id if self._attention_focus else None,
                    "depth": self._attention_focus.depth if self._attention_focus else 0,
                    "stability": self._attention_focus.stability if self._attention_focus else 0
                } if self._attention_focus else None,
                "inhibited_count": len(self._inhibited_ids),
                "metrics": {
                    "switch_count": self._cognitive_metrics.switch_count,
                    "suppression_count": self._cognitive_metrics.suppression_count,
                    "distraction_count": self._cognitive_metrics.distraction_count,
                    "throughput": self._cognitive_metrics.throughput
                },
                "ranking": self.get_importance_ranking()[:3]
            }

    def clear(self):
        """清空工作记忆"""
        with self._lock:
            self._chunks.clear()
            self._chunk_order.clear()
            self._attention_focus = None
            self._inhibited_ids.clear()
            self._cognitive_metrics = CognitiveMetrics()
            self._load_history.clear()

    def __len__(self) -> int:
        """获取当前组块数量"""
        return len(self._chunks)

    def __contains__(self, chunk_id: str) -> bool:
        """检查组块是否存在"""
        return chunk_id in self._chunks

    def __repr__(self) -> str:
        return f"WorkingMemoryV2(capacity={self.capacity}, size={len(self._chunks)}, load={self._cognitive_metrics.current_load:.2f})"
