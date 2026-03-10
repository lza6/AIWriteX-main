"""
记忆巩固系统 - 模拟睡眠中的记忆处理
├── 日间记忆捕获: 实时记录重要事件
├── 记忆重放: 离线时的记忆回顾
├── 噪声过滤: 去除不重要的记忆痕迹
├── 模式提取: 从经验中抽取一般知识
├── 记忆整合: 将新记忆融入现有知识结构
└── 遗忘机制: 主动遗忘过时信息
"""

import numpy as np
from typing import Dict, List, Optional, Any, Tuple, Set, Callable
from dataclasses import dataclass, field
from datetime import datetime, timedelta
from enum import Enum, auto
from collections import defaultdict, deque
import hashlib
import json
import threading
import time
import random


class ConsolidationPhase(Enum):
    """巩固阶段"""
    AWAKE = "awake"             # 清醒期（记忆捕获）
    LIGHT_SLEEP = "light_sleep"     # 浅睡期（记忆重放）
    DEEP_SLEEP = "deep_sleep"       # 深睡期（记忆整合）
    REM = "rem"                 # REM期（模式提取）
    CONSOLIDATED = "consolidated"    # 已巩固


class MemoryImportance(Enum):
    """记忆重要性"""
    CRITICAL = 1.0      # 关键
    HIGH = 0.8          # 高
    MEDIUM = 0.5        # 中
    LOW = 0.3           # 低
    IGNORED = 0.0       # 可忽略


class ReplayType(Enum):
    """重放类型"""
    SPONTANEOUS = "spontaneous"   # 自发重放
    CUELED = "cued"              # 线索触发
    PRIORITY = "priority"        # 优先级重放
    SEQUENTIAL = "sequential"    # 顺序重放


@dataclass
class DaytimeMemory:
    """日间记忆"""
    id: str
    content: Any
    context: Dict[str, Any]
    timestamp: datetime
    importance: MemoryImportance
    emotional_valence: float  # -1 to 1
    access_count: int = 0
    replay_count: int = 0
    consolidation_level: float = 0.0  # 0-1 巩固程度
    tags: Set[str] = field(default_factory=set)
    embedding: Optional[np.ndarray] = None
    metadata: Dict[str, Any] = field(default_factory=dict)


@dataclass
class ReplayEvent:
    """重放事件"""
    id: str
    memory_id: str
    replay_type: ReplayType
    timestamp: datetime
    intensity: float  # 重放强度
    context_activation: Dict[str, float] = field(default_factory=dict)


@dataclass
class PatternExtraction:
    """模式提取"""
    id: str
    source_memory_ids: List[str]
    pattern_type: str  # "temporal" / "causal" / "semantic"
    pattern_content: Any
    confidence: float
    extracted_at: datetime
    applicability: float = 1.0  # 适用性


@dataclass
class ConsolidatedKnowledge:
    """巩固后的知识"""
    id: str
    content: Any
    source_memory_ids: List[str]
    pattern_ids: List[str]
    abstraction_level: float  # 抽象程度
    confidence: float
    created_at: datetime
    last_accessed: datetime
    access_count: int = 0


@dataclass
class ForgettingEvent:
    """遗忘事件"""
    id: str
    memory_id: str
    forgetting_type: str  # "natural" / "interference" / "active"
    timestamp: datetime
    reason: str
    original_importance: MemoryImportance


class MemoryConsolidation:
    """
    记忆巩固系统

    模拟睡眠中的记忆处理过程:
    1. 日间记忆捕获: 实时记录重要事件
    2. 记忆重放: 离线时的记忆回顾
    3. 噪声过滤: 去除不重要记忆
    4. 模式提取: 抽取一般知识
    5. 记忆整合: 融入知识结构
    6. 遗忘机制: 主动遗忘
    """

    # 参数
    MAX_DAYTIME_MEMORIES = 10000
    MIN_IMPORTANCE_THRESHOLD = 0.3
    CONSOLIDATION_THRESHOLD = 0.8
    PATTERN_EXTRACTION_INTERVAL = 3600  # 秒
    DEFAULT_REPLAY_INTENSITY = 0.7

    def __init__(
        self,
        max_memories: int = 10000,
        enable_active_forgetting: bool = True,
        enable_pattern_extraction: bool = True,
        sleep_schedule: Optional[Dict[str, Any]] = None
    ):
        """
        初始化记忆巩固系统

        Args:
            max_memories: 最大日间记忆数
            enable_active_forgetting: 启用主动遗忘
            enable_pattern_extraction: 启用模式提取
            sleep_schedule: 睡眠时间表
        """
        self.max_memories = max_memories
        self.enable_active_forgetting = enable_active_forgetting
        self.enable_pattern_extraction = enable_pattern_extraction

        # 睡眠时间表
        self.sleep_schedule = sleep_schedule or {
            "sleep_hour": 23,
            "wake_hour": 7,
            "light_sleep_ratio": 0.3,
            "deep_sleep_ratio": 0.2,
            "rem_ratio": 0.25
        }

        # 日间记忆
        self._daytime_memories: Dict[str, DaytimeMemory] = {}
        self._memory_counter = 0

        # 巩固后的知识
        self._consolidated_knowledge: Dict[str, ConsolidatedKnowledge] = {}
        self._knowledge_counter = 0

        # 模式提取
        self._patterns: Dict[str, PatternExtraction] = {}
        self._pattern_counter = 0

        # 重放历史
        self._replay_history: deque = deque(maxlen=1000)

        # 遗忘历史
        self._forgetting_history: deque = deque(maxlen=500)

        # 当前阶段
        self._current_phase = ConsolidationPhase.AWAKE
        self._last_phase_change = datetime.now()

        # 统计
        self._statistics = {
            "total_captures": 0,
            "total_replays": 0,
            "patterns_extracted": 0,
            "memories_forgotten": 0,
            "knowledge_created": 0
        }

        # 线程安全
        self._lock = threading.RLock()

    # ==================== 日间记忆捕获 ====================

    def capture_memory(
        self,
        content: Any,
        context: Optional[Dict[str, Any]] = None,
        importance: MemoryImportance = MemoryImportance.MEDIUM,
        emotional_valence: float = 0.0,
        tags: Optional[Set[str]] = None,
        embedding: Optional[np.ndarray] = None
    ) -> str:
        """
        捕获日间记忆

        Args:
            content: 记忆内容
            context: 上下文
            importance: 重要性
            emotional_valence: 情感效价
            tags: 标签
            embedding: 嵌入向量

        Returns:
            记忆ID
        """
        with self._lock:
            # 重要性过滤
            if importance.value < self.MIN_IMPORTANCE_THRESHOLD:
                return None

            memory_id = f"mem_{self._memory_counter}"
            self._memory_counter += 1

            memory = DaytimeMemory(
                id=memory_id,
                content=content,
                context=context or {},
                timestamp=datetime.now(),
                importance=importance,
                emotional_valence=emotional_valence,
                tags=tags or set(),
                embedding=embedding
            )

            self._daytime_memories[memory_id] = memory

            # 更新统计
            self._statistics["total_captures"] += 1

            # 容量管理
            self._manage_memory_capacity()

            return memory_id

    def _manage_memory_capacity(self):
        """管理记忆容量"""
        if len(self._daytime_memories) > self.max_memories:
            # 找出最不重要的记忆
            sorted_memories = sorted(
                self._daytime_memories.values(),
                key=lambda m: (
                    m.importance.value,
                    m.consolidation_level,
                    -m.access_count
                )
            )

            # 移除最低优先级的记忆
            to_remove = len(self._daytime_memories) - self.max_memories + 100
            for memory in sorted_memories[:to_remove]:
                self._forget_memory(memory.id, "capacity")

    # ==================== 记忆重放 ====================

    def replay_memories(
        self,
        duration_minutes: int = 60,
        replay_type: ReplayType = ReplayType.SPONTANEOUS,
        cue: Optional[str] = None
    ) -> List[ReplayEvent]:
        """
        记忆重放（模拟睡眠过程）

        Args:
            duration_minutes: 重放时长
            replay_type: 重放类型
            cue: 线索（可选）

        Returns:
            重放事件列表
        """
        with self._lock:
            events = []

            # 确定当前睡眠阶段
            self._update_sleep_phase(duration_minutes)

            # 根据阶段选择重放策略
            if self._current_phase == ConsolidationPhase.LIGHT_SLEEP:
                events = self._light_sleep_replay(replay_type, cue)
            elif self._current_phase == ConsolidationPhase.DEEP_SLEEP:
                events = self._deep_sleep_replay()
            elif self._current_phase == ConsolidationPhase.REM:
                events = self._rem_replay()

            # 更新统计
            self._statistics["total_replays"] += len(events)

            return events

    def _light_sleep_replay(
        self,
        replay_type: ReplayType,
        cue: Optional[str]
    ) -> List[ReplayEvent]:
        """浅睡期重放：强化重要记忆"""
        events = []

        # 选择要重放的记忆
        memories_to_replay = self._select_memories_for_replay(
            replay_type, cue, priority="importance"
        )

        for memory in memories_to_replay:
            event = self._replay_memory(memory, ReplayType.PRIORITY)
            events.append(event)

            # 增强巩固
            memory.consolidation_level += 0.1

        return events

    def _deep_sleep_replay(self) -> List[ReplayEvent]:
        """深睡期重放：记忆整合"""
        events = []

        # 选择高度重要的记忆进行深度整合
        important_memories = [
            m for m in self._daytime_memories.values()
            if m.importance.value >= MemoryImportance.HIGH.value
        ]

        for memory in important_memories:
            event = self._replay_memory(memory, ReplayType.SEQUENTIAL)
            events.append(event)

            # 深层次巩固
            memory.consolidation_level += 0.2

            # 检查是否可以转化为知识
            if memory.consolidation_level >= self.CONSOLIDATION_THRESHOLD:
                self._consolidate_memory(memory)

        return events

    def _rem_replay(self) -> List[ReplayEvent]:
        """REM期重放：模式提取"""
        events = []

        # 随机选择记忆进行重放
        memories = list(self._daytime_memories.values())
        random.shuffle(memories)

        for memory in memories[:10]:  # 重放10个记忆
            event = self._replay_memory(memory, ReplayType.SPONTANEOUS)
            events.append(event)

            # 触发模式提取
            if self.enable_pattern_extraction:
                self._extract_patterns(memory)

        return events

    def _select_memories_for_replay(
        self,
        replay_type: ReplayType,
        cue: Optional[str],
        priority: str = "importance"
    ) -> List[DaytimeMemory]:
        """选择要重放的记忆"""
        if replay_type == ReplayType.CUELED and cue:
            # 线索触发：选择与线索相关的记忆
            return self._cue_based_selection(cue)
        elif replay_type == ReplayType.PRIORITY:
            # 优先级：选择最重要的
            return self._priority_based_selection()
        else:
            # 其他：随机选择
            return self._random_selection()

    def _cue_based_selection(self, cue: str) -> List[DaytimeMemory]:
        """基于线索选择"""
        selected = []

        for memory in self._daytime_memories.values():
            # 检查标签和上下文
            if cue in memory.tags:
                selected.append(memory)
            elif any(cue in str(v) for v in memory.context.values()):
                selected.append(memory)

        return selected[:20]

    def _priority_based_selection(self) -> List[DaytimeMemory]:
        """基于优先级选择"""
        sorted_memories = sorted(
            self._daytime_memories.values(),
            key=lambda m: (
                m.importance.value,
                m.emotional_valence,
                -m.replay_count
            ),
            reverse=True
        )

        return sorted_memories[:20]

    def _random_selection(self) -> List[DaytimeMemory]:
        """随机选择"""
        memories = list(self._daytime_memories.values())
        return random.sample(memories, min(10, len(memories)))

    def _replay_memory(
        self,
        memory: DaytimeMemory,
        replay_type: ReplayType
    ) -> ReplayEvent:
        """执行记忆重放"""
        event_id = f"replay_{len(self._replay_history)}"

        # 计算重放强度
        intensity = self.DEFAULT_REPLAY_INTENSITY
        if memory.emotional_valence > 0:
            intensity *= (1 + memory.emotional_valence)
        intensity = min(1.0, intensity)

        event = ReplayEvent(
            id=event_id,
            memory_id=memory.id,
            replay_type=replay_type,
            timestamp=datetime.now(),
            intensity=intensity,
            context_activation=memory.context
        )

        # 更新记忆
        memory.replay_count += 1

        # 记录历史
        self._replay_history.append(event)

        return event

    # ==================== 模式提取 ====================

    def _extract_patterns(self, memory: DaytimeMemory):
        """从记忆中提取模式"""
        # 时间模式
        self._extract_temporal_pattern(memory)

        # 语义模式
        self._extract_semantic_pattern(memory)

        # 因果模式
        self._extract_causal_pattern(memory)

    def _extract_temporal_pattern(self, memory: DaytimeMemory):
        """提取时间模式"""
        # 检查时间相邻的记忆
        memory_time = memory.timestamp
        time_window = timedelta(hours=1)

        similar_memories = [
            m for m in self._daytime_memories.values()
            if m.id != memory.id
            and abs((m.timestamp - memory_time).total_seconds()) < time_window.total_seconds()
        ]

        if len(similar_memories) >= 3:
            # 发现时间模式
            pattern_id = f"pattern_{self._pattern_counter}"
            self._pattern_counter += 1

            pattern = PatternExtraction(
                id=pattern_id,
                source_memory_ids=[memory.id] + [m.id for m in similar_memories],
                pattern_type="temporal",
                pattern_content={
                    "description": "时间相近的事件序列",
                    "time_gap": "约1小时内"
                },
                confidence=0.7,
                extracted_at=datetime.now()
            )

            self._patterns[pattern_id] = pattern
            self._statistics["patterns_extracted"] += 1

    def _extract_semantic_pattern(self, memory: DaytimeMemory):
        """提取语义模式"""
        # 检查标签相同的记忆
        if not memory.tags:
            return

        similar_by_tag = [
            m for m in self._daytime_memories.values()
            if m.id != memory.id and m.tags & memory.tags
        ]

        if len(similar_by_tag) >= 3:
            pattern_id = f"pattern_{self._pattern_counter}"
            self._pattern_counter += 1

            pattern = PatternExtraction(
                id=pattern_id,
                source_memory_ids=[memory.id] + [m.id for m in similar_by_tag],
                pattern_type="semantic",
                pattern_content={
                    "shared_tags": list(memory.tags),
                    "description": "相同主题的事件"
                },
                confidence=0.8,
                extracted_at=datetime.now()
            )

            self._patterns[pattern_id] = pattern
            self._statistics["patterns_extracted"] += 1

    def _extract_causal_pattern(self, memory: DaytimeMemory):
        """提取因果模式"""
        # 检查上下文中的因果线索
        context = memory.context

        if "cause" in context and "effect" in context:
            pattern_id = f"pattern_{self._pattern_counter}"
            self._pattern_counter += 1

            pattern = PatternExtraction(
                id=pattern_id,
                source_memory_ids=[memory.id],
                pattern_type="causal",
                pattern_content={
                    "cause": context.get("cause"),
                    "effect": context.get("effect"),
                    "description": "因果关系"
                },
                confidence=0.6,
                extracted_at=datetime.now()
            )

            self._patterns[pattern_id] = pattern
            self._statistics["patterns_extracted"] += 1

    # ==================== 记忆整合 ====================

    def _consolidate_memory(self, memory: DaytimeMemory):
        """将记忆转化为巩固知识"""
        # 查找相关模式
        related_patterns = [
            p for p in self._patterns.values()
            if memory.id in p.source_memory_ids
        ]

        # 创建知识
        knowledge_id = f"knowledge_{self._knowledge_counter}"
        self._knowledge_counter += 1

        knowledge = ConsolidatedKnowledge(
            id=knowledge_id,
            content=memory.content,
            source_memory_ids=[memory.id],
            pattern_ids=[p.id for p in related_patterns],
            abstraction_level=memory.consolidation_level,
            confidence=memory.importance.value,
            created_at=datetime.now(),
            last_accessed=datetime.now()
        )

        self._consolidated_knowledge[knowledge_id] = knowledge
        self._statistics["knowledge_created"] += 1

        # 标记原记忆为已巩固
        memory.consolidation_level = 1.0

    def retrieve_knowledge(
        self,
        query: Any,
        top_k: int = 5
    ) -> List[ConsolidatedKnowledge]:
        """
        检索巩固知识

        Args:
            query: 查询
            top_k: 返回数量

        Returns:
            知识列表
        """
        results = []

        for knowledge in self._consolidated_knowledge.values():
            # 简化：基于访问频率
            score = knowledge.confidence * (1 + 0.1 * knowledge.access_count)
            results.append((knowledge, score))

        # 排序
        results.sort(key=lambda x: x[1], reverse=True)

        # 更新访问
        for knowledge, _ in results[:top_k]:
            knowledge.access_count += 1
            knowledge.last_accessed = datetime.now()

        return [k for k, _ in results[:top_k]]

    # ==================== 遗忘机制 ====================

    def _forget_memory(self, memory_id: str, reason: str):
        """遗忘记忆"""
        if memory_id not in self._daytime_memories:
            return

        memory = self._daytime_memories[memory_id]

        # 记录遗忘事件
        event_id = f"forget_{len(self._forgetting_history)}"
        event = ForgettingEvent(
            id=event_id,
            memory_id=memory_id,
            forgetting_type=reason,
            timestamp=datetime.now(),
            reason=reason,
            original_importance=memory.importance
        )

        self._forgetting_history.append(event)

        # 移除记忆
        del self._daytime_memories[memory_id]
        self._statistics["memories_forgotten"] += 1

    def trigger_active_forgetting(self):
        """触发主动遗忘"""
        if not self.enable_active_forgetting:
            return

        with self._lock:
            # 找出应该遗忘的记忆
            to_forget = []

            for memory in self._daytime_memories.values():
                # 低重要性 + 长时间未访问
                age_days = (datetime.now() - memory.timestamp).days
                if (memory.importance.value < MemoryImportance.MEDIUM.value
                    and age_days > 7
                    and memory.access_count == 0):
                    to_forget.append(memory.id)

            # 遗忘
            for memory_id in to_forget:
                self._forget_memory(memory_id, "active")

    def _update_sleep_phase(self, duration_minutes: int):
        """更新睡眠阶段"""
        now = datetime.now()
        elapsed = (now - self._last_phase_change).total_seconds() / 60

        if elapsed > duration_minutes:
            # 切换阶段
            phases = [
                ConsolidationPhase.LIGHT_SLEEP,
                ConsolidationPhase.DEEP_SLEEP,
                ConsolidationPhase.REM
            ]

            current_idx = phases.index(self._current_phase) if self._current_phase in phases else 0
            next_idx = (current_idx + 1) % len(phases)

            self._current_phase = phases[next_idx]
            self._last_phase_change = now
        elif self._current_phase == ConsolidationPhase.AWAKE:
            # 刚开始睡眠
            self._current_phase = ConsolidationPhase.LIGHT_SLEEP

    # ==================== 统计和状态 ====================

    def get_statistics(self) -> Dict[str, Any]:
        """获取统计信息"""
        return {
            **self._statistics,
            "current_phase": self._current_phase.value,
            "daytime_memories": len(self._daytime_memories),
            "consolidated_knowledge": len(self._consolidated_knowledge),
            "patterns": len(self._patterns),
            "replay_events": len(self._replay_history),
            "forgetting_events": len(self._forgetting_history)
        }

    def get_memory_status(self, memory_id: str) -> Dict[str, Any]:
        """获取记忆状态"""
        if memory_id not in self._daytime_memories:
            return {"status": "not_found"}

        memory = self._daytime_memories[memory_id]

        return {
            "id": memory.id,
            "importance": memory.importance.value,
            "consolidation_level": memory.consolidation_level,
            "replay_count": memory.replay_count,
            "age_hours": (datetime.now() - memory.timestamp).total_seconds() / 3600
        }

    def __repr__(self) -> str:
        return f"MemoryConsolidation(memories={len(self._daytime_memories)}, knowledge={len(self._consolidated_knowledge)})"
