"""
联想记忆网络 - 类人的记忆激活
├── 自由联想: 一个记忆触发相关记忆
├── 语义网络: 概念间的关联图谱
├── 情感标记: 记忆的情绪色彩
├── 情境依赖: 上下文触发的记忆恢复
├── 记忆竞争: 多个记忆的激活竞争
└── 虚假记忆检测: 识别不一致的记忆
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


class AssociationType(Enum):
    """联想类型"""
    SEMANTIC = "semantic"       # 语义联想（相似/相关）
    EPISODIC = "episodic"       # 情景联想（时间相近）
    EMOTIONAL = "emotional"     # 情感联想（情绪相关）
    CAUSAL = "causal"           # 因果联想
    SPATIAL = "spatial"          # 空间联想
    PHONETIC = "phonetic"       # 语音联想


class ActivationState(Enum):
    """激活状态"""
    DORMANT = "dormant"         # 休眠
    PRIMED = "primed"           # 已 priming
    ACTIVE = "active"           # 激活
    WORKING = "working"         # 工作记忆
    CONSOLIDATED = "consolidated"  # 已巩固


class MemoryConsistency(Enum):
    """记忆一致性"""
    CONSISTENT = "consistent"   # 一致
    INCONSISTENT = "inconsistent"  # 不一致
    CONFLICTING = "conflicting"  # 冲突
    UNVERIFIED = "unverified"   # 未验证


@dataclass
class MemoryNode:
    """记忆节点"""
    id: str
    content: Any
    concept: str                # 核心概念
    keywords: Set[str] = field(default_factory=set)
    associations: Dict[str, float] = field(default_factory=dict)  # 关联ID -> 强度
    emotional_tags: Dict[str, float] = field(default_factory=dict)  # 情感标签 -> 强度
    context: Set[str] = field(default_factory=set)  # 情境标签
    activation_level: float = 0.0
    state: ActivationState = ActivationState.DORMANT
    created_at: datetime = field(default_factory=datetime.now)
    last_accessed: datetime = field(default_factory=datetime.now)
    access_count: int = 0
    priming_count: int = 0
    confidence: float = 1.0
    metadata: Dict[str, Any] = field(default_factory=dict)


@dataclass
class Association:
    """联想连接"""
    id: str
    source_id: str
    target_id: str
    association_type: AssociationType
    strength: float             # 联想强度 0-1
    weight: float = 1.0         # 权重（可调节）
    conditions: Dict[str, Any] = field(default_factory=dict)  # 触发条件
    created_at: datetime = field(default_factory=datetime.now)
    usage_count: int = 0


@dataclass
class ActivationTrace:
    """激活轨迹"""
    id: str
    memory_id: str
    timestamp: datetime
    activation_level: float
    trigger: str  # 触发来源
    context: Dict[str, Any] = field(default_factory=dict)


@dataclass
class InconsistencyReport:
    """不一致报告"""
    id: str
    memory_ids: List[str]
    inconsistency_type: str
    severity: float  # 严重程度 0-1
    details: str
    detected_at: datetime
    resolved: bool = False


@dataclass
class RetrievalResult:
    """检索结果"""
    memory: MemoryNode
    activation_level: float
    relevance_score: float
    match_type: str  # "semantic" / "episodic" / "emotional" / "context"
    cues: List[str] = field(default_factory=list)


class AssociativeMemoryNetwork:
    """
    联想记忆网络

    实现类人的记忆激活机制:
    1. 自由联想: 一个记忆触发相关记忆
    2. 语义网络: 概念间的关联图谱
    3. 情感标记: 记忆的情绪色彩
    4. 情境依赖: 上下文触发的记忆恢复
    5. 记忆竞争: 多个记忆的激活竞争
    6. 虚假记忆检测: 识别不一致的记忆
    """

    # 参数
    MAX_MEMORIES = 50000
    ACTIVATION_DECAY = 0.9          # 激活衰减
    PRIMING_THRESHOLD = 0.3         # priming 阈值
    RETRIEVAL_THRESHOLD = 0.5      # 检索阈值
    COMPETITION_WINDOW = 10         # 竞争窗口
    MAX_ASSOCIATIONS_PER_NODE = 50  # 每个节点最大联想数

    def __init__(
        self,
        max_memories: int = 50000,
        enable_emotional: bool = True,
        enable_context: bool = True,
        enable_consistency_check: bool = True
    ):
        """
        初始化联想记忆网络

        Args:
            max_memories: 最大记忆数
            enable_emotional: 启用情感联想
            enable_context: 启用情境联想
            enable_consistency_check: 启用一致性检查
        """
        self.max_memories = max_memories
        self.enable_emotional = enable_emotional
        self.enable_context = enable_context
        self.enable_consistency_check = enable_consistency_check

        # 记忆存储
        self._memories: Dict[str, MemoryNode] = {}
        self._memory_counter = 0

        # 联想网络
        self._associations: Dict[str, Association] = {}
        self._association_counter = 0

        # 概念索引
        self._concept_index: Dict[str, Set[str]] = defaultdict(set)
        self._keyword_index: Dict[str, Set[str]] = defaultdict(set)
        self._context_index: Dict[str, Set[str]] = defaultdict(set)
        self._emotional_index: Dict[str, Set[str]] = defaultdict(set)

        # 激活历史
        self._activation_history: deque = deque(maxlen=1000)
        self._current_activation_trace: List[ActivationTrace] = []

        # 不一致性检测
        self._inconsistencies: List[InconsistencyReport] = []

        # 统计
        self._statistics = {
            "total_memories": 0,
            "total_associations": 0,
            "total_retrievals": 0,
            "inconsistencies_detected": 0,
            "false_memories_flagged": 0
        }

        # 线程安全
        self._lock = threading.RLock()

    # ==================== 记忆存储 ====================

    def store_memory(
        self,
        content: Any,
        concept: str,
        keywords: Optional[Set[str]] = None,
        emotional_tags: Optional[Dict[str, float]] = None,
        context: Optional[Set[str]] = None,
        confidence: float = 1.0,
        metadata: Optional[Dict[str, Any]] = None
    ) -> str:
        """
        存储记忆

        Args:
            content: 记忆内容
            concept: 核心概念
            keywords: 关键词
            emotional_tags: 情感标签
            context: 情境标签
            confidence: 置信度
            metadata: 元数据

        Returns:
            记忆ID
        """
        with self._lock:
            memory_id = f"mem_{self._memory_counter}"
            self._memory_counter += 1

            memory = MemoryNode(
                id=memory_id,
                content=content,
                concept=concept,
                keywords=keywords or set(),
                emotional_tags=emotional_tags or {},
                context=context or set(),
                confidence=confidence,
                metadata=metadata or {}
            )

            self._memories[memory_id] = memory

            # 更新索引
            self._concept_index[concept].add(memory_id)
            for kw in memory.keywords:
                self._keyword_index[kw].add(memory_id)
            for ctx in memory.context:
                self._context_index[ctx].add(memory_id)
            for emo in memory.emotional_tags:
                self._emotional_index[emo].add(memory_id)

            # 容量管理
            if len(self._memories) > self.max_memories:
                self._evict_low_activation_memories()

            # 一致性检查
            if self.enable_consistency_check:
                self._check_consistency(memory_id)

            self._statistics["total_memories"] += 1

            return memory_id

    def _evict_low_activation_memories(self):
        """移除低激活记忆"""
        # 按激活水平和访问次数排序
        sorted_memories = sorted(
            self._memories.values(),
            key=lambda m: (m.activation_level, m.access_count, -m.priming_count)
        )

        # 移除最低的
        to_remove = len(self._memories) - self.max_memories + 100
        for memory in sorted_memories[:to_remove]:
            self._remove_memory(memory.id)

    def _remove_memory(self, memory_id: str):
        """移除记忆"""
        if memory_id not in self._memories:
            return

        memory = self._memories[memory_id]

        # 从索引中移除
        self._concept_index[memory.concept].discard(memory_id)
        for kw in memory.keywords:
            self._keyword_index[kw].discard(memory_id)
        for ctx in memory.context:
            self._context_index[ctx].discard(memory_id)
        for emo in memory.emotional_tags:
            self._emotional_index[emo].discard(memory_id)

        # 移除联想
        self._remove_associations(memory_id)

        del self._memories[memory_id]

    def _remove_associations(self, memory_id: str):
        """移除关联"""
        to_remove = [
            a.id for a in self._associations.values()
            if a.source_id == memory_id or a.target_id == memory_id
        ]
        for assoc_id in to_remove:
            del self._associations[assoc_id]

    # ==================== 联想创建 ====================

    def create_association(
        self,
        source_id: str,
        target_id: str,
        association_type: AssociationType,
        strength: float = 0.5,
        conditions: Optional[Dict[str, Any]] = None
    ) -> str:
        """
        创建联想

        Args:
            source_id: 源记忆ID
            target_id: 目标记忆ID
            association_type: 联想类型
            strength: 联想强度
            conditions: 触发条件

        Returns:
            联想ID
        """
        with self._lock:
            if source_id not in self._memories or target_id not in self._memories:
                raise ValueError("Memory not found")

            assoc_id = f"assoc_{self._association_counter}"
            self._association_counter += 1

            association = Association(
                id=assoc_id,
                source_id=source_id,
                target_id=target_id,
                association_type=association_type,
                strength=strength,
                conditions=conditions or {}
            )

            self._associations[assoc_id] = association

            # 更新记忆的联想
            self._memories[source_id].associations[target_id] = strength
            self._memories[target_id].associations[source_id] = strength

            self._statistics["total_associations"] += 1

            return assoc_id

    def auto_link_memories(
        self,
        memory_id: str,
        threshold: float = 0.3
    ) -> List[str]:
        """
        自动链接相关记忆

        Args:
            memory_id: 记忆ID
            threshold: 相似度阈值

        Returns:
            创建的联想ID列表
        """
        with self._lock:
            if memory_id not in self._memories:
                return []

            memory = self._memories[memory_id]
            assoc_ids = []

            # 语义相似
            semantic_matches = self._find_semantic_matches(memory, threshold)
            for match_id, similarity in semantic_matches:
                assoc_id = self.create_association(
                    memory_id, match_id, AssociationType.SEMANTIC, similarity
                )
                assoc_ids.append(assoc_id)

            # 情感相似
            if self.enable_emotional:
                emotional_matches = self._find_emotional_matches(memory, threshold)
                for match_id, similarity in emotional_matches:
                    if match_id not in [m[0] for m in semantic_matches]:
                        assoc_id = self.create_association(
                            memory_id, match_id, AssociationType.EMOTIONAL, similarity
                        )
                        assoc_ids.append(assoc_id)

            # 情境相似
            if self.enable_context:
                context_matches = self._find_context_matches(memory, threshold)
                for match_id, similarity in context_matches:
                    if match_id not in [m[0] for m in semantic_matches]:
                        assoc_id = self.create_association(
                            memory_id, match_id, AssociationType.EPISODIC, similarity
                        )
                        assoc_ids.append(assoc_id)

            return assoc_ids

    def _find_semantic_matches(
        self,
        memory: MemoryNode,
        threshold: float
    ) -> List[Tuple[str, float]]:
        """找语义匹配"""
        matches = []

        # 概念匹配
        if memory.concept in self._concept_index:
            for other_id in self._concept_index[memory.concept]:
                if other_id != memory.id:
                    matches.append((other_id, 1.0))

        # 关键词匹配
        for kw in memory.keywords:
            if kw in self._keyword_index:
                for other_id in self._keyword_index[kw]:
                    if other_id != memory.id and other_id not in [m[0] for m in matches]:
                        # 计算Jaccard相似度
                        other = self._memories[other_id]
                        intersection = len(memory.keywords & other.keywords)
                        union = len(memory.keywords | other.keywords)
                        similarity = intersection / union if union > 0 else 0
                        if similarity >= threshold:
                            matches.append((other_id, similarity))

        return matches[:10]

    def _find_emotional_matches(
        self,
        memory: MemoryNode,
        threshold: float
    ) -> List[Tuple[str, float]]:
        """找情感匹配"""
        matches = []

        for emo, strength in memory.emotional_tags.items():
            if emo in self._emotional_index:
                for other_id in self._emotional_index[emo]:
                    if other_id != memory.id:
                        other_strength = self._memories[other_id].emotional_tags.get(emo, 0)
                        # 情感强度相似度
                        similarity = 1 - abs(strength - other_strength)
                        if similarity >= threshold:
                            matches.append((other_id, similarity))

        return matches[:10]

    def _find_context_matches(
        self,
        memory: MemoryNode,
        threshold: float
    ) -> List[Tuple[str, float]]:
        """找情境匹配"""
        matches = []

        for ctx in memory.context:
            if ctx in self._context_index:
                for other_id in self._context_index[ctx]:
                    if other_id != memory.id:
                        other = self._memories[other_id]
                        intersection = len(memory.context & other.context)
                        union = len(memory.context | other.context)
                        similarity = intersection / union if union > 0 else 0
                        if similarity >= threshold:
                            matches.append((other_id, similarity))

        return matches[:10]

    # ==================== 自由联想 ====================

    def free_associate(
        self,
        seed_memory_id: str,
        depth: int = 2,
        max_results: int = 20
    ) -> List[RetrievalResult]:
        """
        自由联想

        Args:
            seed_memory_id: 种子记忆ID
            depth: 联想深度
            max_results: 最大结果数

        Returns:
            联想结果
        """
        with self._lock:
            if seed_memory_id not in self._memories:
                return []

            # 激活种子记忆
            self._activate_memory(seed_memory_id, 1.0, "free_association")

            # 扩散激活
            results = []
            current_level = {seed_memory_id}
            visited = {seed_memory_id}

            for d in range(depth):
                next_level = set()

                for memory_id in current_level:
                    # 获取联想记忆
                    associated = self._get_associated_memories(memory_id)

                    for assoc_id, assoc_strength in associated:
                        if assoc_id not in visited:
                            # 计算激活水平
                            source_memory = self._memories[memory_id]
                            activation = source_memory.activation_level * assoc_strength

                            # 激活目标
                            self._activate_memory(assoc_id, activation, f"association_from_{memory_id}")

                            # 添加结果
                            if assoc_id in self._memories:
                                memory = self._memories[assoc_id]
                                result = RetrievalResult(
                                    memory=memory,
                                    activation_level=memory.activation_level,
                                    relevance_score=activation,
                                    match_type="semantic"
                                )
                                results.append(result)

                            next_level.add(assoc_id)
                            visited.add(assoc_id)

                current_level = next_level

            # 排序并限制结果
            results.sort(key=lambda r: r.relevance_score, reverse=True)
            return results[:max_results]

    def _activate_memory(
        self,
        memory_id: str,
        level: float,
        trigger: str
    ):
        """激活记忆"""
        if memory_id not in self._memories:
            return

        memory = self._memories[memory_id]

        # 更新激活水平
        memory.activation_level = max(memory.activation_level, level)

        # 更新状态
        if level >= 0.8:
            memory.state = ActivationState.WORKING
        elif level >= 0.5:
            memory.state = ActivationState.ACTIVE
        elif level >= self.PRIMING_THRESHOLD:
            memory.state = ActivationState.PRIMED
            memory.priming_count += 1

        # 记录激活轨迹
        trace = ActivationTrace(
            id=f"trace_{len(self._activation_history)}",
            memory_id=memory_id,
            timestamp=datetime.now(),
            activation_level=level,
            trigger=trigger
        )
        self._current_activation_trace.append(trace)
        self._activation_history.append(trace)

    def _get_associated_memories(
        self,
        memory_id: str
    ) -> List[Tuple[str, float]]:
        """获取关联记忆"""
        memory = self._memories[memory_id]
        associations = []

        # 从联想边获取
        for assoc in self._associations.values():
            if assoc.source_id == memory_id:
                associations.append((assoc.target_id, assoc.strength))
            elif assoc.target_id == memory_id:
                associations.append((assoc.source_id, assoc.strength))

        # 从记忆节点的关联获取
        for assoc_id, strength in memory.associations.items():
            associations.append((assoc_id, strength))

        return associations

    # ==================== 情境依赖检索 ====================

    def context_dependent_retrieval(
        self,
        context: Set[str],
        emotional_state: Optional[Dict[str, float]] = None,
        top_k: int = 10
    ) -> List[RetrievalResult]:
        """
        情境依赖检索

        Args:
            context: 当前情境
            emotional_state: 当前情感状态
            top_k: 返回数量

        Returns:
            检索结果
        """
        with self._lock:
            results = []

            # 计算每个记忆的情境匹配度
            for memory in self._memories.values():
                score = 0.0
                match_types = []

                # 情境匹配
                if context:
                    context_overlap = len(memory.context & context)
                    if context_overlap > 0:
                        context_score = context_overlap / max(len(memory.context), 1)
                        score += context_score * 0.5
                        match_types.append("context")

                # 情感匹配
                if emotional_state and self.enable_emotional:
                    emo_score = self._compute_emotional_similarity(
                        memory.emotional_tags, emotional_state
                    )
                    if emo_score > 0:
                        score += emo_score * 0.5
                        match_types.append("emotional")

                # 时间接近性（最近的情境更容易被激活）
                time_decay = self._compute_time_decay(memory.last_accessed)
                score *= time_decay

                if score > self.RETRIEVAL_THRESHOLD:
                    result = RetrievalResult(
                        memory=memory,
                        activation_level=score,
                        relevance_score=score,
                        match_type="/".join(match_types) if match_types else "context"
                    )
                    results.append(result)

            # 排序并限制
            results.sort(key=lambda r: r.relevance_score, reverse=True)

            # 激活前几名
            for result in results[:top_k]:
                self._activate_memory(
                    result.memory.id,
                    result.relevance_score,
                    "context_retrieval"
                )

            return results[:top_k]

    def _compute_emotional_similarity(
        self,
        tags1: Dict[str, float],
        tags2: Dict[str, float]
    ) -> float:
        """计算情感相似度"""
        if not tags1 or not tags2:
            return 0.0

        common = set(tags1.keys()) & set(tags2.keys())
        if not common:
            return 0.0

        similarities = []
        for emo in common:
            sim = 1 - abs(tags1[emo] - tags2[emo])
            similarities.append(sim)

        return np.mean(similarities)

    def _compute_time_decay(self, timestamp: datetime) -> float:
        """计算时间衰减"""
        age_hours = (datetime.now() - timestamp).total_seconds() / 3600

        # 指数衰减
        decay = np.exp(-0.1 * age_hours)
        return max(0.1, decay)

    # ==================== 记忆竞争 ====================

    def competitive_retrieval(
        self,
        cues: List[str],
        competition_factor: float = 0.5
    ) -> List[RetrievalResult]:
        """
        竞争检索

        Args:
            cues: 检索线索
            competition_factor: 竞争因子

        Returns:
            竞争后的结果
        """
        with self._lock:
            # 第一步：收集所有候选
            candidates: Dict[str, float] = defaultdict(float)

            for cue in cues:
                # 关键词匹配
                if cue in self._keyword_index:
                    for memory_id in self._keyword_index[cue]:
                        candidates[memory_id] += 1.0

                # 概念匹配
                if cue in self._concept_index:
                    for memory_id in self._concept_index[cue]:
                        candidates[memory_id] += 1.5

            # 第二步：计算初始分数
            results = []
            for memory_id, base_score in candidates.items():
                memory = self._memories[memory_id]

                # 激活水平加成
                activation_boost = memory.activation_level * competition_factor

                # 访问频率加成
                access_boost = np.log1p(memory.access_count) * 0.1

                total_score = (base_score + activation_boost + access_boost) * memory.confidence

                result = RetrievalResult(
                    memory=memory,
                    activation_level=memory.activation_level,
                    relevance_score=total_score,
                    match_type="keyword"
                )
                results.append(result)

            # 第三步：竞争抑制
            results.sort(key=lambda r: r.relevance_score, reverse=True)

            # 抑制效应：排名靠后的被抑制
            for i, result in enumerate(results):
                inhibition = competition_factor * (i / len(results))
                result.relevance_score *= (1 - inhibition)

            # 重新排序
            results.sort(key=lambda r: r.relevance_score, reverse=True)

            # 激活前几名
            for result in results[:5]:
                self._activate_memory(
                    result.memory.id,
                    result.relevance_score,
                    "competitive_retrieval"
                )
                result.memory.access_count += 1
                result.memory.last_accessed = datetime.now()

            self._statistics["total_retrievals"] += len(results)

            return results[:10]

    # ==================== 虚假记忆检测 ====================

    def _check_consistency(self, memory_id: str):
        """检查记忆一致性"""
        if memory_id not in self._memories:
            return

        memory = self._memories[memory_id]

        # 检查冲突的情感标签
        conflicting_emotions = self._detect_emotional_conflicts(memory)
        if conflicting_emotions:
            self._report_inconsistency(
                [memory_id],
                "emotional_conflict",
                0.7,
                f"情感标签冲突: {conflicting_emotions}"
            )

        # 检查概念一致性
        concept_conflicts = self._detect_concept_conflicts(memory)
        if concept_conflicts:
            self._report_inconsistency(
                [memory_id] + concept_conflicts,
                "concept_conflict",
                0.8,
                f"与已有记忆概念冲突"
            )

    def _detect_emotional_conflicts(
        self,
        memory: MemoryNode
    ) -> List[str]:
        """检测情感冲突"""
        conflicts = []
        emotions = list(memory.emotional_tags.keys())

        # 定义互斥情感
        mutually_exclusive = [
            ({"happy", "joy"}, {"sad", "angry"}),
            ({"fear"}, {"confidence"}),
            ({"love", "hate"})
        ]

        for pos_set, neg_set in mutually_exclusive:
            if pos_set & set(emotions) and neg_set & set(emotions):
                conflicts.append(f"{pos_set} vs {neg_set}")

        return conflicts

    def _detect_concept_conflicts(
        self,
        memory: MemoryNode
    ) -> List[str]:
        """检测概念冲突"""
        conflicts = []

        # 检查与已有记忆的概念冲突
        for other in self._memories.values():
            if other.id == memory.id:
                continue

            # 相同概念但不同内容
            if other.concept == memory.concept:
                # 检查时间冲突（同一事件的不同版本）
                time_diff = abs(
                    (memory.created_at - other.created_at).total_seconds()
                )
                if time_diff < 3600:  # 1小时内
                    # 检查内容相似度
                    if self._content_similarity(memory.content, other.content) < 0.3:
                        conflicts.append(other.id)

        return conflicts[:3]

    def _content_similarity(self, content1: Any, content2: Any) -> float:
        """内容相似度"""
        # 简化：字符串比较
        if isinstance(content1, str) and isinstance(content2, str):
            # Jaccard相似度
            set1 = set(content1.split())
            set2 = set(content2.split())
            intersection = len(set1 & set2)
            union = len(set1 | set2)
            return intersection / union if union > 0 else 0
        return 0.5

    def _report_inconsistency(
        self,
        memory_ids: List[str],
        inconsistency_type: str,
        severity: float,
        details: str
    ):
        """报告不一致"""
        report = InconsistencyReport(
            id=f"inc_{len(self._inconsistencies)}",
            memory_ids=memory_ids,
            inconsistency_type=inconsistency_type,
            severity=severity,
            details=details,
            detected_at=datetime.now()
        )

        self._inconsistencies.append(report)
        self._statistics["inconsistencies_detected"] += 1

    def detect_false_memories(self) -> List[InconsistencyReport]:
        """检测虚假记忆"""
        false_memories = []

        # 查找不一致的报告
        for report in self._inconsistencies:
            if not report.resolved and report.severity > 0.6:
                false_memories.append(report)
                self._statistics["false_memories_flagged"] += 1

        return false_memories

    # ==================== 激活衰减 ====================

    def decay_activations(self):
        """衰减所有激活"""
        with self._lock:
            for memory in self._memories.values():
                # 衰减
                memory.activation_level *= self.ACTIVATION_DECAY

                # 更新状态
                if memory.activation_level < self.PRIMING_THRESHOLD:
                    memory.state = ActivationState.DORMANT
                elif memory.activation_level < 0.5:
                    memory.state = ActivationState.PRIMED
                elif memory.activation_level < 0.8:
                    memory.state = ActivationState.ACTIVE

            # 清空当前轨迹
            self._current_activation_trace = []

    # ==================== 统计和查询 ====================

    def get_statistics(self) -> Dict[str, Any]:
        """获取统计"""
        return {
            **self._statistics,
            "total_memories": len(self._memories),
            "total_associations": len(self._associations),
            "active_memories": sum(
                1 for m in self._memories.values()
                if m.state != ActivationState.DORMANT
            ),
            "inconsistencies": len(self._inconsistencies)
        }

    def retrieve_memory(self, memory_id: str) -> Optional[MemoryNode]:
        """检索记忆"""
        memory = self._memories.get(memory_id)
        if memory:
            memory.access_count += 1
            memory.last_accessed = datetime.now()
        return memory

    def __repr__(self) -> str:
        return f"AssociativeMemory(memories={len(self._memories)}, associations={len(self._associations)})"
