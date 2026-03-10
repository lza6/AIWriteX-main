"""
元认知能力 - 系统对自身的认知
├── 认知状态监控: 实时评估推理质量
├── 不确定性量化: 置信度校准
├── 策略选择: 根据任务选择推理模式
├── 错误检测: 识别自身推理缺陷
└── 自我修正: 自主改进推理过程
"""

import numpy as np
from typing import Dict, List, Optional, Any, Callable, Tuple, Set
from dataclasses import dataclass, field
from datetime import datetime, timedelta
from enum import Enum, auto
from collections import deque
import threading
import time
import json


class CognitiveState(Enum):
    """认知状态"""
    OPTIMAL = "optimal"           # 最优
    GOOD = "good"                # 良好
    DEGRADED = "degraded"        # 退化
    UNCERTAIN = "uncertain"      # 不确定
    FAILING = "failing"          # 失效


class StrategyType(Enum):
    """策略类型"""
    CAUTIOUS = "cautious"        # 谨慎策略
    BOLD = "bold"                # 激进策略
    EXPLORATORY = "exploratory"  # 探索策略
    EXPLOITATIVE = "exploitative"  # 利用策略
    ADAPTIVE = "adaptive"        # 自适应策略


class ErrorType(Enum):
    """错误类型"""
    LOGIC_FLAW = "logic_flaw"          # 逻辑缺陷
    PREMISE_ERROR = "premise_error"      # 前提错误
    BIAS = "bias"                      # 偏见
    OVERCONFIDENCE = "overconfidence"   # 过度自信
    UNDERCONFIDENCE = "underconfidence" # 缺乏自信
    INFERENCE_ERROR = "inference_error" # 推理错误
    MEMORY_ERROR = "memory_error"       # 记忆错误


@dataclass
class CognitiveMetrics:
    """认知指标"""
    coherence_score: float = 1.0      # 连贯性得分
    confidence_calibration: float = 1.0  # 置信度校准
    accuracy_rate: float = 1.0        # 准确率
    error_rate: float = 0.0          # 错误率
    processing_speed: float = 1.0    # 处理速度
    resource_efficiency: float = 1.0  # 资源效率


@dataclass
class UncertaintyEstimate:
    """不确定性估计"""
    aleatoric: float = 0.0          # 随机不确定性（不可降低）
    epistemic: float = 0.0           # 认知不确定性（可降低）
    total: float = 0.0              # 总不确定性
    confidence_interval: Tuple[float, float] = (0.0, 1.0)
    calibration_history: List[float] = field(default_factory=list)

    def compute_total(self):
        """计算总不确定性"""
        self.total = self.aleatoric + self.epistemic
        return self.total


@dataclass
class StrategySelection:
    """策略选择"""
    selected_strategy: StrategyType
    alternatives: List[Tuple[StrategyType, float]]  # (策略, 得分)
    reasoning: str
    expected_outcome: float
    risk_level: float


@dataclass
class DetectedError:
    """检测到的错误"""
    id: str
    error_type: ErrorType
    description: str
    severity: float  # 0-1
    location: Dict[str, Any]  # 错误位置
    evidence: List[str]
    timestamp: datetime = field(default_factory=datetime.now)
    corrected: bool = False
    correction: Optional[str] = None


@dataclass
class CorrectionAction:
    """修正行动"""
    error_id: str
    action_type: str
    description: str
    success_probability: float
    executed: bool = False
    result: Optional[bool] = None
    timestamp: datetime = field(default_factory=datetime.now)


@dataclass
class SelfAssessment:
    """自我评估"""
    cognitive_state: CognitiveState
    overall_confidence: float
    strengths: List[str]
    weaknesses: List[str]
    improvement_areas: List[str]
    recommendations: List[str]
    timestamp: datetime = field(default_factory=datetime.now)


class MetaCognition:
    """
    元认知能力系统

    实现对自身认知过程的监控、评估和优化:
    1. 认知状态监控: 实时跟踪推理质量
    2. 不确定性量化: 评估答案的可靠性
    3. 策略选择: 根据情况选择最佳策略
    4. 错误检测: 识别推理过程中的错误
    5. 自我修正: 自主改进认知过程
    """

    # 阈值参数
    COHERENCE_THRESHOLD = 0.7
    CALIBRATION_THRESHOLD = 0.8
    ERROR_RATE_THRESHOLD = 0.15
    UNCERTAINTY_THRESHOLD = 0.6

    # 校准参数
    CALIBRATION_WINDOW = 100
    CALIBRATION_LEARNING_RATE = 0.1

    def __init__(
        self,
        calibration_enabled: bool = True,
        error_detection_enabled: bool = True,
        self_correction_enabled: bool = True,
        monitoring_window: int = 50
    ):
        """
        初始化元认知系统

        Args:
            calibration_enabled: 启用置信度校准
            error_detection_enabled: 启用错误检测
            self_correction_enabled: 启用自我修正
            monitoring_window: 监控窗口大小
        """
        self.calibration_enabled = calibration_enabled
        self.error_detection_enabled = error_detection_enabled
        self.self_correction_enabled = self_correction_enabled
        self.monitoring_window = monitoring_window

        # 认知状态
        self._current_state = CognitiveState.OPTIMAL
        self._metrics = CognitiveMetrics()

        # 历史记录
        self._prediction_history: deque = deque(maxlen=1000)  # (预测, 实际, 置信度)
        self._error_history: deque = deque(maxlen=500)
        self._correction_history: deque = deque(maxlen=200)
        self._state_history: deque = deque(maxlen=monitoring_window)

        # 校准
        self._calibration_samples: deque = deque(maxlen=self.CALIBRATION_WINDOW)
        self._calibration_model: Dict[str, float] = {"slope": 1.0, "intercept": 0.0}

        # 错误检测
        self._error_patterns: Dict[ErrorType, Callable] = {}
        self._known_biases: Set[str] = set()
        self._register_error_patterns()

        # 策略
        self._strategy_scores: Dict[StrategyType, float] = {
            StrategyType.CAUTIOUS: 0.8,
            StrategyType.BOLD: 0.6,
            StrategyType.EXPLORATORY: 0.7,
            StrategyType.EXPLOITATIVE: 0.75,
            StrategyType.ADAPTIVE: 0.9
        }

        # 线程安全
        self._lock = threading.RLock()

    def _register_error_patterns(self):
        """注册错误检测模式"""
        self._error_patterns = {
            ErrorType.LOGIC_FLAW: self._detect_logic_flaw,
            ErrorType.PREMISE_ERROR: self._detect_premise_error,
            ErrorType.BIAS: self._detect_bias,
            ErrorType.OVERCONFIDENCE: self._detect_overconfidence,
            ErrorType.UNDERCONFIDENCE: self._detect_underconfidence,
            ErrorType.INFERENCE_ERROR: self._detect_inference_error,
            ErrorType.MEMORY_ERROR: self._detect_memory_error
        }

    # ==================== 认知状态监控 ====================

    def monitor_cognition(self, reasoning_output: Any, context: Dict[str, Any]) -> CognitiveState:
        """
        监控认知状态

        Args:
            reasoning_output: 推理输出
            context: 上下文信息

        Returns:
            当前认知状态
        """
        with self._lock:
            # 评估连贯性
            coherence = self._evaluate_coherence(reasoning_output, context)

            # 评估准确率
            accuracy = self._evaluate_accuracy()

            # 综合评估
            if coherence >= 0.9 and accuracy >= 0.9:
                state = CognitiveState.OPTIMAL
            elif coherence >= 0.7 and accuracy >= 0.7:
                state = CognitiveState.GOOD
            elif coherence >= 0.5 or accuracy >= 0.5:
                state = CognitiveState.DEGRADED
            elif coherence >= 0.3 or accuracy >= 0.3:
                state = CognitiveState.UNCERTAIN
            else:
                state = CognitiveState.FAILING

            self._current_state = state
            self._update_metrics(coherence, accuracy)
            self._state_history.append({
                "state": state,
                "coherence": coherence,
                "accuracy": accuracy,
                "timestamp": datetime.now()
            })

            return state

    def _evaluate_coherence(self, output: Any, context: Dict[str, Any]) -> float:
        """评估输出连贯性"""
        score = 1.0

        # 检查输出与上下文的一致性
        if "expected_type" in context:
            expected = context["expected_type"]
            actual_type = type(output).__name__
            if expected != actual_type:
                score *= 0.7

        # 检查输出的内部一致性
        if isinstance(output, dict):
            # 检查必要字段
            required = context.get("required_fields", [])
            missing = [f for f in required if f not in output]
            if missing:
                score *= (1 - len(missing) / len(required) * 0.5)

        # 检查逻辑一致性
        if "logical_constraints" in context:
            constraints = context["logical_constraints"]
            violated = self._check_constraints(output, constraints)
            if violated:
                score *= (1 - violated * 0.2)

        return score

    def _evaluate_accuracy(self) -> float:
        """评估历史准确率"""
        if not self._prediction_history:
            return 1.0

        correct = sum(1 for _, actual, _ in self._prediction_history
                    if actual is not None)
        total = len([p for p in self._prediction_history if p[1] is not None])

        return correct / total if total > 0 else 1.0

    def _check_constraints(self, output: Any, constraints: List[Dict]) -> int:
        """检查逻辑约束"""
        violations = 0
        for constraint in constraints:
            op = constraint.get("operator")
            field = constraint.get("field")
            value = constraint.get("value")

            if isinstance(output, dict) and field in output:
                actual = output[field]
                if op == "==" and actual != value:
                    violations += 1
                elif op == ">" and actual <= value:
                    violations += 1
                elif op == "<" and actual >= value:
                    violations += 1
                elif op == "!=" and actual == value:
                    violations += 1

        return violations

    def _update_metrics(self, coherence: float, accuracy: float):
        """更新认知指标"""
        self._metrics.coherence_score = coherence
        self._metrics.accuracy_rate = accuracy
        self._metrics.error_rate = 1 - accuracy

        # 资源效率（基于处理时间）
        self._metrics.resource_efficiency = min(1.0, 1.0 / (1 + self._error_history.count))

    def get_current_state(self) -> Tuple[CognitiveState, CognitiveMetrics]:
        """获取当前状态"""
        return self._current_state, self._metrics

    # ==================== 不确定性量化 ====================

    def quantify_uncertainty(
        self,
        prediction: Any,
        evidence: List[Any],
        context: Dict[str, Any]
    ) -> UncertaintyEstimate:
        """
        量化不确定性

        Args:
            prediction: 预测结果
            evidence: 支持证据
            context: 上下文

        Returns:
            不确定性估计
        """
        with self._lock:
            estimate = UncertaintyEstimate()

            # 1. 随机不确定性（基于证据数量和质量）
            if not evidence:
                estimate.aleatoric = 0.8
            else:
                evidence_quality = self._assess_evidence_quality(evidence)
                estimate.aleatoric = 1.0 - evidence_quality

            # 2. 认知不确定性（基于模型置信度）
            epistemic = self._compute_epistemic_uncertainty(prediction, context)
            estimate.epistemic = epistemic

            # 3. 计算总不确定性
            estimate.compute_total()

            # 4. 计算置信区间
            margin = estimate.total * 0.5
            estimate.confidence_interval = (
                max(0, 0.5 - margin),
                min(1, 0.5 + margin)
            )

            return estimate

    def _assess_evidence_quality(self, evidence: List[Any]) -> float:
        """评估证据质量"""
        if not evidence:
            return 0.0

        scores = []

        for e in evidence:
            # 基于证据类型评分
            if isinstance(e, dict):
                if "source" in e and "content" in e:
                    scores.append(0.9)
                elif "content" in e:
                    scores.append(0.7)
                else:
                    scores.append(0.5)
            elif isinstance(e, str):
                scores.append(0.6)
            else:
                scores.append(0.4)

        return np.mean(scores) if scores else 0.0

    def _compute_epistemic_uncertainty(self, prediction: Any, context: Dict[str, Any]) -> float:
        """计算认知不确定性"""
        uncertainty = 0.0

        # 基于上下文复杂度
        complexity = context.get("complexity", 0.5)
        uncertainty += complexity * 0.3

        # 基于历史错误率
        uncertainty += self._metrics.error_rate * 0.4

        # 基于相似任务的准确性
        similar_accuracy = context.get("similar_task_accuracy", 0.8)
        uncertainty += (1 - similar_accuracy) * 0.3

        return min(1.0, uncertainty)

    def calibrate_confidence(self, prediction: Any, actual: Any) -> float:
        """
        校准置信度

        Args:
            prediction: 预测结果
            actual: 实际结果

        Returns:
            校准后的置信度
        """
        with self._lock:
            if not self.calibration_enabled:
                return 0.5

            # 判断是否正确
            is_correct = self._check_correctness(prediction, actual)

            # 记录样本
            current_confidence = self._get_current_confidence(prediction)
            self._calibration_samples.append((current_confidence, 1.0 if is_correct else 0.0))

            # 更新校准模型
            if len(self._calibration_samples) >= 10:
                self._update_calibration_model()

            # 计算校准得分
            calibration = self._compute_calibration_score()
            self._metrics.confidence_calibration = calibration

            return calibration

    def _check_correctness(self, prediction: Any, actual: Any) -> bool:
        """检查预测是否正确"""
        if prediction == actual:
            return True
        if isinstance(prediction, (int, float)) and isinstance(actual, (int, float)):
            return abs(prediction - actual) < 0.01
        if isinstance(prediction, str) and isinstance(actual, str):
            return prediction.lower().strip() == actual.lower().strip()
        return False

    def _get_current_confidence(self, prediction: Any) -> float:
        """获取当前预测的置信度"""
        # 简化实现
        return 0.7

    def _update_calibration_model(self):
        """更新校准模型（线性回归）"""
        samples = list(self._calibration_samples)
        confidences = [s[0] for s in samples]
        outcomes = [s[1] for s in samples]

        if len(set(outcomes)) < 2:
            return

        # 简单线性回归
        mean_c = np.mean(confidences)
        mean_o = np.mean(outcomes)

        slope = np.sum((np.array(confidences) - mean_c) * (np.array(outcomes) - mean_o))
        slope /= (np.sum((np.array(confidences) - mean_c) ** 2) + 1e-8)

        intercept = mean_o - slope * mean_c

        # 更新模型
        self._calibration_model["slope"] = self._calibration_model["slope"] * (1 - self.CALIBRATION_LEARNING_RATE) + slope * self.CALIBRATION_LEARNING_RATE
        self._calibration_model["intercept"] = self._calibration_model["intercept"] * (1 - self.CALIBRATION_LEARNING_RATE) + intercept * self.CALIBRATION_LEARNING_RATE

    def _compute_calibration_score(self) -> float:
        """计算校准得分"""
        if not self._calibration_samples:
            return 1.0

        total_error = 0.0
        for confidence, outcome in self._calibration_samples:
            predicted = confidence
            error = abs(predicted - outcome)
            total_error += error

        return 1.0 - (total_error / len(self._calibration_samples))

    # ==================== 策略选择 ====================

    def select_strategy(
        self,
        task_complexity: float,
        time_constraint: float,
        risk_tolerance: float,
        context: Dict[str, Any]
    ) -> StrategySelection:
        """
        选择最佳策略

        Args:
            task_complexity: 任务复杂度 (0-1)
            time_constraint: 时间约束 (0-1, 越高越紧急)
            risk_tolerance: 风险容忍度 (0-1)
            context: 上下文

        Returns:
            策略选择结果
        """
        with self._lock:
            # 评估每种策略
            strategy_scores = {}

            # 谨慎策略
            if task_complexity > 0.7:
                strategy_scores[StrategyType.CAUTIOUS] = 0.9
            else:
                strategy_scores[StrategyType.CAUTIOUS] = 0.5

            # 激进策略
            if risk_tolerance > 0.7 and time_constraint > 0.8:
                strategy_scores[StrategyType.BOLD] = 0.8
            else:
                strategy_scores[StrategyType.BOLD] = 0.3

            # 探索策略
            if context.get("exploration_needed", False):
                strategy_scores[StrategyType.EXPLORATORY] = 0.85
            else:
                strategy_scores[StrategyType.EXPLORATORY] = 0.4

            # 利用策略
            if context.get("known_solution", False):
                strategy_scores[StrategyType.EXPLOITATIVE] = 0.9
            else:
                strategy_scores[StrategyType.EXPLOITATIVE] = 0.4

            # 自适应策略（考虑当前状态）
            state_factor = 1.0
            if self._current_state == CognitiveState.OPTIMAL:
                state_factor = 1.2
            elif self._current_state == CognitiveState.DEGRADED:
                state_factor = 0.7

            strategy_scores[StrategyType.ADAPTIVE] = 0.8 * state_factor

            # 加入历史表现
            for strategy in strategy_scores:
                if strategy in self._strategy_scores:
                    strategy_scores[strategy] *= (0.7 + 0.3 * self._strategy_scores[strategy])

            # 选择最佳策略
            best = max(strategy_scores.items(), key=lambda x: x[1])

            # 排序
            alternatives = sorted(strategy_scores.items(), key=lambda x: x[1], reverse=True)

            return StrategySelection(
                selected_strategy=best[0],
                alternatives=[(s, sc) for s, sc in alternatives if s != best[0]],
                reasoning=f"任务复杂度={task_complexity}, 时间约束={time_constraint}, 当前状态={self._current_state.value}",
                expected_outcome=best[1],
                risk_level=1 - risk_tolerance
            )

    # ==================== 错误检测 ====================

    def detect_errors(
        self,
        reasoning_chain: List[Dict[str, Any]],
        output: Any
    ) -> List[DetectedError]:
        """
        检测推理错误

        Args:
            reasoning_chain: 推理链
            output: 输出结果

        Returns:
            检测到的错误列表
        """
        if not self.error_detection_enabled:
            return []

        with self._lock:
            errors = []

            # 使用各种检测器
            for error_type, detector in self._error_patterns.items():
                detected = detector(reasoning_chain, output)
                if detected:
                    errors.extend(detected)

            # 记录错误
            for error in errors:
                self._error_history.append(error)

            return errors

    def _detect_logic_flaw(self, chain: List[Dict], output: Any) -> List[DetectedError]:
        """检测逻辑缺陷"""
        errors = []

        for i, step in enumerate(chain):
            if "conclusion" in step and "premises" in step:
                # 检查前提是否支持结论
                if not step.get("evidence"):
                    error = DetectedError(
                        id=f"logic_{i}_{len(self._error_history)}",
                        error_type=ErrorType.LOGIC_FLAW,
                        description=f"步骤 {i} 缺乏证据支持",
                        severity=0.6,
                        location={"step": i, "type": "missing_evidence"},
                        evidence=[]
                    )
                    errors.append(error)

        return errors

    def _detect_premise_error(self, chain: List[Dict], output: Any) -> List[DetectedError]:
        """检测前提错误"""
        errors = []

        for i, step in enumerate(chain):
            premises = step.get("premises", [])
            for j, premise in enumerate(premises):
                # 检查前提是否可疑
                if "可能" in premise or "也许" in premise:
                    error = DetectedError(
                        id=f"premise_{i}_{j}_{len(self._error_history)}",
                        error_type=ErrorType.PREMISE_ERROR,
                        description=f"步骤 {i} 前提不确定: {premise}",
                        severity=0.4,
                        location={"step": i, "premise_index": j},
                        evidence=[premise]
                    )
                    errors.append(error)

        return errors

    def _detect_bias(self, chain: List[Dict], output: Any) -> List[DetectedError]:
        """检测偏见"""
        errors = []

        # 检查常见的偏见模式
        bias_keywords = ["显然", "必然", "所有人都知道", "毫无疑问"]

        for i, step in enumerate(chain):
            desc = step.get("description", "")
            for keyword in bias_keywords:
                if keyword in desc:
                    error = DetectedError(
                        id=f"bias_{i}_{len(self._error_history)}",
                        error_type=ErrorType.BIAS,
                        description=f"检测到可能的偏见: {keyword}",
                        severity=0.5,
                        location={"step": i, "keyword": keyword},
                        evidence=[desc]
                    )
                    errors.append(error)

        return errors

    def _detect_overconfidence(self, chain: List[Dict], output: Any) -> List[DetectedError]:
        """检测过度自信"""
        errors = []

        # 检查置信度
        for i, step in enumerate(chain):
            confidence = step.get("confidence", 0.5)
            if confidence > 0.95:
                error = DetectedError(
                    id=f"overconf_{i}_{len(self._error_history)}",
                    error_type=ErrorType.OVERCONFIDENCE,
                    description=f"步骤 {i} 过度自信: {confidence}",
                    severity=0.3,
                    location={"step": i},
                    evidence=[f"confidence={confidence}"]
                )
                errors.append(error)

        return errors

    def _detect_underconfidence(self, chain: List[Dict], output: Any) -> List[DetectedError]:
        """检测缺乏自信"""
        errors = []

        for i, step in enumerate(chain):
            confidence = step.get("confidence", 0.5)
            if confidence < 0.3:
                error = DetectedError(
                    id=f"underconf_{i}_{len(self._error_history)}",
                    error_type=ErrorType.UNDERCONFIDENCE,
                    description=f"步骤 {i} 缺乏自信: {confidence}",
                    severity=0.2,
                    location={"step": i},
                    evidence=[f"confidence={confidence}"]
                )
                errors.append(error)

        return errors

    def _detect_inference_error(self, chain: List[Dict], output: Any) -> List[DetectedError]:
        """检测推理错误"""
        errors = []

        # 检查推理链的连贯性
        for i in range(len(chain) - 1):
            current = chain[i].get("conclusion", "")
            next_premises = chain[i + 1].get("premises", [])

            # 简单检查：下一 Premises 是否包含上一结论
            if current and current not in str(next_premises):
                error = DetectedError(
                    id=f"inference_{i}_{len(self._error_history)}",
                    error_type=ErrorType.INFERENCE_ERROR,
                    description=f"推理链不连贯: 步骤 {i} 的结论未在步骤 {i+1} 中使用",
                    severity=0.5,
                    location={"from_step": i, "to_step": i + 1},
                    evidence=[current]
                )
                errors.append(error)

        return errors

    def _detect_memory_error(self, chain: List[Dict], output: Any) -> List[DetectedError]:
        """检测记忆错误"""
        errors = []

        # 检查与历史输出的一致性
        if self._prediction_history:
            last_prediction = self._prediction_history[-1][0]
            if last_prediction != output:
                similarity = self._compute_similarity(last_prediction, output)
                if similarity > 0.9:
                    # 可能是记忆错误：与上次输出过于相似
                    error = DetectedError(
                        id=f"memory_{len(self._error_history)}",
                        error_type=ErrorType.MEMORY_ERROR,
                        description="输出与上次过于相似，可能存在记忆干扰",
                        severity=0.4,
                        location={"index": len(self._prediction_history)},
                        evidence=[str(last_prediction)[:100]]
                    )
                    errors.append(error)

        return errors

    def _compute_similarity(self, a: Any, b: Any) -> float:
        """计算相似度"""
        a_str = str(a).lower()
        b_str = str(b).lower()

        if a_str == b_str:
            return 1.0

        # 简单词重叠
        a_words = set(a_str.split())
        b_words = set(b_str.split())

        if not a_words or not b_words:
            return 0.0

        overlap = len(a_words & b_words)
        return overlap / min(len(a_words), len(b_words))

    # ==================== 自我修正 ====================

    def self_correct(
        self,
        errors: List[DetectedError],
        reasoning_chain: List[Dict],
        output: Any
    ) -> Tuple[Any, List[CorrectionAction]]:
        """
        自我修正

        Args:
            errors: 检测到的错误
            reasoning_chain: 推理链
            output: 当前输出

        Returns:
            (修正后的输出, 修正行动列表)
        """
        if not self.self_correction_enabled:
            return output, []

        with self._lock:
            corrections = []
            corrected_output = output

            for error in errors:
                action = self._apply_correction(error, reasoning_chain, corrected_output)
                corrections.append(action)

                if action.executed and action.result:
                    # 应用修正
                    corrected_output = self._apply_output_correction(error, corrected_output)

                self._correction_history.append(action)

            # 更新策略得分
            self._update_strategy_scores(corrections)

            return corrected_output, corrections

    def _apply_correction(
        self,
        error: DetectedError,
        chain: List[Dict],
        output: Any
    ) -> CorrectionAction:
        """应用修正"""
        action = CorrectionAction(
            error_id=error.id,
            action_type="unknown",
            description="",
            success_probability=0.5
        )

        # 根据错误类型选择修正方法
        if error.error_type == ErrorType.LOGIC_FLAW:
            action.action_type = "add_evidence"
            action.description = "添加更多证据支持结论"
            action.success_probability = 0.7

        elif error.error_type == ErrorType.PREMISE_ERROR:
            action.action_type = "verify_premise"
            action.description = "验证并修正前提"
            action.success_probability = 0.8

        elif error.error_type == ErrorType.BIAS:
            action.action_type = "reframe"
            action.description = "重新框架化表述"
            action.success_probability = 0.6

        elif error.error_type == ErrorType.OVERCONFIDENCE:
            action.action_type = "lower_confidence"
            action.description = "降低置信度"
            action.success_probability = 0.9

        elif error.error_type == ErrorType.UNDERCONFIDENCE:
            action.action_type = "raise_confidence"
            action.description = "提高置信度"
            action.success_probability = 0.9

        elif error.error_type == ErrorType.INFERENCE_ERROR:
            action.action_type = "fix_chain"
            action.description = "修复推理链"
            action.success_probability = 0.5

        elif error.error_type == ErrorType.MEMORY_ERROR:
            action.action_type = "regenerate"
            action.description = "重新生成输出"
            action.success_probability = 0.7

        # 执行修正
        action.executed = True
        action.result = np.random.random() < action.success_probability

        return action

    def _apply_output_correction(self, error: DetectedError, output: Any) -> Any:
        """应用输出修正"""
        # 简单实现：根据错误类型修改输出
        if isinstance(output, dict):
            corrected = output.copy()
            corrected["_corrected"] = True
            corrected["_correction_type"] = error.error_type.value
            return corrected

        return {"original": output, "corrected": True, "type": error.error_type.value}

    def _update_strategy_scores(self, corrections: List[CorrectionAction]):
        """更新策略得分"""
        if not corrections:
            return

        # 基于修正成功率更新
        success_rate = sum(1 for c in corrections if c.result) / len(corrections)

        # 调整策略
        if success_rate > 0.7:
            # 做得好，增加探索
            self._strategy_scores[StrategyType.EXPLORATORY] *= 1.1
        elif success_rate < 0.3:
            # 做得差，减少冒险
            self._strategy_scores[StrategyType.BOLD] *= 0.9

        # 归一化
        total = sum(self._strategy_scores.values())
        for strategy in self._strategy_scores:
            self._strategy_scores[strategy] /= total

    # ==================== 自我评估 ====================

    def self_assess(self) -> SelfAssessment:
        """
        自我评估

        Returns:
            自我评估报告
        """
        with self._lock:
            strengths = []
            weaknesses = []
            improvements = []
            recommendations = []

            # 分析指标
            if self._metrics.coherence_score > 0.8:
                strengths.append("推理连贯性好")
            else:
                weaknesses.append("推理连贯性需要改进")

            if self._metrics.confidence_calibration > 0.8:
                strengths.append("置信度校准准确")
            else:
                weaknesses.append("置信度估计不够准确")
                improvements.append("增加校准样本")
                recommendations.append("使用更多的验证数据")

            if self._metrics.accuracy_rate > 0.85:
                strengths.append("历史准确率高")
            else:
                weaknesses.append("准确率有待提升")

            if self._metrics.error_rate < 0.1:
                strengths.append("错误率低")
            else:
                improvements.append("降低错误率")
                recommendations.append("启用更严格的错误检测")

            # 生成建议
            if not recommendations:
                recommendations.append("保持当前状态")

            return SelfAssessment(
                cognitive_state=self._current_state,
                overall_confidence=self._metrics.confidence_calibration,
                strengths=strengths,
                weaknesses=weaknesses,
                improvement_areas=improvements,
                recommendations=recommendations
            )

    # ==================== 历史记录 ====================

    def record_prediction(self, prediction: Any, actual: Any, confidence: float):
        """记录预测结果"""
        self._prediction_history.append((prediction, actual, confidence))

    def get_history_summary(self) -> Dict[str, Any]:
        """获取历史摘要"""
        return {
            "total_predictions": len(self._prediction_history),
            "total_errors": len(self._error_history),
            "total_corrections": len(self._correction_history),
            "current_state": self._current_state.value,
            "calibration_score": self._metrics.confidence_calibration,
            "accuracy_rate": self._metrics.accuracy_rate
        }

    def __repr__(self) -> str:
        return f"MetaCognition(state={self._current_state.value}, accuracy={self._metrics.accuracy_rate:.2f}, calibration={self._metrics.confidence_calibration:.2f})"
