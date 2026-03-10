"""
因果推理系统 - 超越相关性
├── 因果发现: 从数据中学习因果关系
├── 因果干预模拟: "如果...会怎样"分析
├── 反事实推理: 对比现实与假设
├── 因果解释生成: 解释"为什么"
└── 因果图维护: 动态更新的因果知识库
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


class CausalRelationType(Enum):
    """因果关系类型"""
    DIRECT = "direct"             # 直接因果
    INDIRECT = "indirect"         # 间接因果
    CONDITIONAL = "conditional"   # 条件因果
    MEDIATING = "mediating"       # 中介因果
    MODERATING = "moderating"     # 调节因果
    SPURIOUS = "spurious"         # 伪因果


class EvidenceStrength(Enum):
    """证据强度"""
    STRONG = 1.0       # 强
    MODERATE = 0.7     # 中等
    WEAK = 0.4         # 弱
    ANECDOTAL = 0.2    # 逸事


@dataclass
class CausalNode:
    """因果节点"""
    id: str
    name: str
    description: str
    node_type: str  # "variable" / "event" / "concept"
    states: List[str] = field(default_factory=list)  # 可能状态
    metadata: Dict[str, Any] = field(default_factory=dict)


@dataclass
class CausalEdge:
    """因果边"""
    id: str
    source: str  # 原因节点ID
    target: str  # 结果节点ID
    relation_type: CausalRelationType
    strength: float  # 因果强度 0-1
    confidence: float  # 置信度 0-1
    evidence: List[str] = field(default_factory=list)
    conditions: Dict[str, Any] = field(default_factory=dict)  # 条件
    delay: float = 0.0  # 时间延迟
    metadata: Dict[str, Any] = field(default_factory=dict)


@dataclass
class CausalGraph:
    """因果图"""
    nodes: Dict[str, CausalNode] = field(default_factory=dict)
    edges: Dict[str, CausalEdge] = field(default_factory=dict)
    adjacencies: Dict[str, Set[str]] = field(default_factory=lambda: defaultdict(set))


@dataclass
class Intervention:
    """干预"""
    id: str
    node_id: str
    new_value: Any
    original_value: Any
    timestamp: datetime = field(default_factory=datetime.now)
    effects: Dict[str, Any] = field(default_factory=dict)


@dataclass
class Counterfactual:
    """反事实"""
    id: str
    condition: str  # 条件描述
    hypothetical: str  # 假设描述
    original_outcome: Any
    hypothetical_outcome: Any
    difference: float  # 差异程度
    plausibility: float  # 合理性 0-1
    reasoning: str = ""


@dataclass
class CausalExplanation:
    """因果解释"""
    id: str
    cause: str
    effect: str
    mechanism: str  # 因果机制
    chain: List[str] = field(default_factory=list)
    confidence: float = 0.0
    evidence: List[str] = field(default_factory=list)
    alternatives: List[str] = field(default_factory=list)


@dataclass
class CausalDiscovery:
    """因果发现结果"""
    relations: List[Tuple[str, str, float]]  # (原因, 结果, 强度)
    confidence: float
    method: str
    evidence: Dict[str, List[str]] = field(default_factory=dict)


class CausalEngine:
    """
    因果推理系统

    实现超越相关性的因果推理能力:
    1. 因果发现: 从数据中学习因果关系
    2. 因果干预: 模拟干预效果
    3. 反事实推理: 对比现实与假设
    4. 因果解释: 生成"为什么"解释
    5. 因果图: 维护动态因果知识库
    """

    # 参数
    MIN_CAUSAL_STRENGTH = 0.3
    CONFIDENCE_THRESHOLD = 0.5
    MAX_CHAIN_LENGTH = 5

    def __init__(
        self,
        enable_discovery: bool = True,
        enable_intervention: bool = True,
        enable_counterfactual: bool = True,
        max_graph_size: int = 1000
    ):
        """
        初始化因果推理系统

        Args:
            enable_discovery: 启用因果发现
            enable_intervention: 启用因果干预
            enable_counterfactual: 启用反事实推理
            max_graph_size: 最大图规模
        """
        self.enable_discovery = enable_discovery
        self.enable_intervention = enable_intervention
        self.enable_counterfactual = enable_counterfactual
        self.max_graph_size = max_graph_size

        # 因果图
        self._graph = CausalGraph()
        self._node_counter = 0
        self._edge_counter = 0

        # 历史记录
        self._intervention_history: deque = deque(maxlen=500)
        self._counterfactual_history: deque = deque(maxlen=500)
        self._explanation_history: deque = deque(maxlen=500)

        # 发现算法缓存
        self._discovery_cache: Dict[str, CausalDiscovery] = {}

        # 线程安全
        self._lock = threading.RLock()

    # ==================== 因果发现 ====================

    def discover_causal_relations(
        self,
        data: List[Dict[str, Any]],
        variables: List[str],
        method: str = "correlation"
    ) -> CausalDiscovery:
        """
        因果发现

        Args:
            data: 观测数据
            variables: 变量列表
            method: 发现方法

        Returns:
            因果发现结果
        """
        with self._lock:
            # 缓存检查
            cache_key = f"{method}:{len(data)}:{len(variables)}"
            if cache_key in self._discovery_cache:
                return self._discovery_cache[cache_key]

            # 选择发现方法
            if method == "correlation":
                relations = self._discover_by_correlation(data, variables)
            elif method == "granger":
                relations = self._discover_by_granger(data, variables)
            elif method == "pc":
                relations = self._discover_by_pc(data, variables)
            else:
                relations = self._discover_by_correlation(data, variables)

            # 计算置信度
            confidence = self._compute_discovery_confidence(relations)

            result = CausalDiscovery(
                relations=relations,
                confidence=confidence,
                method=method,
                evidence={}
            )

            # 缓存
            self._discovery_cache[cache_key] = result

            # 自动添加到因果图
            self._add_discovered_relations(relations)

            return result

    def _discover_by_correlation(
        self,
        data: List[Dict],
        variables: List[str]
    ) -> List[Tuple[str, str, float]]:
        """基于相关性的因果发现"""
        relations = []

        # 计算相关矩阵
        corr_matrix = self._compute_correlation_matrix(data, variables)

        # 找出强相关对
        for i, var1 in enumerate(variables):
            for j, var2 in enumerate(variables):
                if i >= j:
                    continue

                corr = abs(corr_matrix[i, j])

                if corr > self.MIN_CAUSAL_STRENGTH:
                    # 方向判断：时间序列中，前面的为因
                    # 简化：假设变量名字典序小的为因
                    if var1 < var2:
                        relations.append((var1, var2, corr))
                    else:
                        relations.append((var2, var1, corr))

        return relations

    def _discover_by_granger(
        self,
        data: List[Dict],
        variables: List[str]
    ) -> List[Tuple[str, str, float]]:
        """基于Granger因果性的发现"""
        # 简化实现：时序因果
        relations = []

        if len(data) < 10:
            return relations

        # 检查每个变量是否能预测其他变量
        for target_var in variables:
            for predictor_var in variables:
                if target_var == predictor_var:
                    continue

                # 简单Granger检验
                prediction_power = self._granger_test(
                    data, predictor_var, target_var
                )

                if prediction_power > self.MIN_CAUSAL_STRENGTH:
                    relations.append((predictor_var, target_var, prediction_power))

        return relations

    def _discover_by_pc(
        self,
        data: List[Dict],
        variables: List[str]
    ) -> List[Tuple[str, str, float]]:
        """PC算法（简化版）"""
        # 1. 先找无向边
        relations = self._discover_by_correlation(data, variables)

        # 2. 定向（简化：基于时间顺序）
        directed = []
        for cause, effect, strength in relations:
            directed.append((cause, effect, strength))

        return directed

    def _compute_correlation_matrix(
        self,
        data: List[Dict],
        variables: List[str]
    ) -> np.ndarray:
        """计算相关矩阵"""
        n = len(variables)
        matrix = np.zeros((n, n))

        # 提取数据
        values = []
        for var in variables:
            var_values = [d.get(var, 0) for d in data]
            values.append(var_values)

        # 计算相关
        for i in range(n):
            for j in range(n):
                if i == j:
                    matrix[i, j] = 1.0
                else:
                    corr = np.corrcoef(values[i], values[j])[0, 1]
                    matrix[i, j] = corr if not np.isnan(corr) else 0.0

        return matrix

    def _granger_test(
        self,
        data: List[Dict],
        predictor: str,
        target: str
    ) -> float:
        """Granger因果检验"""
        if len(data) < 5:
            return 0.0

        predictor_vals = [d.get(predictor, 0) for d in data]
        target_vals = [d.get(target, 0) for d in data]

        # 简化：比较带滞后和不带滞后的预测误差
        # 无滞后预测
        pred_no_lag = target_vals[:-1]
        actual_no_lag = target_vals[1:]
        error_no_lag = np.mean((np.array(pred_no_lag) - np.array(actual_no_lag)) ** 2)

        # 有滞后预测
        pred_with_lag = predictor_vals[:-1]
        error_with_lag = np.mean((np.array(pred_with_lag) - np.array(actual_no_lag)) ** 2)

        # 计算改善
        if error_no_lag == 0:
            return 0.0

        improvement = (error_no_lag - error_with_lag) / error_no_lag

        return max(0.0, improvement)

    def _compute_discovery_confidence(
        self,
        relations: List[Tuple[str, str, float]]
    ) -> float:
        """计算发现置信度"""
        if not relations:
            return 0.0

        # 基于关系强度
        avg_strength = np.mean([r[2] for r in relations])

        # 基于关系数量
        count_factor = min(len(relations) / 10, 1.0)

        return avg_strength * 0.7 + count_factor * 0.3

    def _add_discovered_relations(
        self,
        relations: List[Tuple[str, str, float]]
    ):
        """将发现的因果关系添加到图中"""
        for cause, effect, strength in relations:
            # 添加节点
            if cause not in self._graph.nodes:
                self._add_node(cause, cause, "variable")
            if effect not in self._graph.nodes:
                self._add_node(effect, effect, "variable")

            # 添加边
            edge_id = f"edge_{cause}_{effect}"
            if edge_id not in self._graph.edges:
                self._add_edge(
                    cause, effect,
                    CausalRelationType.DIRECT,
                    strength,
                    strength * 0.8  # 发现置信度略低
                )

    # ==================== 因果图管理 ====================

    def _add_node(
        self,
        node_id: str,
        name: str,
        node_type: str = "variable",
        states: Optional[List[str]] = None
    ) -> CausalNode:
        """添加节点"""
        node = CausalNode(
            id=node_id,
            name=name,
            description=name,
            node_type=node_type,
            states=states or []
        )
        self._graph.nodes[node_id] = node
        return node

    def _add_edge(
        self,
        source: str,
        target: str,
        relation_type: CausalRelationType,
        strength: float,
        confidence: float,
        evidence: Optional[List[str]] = None
    ) -> CausalEdge:
        """添加边"""
        edge_id = f"edge_{len(self._graph.edges)}"
        edge = CausalEdge(
            id=edge_id,
            source=source,
            target=target,
            relation_type=relation_type,
            strength=strength,
            confidence=confidence,
            evidence=evidence or []
        )
        self._graph.edges[edge_id] = edge
        self._graph.adjacencies[source].add(target)
        return edge

    def add_causal_relation(
        self,
        cause: str,
        effect: str,
        strength: float,
        relation_type: CausalRelationType = CausalRelationType.DIRECT,
        confidence: float = 0.8,
        evidence: Optional[List[str]] = None,
        conditions: Optional[Dict[str, Any]] = None
    ):
        """
        手动添加因果关系

        Args:
            cause: 原因
            effect: 结果
            strength: 因果强度
            relation_type: 关系类型
            confidence: 置信度
            evidence: 证据
            conditions: 条件
        """
        with self._lock:
            # 添加节点
            if cause not in self._graph.nodes:
                self._add_node(cause, cause, "variable")
            if effect not in self._graph.nodes:
                self._add_node(effect, effect, "variable")

            # 添加边
            self._add_edge(
                cause, effect,
                relation_type,
                strength,
                confidence,
                evidence,
                conditions or {}
            )

    def get_causal_graph(self) -> CausalGraph:
        """获取因果图"""
        return self._graph

    def find_causal_chain(
        self,
        start: str,
        end: str,
        max_length: int = 5
    ) -> List[List[str]]:
        """
        查找因果链

        Args:
            start: 起点
            end: 终点
            max_length: 最大长度

        Returns:
            因果链列表
        """
        chains = []

        # BFS搜索
        queue = [(start, [start])]

        while queue:
            current, path = queue.pop(0)

            if len(path) > max_length:
                continue

            if current == end:
                chains.append(path)
                continue

            # 扩展
            for neighbor in self._graph.adjacencies.get(current, []):
                if neighbor not in path:
                    queue.append((neighbor, path + [neighbor]))

        # 按长度排序
        chains.sort(key=len)

        return chains

    def get_ancestors(self, node_id: str) -> Set[str]:
        """获取节点的祖先（所有原因）"""
        ancestors = set()
        queue = [node_id]
        visited = set()

        while queue:
            current = queue.pop(0)
            if current in visited:
                continue
            visited.add(current)

            # 找父节点
            for edge in self._graph.edges.values():
                if edge.target == current:
                    ancestors.add(edge.source)
                    queue.append(edge.source)

        return ancestors

    def get_descendants(self, node_id: str) -> Set[str]:
        """获取节点的后代（所有结果）"""
        descendants = set()
        queue = [node_id]
        visited = set()

        while queue:
            current = queue.pop(0)
            if current in visited:
                continue
            visited.add(current)

            # 找子节点
            for neighbor in self._graph.adjacencies.get(current, []):
                descendants.add(neighbor)
                queue.append(neighbor)

        return descendants

    # ==================== 因果干预 ====================

    def intervene(
        self,
        node_id: str,
        new_value: Any,
        context: Optional[Dict[str, Any]] = None
    ) -> Intervention:
        """
        因果干预

        Args:
            node_id: 干预节点ID
            new_value: 新值
            context: 上下文

        Returns:
            干预结果
        """
        if not self.enable_intervention:
            raise ValueError("因果干预未启用")

        with self._lock:
            intervention_id = f"int_{len(self._intervention_history)}"

            # 记录原始值（简化）
            original_value = context.get(node_id) if context else None

            # 创建干预
            intervention = Intervention(
                id=intervention_id,
                node_id=node_id,
                new_value=new_value,
                original_value=original_value
            )

            # 计算干预效果
            effects = self._compute_intervention_effects(
                node_id, new_value, context or {}
            )
            intervention.effects = effects

            # 记录历史
            self._intervention_history.append(intervention)

            return intervention

    def _compute_intervention_effects(
        self,
        node_id: str,
        new_value: Any,
        context: Dict
    ) -> Dict[str, Any]:
        """计算干预效果"""
        effects = {}

        # 获取所有后代节点
        descendants = self.get_descendants(node_id)

        for desc_id in descendants:
            # 查找因果边
            for edge in self._graph.edges.values():
                if edge.source == node_id and edge.target == desc_id:
                    # 计算效果
                    effect_strength = edge.strength

                    # 考虑调节变量
                    if edge.conditions:
                        condition_factor = self._evaluate_conditions(
                            edge.conditions, context
                        )
                        effect_strength *= condition_factor

                    effects[desc_id] = {
                        "value": new_value,
                        "effect_size": effect_strength,
                        "direction": "positive" if effect_strength > 0 else "negative"
                    }

        return effects

    def _evaluate_conditions(
        self,
        conditions: Dict[str, Any],
        context: Dict
    ) -> float:
        """评估条件满足程度"""
        if not conditions:
            return 1.0

        satisfied = 0
        total = len(conditions)

        for key, expected in conditions.items():
            actual = context.get(key)
            if actual == expected:
                satisfied += 1

        return satisfied / total if total > 0 else 1.0

    def simulate_intervention(
        self,
        intervention: Intervention,
        steps: int = 3
    ) -> List[Dict[str, Any]]:
        """
        模拟干预的级联效果

        Args:
            intervention: 干预
            steps: 模拟步数

        Returns:
            每步的状态
        """
        states = []

        # 初始状态
        current_state = {
            intervention.node_id: intervention.new_value
        }
        states.append(current_state.copy())

        # 模拟传播
        for step in range(steps):
            next_state = current_state.copy()

            for node_id in current_state:
                # 获取该节点的影响
                for edge in self._graph.edges.values():
                    if edge.source == node_id:
                        effect = current_state[node_id] * edge.strength
                        target = edge.target

                        if target in next_state:
                            next_state[target] += effect
                        else:
                            next_state[target] = effect

            states.append(next_state.copy())
            current_state = next_state

        return states

    # ==================== 反事实推理 ====================

    def counterfactual_reasoning(
        self,
        observed: Dict[str, Any],
        condition: str,
        hypothetical: str
    ) -> Counterfactual:
        """
        反事实推理

        Args:
            observed: 观测事实
            condition: 条件
            hypothetical: 假设

        Returns:
            反事实结果
        """
        with self._lock:
            cf_id = f"cf_{len(self._counterfactual_history)}"

            # 原始结果
            original_outcome = self._predict_outcome(observed)

            # 假设结果
            hypothetical_data = observed.copy()
            hypothetical_data["_counterfactual"] = True
            hypothetical_outcome = self._predict_outcome(hypothetical_data)

            # 计算差异
            difference = self._compute_difference(
                original_outcome, hypothetical_outcome
            )

            # 评估合理性
            plausibility = self._assess_plausibility(
                condition, observed
            )

            result = Counterfactual(
                id=cf_id,
                condition=condition,
                hypothetical=hypothetical,
                original_outcome=original_outcome,
                hypothetical_outcome=hypothetical_outcome,
                difference=difference,
                plausibility=plausibility,
                reasoning=self._generate_counterfactual_reasoning(
                    condition, original_outcome, hypothetical_outcome
                )
            )

            self._counterfactual_history.append(result)

            return result

    def _predict_outcome(self, data: Dict[str, Any]) -> Any:
        """预测结果"""
        # 简化实现：基于因果图的预测
        # 找到所有根节点
        root_nodes = self._get_root_nodes()

        # 传播效应
        outcome = {}
        for root in root_nodes:
            if root in data:
                # 沿着因果链传播
                self._propagate_effect(root, data[root], outcome)

        return outcome

    def _get_root_nodes(self) -> List[str]:
        """获取根节点（无父节点）"""
        roots = []
        for node_id in self._graph.nodes:
            is_root = True
            for edge in self._graph.edges.values():
                if edge.target == node_id:
                    is_root = False
                    break
            if is_root:
                roots.append(node_id)
        return roots

    def _propagate_effect(
        self,
        source: str,
        value: Any,
        outcome: Dict[str, Any]
    ):
        """传播效应"""
        queue = [(source, value)]
        visited = set()

        while queue:
            node, val = queue.pop(0)
            if node in visited:
                continue
            visited.add(node)

            # 添加到结果
            outcome[node] = val

            # 传播到子节点
            for neighbor in self._graph.adjacencies.get(node, []):
                edge = self._find_edge(node, neighbor)
                if edge:
                    new_val = val * edge.strength
                    queue.append((neighbor, new_val))

    def _find_edge(self, source: str, target: str) -> Optional[CausalEdge]:
        """查找边"""
        for edge in self._graph.edges.values():
            if edge.source == source and edge.target == target:
                return edge
        return None

    def _compute_difference(
        self,
        original: Any,
        hypothetical: Any
    ) -> float:
        """计算差异"""
        if isinstance(original, dict) and isinstance(hypothetical, dict):
            diff_count = 0
            all_keys = set(original.keys()) | set(hypothetical.keys())

            for key in all_keys:
                if original.get(key) != hypothetical.get(key):
                    diff_count += 1

            return diff_count / len(all_keys) if all_keys else 0.0

        return 0.0 if original == hypothetical else 1.0

    def _assess_plausibility(
        self,
        condition: str,
        context: Dict
    ) -> float:
        """评估反事实合理性"""
        # 简化：基于条件是否与已知因果关系一致
        plausibility = 0.5

        # 检查条件中的变量是否在因果图中
        for node_id in self._graph.nodes:
            if node_id in condition:
                plausibility += 0.1

        return min(1.0, plausibility)

    def _generate_counterfactual_reasoning(
        self,
        condition: str,
        original: Any,
        hypothetical: Any
    ) -> str:
        """生成反事实推理"""
        return f"如果{condition}，则结果将从{original}变为{hypothetical}"

    # ==================== 因果解释 ====================

    def explain_causation(
        self,
        cause: str,
        effect: str,
        context: Optional[Dict[str, Any]] = None
    ) -> CausalExplanation:
        """
        因果解释

        Args:
            cause: 原因
            effect: 结果
            context: 上下文

        Returns:
            因果解释
        """
        with self._lock:
            exp_id = f"exp_{len(self._explanation_history)}"

            # 查找因果链
            chains = self.find_causal_chain(cause, effect)

            # 选择最短链
            chain = chains[0] if chains else [cause, effect]

            # 构建机制描述
            mechanism = self._generate_mechanism(chain)

            # 查找证据
            evidence = self._find_evidence(cause, effect)

            # 计算置信度
            confidence = self._compute_explanation_confidence(chain)

            # 查找替代解释
            alternatives = self._find_alternatives(cause, effect)

            explanation = CausalExplanation(
                id=exp_id,
                cause=cause,
                effect=effect,
                mechanism=mechanism,
                chain=chain,
                confidence=confidence,
                evidence=evidence,
                alternatives=alternatives
            )

            self._explanation_history.append(explanation)

            return explanation

    def _generate_mechanism(self, chain: List[str]) -> str:
        """生成因果机制描述"""
        if len(chain) < 2:
            return "无法确定因果机制"

        parts = []
        for i in range(len(chain) - 1):
            parts.append(f"{chain[i]}影响{chain[i+1]}")

        return " → ".join(parts)

    def _find_evidence(self, cause: str, effect: str) -> List[str]:
        """查找证据"""
        evidence = []

        # 查找因果边
        for edge in self._graph.edges.values():
            if edge.source == cause and edge.target == effect:
                evidence.extend(edge.evidence)

        return evidence if evidence else ["基于统计相关性"]

    def _compute_explanation_confidence(self, chain: List[str]) -> float:
        """计算解释置信度"""
        if not chain:
            return 0.0

        # 基于链长度和边强度
        total_strength = 0.0

        for i in range(len(chain) - 1):
            edge = self._find_edge(chain[i], chain[i + 1])
            if edge:
                total_strength += edge.strength * edge.confidence

        avg_confidence = total_strength / (len(chain) - 1) if len(chain) > 1 else 0.0

        # 惩罚过长链
        length_penalty = 0.1 * (len(chain) - 2) if len(chain) > 2 else 0.0

        return max(0.0, avg_confidence - length_penalty)

    def _find_alternatives(self, cause: str, effect: str) -> List[str]:
        """查找替代解释"""
        alternatives = []

        # 查找共同原因
        cause_ancestors = self.get_ancestors(cause)
        effect_ancestors = self.get_ancestors(effect)
        common_ancestors = cause_ancestors & effect_ancestors

        for ancestor in common_ancestors:
            if ancestor != cause and ancestor != effect:
                alternatives.append(f"可能存在共同原因: {ancestor}")

        # 查找间接路径
        chains = self.find_causal_chain(cause, effect, max_length=3)
        if len(chains) > 1:
            alternatives.append("可能存在其他因果路径")

        return alternatives

    def why_because(
        self,
        effect: str,
        context: Optional[Dict[str, Any]] = None
    ) -> str:
        """
        "为什么"解释

        Args:
            effect: 结果
            context: 上下文

        Returns:
            因为...所以...
        """
        ancestors = self.get_ancestors(effect)

        if not ancestors:
            return f"无法解释为什么{effect}"

        # 选择最强的原因
        strongest_cause = None
        strongest_strength = 0.0

        for ancestor in ancestors:
            edge = self._find_edge(ancestor, effect)
            if edge and edge.strength > strongest_strength:
                strongest_strength = edge.strength
                strongest_cause = ancestor

        if strongest_cause:
            return f"因为{strongest_cause}，所以{effect}（因果强度: {strongest_strength:.2f}）"
        else:
            return f"无法确定为什么{effect}"

    # ==================== 历史和统计 ====================

    def get_statistics(self) -> Dict[str, Any]:
        """获取统计信息"""
        return {
            "graph_nodes": len(self._graph.nodes),
            "graph_edges": len(self._graph.edges),
            "interventions": len(self._intervention_history),
            "counterfactuals": len(self._counterfactual_history),
            "explanations": len(self._explanation_history),
            "discovery_cache": len(self._discovery_cache)
        }

    def __repr__(self) -> str:
        return f"CausalEngine(nodes={len(self._graph.nodes)}, edges={len(self._graph.edges)})"
