"""
神经符号融合推理
├── 神经感知: 基于深度学习的模式识别
├── 符号推理: 逻辑规则和知识图谱
├── 神经→符号: 从感知到概念的转换
├── 符号→神经: 将逻辑约束注入神经网络
└── 混合推理链: 灵活组合两种范式
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
import random
import re


class ReasoningParadigm(Enum):
    """推理范式"""
    NEURAL = "neural"           # 神经推理
    SYMBOLIC = "symbolic"       # 符号推理
    HYBRID = "hybrid"           # 混合推理


class ConceptLevel(Enum):
    """概念层次"""
    PERCEPTUAL = "perceptual"   # 感知层（原始特征）
    CONCEPTUAL = "conceptual"  # 概念层（抽象概念）
    RELATIONAL = "relational"   # 关系层（实体关系）
    CAUSAL = "causal"          # 因果层（因果推断）


class LogicalOperator(Enum):
    """逻辑运算符"""
    AND = "and"
    OR = "or"
    NOT = "not"
    IMPLIES = "implies"
    EQUIV = "equivalent"


@dataclass
class NeuralPattern:
    """神经模式"""
    id: str
    features: np.ndarray
    embedding: np.ndarray
    confidence: float
    source_modality: str  # "text" / "image" / "audio"
    timestamp: datetime = field(default_factory=datetime.now)
    metadata: Dict[str, Any] = field(default_factory=dict)


@dataclass
class SymbolicConcept:
    """符号概念"""
    id: str
    name: str
    description: str
    level: ConceptLevel
    attributes: Dict[str, Any] = field(default_factory=dict)
    relations: Dict[str, List[str]] = field(default_factory=lambda: defaultdict(list))
    confidence: float = 1.0
    evidence: List[str] = field(default_factory=list)


@dataclass
class LogicalRule:
    """逻辑规则"""
    id: str
    name: str
    antecedent: str  # 前件 (IF)
    consequent: str  # 后件 (THEN)
    operator: LogicalOperator
    confidence: float
    conditions: Dict[str, Any] = field(default_factory=dict)
    examples: List[Tuple[Any, Any]] = field(default_factory=list)


@dataclass
class NeuralToSymbolicMapping:
    """神经到符号映射"""
    id: str
    neural_pattern_id: str
    concept_id: str
    mapping_type: str  # "extraction" / "classification" / "clustering"
    confidence: float
    transformation: str = ""  # 转换描述


@dataclass
class SymbolicToNeuralConstraint:
    """符号到神经约束"""
    id: str
    rule_id: str
    constraint_type: str  # "regularization" / "attention" / "output"
    target_layer: str
    weight: float
    description: str


@dataclass
class HybridReasoningChain:
    """混合推理链"""
    id: str
    steps: List[Dict[str, Any]]  # [{"paradigm": "neural"/"symbolic", "operation": "...", "input": ..., "output": ...}]
    input_data: Any
    output: Any
    confidence: float
    explanation: str
    timestamp: datetime = field(default_factory=datetime.now)


@dataclass
class KnowledgeGraph:
    """知识图谱"""
    entities: Dict[str, SymbolicConcept] = field(default_factory=dict)
    relations: Dict[str, Tuple[str, str, float]] = field(default_factory=dict)  # (subject, predicate, object)
    rules: Dict[str, LogicalRule] = field(default_factory=dict)


class NeuroSymbolicEngine:
    """
    神经符号融合推理引擎

    实现神经与符号推理的融合:
    1. 神经感知: 深度学习模式识别
    2. 符号推理: 逻辑规则和知识图谱
    3. 神经→符号: 感知到概念的转换
    4. 符号→神经: 逻辑约束注入
    5. 混合推理: 灵活组合两种范式
    """

    # 参数
    DEFAULT_EMBEDDING_DIM = 256
    MIN_CONFIDENCE_THRESHOLD = 0.5
    MAX_CHAIN_LENGTH = 10

    def __init__(
        self,
        embedding_dim: int = 256,
        enable_neural: bool = True,
        enable_symbolic: bool = True,
        enable_hybrid: bool = True
    ):
        """
        初始化神经符号引擎

        Args:
            embedding_dim: 嵌入维度
            enable_neural: 启用神经推理
            enable_symbolic: 启用符号推理
            enable_hybrid: 启用混合推理
        """
        self.embedding_dim = embedding_dim
        self.enable_neural = enable_neural
        self.enable_symbolic = enable_symbolic
        self.enable_hybrid = enable_hybrid

        # 神经组件
        self._neural_patterns: Dict[str, NeuralPattern] = {}
        self._pattern_counter = 0

        # 符号组件
        self._concepts: Dict[str, SymbolicConcept] = {}
        self._rules: Dict[str, LogicalRule] = {}
        self._knowledge_graph = KnowledgeGraph()
        self._concept_counter = 0
        self._rule_counter = 0

        # 映射组件
        self._neural_to_symbolic: Dict[str, NeuralToSymbolicMapping] = {}
        self._symbolic_to_neural: Dict[str, SymbolicToNeuralConstraint] = {}
        self._mapping_counter = 0

        # 推理历史
        self._reasoning_history: deque = deque(maxlen=500)

        # 线程安全
        self._lock = threading.RLock()

    # ==================== 神经感知 ====================

    def register_neural_pattern(
        self,
        features: np.ndarray,
        source_modality: str,
        confidence: float = 0.8,
        metadata: Optional[Dict[str, Any]] = None
    ) -> NeuralPattern:
        """
        注册神经模式

        Args:
            features: 原始特征向量
            source_modality: 来源模态
            confidence: 置信度
            metadata: 元数据

        Returns:
            注册的神经模式
        """
        with self._lock:
            pattern_id = f"pattern_{self._pattern_counter}"
            self._pattern_counter += 1

            # 生成嵌入
            embedding = self._generate_embedding(features)

            pattern = NeuralPattern(
                id=pattern_id,
                features=features,
                embedding=embedding,
                confidence=confidence,
                source_modality=source_modality,
                metadata=metadata or {}
            )

            self._neural_patterns[pattern_id] = pattern
            return pattern

    def _generate_embedding(self, features: np.ndarray) -> np.ndarray:
        """生成嵌入向量"""
        # 简化实现：归一化特征
        if len(features) == 0:
            return np.zeros(self.embedding_dim)

        # 调整维度
        if len(features) < self.embedding_dim:
            embedding = np.pad(features, (0, self.embedding_dim - len(features)))
        else:
            embedding = features[:self.embedding_dim]

        # 归一化
        norm = np.linalg.norm(embedding)
        if norm > 0:
            embedding = embedding / norm

        return embedding

    def recognize_pattern(
        self,
        features: np.ndarray,
        source_modality: str = "text"
    ) -> List[Tuple[NeuralPattern, float]]:
        """
        模式识别

        Args:
            features: 输入特征
            source_modality: 来源模态

        Returns:
            相似模式列表 (模式, 相似度)
        """
        query_embedding = self._generate_embedding(features)

        similarities = []
        for pattern in self._neural_patterns.values():
            if pattern.source_modality == source_modality:
                sim = np.dot(query_embedding, pattern.embedding)
                similarities.append((pattern, float(sim)))

        # 按相似度排序
        similarities.sort(key=lambda x: x[1], reverse=True)

        return similarities[:5]

    # ==================== 符号推理 ====================

    def add_concept(
        self,
        name: str,
        description: str,
        level: ConceptLevel = ConceptLevel.CONCEPTUAL,
        attributes: Optional[Dict[str, Any]] = None,
        confidence: float = 1.0
    ) -> SymbolicConcept:
        """
        添加概念

        Args:
            name: 概念名称
            description: 概念描述
            level: 概念层次
            attributes: 属性
            confidence: 置信度

        Returns:
            创建的概念
        """
        with self._lock:
            concept_id = f"concept_{self._concept_counter}"
            self._concept_counter += 1

            concept = SymbolicConcept(
                id=concept_id,
                name=name,
                description=description,
                level=level,
                attributes=attributes or {},
                confidence=confidence
            )

            self._concepts[concept_id] = concept
            self._knowledge_graph.entities[concept_id] = concept

            return concept

    def add_relation(
        self,
        subject: str,
        predicate: str,
        object: str,
        confidence: float = 0.8
    ):
        """
        添加关系

        Args:
            subject: 主语
            predicate: 谓词
            object: 宾语
            confidence: 置信度
        """
        with self._lock:
            relation_id = f"rel_{subject}_{predicate}_{object}"
            self._knowledge_graph.relations[relation_id] = (subject, predicate, object)

            # 更新概念的关联
            if subject in self._concepts:
                self._concepts[subject].relations[predicate].append(object)

    def add_logical_rule(
        self,
        name: str,
        antecedent: str,
        consequent: str,
        operator: LogicalOperator = LogicalOperator.IMPLIES,
        confidence: float = 0.9,
        conditions: Optional[Dict[str, Any]] = None
    ) -> LogicalRule:
        """
        添加逻辑规则

        Args:
            name: 规则名称
            antecedent: 前件 (IF)
            consequent: 后件 (THEN)
            operator: 逻辑运算符
            confidence: 置信度
            conditions: 条件

        Returns:
            创建的规则
        """
        with self._lock:
            rule_id = f"rule_{self._rule_counter}"
            self._rule_counter += 1

            rule = LogicalRule(
                id=rule_id,
                name=name,
                antecedent=antecedent,
                consequent=consequent,
                operator=operator,
                confidence=confidence,
                conditions=conditions or {}
            )

            self._rules[rule_id] = rule
            self._knowledge_graph.rules[rule_id] = rule

            return rule

    def symbolic_reasoning(
        self,
        query: str,
        context: Optional[Dict[str, Any]] = None
    ) -> Dict[str, Any]:
        """
        符号推理

        Args:
            query: 查询
            context: 上下文

        Returns:
            推理结果
        """
        with self._lock:
            context = context or {}

            # 1. 解析查询
            entities = self._extract_entities(query)

            # 2. 应用规则
            conclusions = []
            for rule in self._rules.values():
                if self._check_antecedent(rule.antecedent, entities, context):
                    conclusion = self._apply_rule(rule, entities, context)
                    conclusions.append({
                        "rule": rule.name,
                        "conclusion": conclusion,
                        "confidence": rule.confidence
                    })

            # 3. 查询关系
            relations = self._query_relations(entities)

            return {
                "query": query,
                "entities": entities,
                "conclusions": conclusions,
                "relations": relations,
                "reasoning_type": "symbolic"
            }

    def _extract_entities(self, text: str) -> Set[str]:
        """提取实体"""
        # 简化：提取概念名称
        entities = set()
        for concept in self._concepts.values():
            if concept.name in text:
                entities.add(concept.name)
        return entities

    def _check_antecedent(
        self,
        antecedent: str,
        entities: Set[str],
        context: Dict
    ) -> bool:
        """检查前件是否满足"""
        # 简化实现
        return any(entity in antecedent for entity in entities)

    def _apply_rule(
        self,
        rule: LogicalRule,
        entities: Set[str],
        context: Dict
    ) -> str:
        """应用规则"""
        # 替换占位符
        consequent = rule.consequent
        for entity in entities:
            consequent = consequent.replace("?", entity)
        return consequent

    def _query_relations(self, entities: Set[str]) -> List[Dict[str, str]]:
        """查询关系"""
        relations = []

        for rel_id, (subject, predicate, obj) in self._knowledge_graph.relations.items():
            if subject in entities or obj in entities:
                relations.append({
                    "subject": subject,
                    "predicate": predicate,
                    "object": obj
                })

        return relations

    # ==================== 神经→符号 ====================

    def neural_to_symbolic(
        self,
        pattern_id: str,
        target_concept_level: ConceptLevel = ConceptLevel.CONCEPTUAL
    ) -> NeuralToSymbolicMapping:
        """
        神经到符号转换

        Args:
            pattern_id: 神经模式ID
            target_concept_level: 目标概念层次

        Returns:
            映射结果
        """
        with self._lock:
            if pattern_id not in self._neural_patterns:
                raise ValueError(f"Pattern {pattern_id} not found")

            pattern = self._neural_patterns[pattern_id]

            # 找到最匹配的概念
            best_concept = None
            best_confidence = 0.0

            for concept in self._concepts.values():
                if concept.level == target_concept_level:
                    # 计算相似度
                    concept_embedding = self._get_concept_embedding(concept)
                    similarity = np.dot(pattern.embedding, concept_embedding)

                    if similarity > best_confidence:
                        best_confidence = similarity
                        best_concept = concept

            if best_concept is None:
                # 创建新概念
                best_concept = self.add_concept(
                    name=f"concept_from_{pattern_id}",
                    description=f"Derived from neural pattern {pattern_id}",
                    level=target_concept_level,
                    confidence=best_confidence
                )

            # 创建映射
            mapping_id = f"mapping_{self._mapping_counter}"
            self._mapping_counter += 1

            mapping = NeuralToSymbolicMapping(
                id=mapping_id,
                neural_pattern_id=pattern_id,
                concept_id=best_concept.id,
                mapping_type="extraction",
                confidence=best_confidence
            )

            self._neural_to_symbolic[mapping_id] = mapping
            return mapping

    def _get_concept_embedding(self, concept: SymbolicConcept) -> np.ndarray:
        """获取概念嵌入"""
        # 基于属性生成嵌入
        features = []
        for key, value in concept.attributes.items():
            if isinstance(value, (int, float)):
                features.append(value)

        if features:
            return self._generate_embedding(np.array(features))
        else:
            # 基于名称生成
            name_features = np.array([ord(c) for c in concept.name[:50]])
            return self._generate_embedding(name_features)

    # ==================== 符号→神经 ====================

    def symbolic_to_neural(
        self,
        rule_id: str,
        constraint_type: str = "regularization",
        target_layer: str = "output",
        weight: float = 0.1
    ) -> SymbolicToNeuralConstraint:
        """
        符号到神经约束

        Args:
            rule_id: 规则ID
            constraint_type: 约束类型
            target_layer: 目标层
            weight: 权重

        Returns:
            约束定义
        """
        with self._lock:
            if rule_id not in self._rules:
                raise ValueError(f"Rule {rule_id} not found")

            constraint_id = f"constraint_{rule_id}_{constraint_type}"

            constraint = SymbolicToNeuralConstraint(
                id=constraint_id,
                rule_id=rule_id,
                constraint_type=constraint_type,
                target_layer=target_layer,
                weight=weight,
                description=f"Apply rule {rule_id} as {constraint_type} constraint"
            )

            self._symbolic_to_neural[constraint_id] = constraint
            return constraint

    def apply_neural_constraints(
        self,
        layer_outputs: Dict[str, np.ndarray]
    ) -> Dict[str, np.ndarray]:
        """
        应用神经约束

        Args:
            layer_outputs: 层输出

        Returns:
            调整后的输出
        """
        adjusted = layer_outputs.copy()

        for constraint in self._symbolic_to_neural.values():
            if constraint.target_layer in layer_outputs:
                # 获取规则
                rule = self._rules.get(constraint.rule_id)
                if not rule:
                    continue

                # 应用约束（简化实现）
                if constraint.constraint_type == "regularization":
                    # 正则化：惩罚违背规则的结果
                    output = adjusted[constraint.target_layer]
                    penalty = self._compute_rule_penalty(rule, output)
                    adjusted[constraint.target_layer] = output - constraint.weight * penalty

                elif constraint.constraint_type == "attention":
                    # 注意力：聚焦相关概念
                    output = adjusted[constraint.target_layer]
                    attention = self._compute_rule_attention(rule, output)
                    adjusted[constraint.target_layer] = output * attention

                elif constraint.constraint_type == "output":
                    # 输出：直接调整
                    output = adjusted[constraint.target_layer]
                    adjustment = self._compute_rule_adjustment(rule, output)
                    adjusted[constraint.target_layer] = output + adjustment

        return adjusted

    def _compute_rule_penalty(self, rule: LogicalRule, output: np.ndarray) -> np.ndarray:
        """计算规则违背惩罚"""
        # 简化：返回均匀惩罚
        return np.ones_like(output) * 0.1

    def _compute_rule_attention(self, rule: LogicalRule, output: np.ndarray) -> np.ndarray:
        """计算规则注意力"""
        # 简化：均匀注意力
        return np.ones_like(output)

    def _compute_rule_adjustment(self, rule: LogicalRule, output: np.ndarray) -> np.ndarray:
        """计算规则调整"""
        # 简化：无调整
        return np.zeros_like(output)

    # ==================== 混合推理 ====================

    def hybrid_reasoning(
        self,
        input_data: Any,
        strategy: str = "neural_first",
        max_steps: int = 5
    ) -> HybridReasoningChain:
        """
        混合推理

        Args:
            input_data: 输入数据
            strategy: 策略 ("neural_first" / "symbolic_first" / "交替")
            max_steps: 最大步数

        Returns:
            混合推理链
        """
        with self._lock:
            chain_id = f"chain_{len(self._reasoning_history)}"

            steps = []
            current_data = input_data

            # 根据策略执行
            if strategy == "neural_first":
                execution_order = ["neural", "symbolic", "neural", "symbolic"]
            elif strategy == "symbolic_first":
                execution_order = ["symbolic", "neural", "symbolic", "neural"]
            else:  # 交替
                execution_order = ["neural", "symbolic"] * 2

            explanation_parts = []

            for i, paradigm in enumerate(execution_order[:max_steps]):
                if paradigm == "neural":
                    # 神经处理
                    result = self._neural_step(current_data)
                    steps.append({
                        "paradigm": "neural",
                        "operation": "pattern_recognition",
                        "input": str(current_data)[:100],
                        "output": result
                    })
                    explanation_parts.append("通过神经模式识别提取特征")
                else:
                    # 符号处理
                    result = self._symbolic_step(current_data)
                    steps.append({
                        "paradigm": "symbolic",
                        "operation": "logical_inference",
                        "input": str(current_data)[:100],
                        "output": result
                    })
                    explanation_parts.append("通过符号逻辑推理得出结论")

                current_data = result

            # 构建结果
            chain = HybridReasoningChain(
                id=chain_id,
                steps=steps,
                input_data=input_data,
                output=current_data,
                confidence=self._compute_chain_confidence(steps),
                explanation=" → ".join(explanation_parts)
            )

            self._reasoning_history.append(chain)
            return chain

    def _neural_step(self, data: Any) -> Dict[str, Any]:
        """神经推理步骤"""
        if isinstance(data, np.ndarray):
            # 特征处理
            pattern = self.register_neural_pattern(
                features=data,
                source_modality="text",
                confidence=0.8
            )
            return {"pattern_id": pattern.id, "confidence": pattern.confidence}
        elif isinstance(data, dict):
            # 字典转特征
            features = np.array([v for v in data.values() if isinstance(v, (int, float))])
            if len(features) == 0:
                features = np.ones(10)
            return self._neural_step(features)
        else:
            # 文本转特征
            features = np.array([ord(c) for c in str(data)[:100]])
            return self._neural_step(features)

    def _symbolic_step(self, data: Any) -> Dict[str, Any]:
        """符号推理步骤"""
        if isinstance(data, dict) and "pattern_id" in data:
            # 转换神经结果到符号
            mapping = self.neural_to_symbolic(data["pattern_id"])
            concept = self._concepts.get(mapping.concept_id)
            if concept:
                return {
                    "concept": concept.name,
                    "description": concept.description,
                    "confidence": mapping.confidence
                }

        # 执行符号推理
        query = str(data)
        return self.symbolic_reasoning(query)

    def _compute_chain_confidence(self, steps: List[Dict]) -> float:
        """计算推理链置信度"""
        if not steps:
            return 0.0

        confidences = []
        for step in steps:
            output = step.get("output", {})
            if isinstance(output, dict):
                conf = output.get("confidence", 0.5)
                confidences.append(conf)
            else:
                confidences.append(0.5)

        return np.mean(confidences)

    # ==================== 知识图谱查询 ====================

    def query_knowledge_graph(
        self,
        entity: str,
        relation: Optional[str] = None,
        depth: int = 2
    ) -> Dict[str, Any]:
        """
        查询知识图谱

        Args:
            entity: 实体
            relation: 关系（可选）
            depth: 查询深度

        Returns:
            查询结果
        """
        results = {
            "entity": entity,
            "relations": [],
            "connected_entities": []
        }

        # 查询直接关系
        for rel_id, (subject, predicate, obj) in self._knowledge_graph.relations.items():
            if subject == entity:
                results["relations"].append({
                    "predicate": predicate,
                    "object": obj,
                    "type": "outgoing"
                })
                if depth > 1:
                    results["connected_entities"].append(obj)
            elif obj == entity:
                results["relations"].append({
                    "predicate": predicate,
                    "subject": subject,
                    "type": "incoming"
                })
                if depth > 1:
                    results["connected_entities"].append(subject)

        # 筛选特定关系
        if relation:
            results["relations"] = [
                r for r in results["relations"]
                if r.get("predicate") == relation
            ]

        return results

    # ==================== 统计和导出 ====================

    def get_statistics(self) -> Dict[str, Any]:
        """获取统计信息"""
        return {
            "neural_patterns": len(self._neural_patterns),
            "concepts": len(self._concepts),
            "rules": len(self._rules),
            "neural_to_symbolic_mappings": len(self._neural_to_symbolic),
            "symbolic_to_neural_constraints": len(self._symbolic_to_neural),
            "reasoning_chains": len(self._reasoning_history),
            "knowledge_graph_entities": len(self._knowledge_graph.entities),
            "knowledge_graph_relations": len(self._knowledge_graph.relations)
        }

    def export_knowledge_graph(self) -> Dict[str, Any]:
        """导出知识图谱"""
        return {
            "entities": {
                k: {
                    "name": v.name,
                    "description": v.description,
                    "level": v.level.value,
                    "attributes": v.attributes
                }
                for k, v in self._knowledge_graph.entities.items()
            },
            "relations": {
                k: {"subject": s, "predicate": p, "object": o}
                for k, (s, p, o) in self._knowledge_graph.relations.items()
            },
            "rules": {
                k: {
                    "name": v.name,
                    "antecedent": v.antecedent,
                    "consequent": v.consequent,
                    "operator": v.operator.value,
                    "confidence": v.confidence
                }
                for k, v in self._knowledge_graph.rules.items()
            }
        }

    def __repr__(self) -> str:
        return f"NeuroSymbolicEngine(patterns={len(self._neural_patterns)}, concepts={len(self._concepts)}, rules={len(self._rules)})"
