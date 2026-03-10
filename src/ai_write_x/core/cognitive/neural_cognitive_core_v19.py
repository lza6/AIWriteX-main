"""
AIWriteX V19 - Neural Cognitive Core
神经认知核心 V19 - 类人认知能力架构

架构组成:
1. 记忆网络三层架构
   ├── 工作记忆: 当前任务上下文 (注意力管理)
   ├── 情景记忆: 具体事件经验 (向量数据库)
   └── 语义记忆: 抽象知识概念 (知识图谱)

2. 推理引擎多模式
   ├── 演绎推理: 从一般到特殊
   ├── 归纳推理: 从特殊到一般
   ├── 溯因推理: 最佳解释推理
   ├── 类比推理: 基于相似性推理
   └── 反事实推理: "如果...会怎样"

3. 认知控制
   ├── 注意力机制: 选择性关注
   ├── 认知负荷: 任务复杂度管理
   └── 元认知: 对自身认知的监控
"""

import numpy as np
from typing import Dict, List, Optional, Any, Callable, Union, Tuple
from dataclasses import dataclass, field
from datetime import datetime, timedelta
from enum import Enum, auto
import hashlib
import json
from collections import deque


class MemoryType(Enum):
    """记忆类型"""
    WORKING = "working"      # 工作记忆
    EPISODIC = "episodic"    # 情景记忆
    SEMANTIC = "semantic"    # 语义记忆
    PROCEDURAL = "procedural"  # 程序记忆


class ReasoningType(Enum):
    """推理类型"""
    DEDUCTIVE = "deductive"      # 演绎推理
    INDUCTIVE = "inductive"      # 归纳推理
    ABDUCTIVE = "abductive"      # 溯因推理
    ANALOGICAL = "analogical"    # 类比推理
    COUNTERFACTUAL = "counterfactual"  # 反事实推理


@dataclass
class MemoryTrace:
    """记忆痕迹"""
    id: str
    content: Any
    memory_type: MemoryType
    timestamp: datetime
    importance: float = 1.0
    access_count: int = 0
    last_accessed: datetime = field(default_factory=datetime.now)
    associations: List[str] = field(default_factory=list)
    embedding: Optional[np.ndarray] = None
    metadata: Dict[str, Any] = field(default_factory=dict)
    
    def calculate_strength(self) -> float:
        """计算记忆强度（基于时间衰减和访问频率）"""
        age_hours = (datetime.now() - self.timestamp).total_seconds() / 3600
        recency_factor = np.exp(-age_hours / 168)  # 一周衰减
        frequency_factor = np.log1p(self.access_count)
        return self.importance * recency_factor * (1 + 0.1 * frequency_factor)
    
    def access(self):
        """访问记忆，更新统计"""
        self.access_count += 1
        self.last_accessed = datetime.now()


@dataclass
class ReasoningStep:
    """推理步骤"""
    step_number: int
    reasoning_type: ReasoningType
    premise: str
    conclusion: str
    confidence: float
    supporting_evidence: List[str]
    timestamp: datetime = field(default_factory=datetime.now)


@dataclass
class ReasoningChain:
    """推理链"""
    id: str
    goal: str
    steps: List[ReasoningStep] = field(default_factory=list)
    final_conclusion: str = ""
    overall_confidence: float = 0.0
    created_at: datetime = field(default_factory=datetime.now)
    
    def add_step(self, step: ReasoningStep):
        """添加推理步骤"""
        self.steps.append(step)
        self._update_confidence()
    
    def _update_confidence(self):
        """更新整体置信度"""
        if not self.steps:
            self.overall_confidence = 0.0
            return
        
        confidences = [step.confidence for step in self.steps]
        self.overall_confidence = np.exp(np.mean(np.log(confidences)))


class WorkingMemory:
    """
    工作记忆 - 当前任务上下文管理
    
    特性:
    - 容量限制（7±2 个组块）
    - 注意力机制
    - 临时信息存储
    """
    
    def __init__(self, capacity: int = 7):
        self.capacity = capacity
        self.focused_items: deque = deque(maxlen=capacity)
        self.attention_weights: Dict[str, float] = {}
        self.context_buffer: Dict[str, Any] = {}
        
    def focus(self, item_id: str, content: Any, importance: float = 1.0) -> bool:
        """将项目加入工作记忆焦点"""
        if len(self.focused_items) >= self.capacity:
            self._evict_least_important()
        
        self.focused_items.append({
            "id": item_id,
            "content": content,
            "importance": importance,
            "timestamp": datetime.now()
        })
        self.attention_weights[item_id] = importance
        return True
    
    def _evict_least_important(self):
        """移除注意力权重最低的项目"""
        if not self.focused_items:
            return
        
        min_item = min(self.focused_items, key=lambda x: x["importance"])
        self.focused_items.remove(min_item)
        self.attention_weights.pop(min_item["id"], None)
    
    def update_attention(self, item_id: str, delta: float):
        """更新注意力权重"""
        if item_id in self.attention_weights:
            self.attention_weights[item_id] = max(0.0, min(1.0, 
                self.attention_weights[item_id] + delta))
    
    def get_focused_content(self) -> List[Any]:
        """获取当前焦点内容"""
        return [item["content"] for item in self.focused_items]
    
    def clear(self):
        """清空工作记忆"""
        self.focused_items.clear()
        self.attention_weights.clear()
        self.context_buffer.clear()
    
    def set_context(self, key: str, value: Any):
        """设置上下文变量"""
        self.context_buffer[key] = value
    
    def get_context(self, key: str, default=None) -> Any:
        """获取上下文变量"""
        return self.context_buffer.get(key, default)


class EpisodicMemory:
    """
    情景记忆 - 具体事件经验存储
    
    使用向量数据库存储和检索
    """
    
    def __init__(self, embedding_dim: int = 384):
        self.embedding_dim = embedding_dim
        self.memories: Dict[str, MemoryTrace] = {}
        self.index: Dict[str, List[float]] = {}  # 简化的向量索引
        
    def store(self, content: Any, importance: float = 1.0, 
              metadata: Optional[Dict] = None) -> str:
        """存储新记忆"""
        memory_id = hashlib.md5(
            f"{content}:{datetime.now()}".encode()
        ).hexdigest()[:16]
        embedding = self._generate_embedding(content)
        
        memory = MemoryTrace(
            id=memory_id,
            content=content,
            memory_type=MemoryType.EPISODIC,
            timestamp=datetime.now(),
            importance=importance,
            embedding=embedding,
            metadata=metadata or {}
        )
        
        self.memories[memory_id] = memory
        self.index[memory_id] = embedding.tolist()
        
        return memory_id
    
    def _generate_embedding(self, content: Any) -> np.ndarray:
        """生成嵌入向量（简化版）"""
        content_str = str(content)
        # 使用字符编码生成固定长度向量
        vector = np.zeros(self.embedding_dim)
        for i, char in enumerate(content_str[:self.embedding_dim]):
            vector[i] = ord(char) / 255.0
        # 归一化
        norm = np.linalg.norm(vector)
        if norm > 0:
            vector = vector / norm
        return vector
    
    def retrieve_similar(self, query: Any, top_k: int = 5) -> List[MemoryTrace]:
        """检索相似记忆"""
        if not self.memories:
            return []
        
        query_embedding = self._generate_embedding(query)
        
        # 计算相似度
        similarities = []
        for memory_id, memory in self.memories.items():
            if memory.embedding is not None:
                similarity = np.dot(query_embedding, memory.embedding)
                memory_strength = memory.calculate_strength()
                combined_score = similarity * memory_strength
                similarities.append((memory_id, combined_score))
        
        # 排序并返回top_k
        similarities.sort(key=lambda x: x[1], reverse=True)
        
        results = []
        for memory_id, score in similarities[:top_k]:
            memory = self.memories[memory_id]
            memory.access()  # 更新访问统计
            results.append(memory)
        
        return results
    
    def retrieve_by_time(self, start: datetime, end: datetime) -> List[MemoryTrace]:
        """按时间范围检索"""
        return [
            m for m in self.memories.values()
            if start <= m.timestamp <= end
        ]
    
    def consolidate(self, threshold_days: int = 30):
        """记忆巩固 - 将旧记忆转移到长期存储"""
        cutoff = datetime.now() - timedelta(days=threshold_days)
        old_memories = [
            m for m in self.memories.values()
            if m.timestamp < cutoff and m.access_count < 2
        ]
        
        for memory in old_memories:
            # 降低重要性，但不删除
            memory.importance *= 0.5


class SemanticMemory:
    """
    语义记忆 - 抽象知识概念存储
    
    使用知识图谱存储概念和关系
    """
    
    def __init__(self):
        self.concepts: Dict[str, Dict[str, Any]] = {}
        self.relations: List[Dict[str, str]] = []
        self.category_hierarchy: Dict[str, List[str]] = {}
        
    def add_concept(self, concept: str, category: str, 
                   properties: Optional[Dict] = None):
        """添加概念"""
        self.concepts[concept] = {
            "category": category,
            "properties": properties or {},
            "added_at": datetime.now(),
            "relations": []
        }
        
        if category not in self.category_hierarchy:
            self.category_hierarchy[category] = []
        if concept not in self.category_hierarchy[category]:
            self.category_hierarchy[category].append(concept)
    
    def add_relation(self, concept1: str, relation: str, concept2: str):
        """添加概念间关系"""
        self.relations.append({
            "from": concept1,
            "relation": relation,
            "to": concept2
        })
        
        if concept1 in self.concepts:
            self.concepts[concept1]["relations"].append({
                "relation": relation,
                "to": concept2
            })
    
    def query_concept(self, concept: str) -> Optional[Dict]:
        """查询概念信息"""
        return self.concepts.get(concept)
    
    def find_related(self, concept: str, relation_type: Optional[str] = None) -> List[str]:
        """查找相关概念"""
        related = []
        for rel in self.relations:
            if rel["from"] == concept:
                if relation_type is None or rel["relation"] == relation_type:
                    related.append(rel["to"])
            elif rel["to"] == concept:
                if relation_type is None or rel["relation"] == relation_type:
                    related.append(rel["from"])
        return related
    
    def infer_category(self, concept: str) -> Optional[str]:
        """推断概念所属类别"""
        if concept in self.concepts:
            return self.concepts[concept]["category"]
        
        # 尝试通过关系推断
        for related in self.find_related(concept):
            if related in self.concepts:
                return self.concepts[related]["category"]
        
        return None


class ReasoningEngine:
    """
    推理引擎 - 多模式推理
    """
    
    def __init__(self, semantic_memory: SemanticMemory):
        self.semantic_memory = semantic_memory
        self.reasoning_history: List[ReasoningChain] = []
        
    def deductive_reasoning(self, general_rule: str, specific_case: str) -> ReasoningStep:
        """
        演绎推理: 从一般到特殊
        例: 所有人都会死，苏格拉底是人，所以苏格拉底会死
        """
        # 简化的演绎推理实现
        confidence = 0.9  # 演绎推理通常置信度较高
        
        conclusion = f"基于规则'{general_rule}'，案例'{specific_case}'得出相应结论"
        
        return ReasoningStep(
            step_number=1,
            reasoning_type=ReasoningType.DEDUCTIVE,
            premise=f"{general_rule} + {specific_case}",
            conclusion=conclusion,
            confidence=confidence,
            supporting_evidence=[general_rule, specific_case]
        )
    
    def inductive_reasoning(self, observations: List[str]) -> ReasoningStep:
        """
        归纳推理: 从特殊到一般
        例: 观察到的天鹅都是白色的，推断所有天鹅都是白色的
        """
        # 基于观察数量计算置信度
        confidence = min(0.95, 0.5 + len(observations) * 0.05)
        
        pattern = self._extract_pattern(observations)
        conclusion = f"基于{len(observations)}个观察，推断出一般规律: {pattern}"
        
        return ReasoningStep(
            step_number=1,
            reasoning_type=ReasoningType.INDUCTIVE,
            premise=f"观察: {', '.join(observations[:3])}...",
            conclusion=conclusion,
            confidence=confidence,
            supporting_evidence=observations
        )
    
    def _extract_pattern(self, observations: List[str]) -> str:
        """从观察中提取模式（简化实现）"""
        if not observations:
            return "无模式"
        
        # 寻找共同子串
        common = observations[0]
        for obs in observations[1:]:
            # 简化处理：返回第一个观察的前20个字符
            common = obs[:20] if len(obs) < len(common) else common[:20]
        
        return f"共同特征: {common}..."
    
    def abductive_reasoning(self, observation: str, possible_explanations: List[str]) -> ReasoningStep:
        """
        溯因推理: 寻找最佳解释
        例: 草地湿了，可能是下雨或洒水器，选择最可能的解释
        """
        # 选择最简单（最短）的解释作为最佳解释
        best_explanation = min(possible_explanations, key=len) if possible_explanations else "未知"
        confidence = 0.6  # 溯因推理置信度中等
        
        return ReasoningStep(
            step_number=1,
            reasoning_type=ReasoningType.ABDUCTIVE,
            premise=f"观察到: {observation}",
            conclusion=f"最佳解释: {best_explanation}",
            confidence=confidence,
            supporting_evidence=possible_explanations
        )
    
    def analogical_reasoning(self, source_domain: str, target_domain: str, 
                           mapping: Dict[str, str]) -> ReasoningStep:
        """
        类比推理: 基于相似性推理
        例: 水波像光波，所以光也可能有衍射现象
        """
        confidence = 0.7  # 类比推理置信度中等
        
        conclusion = f"基于{source_domain}和{target_domain}的相似性，通过类比得出推断"
        
        return ReasoningStep(
            step_number=1,
            reasoning_type=ReasoningType.ANALOGICAL,
            premise=f"源领域: {source_domain}, 目标领域: {target_domain}",
            conclusion=conclusion,
            confidence=confidence,
            supporting_evidence=[f"{k} -> {v}" for k, v in mapping.items()]
        )
    
    def counterfactual_reasoning(self, premise: str, hypothetical_change: str) -> ReasoningStep:
        """
        反事实推理: "如果...会怎样"
        例: 如果当初选择另一条路，现在会怎样
        """
        confidence = 0.4  # 反事实推理置信度较低
        
        conclusion = f"如果{hypothetical_change}，则{premise}可能会导致不同的结果"
        
        return ReasoningStep(
            step_number=1,
            reasoning_type=ReasoningType.COUNTERFACTUAL,
            premise=premise,
            conclusion=conclusion,
            confidence=confidence,
            supporting_evidence=[hypothetical_change]
        )
    
    def execute_reasoning_chain(self, goal: str, 
                               reasoning_types: List[ReasoningType]) -> ReasoningChain:
        """执行多步推理链"""
        chain = ReasoningChain(
            id=hashlib.md5(f"{goal}:{datetime.now()}".encode()).hexdigest()[:16],
            goal=goal
        )
        
        # 这里简化处理，实际应根据具体问题选择合适的推理步骤
        for i, rtype in enumerate(reasoning_types):
            if rtype == ReasoningType.DEDUCTIVE:
                step = self.deductive_reasoning("一般规则", "具体案例")
            elif rtype == ReasoningType.INDUCTIVE:
                step = self.inductive_reasoning(["观察1", "观察2", "观察3"])
            elif rtype == ReasoningType.ABDUCTIVE:
                step = self.abductive_reasoning("观察", ["解释1", "解释2"])
            elif rtype == ReasoningType.ANALOGICAL:
                step = self.analogical_reasoning("源域", "目标域", {"A": "B"})
            else:  # COUNTERFACTUAL
                step = self.counterfactual_reasoning("前提", "假设变化")
            
            step.step_number = i + 1
            chain.add_step(step)
        
        self.reasoning_history.append(chain)
        return chain


class NeuralCognitiveCoreV19:
    """
    神经认知核心 V19
    
    整合三层记忆系统和多模式推理引擎
    """
    
    def __init__(self):
        self.working_memory = WorkingMemory(capacity=7)
        self.episodic_memory = EpisodicMemory(embedding_dim=384)
        self.semantic_memory = SemanticMemory()
        self.reasoning_engine = ReasoningEngine(self.semantic_memory)
        
        self.active_goals: List[str] = []
        self.cognitive_load: float = 0.0
        self.max_cognitive_load: float = 1.0
        
    def perceive(self, input_data: Any, importance: float = 1.0) -> str:
        """
        感知输入
        
        1. 进入工作记忆
        2. 存入情景记忆
        3. 激活相关语义记忆
        """
        # 生成感知ID
        perception_id = hashlib.md5(
            f"{input_data}:{datetime.now()}".encode()
        ).hexdigest()[:16]
        
        # 进入工作记忆
        self.working_memory.focus(perception_id, input_data, importance)
        
        # 存入情景记忆
        memory_id = self.episodic_memory.store(
            content=input_data,
            importance=importance,
            metadata={"source": "perception", "perception_id": perception_id}
        )
        
        # 更新认知负荷
        self._update_cognitive_load(0.1)
        
        return memory_id
    
    def recall(self, query: Any, memory_type: MemoryType = MemoryType.EPISODIC) -> List[Any]:
        """回忆相关信息"""
        if memory_type == MemoryType.WORKING:
            return self.working_memory.get_focused_content()
        elif memory_type == MemoryType.EPISODIC:
            memories = self.episodic_memory.retrieve_similar(query)
            return [m.content for m in memories]
        elif memory_type == MemoryType.SEMANTIC:
            concept_info = self.semantic_memory.query_concept(str(query))
            return [concept_info] if concept_info else []
        
        return []
    
    def reason(self, goal: str, 
              reasoning_types: Optional[List[ReasoningType]] = None) -> ReasoningChain:
        """执行推理"""
        if reasoning_types is None:
            # 默认使用多种推理
            reasoning_types = [
                ReasoningType.DEDUCTIVE,
                ReasoningType.INDUCTIVE,
                ReasoningType.ABDUCTIVE
            ]
        
        # 检查认知负荷
        if self.cognitive_load > self.max_cognitive_load * 0.8:
            # 认知负荷过高，先进行一些清理
            self._reduce_cognitive_load()
        
        # 执行推理
        chain = self.reasoning_engine.execute_reasoning_chain(goal, reasoning_types)
        
        # 更新认知负荷
        self._update_cognitive_load(0.2 * len(reasoning_types))
        
        return chain
    
    def learn_concept(self, concept: str, category: str, 
                     properties: Optional[Dict] = None):
        """学习新概念"""
        self.semantic_memory.add_concept(concept, category, properties)
    
    def learn_relation(self, concept1: str, relation: str, concept2: str):
        """学习概念间关系"""
        self.semantic_memory.add_relation(concept1, relation, concept2)
    
    def _update_cognitive_load(self, delta: float):
        """更新认知负荷"""
        self.cognitive_load = max(0.0, min(self.max_cognitive_load, 
                                          self.cognitive_load + delta))
    
    def _reduce_cognitive_load(self):
        """降低认知负荷"""
        # 清理工作记忆
        if len(self.working_memory.focused_items) > self.working_memory.capacity // 2:
            self.working_memory._evict_least_important()
        
        # 记忆巩固
        self.episodic_memory.consolidate()
        
        self.cognitive_load *= 0.8
    
    def get_cognitive_state(self) -> Dict[str, Any]:
        """获取认知状态"""
        return {
            "working_memory_items": len(self.working_memory.focused_items),
            "episodic_memories": len(self.episodic_memory.memories),
            "semantic_concepts": len(self.semantic_memory.concepts),
            "cognitive_load": self.cognitive_load,
            "active_goals": self.active_goals,
            "reasoning_chains": len(self.reasoning_engine.reasoning_history)
        }
    
    def reset(self):
        """重置认知状态"""
        self.working_memory.clear()
        self.cognitive_load = 0.0
        self.active_goals.clear()


# 全局认知核心实例
cognitive_core_v19 = NeuralCognitiveCoreV19()
