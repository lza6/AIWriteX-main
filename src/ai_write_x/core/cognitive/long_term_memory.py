"""
AIWriteX V19.0 - Long Term Memory Module
长期记忆系统 - 持久化记忆存储与检索

功能:
1. 多类型记忆: 事实记忆、程序记忆、情景记忆、语义记忆
2. 记忆编码: 向量化表示，支持语义相似度搜索
3. 记忆巩固: 重要记忆强化，遗忘机制
4. 记忆检索: 上下文感知的多模态检索
"""

import json
import hashlib
from typing import Dict, List, Optional, Any, Tuple
from dataclasses import dataclass, field
from datetime import datetime, timedelta
from enum import Enum, auto
from uuid import uuid4
import numpy as np
from collections import defaultdict


class MemoryType(Enum):
    """记忆类型"""
    FACTUAL = "factual"             # 事实记忆: 客观知识
    PROCEDURAL = "procedural"       # 程序记忆: 操作技能
    EPISODIC = "episodic"           # 情景记忆: 特定事件
    SEMANTIC = "semantic"           # 语义记忆: 概念关系
    EMOTIONAL = "emotional"         # 情感记忆: 情感体验
    SPATIAL = "spatial"             # 空间记忆: 位置信息


class MemoryImportance(Enum):
    """记忆重要性级别"""
    CRITICAL = 1.0      # 关键信息，永不忘却
    HIGH = 0.8          # 重要信息，长期保留
    MEDIUM = 0.5        # 一般信息，定期清理
    LOW = 0.3           # 次要信息，快速遗忘
    TRIVIAL = 0.1       # 琐碎信息，立即遗忘


@dataclass
class MemoryEntry:
    """记忆条目"""
    id: str
    content: str
    memory_type: MemoryType
    importance: MemoryImportance
    timestamp: datetime
    access_count: int = 0
    last_accessed: Optional[datetime] = None
    associations: List[str] = field(default_factory=list)  # 关联记忆ID
    metadata: Dict[str, Any] = field(default_factory=dict)
    embedding: Optional[List[float]] = None  # 向量表示
    decay_rate: float = 0.01  # 遗忘速率
    
    def calculate_strength(self) -> float:
        """计算当前记忆强度 (0-1)"""
        # 基于重要性、访问次数、时间衰减计算
        base_strength = self.importance.value
        
        # 访问强化
        access_bonus = min(self.access_count * 0.05, 0.3)
        
        # 时间衰减
        time_decay = 0.0
        if self.last_accessed:
            days_since_access = (datetime.now() - self.last_accessed).days
            time_decay = days_since_access * self.decay_rate
        
        strength = base_strength + access_bonus - time_decay
        return max(0.0, min(1.0, strength))
    
    def access(self):
        """访问记忆，强化记忆"""
        self.access_count += 1
        self.last_accessed = datetime.now()
        # 降低遗忘速率
        self.decay_rate *= 0.9
    
    def to_dict(self) -> Dict:
        return {
            "id": self.id,
            "content": self.content[:100] + "..." if len(self.content) > 100 else self.content,
            "memory_type": self.memory_type.value,
            "importance": self.importance.name,
            "strength": self.calculate_strength(),
            "timestamp": self.timestamp.isoformat(),
            "access_count": self.access_count,
            "associations": self.associations
        }


class LongTermMemory:
    """
    长期记忆系统
    
    模拟人类长期记忆，支持编码、存储、巩固、检索
    """
    
    _instance = None
    
    def __new__(cls):
        if cls._instance is None:
            cls._instance = super().__new__(cls)
            cls._instance._initialized = False
        return cls._instance
    
    def __init__(self):
        if self._initialized:
            return
            
        self._initialized = True
        self.memories: Dict[str, MemoryEntry] = {}
        self.type_index: Dict[MemoryType, List[str]] = defaultdict(list)
        self.tag_index: Dict[str, List[str]] = defaultdict(list)
        self._consolidation_threshold = 0.3  # 记忆巩固阈值
        self._max_memories = 10000  # 最大记忆数
        
    def encode(
        self,
        content: str,
        memory_type: MemoryType,
        importance: MemoryImportance = MemoryImportance.MEDIUM,
        tags: List[str] = None,
        associations: List[str] = None,
        metadata: Dict = None
    ) -> MemoryEntry:
        """
        编码新记忆
        
        Args:
            content: 记忆内容
            memory_type: 记忆类型
            importance: 重要性级别
            tags: 标签列表
            associations: 关联记忆ID
            metadata: 元数据
            
        Returns:
            记忆条目
        """
        memory_id = str(uuid4())
        
        entry = MemoryEntry(
            id=memory_id,
            content=content,
            memory_type=memory_type,
            importance=importance,
            timestamp=datetime.now(),
            associations=associations or [],
            metadata=metadata or {}
        )
        
        # 生成简单embedding (实际应使用语言模型)
        entry.embedding = self._generate_embedding(content)
        
        # 存储记忆
        self.memories[memory_id] = entry
        self.type_index[memory_type].append(memory_id)
        
        # 索引标签
        if tags:
            for tag in tags:
                self.tag_index[tag].append(memory_id)
                if "tags" not in entry.metadata:
                    entry.metadata["tags"] = []
                entry.metadata["tags"].append(tag)
        
        # 检查是否需要清理
        self._consolidate_if_needed()
        
        return entry
    
    def _generate_embedding(self, content: str) -> List[float]:
        """生成内容的向量表示 (简化版)"""
        # 使用hash生成确定性向量
        hash_obj = hashlib.md5(content.encode())
        hash_int = int(hash_obj.hexdigest(), 16)
        np.random.seed(hash_int % 2**32)
        return np.random.randn(128).tolist()
    
    def retrieve(
        self,
        query: str,
        memory_type: Optional[MemoryType] = None,
        top_k: int = 5,
        min_strength: float = 0.3
    ) -> List[Tuple[MemoryEntry, float]]:
        """
        检索记忆
        
        Args:
            query: 查询内容
            memory_type: 指定记忆类型
            top_k: 返回结果数
            min_strength: 最小记忆强度
            
        Returns:
            [(记忆条目, 相似度分数), ...]
        """
        query_embedding = self._generate_embedding(query)
        
        # 筛选候选记忆
        candidates = []
        if memory_type:
            candidate_ids = self.type_index[memory_type]
        else:
            candidate_ids = list(self.memories.keys())
        
        for memory_id in candidate_ids:
            entry = self.memories[memory_id]
            strength = entry.calculate_strength()
            
            if strength < min_strength:
                continue
            
            # 计算相似度
            if entry.embedding:
                similarity = self._cosine_similarity(query_embedding, entry.embedding)
                # 综合考虑相似度和记忆强度
                score = similarity * strength
                candidates.append((entry, score))
        
        # 排序并返回Top-K
        candidates.sort(key=lambda x: x[1], reverse=True)
        
        # 强化被检索的记忆
        for entry, _ in candidates[:top_k]:
            entry.access()
        
        return candidates[:top_k]
    
    def _cosine_similarity(self, a: List[float], b: List[float]) -> float:
        """计算余弦相似度"""
        a_arr = np.array(a)
        b_arr = np.array(b)
        norm_a = np.linalg.norm(a_arr)
        norm_b = np.linalg.norm(b_arr)
        if norm_a == 0 or norm_b == 0:
            return 0.0
        return float(np.dot(a_arr, b_arr) / (norm_a * norm_b))
    
    def retrieve_by_association(self, memory_id: str) -> List[MemoryEntry]:
        """通过关联检索记忆"""
        if memory_id not in self.memories:
            return []
        
        entry = self.memories[memory_id]
        associated = []
        
        for assoc_id in entry.associations:
            if assoc_id in self.memories:
                associated.append(self.memories[assoc_id])
        
        return associated
    
    def retrieve_by_tag(self, tag: str) -> List[MemoryEntry]:
        """通过标签检索记忆"""
        memory_ids = self.tag_index.get(tag, [])
        return [self.memories[mid] for mid in memory_ids if mid in self.memories]
    
    def update(self, memory_id: str, content: str = None, importance: MemoryImportance = None):
        """更新记忆"""
        if memory_id not in self.memories:
            return
        
        entry = self.memories[memory_id]
        
        if content:
            entry.content = content
            entry.embedding = self._generate_embedding(content)
        
        if importance:
            entry.importance = importance
        
        entry.access()  # 更新访问记录
    
    def forget(self, memory_id: str):
        """主动遗忘记忆"""
        if memory_id not in self.memories:
            return
        
        entry = self.memories[memory_id]
        
        # 从索引中移除
        self.type_index[entry.memory_type].remove(memory_id)
        
        if "tags" in entry.metadata:
            for tag in entry.metadata["tags"]:
                if tag in self.tag_index and memory_id in self.tag_index[tag]:
                    self.tag_index[tag].remove(memory_id)
        
        # 移除关联
        for other_entry in self.memories.values():
            if memory_id in other_entry.associations:
                other_entry.associations.remove(memory_id)
        
        # 删除记忆
        del self.memories[memory_id]
    
    def _consolidate_if_needed(self):
        """记忆巩固: 清理弱记忆"""
        if len(self.memories) < self._max_memories * 0.9:
            return
        
        # 计算所有记忆强度
        strengths = [
            (mid, entry.calculate_strength())
            for mid, entry in self.memories.items()
        ]
        
        # 按强度排序
        strengths.sort(key=lambda x: x[1])
        
        # 删除最弱的记忆 (保留90%)
        to_remove = int(len(strengths) * 0.1)
        for mid, _ in strengths[:to_remove]:
            self.forget(mid)
    
    def consolidate_important(self):
        """强化重要记忆"""
        for entry in self.memories.values():
            if entry.importance == MemoryImportance.CRITICAL:
                entry.decay_rate *= 0.5  # 显著降低遗忘速率
            elif entry.importance == MemoryImportance.HIGH:
                entry.decay_rate *= 0.7
    
    def get_memory_stats(self) -> Dict:
        """获取记忆统计"""
        type_counts = {mt.value: len(mids) for mt, mids in self.type_index.items()}
        
        strengths = [entry.calculate_strength() for entry in self.memories.values()]
        
        return {
            "total_memories": len(self.memories),
            "by_type": type_counts,
            "avg_strength": np.mean(strengths) if strengths else 0,
            "total_tags": len(self.tag_index),
            "consolidation_threshold": self._consolidation_threshold
        }
    
    def export_memories(self, memory_type: Optional[MemoryType] = None) -> List[Dict]:
        """导出记忆"""
        if memory_type:
            memory_ids = self.type_index[memory_type]
        else:
            memory_ids = list(self.memories.keys())
        
        return [self.memories[mid].to_dict() for mid in memory_ids]
    
    def create_association(self, memory_id1: str, memory_id2: str):
        """创建记忆关联"""
        if memory_id1 in self.memories and memory_id2 in self.memories:
            if memory_id2 not in self.memories[memory_id1].associations:
                self.memories[memory_id1].associations.append(memory_id2)
            if memory_id1 not in self.memories[memory_id2].associations:
                self.memories[memory_id2].associations.append(memory_id1)


# 全局长期记忆实例
ltm = LongTermMemory()


def get_long_term_memory() -> LongTermMemory:
    """获取长期记忆实例"""
    return ltm
