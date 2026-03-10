"""
情景-语义记忆桥梁
├── 记忆巩固: 情景 → 语义的知识抽取
├── 模式识别: 跨情景的共性提取
├── 预测编码: 基于记忆的未来状态预测
└── 记忆重构: 类似人类的记忆重塑机制
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


class ConsolidationStatus(Enum):
    """记忆巩固状态"""
    RAW = "raw"                    # 原始情景
    CONSOLIDATING = "consolidating"  # 巩固中
    CONSOLIDATED = "consolidated"    # 已巩固
    REACTIVATED = "reactivated"     # 重新激活
    DECAYED = "decayed"             # 已衰减


class PatternType(Enum):
    """模式类型"""
    SEQUENTIAL = "sequential"       # 序列模式
    CAUSAL = "causal"              # 因果模式
    TEMPORAL = "temporal"          # 时间模式
    SPATIAL = "spatial"            # 空间模式
    ASSOCIATIVE = "associative"     # 关联模式
    SEMANTIC = "semantic"          # 语义模式


@dataclass
class EpisodicMemory:
    """情景记忆单元"""
    id: str
    content: Any
    context: Dict[str, Any]
    timestamp: datetime
    duration: float = 0.0
    emotional_valence: float = 0.0  # 情感效价 (-1 to 1)
    importance: float = 1.0
    access_count: int = 0
    associations: Set[str] = field(default_factory=set)
    embedding: Optional[np.ndarray] = None
    metadata: Dict[str, Any] = field(default_factory=dict)

    def get_age_hours(self) -> float:
        """获取记忆年龄（小时）"""
        return (datetime.now() - self.timestamp).total_seconds() / 3600


@dataclass
class SemanticConcept:
    """语义概念"""
    id: str
    name: str
    definition: str
    attributes: Dict[str, Any] = field(default_factory=dict)
    instances: Set[str] = field(default_factory=set)  # 关联的情景ID
    generalizations: Set[str] = field(default_factory=set)  # 上位概念
    specializations: Set[str] = field(default_factory=set)  # 下位概念
    created_at: datetime = field(default_factory=datetime.now)
    updated_at: datetime = field(default_factory=datetime.now)
    confidence: float = 1.0

    def add_instance(self, episodic_id: str):
        """添加实例"""
        self.instances.add(episodic_id)
        self.updated_at = datetime.now()

    def generalize_to(self, concept_id: str):
        """建立上位关系"""
        self.generalizations.add(concept_id)
        self.updated_at = datetime.now()


@dataclass
class CrossPattern:
    """跨情景模式"""
    id: str
    pattern_type: PatternType
    episodes: Set[str]
    pattern_data: Dict[str, Any]
    frequency: int = 1
    first_seen: datetime = field(default_factory=datetime.now)
    last_seen: datetime = field(default_factory=datetime.now)
    confidence: float = 0.5
    predictive_power: float = 0.0  # 预测能力

    def update(self):
        """更新模式"""
        self.frequency += 1
        self.last_seen = datetime.now()
        self.confidence = min(1.0, self.frequency / 10)


@dataclass
class Prediction:
    """预测结果"""
    id: str
    pattern_id: str
    predicted_content: Any
    probability: float
    context: Dict[str, Any]
    timestamp: datetime = field(default_factory=datetime.now)
    verified: bool = False
    accuracy: Optional[float] = None


@dataclass
class MemoryFragment:
    """记忆碎片（用于重构）"""
    episodic_ids: List[str]
    semantic_constraints: Dict[str, Any]
    temporal_order: List[str]
    confidence: float = 0.5
    reconstructed_content: Optional[Any] = None


class EpisodicSemanticBridge:
    """
    情景-语义记忆桥梁

    实现人类记忆的整合与抽象过程:
    1. 记忆巩固: 从具体经验中抽取抽象知识
    2. 模式识别: 发现重复出现的规律
    3. 预测编码: 基于过去预测未来
    4. 记忆重构: 根据线索重建记忆
    """

    # 巩固参数
    CONSOLIDATION_THRESHOLD = 3  # 最小出现次数
    CONSOLIDATION_TIME_HOURS = 24  # 巩固所需时间
    PATTERN_MIN_FREQUENCY = 2  # 最小模式频率
    PREDICTION_HORIZON_HOURS = 48  # 预测范围

    def __init__(
        self,
        embedding_fn: Optional[Callable[[str], np.ndarray]] = None,
        similarity_threshold: float = 0.7,
        consolidation_interval: int = 100,
        max_patterns: int = 1000,
        max_concepts: int = 5000
    ):
        """
        初始化桥梁

        Args:
            embedding_fn: 文本嵌入函数
            similarity_threshold: 相似度阈值
            consolidation_interval: 巩固检查间隔
            max_patterns: 最大模式数
            max_concepts: 最大概念数
        """
        self.embedding_fn = embedding_fn or self._default_embedding
        self.similarity_threshold = similarity_threshold
        self.consolidation_interval = consolidation_interval
        self.max_patterns = max_patterns
        self.max_concepts = max_concepts

        # 存储
        self._episodic_store: Dict[str, EpisodicMemory] = {}
        self._semantic_concepts: Dict[str, SemanticConcept] = {}
        self._patterns: Dict[str, CrossPattern] = {}
        self._predictions: Dict[str, Prediction] = {}

        # 索引
        self._episodic_by_time: deque = deque(maxlen=10000)
        self._episodic_by_embedding: Dict[str, List[str]] = defaultdict(list)
        self._concept_by_attribute: Dict[str, Dict[Any, Set[str]]] = defaultdict(
            lambda: defaultdict(set)
        )

        # 统计
        self._consolidation_count = 0
        self._pattern_detection_count = 0
        self._prediction_count = 0
        self._reconstruction_count = 0

        # 队列
        self._consolidation_queue: deque = deque()
        self._operation_counter = 0

        # 线程安全
        self._lock = threading.RLock()

    def _default_embedding(self, text: str) -> np.ndarray:
        """默认嵌入函数（简单词袋）"""
        words = text.lower().split()
        vec = np.random.randn(64)
        for w in words:
            vec += hash(w) % 100 / 100
        return vec / (len(words) + 1)

    # ==================== 记忆巩固 ====================

    def store_episodic(
        self,
        content: Any,
        context: Optional[Dict[str, Any]] = None,
        emotional_valence: float = 0.0,
        importance: float = 1.0,
        episodic_id: Optional[str] = None
    ) -> str:
        """
        存储情景记忆

        Args:
            content: 记忆内容
            context: 上下文信息
            emotional_valence: 情感效价
            importance: 重要性
            episodic_id: ID（可选）

        Returns:
            episodic_id: 存储的记忆ID
        """
        with self._lock:
            if episodic_id is None:
                episodic_id = f"epi_{len(self._episodic_store)}_{int(time.time() * 1000)}"

            # 生成嵌入
            content_str = json.dumps(content) if not isinstance(content, str) else content
            embedding = self.embedding_fn(content_str)

            episodic = EpisodicMemory(
                id=episodic_id,
                content=content,
                context=context or {},
                timestamp=datetime.now(),
                emotional_valence=emotional_valence,
                importance=importance,
                embedding=embedding
            )

            self._episodic_store[episodic_id] = episodic
            self._episodic_by_time.append(episodic_id)

            # 加入巩固队列
            self._consolidation_queue.append(episodic_id)

            # 检查是否需要巩固
            self._operation_counter += 1
            if self._operation_counter % self.consolidation_interval == 0:
                self._check_consolidation()

            return episodic_id

    def consolidate_episodic_to_semantic(self, episodic_ids: List[str]) -> Optional[str]:
        """
        将情景记忆巩固为语义概念

        Args:
            episodic_ids: 要巩固的情景ID列表

        Returns:
            concept_id: 生成的语义概念ID
        """
        with self._lock:
            if len(episodic_ids) < self.CONSOLIDATION_THRESHOLD:
                return None

            # 获取所有情景
            episodes = [self._episodic_store[eid] for eid in episodic_ids
                       if eid in self._episodic_store]
            if not episodes:
                return None

            # 提取共性
            common_attrs = self._extract_common_attributes(episodes)
            if not common_attrs:
                return None

            # 生成概念ID
            concept_name = common_attrs.get("name", f"concept_{len(self._semantic_concepts)}")
            concept_id = f"sem_{hash(concept_name) % 100000}"

            # 检查是否已存在相似概念
            existing = self._find_similar_concept(common_attrs)
            if existing:
                # 更新现有概念
                for eid in episodic_ids:
                    existing.add_instance(eid)
                return existing.id

            # 创建新概念
            concept = SemanticConcept(
                id=concept_id,
                name=concept_name,
                definition=common_attrs.get("definition", ""),
                attributes=common_attrs,
                confidence=min(1.0, len(episodes) / 10)
            )

            # 绑定所有情景
            for eid in episodic_ids:
                concept.add_instance(eid)

            # 存储
            self._semantic_concepts[concept_id] = concept
            self._consolidation_count += 1

            # 更新索引
            for attr, value in common_attrs.items():
                self._concept_by_attribute[attr][value].add(concept_id)

            return concept_id

    def _extract_common_attributes(self, episodes: List[EpisodicMemory]) -> Dict[str, Any]:
        """从情景列表中提取共性属性"""
        if not episodes:
            return {}

        # 收集所有属性
        all_contexts = [e.context for e in episodes]
        all_contents = [e.content for e in episodes]

        # 找共同键
        common_keys = set(all_contexts[0].keys())
        for ctx in all_contexts[1:]:
            common_keys &= set(ctx.keys())

        # 提取共性
        common_attrs = {}
        for key in common_keys:
            values = [ctx[key] for ctx in all_contexts]
            if len(set(values)) == 1:
                common_attrs[key] = values[0]

        # 检查内容相似性
        if all_contents:
            first_content = all_contents[0]
            similar_count = 0
            for content in all_contents[1:]:
                if self._compute_similarity(first_content, content) > self.similarity_threshold:
                    similar_count += 1

            if similar_count > len(all_contents) / 2:
                common_attrs["name"] = str(first_content)[:50]
                common_attrs["definition"] = f"从{len(episodes)}个相似情景中提取"

        return common_attrs

    def _compute_similarity(self, content1: Any, content2: Any) -> float:
        """计算内容相似度"""
        if isinstance(content1, str) and isinstance(content2, str):
            emb1 = self.embedding_fn(content1)
            emb2 = self.embedding_fn(content2)
            return float(np.dot(emb1, emb2) / (np.linalg.norm(emb1) * np.linalg.norm(emb2) + 1e-8))
        return 0.0 if content1 != content2 else 1.0

    def _find_similar_concept(self, attributes: Dict[str, Any]) -> Optional[SemanticConcept]:
        """查找相似概念"""
        if "name" not in attributes:
            return None

        name = attributes["name"]
        for concept in self._semantic_concepts.values():
            if concept.name == name:
                return concept
            if self._compute_similarity(name, concept.name) > self.similarity_threshold:
                return concept

        return None

    def _check_consolidation(self):
        """检查并执行巩固"""
        # 按时间分组情景
        recent_window = datetime.now() - timedelta(hours=self.CONSOLIDATION_TIME_HOURS)
        recent_ids = [
            eid for eid in self._episodic_by_time
            if eid in self._episodic_store and
            self._episodic_store[eid].timestamp >= recent_window
        ]

        if len(recent_ids) < self.CONSOLIDATION_THRESHOLD:
            return

        # 聚类相似情景
        clusters = self._cluster_episodes(recent_ids)

        # 对高频簇进行巩固
        for cluster in clusters:
            if len(cluster) >= self.CONSOLIDATION_THRESHOLD:
                self.consolidate_episodic_to_semantic(cluster)

    def _cluster_episodes(self, episode_ids: List[str]) -> List[List[str]]:
        """聚类相似情景"""
        clusters = []
        assigned = set()

        for eid1 in episode_ids:
            if eid1 in assigned:
                continue

            epi1 = self._episodic_store.get(eid1)
            if not epi1:
                continue

            cluster = [eid1]
            assigned.add(eid1)

            for eid2 in episode_ids:
                if eid2 in assigned:
                    continue

                epi2 = self._episodic_store.get(eid2)
                if not epi2:
                    continue

                sim = self._compute_similarity(epi1.content, epi2.content)
                if sim > self.similarity_threshold:
                    cluster.append(eid2)
                    assigned.add(eid2)

            if len(cluster) >= 2:
                clusters.append(cluster)

        return clusters

    # ==================== 模式识别 ====================

    def detect_patterns(self, min_frequency: int = None) -> List[CrossPattern]:
        """
        检测跨情景模式

        Args:
            min_frequency: 最小频率

        Returns:
            检测到的模式列表
        """
        min_freq = min_frequency or self.PATTERN_MIN_FREQUENCY

        with self._lock:
            # 序列模式
            sequential = self._detect_sequential_patterns()

            # 因果模式
            causal = self._detect_causal_patterns()

            # 时间模式
            temporal = self._detect_temporal_patterns()

            # 合并并过滤
            all_patterns = sequential + causal + temporal
            filtered = [p for p in all_patterns if p.frequency >= min_freq]

            # 存储
            for pattern in filtered:
                if pattern.id not in self._patterns:
                    if len(self._patterns) < self.max_patterns:
                        self._patterns[pattern.id] = pattern

            self._pattern_detection_count += 1
            return filtered

    def _detect_sequential_patterns(self) -> List[CrossPattern]:
        """检测序列模式"""
        patterns = []
        sequence_window = 5

        recent = list(self._episodic_by_time)[-100:]  # 最近100条

        for i in range(len(recent) - sequence_window):
            seq = recent[i:i + sequence_window]
            pattern_key = "|".join(seq)

            # 检查是否已存在
            pattern_id = f"seq_{hash(pattern_key) % 100000}"
            existing = self._patterns.get(pattern_id)

            if existing:
                existing.update()
                patterns.append(existing)
            else:
                pattern = CrossPattern(
                    id=pattern_id,
                    pattern_type=PatternType.SEQUENTIAL,
                    episodes=set(seq),
                    pattern_data={"sequence": seq}
                )
                patterns.append(pattern)

        return patterns

    def _detect_causal_patterns(self) -> List[CrossPattern]:
        """检测因果模式"""
        patterns = []
        cause_effect_pairs: Dict[Tuple[str, str], List[str]] = defaultdict(list)

        for episodic in self._episodic_store.values():
            # 从上下文提取因果关系
            cause = episodic.context.get("cause")
            effect = episodic.context.get("effect")

            if cause and effect:
                key = (str(cause), str(effect))
                cause_effect_pairs[key].append(episodic.id)

        for (cause, effect), epi_ids in cause_effect_pairs.items():
            if len(epi_ids) >= self.PATTERN_MIN_FREQUENCY:
                pattern_id = f"causal_{hash(cause + effect) % 100000}"
                pattern = CrossPattern(
                    id=pattern_id,
                    pattern_type=PatternType.CAUSAL,
                    episodes=set(epi_ids),
                    pattern_data={"cause": cause, "effect": effect},
                    frequency=len(epi_ids)
                )
                patterns.append(pattern)

        return patterns

    def _detect_temporal_patterns(self) -> List[CrossPattern]:
        """检测时间模式"""
        patterns = []
        hour_buckets: Dict[int, List[str]] = defaultdict(list)

        for episodic in self._episodic_store.values():
            hour = episodic.timestamp.hour
            hour_buckets[hour].append(episodic.id)

        for hour, epi_ids in hour_buckets.items():
            if len(epi_ids) >= self.PATTERN_MIN_FREQUENCY:
                pattern_id = f"temporal_{hour}"
                pattern = CrossPattern(
                    id=pattern_id,
                    pattern_type=PatternType.TEMPORAL,
                    episodes=set(epi_ids),
                    pattern_data={"hour": hour, "recurrence": len(epi_ids)},
                    frequency=len(epi_ids)
                )
                patterns.append(pattern)

        return patterns

    # ==================== 预测编码 ====================

    def predict(
        self,
        context: Dict[str, Any],
        horizon_hours: float = None
    ) -> List[Prediction]:
        """
        基于记忆进行预测

        Args:
            context: 当前上下文
            horizon_hours: 预测时间范围

        Returns:
            预测结果列表
        """
        horizon = horizon_hours or self.PREDICTION_HORIZON_HOURS

        with self._lock:
            predictions = []

            # 匹配时间模式
            current_hour = datetime.now().hour
            temporal_patterns = [
                p for p in self._patterns.values()
                if p.pattern_type == PatternType.TEMPORAL
                and p.pattern_data.get("hour") == current_hour
            ]

            for pattern in temporal_patterns:
                pred = Prediction(
                    id=f"pred_{self._prediction_count}",
                    pattern_id=pattern.id,
                    predicted_content=pattern.pattern_data,
                    probability=pattern.confidence * pattern.predictive_power,
                    context=context
                )
                predictions.append(pred)
                self._predictions[pred.id] = pred
                self._prediction_count += 1

            # 匹配因果模式
            cause = context.get("current_state")
            if cause:
                causal_patterns = [
                    p for p in self._patterns.values()
                    if p.pattern_type == PatternType.CAUSAL
                    and p.pattern_data.get("cause") == cause
                ]

                for pattern in causal_patterns:
                    pred = Prediction(
                        id=f"pred_{self._prediction_count}",
                        pattern_id=pattern.id,
                        predicted_content=pattern.pattern_data.get("effect"),
                        probability=pattern.confidence,
                        context=context
                    )
                    predictions.append(pred)
                    self._predictions[pred.id] = pred
                    self._prediction_count += 1

            return predictions

    def verify_prediction(self, prediction_id: str, actual: Any) -> float:
        """
        验证预测准确性

        Args:
            prediction_id: 预测ID
            actual: 实际结果

        Returns:
            accuracy: 准确度 (0-1)
        """
        with self._lock:
            pred = self._predictions.get(prediction_id)
            if not pred:
                return 0.0

            # 计算准确度
            if pred.predicted_content == actual:
                accuracy = 1.0
            elif isinstance(pred.predicted_content, dict) and isinstance(actual, dict):
                matches = sum(1 for k, v in pred.predicted_content.items() if actual.get(k) == v)
                accuracy = matches / len(pred.predicted_content)
            else:
                accuracy = 0.0

            pred.verified = True
            pred.accuracy = accuracy

            # 更新模式预测能力
            pattern = self._patterns.get(pred.pattern_id)
            if pattern:
                old_power = pattern.predictive_power
                pattern.predictive_power = old_power * 0.9 + accuracy * 0.1

            return accuracy

    # ==================== 记忆重构 ====================

    def reconstruct(
        self,
        cues: Dict[str, Any],
        max_fragments: int = 5
    ) -> List[MemoryFragment]:
        """
        基于线索重构记忆

        Args:
            cues: 线索字典
            max_fragments: 最大碎片数

        Returns:
            重构的记忆碎片列表
        """
        with self._lock:
            fragments = []

            # 匹配相关情景
            matching_episodes = self._retrieve_by_cues(cues)

            if not matching_episodes:
                return []

            # 构建碎片
            for i in range(0, len(matching_episodes), max_fragments):
                chunk = matching_episodes[i:i + max_fragments]

                fragment = MemoryFragment(
                    episodic_ids=chunk,
                    semantic_constraints=cues,
                    temporal_order=sorted(chunk, key=lambda eid:
                        self._episodic_store[eid].timestamp if eid in self._episodic_store else datetime.min),
                    confidence=len(chunk) / 10
                )

                # 重构内容
                fragment.reconstructed_content = self._reconstruct_content(fragment)
                fragments.append(fragment)
                self._reconstruction_count += 1

            return fragments

    def _retrieve_by_cues(self, cues: Dict[str, Any]) -> List[str]:
        """根据线索检索情景"""
        scores: Dict[str, float] = {}

        for eid, episodic in self._episodic_store.items():
            score = 0.0

            # 上下文匹配
            for key, value in cues.items():
                if episodic.context.get(key) == value:
                    score += 1.0

            # 时间接近度
            age_hours = episodic.get_age_hours()
            if age_hours < 24:
                score += 1.0
            elif age_hours < 168:
                score += 0.5

            # 情感匹配
            if "emotional_valence" in cues:
                valence_diff = abs(episodic.emotional_valence - cues["emotional_valence"])
                score += max(0, 1 - valence_diff)

            if score > 0:
                scores[eid] = score

        # 排序返回
        return [eid for eid, _ in sorted(scores.items(), key=lambda x: x[1], reverse=True)]

    def _reconstruct_content(self, fragment: MemoryFragment) -> Any:
        """重构具体内容"""
        if not fragment.episodic_ids:
            return None

        # 合并内容
        contents = [
            self._episodic_store[eid].content
            for eid in fragment.episodic_ids
            if eid in self._episodic_store
        ]

        if not contents:
            return None

        # 返回最常见或最新的
        if len(contents) == 1:
            return contents[0]

        # 简单合并
        return {
            "type": "reconstructed",
            "episodes": len(contents),
            "content": contents[0],
            "confidence": fragment.confidence
        }

    # ==================== 查询接口 ====================

    def get_episodic(self, episodic_id: str) -> Optional[EpisodicMemory]:
        """获取情景记忆"""
        return self._episodic_store.get(episodic_id)

    def get_concept(self, concept_id: str) -> Optional[SemanticConcept]:
        """获取语义概念"""
        return self._semantic_concepts.get(concept_id)

    def get_pattern(self, pattern_id: str) -> Optional[CrossPattern]:
        """获取模式"""
        return self._patterns.get(pattern_id)

    def search_semantic(self, query: str, top_k: int = 5) -> List[Tuple[SemanticConcept, float]]:
        """语义搜索"""
        query_emb = self.embedding_fn(query)
        scores = []

        for concept in self._semantic_concepts.values():
            # 基于名称相似度
            name_emb = self.embedding_fn(concept.name)
            sim = float(np.dot(query_emb, name_emb) / (np.linalg.norm(query_emb) * np.linalg.norm(name_emb) + 1e-8))
            scores.append((concept, sim))

        scores.sort(key=lambda x: x[1], reverse=True)
        return scores[:top_k]

    def get_statistics(self) -> Dict[str, Any]:
        """获取统计信息"""
        with self._lock:
            return {
                "episodic_count": len(self._episodic_store),
                "semantic_concepts": len(self._semantic_concepts),
                "patterns": len(self._patterns),
                "predictions": len(self._predictions),
                "consolidations": self._consolidation_count,
                "pattern_detections": self._pattern_detection_count,
                "reconstructions": self._reconstruction_count,
                "consolidation_queue": len(self._consolidation_queue)
            }

    def __len__(self) -> int:
        return len(self._episodic_store)

    def __repr__(self) -> str:
        return f"EpisodicSemanticBridge(episodic={len(self._episodic_store)}, semantic={len(self._semantic_concepts)}, patterns={len(self._patterns)})"
