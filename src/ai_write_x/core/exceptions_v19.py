"""
V19认知异常处理 - 类人的错误应对
├── 认知失调检测: 识别逻辑不一致
├── 错误归因: 分析错误根本原因
├── 策略重选: 失败后更换认知策略
├── 经验学习: 从错误中学习的机制
├── 预防性回避: 基于历史避免已知陷阱
└── 优雅降级: 保持核心功能的降级模式
"""

import numpy as np
from typing import Dict, List, Optional, Any, Tuple, Set, Callable, Union
from dataclasses import dataclass, field
from datetime import datetime, timedelta
from enum import Enum, auto
from collections import defaultdict, deque
import traceback
import threading
import time
import random
import json


class CognitiveErrorType(Enum):
    """认知错误类型"""
    PERCEPTION = "perception"           # 感知错误
    MEMORY = "memory"                   # 记忆错误
    REASONING = "reasoning"             # 推理错误
    DECISION = "decision"               # 决策错误
    ATTRIBUTION = "attribution"          # 归因错误
    CONSISTENCY = "consistency"         # 一致性错误
    PREDICTION = "prediction"           # 预测错误
    LEARNING = "learning"                # 学习错误
    STRATEGY = "strategy"               # 策略错误
    EXECUTION = "execution"             # 执行错误


class ErrorSeverity(Enum):
    """错误严重程度"""
    MINOR = 0.2      # 轻微
    MODERATE = 0.5   # 中等
    MAJOR = 0.7      # 重要
    CRITICAL = 1.0   # 关键


class StrategyType(Enum):
    """策略类型"""
    HEURISTIC = "heuristic"             # 启发式
    ANALYTICAL = "analytical"           # 分析式
    INTUITIVE = "intuitive"             # 直觉式
    CREATIVE = "creative"               # 创造性
    CONSERVATIVE = "conservative"       # 保守式
    ADAPTIVE = "adaptive"               # 自适应


class RecoveryAction(Enum):
    """恢复动作"""
    RETRY = "retry"                     # 重试
    FALLBACK = "fallback"               # 回退
    SUBSTITUTE = "substitute"           # 替代
    DECOMPOSE = "decompose"             # 分解
    SIMPLIFY = "simplify"               # 简化
    ESCALATE = "escalate"               # 升级
    ABORT = "abort"                     # 中止
    IGNORE = "ignore"                   # 忽略


class DegradationLevel(Enum):
    """降级级别"""
    FULL = "full"                       # 完全功能
    REDUCED = "reduced"                 # 降级功能
    MINIMAL = "minimal"                 # 最小功能
    EMERGENCY = "emergency"            # 紧急模式
    FAILSAFE = "failsafe"               # 安全失效


@dataclass
class CognitiveError:
    """认知错误"""
    id: str
    error_type: CognitiveErrorType
    severity: ErrorSeverity
    timestamp: datetime
    description: str
    context: Dict[str, Any] = field(default_factory=dict)
    stack_trace: Optional[str] = None
    previous_errors: List[str] = field(default_factory=list)
    resolved: bool = False
    resolution: Optional[str] = None


@dataclass
class CognitiveDissonance:
    """认知失调"""
    id: str
    description: str
    conflicting_beliefs: List[str] = field(default_factory=list)
    tension_level: float = 0.0          # 紧张程度 0-1
    detected_at: datetime
    resolution_strategy: Optional[str] = None
    resolved: bool = False


@dataclass
class ErrorAttribution:
    """错误归因"""
    error_id: str
    root_cause: str                      # 根本原因
    cause_category: str                 # 原因类别
    confidence: float                   # 置信度
    contributing_factors: List[str] = field(default_factory=list)
    external_blame: float = 0.0         # 外部归因程度
    internal_blame: float = 0.0         # 内部归因程度


@dataclass
class StrategyAttempt:
    """策略尝试"""
    id: str
    strategy_type: StrategyType
    success: bool
    outcome: Any = None
    error: Optional[str] = None
    execution_time: float = 0.0
    resource_usage: float = 0.0
    timestamp: datetime = field(default_factory=datetime.now)


@dataclass
class LearnedExperience:
    """学习经验"""
    id: str
    situation: str                      # 情境描述
    action_taken: str                   # 采取的行动
    outcome: str                        # 结果
    lesson: str                         # 学到的教训
    success: bool                       # 是否成功
    applicability: float = 1.0          # 适用性
    times_applied: int = 0
    last_applied: Optional[datetime] = None
    created_at: datetime = field(default_factory=datetime.now)


@dataclass
class AvoidancePattern:
    """回避模式"""
    id: str
    trigger_situation: str              # 触发情境
    description: str                    # 描述
    failure_history: List[str] = field(default_factory=list)
    success_count: int = 0
    avoidance_strength: float = 0.0    # 回避强度
    created_at: datetime = field(default_factory=datetime.now)
    last_triggered: Optional[datetime] = None


@dataclass
class RecoveryPlan:
    """恢复计划"""
    id: str
    error_id: str
    primary_action: RecoveryAction
    fallback_actions: List[RecoveryAction] = field(default_factory=list)
    target_state: str = ""
    estimated_success_rate: float = 0.5
    resource_requirements: Dict[str, Any] = field(default_factory=dict)
    executed: bool = False
    execution_result: Optional[str] = None


@dataclass
class SystemState:
    """系统状态"""
    degradation_level: DegradationLevel
    active_strategies: List[StrategyType] = field(default_factory=list)
    error_rate: float = 0.0
    success_rate: float = 1.0
    available_resources: Dict[str, float] = field(default_factory=dict)
    last_error: Optional[str] = None
    uptime: float = 0.0


class CognitiveExceptionHandler:
    """
    V19认知异常处理系统

    实现类人的错误应对机制:
    1. 认知失调检测: 识别逻辑不一致
    2. 错误归因: 分析错误根本原因
    3. 策略重选: 失败后更换认知策略
    4. 经验学习: 从错误中学习的机制
    5. 预防性回避: 基于历史避免已知陷阱
    6. 优雅降级: 保持核心功能的降级模式
    """

    # 参数
    MAX_ERROR_HISTORY = 1000
    MAX_EXPERIENCES = 500
    MAX_AVOIDANCE_PATTERNS = 100
    DISSONANCE_THRESHOLD = 0.7
    STRATEGY_SWITCH_THRESHOLD = 3
    DEGRADATION_THRESHOLD = 0.3

    def __init__(
        self,
        enable_dissonance: bool = True,
        enable_attribution: bool = True,
        enable_learning: bool = True,
        enable_avoidance: bool = True,
        enable_degradation: bool = True
    ):
        """
        初始化认知异常处理器

        Args:
            enable_dissonance: 启用认知失调检测
            enable_attribution: 启用错误归因
            enable_learning: 启用经验学习
            enable_avoidance: 启用预防性回避
            enable_degradation: 启用优雅降级
        """
        self.enable_dissonance = enable_dissonance
        self.enable_attribution = enable_attribution
        self.enable_learning = enable_learning
        self.enable_avoidance = enable_avoidance
        self.enable_degradation = enable_degradation

        # 错误历史
        self._errors: Dict[str, CognitiveError] = {}
        self._error_counter = 0

        # 认知失调
        self._dissonances: Dict[str, CognitiveDissonance] = {}
        self._dissonance_counter = 0

        # 错误归因
        self._attributions: Dict[str, ErrorAttribution] = {}

        # 策略历史
        self._strategy_history: deque = deque(maxlen=100)
        self._current_strategy = StrategyType.ANALYTICAL
        self._strategy_attempts: Dict[StrategyType, List[StrategyAttempt]] = defaultdict(list)
        self._failed_strategies: Set[StrategyType] = set()

        # 学习经验
        self._experiences: Dict[str, LearnedExperience] = {}
        self._experience_counter = 0

        # 回避模式
        self._avoidance_patterns: Dict[str, AvoidancePattern] = {}
        self._avoidance_counter = 0

        # 恢复计划
        self._recovery_plans: Dict[str, RecoveryPlan] = {}
        self._recovery_counter = 0

        # 系统状态
        self._system_state = SystemState(
            degradation_level=DegradationLevel.FULL,
            active_strategies=[StrategyType.ANALYTICAL],
            error_rate=0.0,
            success_rate=1.0,
            available_resources={"cpu": 1.0, "memory": 1.0, "time": 1.0}
        )

        # 统计
        self._statistics = {
            "total_errors": 0,
            "errors_resolved": 0,
            "dissonances_detected": 0,
            "dissonances_resolved": 0,
            "strategies_switched": 0,
            "experiences_learned": 0,
            "avoidances_triggered": 0,
            "recoveries_successful": 0,
            "degradations_triggered": 0
        }

        # 线程安全
        self._lock = threading.RLock()

        # 启动时间
        self._start_time = time.time()

    # ==================== 错误记录 ====================

    def record_error(
        self,
        error_type: CognitiveErrorType,
        severity: ErrorSeverity,
        description: str,
        context: Optional[Dict[str, Any]] = None,
        exception: Optional[Exception] = None
    ) -> str:
        """
        记录错误

        Args:
            error_type: 错误类型
            severity: 严重程度
            description: 描述
            context: 上下文
            exception: 异常对象

        Returns:
            错误ID
        """
        with self._lock:
            error_id = f"err_{self._error_counter}"
            self._error_counter += 1

            # 获取堆栈跟踪
            stack_trace = None
            if exception:
                stack_trace = traceback.format_exc()

            # 检查连续错误
            previous_errors = []
            if self._errors:
                recent = list(self._errors.values())[-3:]
                for err in recent:
                    if not err.resolved:
                        previous_errors.append(err.id)

            error = CognitiveError(
                id=error_id,
                error_type=error_type,
                severity=severity,
                timestamp=datetime.now(),
                description=description,
                context=context or {},
                stack_trace=stack_trace,
                previous_errors=previous_errors
            )

            self._errors[error_id] = error

            # 更新统计
            self._statistics["total_errors"] += 1

            # 更新系统状态
            self._update_error_rate()

            # 触发处理流程
            self._handle_error(error)

            return error_id

    def _update_error_rate(self):
        """更新错误率"""
        uptime = time.time() - self._start_time
        if uptime > 0:
            recent_errors = sum(
                1 for e in self._errors.values()
                if (datetime.now() - e.timestamp).total_seconds() < 300
            )
            self._system_state.error_rate = recent_errors / max(uptime / 60, 1)
            self._system_state.success_rate = 1.0 - self._system_state.error_rate
            self._system_state.uptime = uptime

        self._system_state.last_error = list(self._errors.keys())[-1] if self._errors else None

    # ==================== 认知失调检测 ====================

    def detect_dissonance(
        self,
        belief1: str,
        belief2: str,
        tension_level: float = 0.5
    ) -> Optional[str]:
        """
        检测认知失调

        Args:
            belief1: 信念1
            belief2: 信念2（冲突）
            tension_level: 紧张程度

        Returns:
            失调ID
        """
        if not self.enable_dissonance:
            return None

        with self._lock:
            # 检查是否已有类似的失调
            for dissonance in self._dissonances.values():
                if (belief1 in dissonance.conflicting_beliefs or 
                    belief2 in dissonance.conflicting_beliefs):
                    # 更新紧张程度
                    dissonance.tension_level = max(dissonance.tension_level, tension_level)
                    return dissonance.id

            # 创建新失调
            dissonance_id = f"dis_{self._dissonance_counter}"
            self._dissonance_counter += 1

            dissonance = CognitiveDissonance(
                id=dissonance_id,
                description=f"信念冲突: {belief1} vs {belief2}",
                conflicting_beliefs=[belief1, belief2],
                tension_level=tension_level,
                detected_at=datetime.now()
            )

            self._dissonances[dissonance_id] = dissonance
            self._statistics["dissonances_detected"] += 1

            # 高紧张程度时触发解决
            if tension_level >= self.DISSONANCE_THRESHOLD:
                self._resolve_dissonance(dissonance_id)

            return dissonance_id

    def _resolve_dissonance(self, dissonance_id: str):
        """解决认知失调"""
        if dissonance_id not in self._dissonances:
            return

        dissonance = self._dissonances[dissonance_id]

        # 策略1: 改变信念
        # 策略2: 添加新信念
        # 策略3: 最小化重要性
        resolution_strategies = [
            "改变信念",
            "添加调和信念",
            "降低重要性",
            "寻求支持证据",
            "回避冲突信息"
        ]

        chosen = random.choice(resolution_strategies)
        dissonance.resolution_strategy = chosen
        dissonance.resolved = True
        self._statistics["dissonances_resolved"] += 1

    # ==================== 错误归因 ====================

    def attribute_error(self, error_id: str) -> Optional[ErrorAttribution]:
        """
        归因错误

        Args:
            error_id: 错误ID

        Returns:
            归因结果
        """
        if not self.enable_attribution:
            return None

        with self._lock:
            if error_id not in self._errors:
                return None

            error = self._errors[error_id]

            # 归因分析
            root_cause, category = self._analyze_root_cause(error)

            # 计算归因
            internal_blame = self._calculate_internal_blame(error)
            external_blame = 1.0 - internal_blame

            attribution = ErrorAttribution(
                error_id=error_id,
                root_cause=root_cause,
                cause_category=category,
                confidence=0.7,
                contributing_factors=self._identify_contributing_factors(error),
                internal_blame=internal_blame,
                external_blame=external_blame
            )

            self._attributions[error_id] = attribution

            # 记录学习经验
            if self.enable_learning:
                self._learn_from_error(error, attribution)

            return attribution

    def _analyze_root_cause(
        self,
        error: CognitiveError
    ) -> Tuple[str, str]:
        """分析根本原因"""
        context = error.context

        # 基于错误类型分析
        if error.error_type == CognitiveErrorType.PERCEPTION:
            return ("感知信息不完整或误解", "information")
        elif error.error_type == CognitiveErrorType.REASONING:
            return ("推理过程存在逻辑缺陷", "process")
        elif error.error_type == CognitiveErrorType.DECISION:
            return ("决策依据不足或偏差", "decision")
        elif error.error_type == CognitiveErrorType.MEMORY:
            return ("记忆提取错误或混淆", "memory")
        elif error.error_type == CognitiveErrorType.PREDICTION:
            return ("预测模型不准确", "model")
        else:
            # 基于上下文分析
            if "resource" in context:
                return ("资源不足导致失败", "resource")
            elif "timeout" in context:
                return ("时间限制导致不完整", "time")
            elif "data" in context:
                return ("数据质量问题", "data")
            else:
                return ("未知原因", "unknown")

    def _calculate_internal_blame(self, error: CognitiveError) -> float:
        """计算内部归因程度"""
        # 简化：基于错误严重程度
        base_blame = error.severity.value * 0.5

        # 考虑历史错误
        if len(error.previous_errors) > 2:
            base_blame += 0.2

        return min(1.0, base_blame)

    def _identify_contributing_factors(
        self,
        error: CognitiveError
    ) -> List[str]:
        """识别贡献因素"""
        factors = []

        context = error.context

        if "experience" in context and context["experience"] < 3:
            factors.append("经验不足")

        if "time_pressure" in context and context["time_pressure"]:
            factors.append("时间压力")

        if "complexity" in context and context["complexity"] > 0.7:
            factors.append("任务复杂度高")

        if len(error.previous_errors) > 0:
            factors.append("历史错误累积")

        return factors

    # ==================== 策略重选 ====================

    def attempt_strategy(
        self,
        strategy_type: StrategyType,
        action: Callable,
        *args,
        **kwargs
    ) -> Tuple[bool, Any]:
        """
        尝试策略

        Args:
            strategy_type: 策略类型
            action: 执行动作
            args, kwargs: 动作参数

        Returns:
            (成功标志, 结果)
        """
        with self._lock:
            # 检查是否应该回避
            if self.enable_avoidance:
                situation_key = f"{strategy_type.value}_attempt"
                if self._should_avoid(situation_key):
                    # 尝试替代策略
                    alternative = self._get_alternative_strategy(strategy_type)
                    if alternative:
                        strategy_type = alternative

            attempt_id = f"attempt_{len(self._strategy_history)}"
            start_time = time.time()

            try:
                # 记录尝试
                attempt = StrategyAttempt(
                    id=attempt_id,
                    strategy_type=strategy_type,
                    success=False,
                    timestamp=datetime.now()
                )

                # 执行
                result = action(*args, **kwargs)

                # 成功
                attempt.success = True
                attempt.outcome = result
                attempt.execution_time = time.time() - start_time

                # 更新当前策略
                self._current_strategy = strategy_type

                if strategy_type not in self._system_state.active_strategies:
                    self._system_state.active_strategies.append(strategy_type)

                # 记录成功经验
                if self.enable_learning:
                    self._record_strategy_success(strategy_type, result)

                self._strategy_history.append(attempt)
                self._strategy_attempts[strategy_type].append(attempt)

                return True, result

            except Exception as e:
                # 失败
                attempt.success = False
                attempt.error = str(e)
                attempt.execution_time = time.time() - start_time

                self._strategy_history.append(attempt)
                self._strategy_attempts[strategy_type].append(attempt)

                # 检查是否需要切换策略
                self._check_strategy_switch(strategy_type)

                return False, None

    def _check_strategy_switch(self, failed_strategy: StrategyType):
        """检查是否需要切换策略"""
        # 记录失败
        self._failed_strategies.add(failed_strategy)

        # 统计失败次数
        recent_failures = sum(
            1 for attempt in self._strategy_attempts[failed_strategy][-5:]
            if not attempt.success
        )

        # 连续失败阈值
        if recent_failures >= self.STRATEGY_SWITCH_THRESHOLD:
            # 切换到新策略
            new_strategy = self._select_new_strategy()
            if new_strategy and new_strategy != self._current_strategy:
                self._current_strategy = new_strategy
                self._statistics["strategies_switched"] += 1

                # 创建回避模式
                if self.enable_avoidance:
                    self._create_avoidance_pattern(
                        f"{failed_strategy.value}_recurrent_failure",
                        f"策略{failed_strategy.value}持续失败"
                    )

    def _select_new_strategy(self) -> Optional[StrategyType]:
        """选择新策略"""
        # 可用的策略
        available = [s for s in StrategyType if s not in self._failed_strategies]

        if not available:
            # 重置失败记录
            self._failed_strategies.clear()
            available = list(StrategyType)

        # 根据当前系统状态选择
        if self._system_state.degradation_level != DegradationLevel.FULL:
            # 降级模式：使用保守策略
            return StrategyType.CONSERVATIVE

        # 基于学习经验选择
        best_from_experience = self._get_best_strategy_from_experience()
        if best_from_experience:
            return best_from_experience

        return random.choice(available) if available else None

    def _get_best_strategy_from_experience(self) -> Optional[StrategyType]:
        """从经验中获取最佳策略"""
        if not self._experiences:
            return None

        # 找最成功的经验
        successful = [
            e for e in self._experiences.values()
            if e.success and e.applicability > 0.7
        ]

        if not successful:
            return None

        # 简化：随机返回一个成功过的策略
        return random.choice([
            StrategyType.HEURISTIC,
            StrategyType.ANALYTICAL,
            StrategyType.ADAPTIVE
        ])

    def _get_alternative_strategy(
        self,
        original: StrategyType
    ) -> Optional[StrategyType]:
        """获取替代策略"""
        # 简单替代映射
        alternatives = {
            StrategyType.CREATIVE: StrategyType.CONSERVATIVE,
            StrategyType.INTUITIVE: StrategyType.ANALYTICAL,
            StrategyType.HEURISTIC: StrategyType.ANALYTICAL
        }

        return alternatives.get(original)

    # ==================== 经验学习 ====================

    def _learn_from_error(
        self,
        error: CognitiveError,
        attribution: ErrorAttribution
    ):
        """从错误中学习"""
        experience_id = f"exp_{self._experience_counter}"
        self._experience_counter += 1

        # 提取教训
        lesson = self._extract_lesson(error, attribution)

        experience = LearnedExperience(
            id=experience_id,
            situation=str(error.error_type.value),
            action_taken=attribution.cause_category,
            outcome="失败",
            lesson=lesson,
            success=False,
            applicability=1.0 - attribution.external_blame
        )

        self._experiences[experience_id] = experience
        self._statistics["experiences_learned"] += 1

    def _record_strategy_success(
        self,
        strategy: StrategyType,
        outcome: Any
    ):
        """记录策略成功"""
        experience_id = f"exp_{self._experience_counter}"
        self._experience_counter += 1

        experience = LearnedExperience(
            id=experience_id,
            situation=f"策略{strategy.value}",
            action_taken=strategy.value,
            outcome="成功",
            lesson=f"策略{strategy.value}在此情境下有效",
            success=True,
            applicability=0.8
        )

        self._experiences[experience_id] = experience
        self._statistics["experiences_learned"] += 1

    def _extract_lesson(
        self,
        error: CognitiveError,
        attribution: ErrorAttribution
    ) -> str:
        """提取教训"""
        lessons = []

        # 基于归因
        if attribution.internal_blame > 0.5:
            lessons.append("需要改进内部认知过程")
        if attribution.internal_blame < 0.3:
            lessons.append("需要更多外部信息支持")

        # 基于因素
        for factor in attribution.contributing_factors:
            if "经验" in factor:
                lessons.append("增加相关经验")
            elif "时间" in factor:
                lessons.append("预留更多时间")
            elif "复杂" in factor:
                lessons.append("简化任务或分步执行")

        return "; ".join(lessons) if lessons else "需要进一步分析"

    def get_applicable_experience(
        self,
        situation: str
    ) -> Optional[LearnedExperience]:
        """获取适用经验"""
        applicable = [
            e for e in self._experiences.values()
            if situation in e.situation and e.applicability > 0.5
        ]

        if not applicable:
            return None

        # 返回最成功的
        best = max(applicable, key=lambda e: (e.success, e.applicability))
        best.times_applied += 1
        best.last_applied = datetime.now()

        return best

    # ==================== 预防性回避 ====================

    def _create_avoidance_pattern(
        self,
        trigger: str,
        description: str
    ):
        """创建回避模式"""
        pattern_id = f"avoid_{self._avoidance_counter}"
        self._avoidance_counter += 1

        pattern = AvoidancePattern(
            id=pattern_id,
            trigger_situation=trigger,
            description=description,
            avoidance_strength=0.8
        )

        self._avoidance_patterns[pattern_id] = pattern

    def _should_avoid(self, situation: str) -> bool:
        """检查是否应该回避"""
        for pattern in self._avoidance_patterns.values():
            if situation in pattern.trigger_situation:
                if pattern.avoidance_strength > 0.6:
                    pattern.last_triggered = datetime.now()
                    self._statistics["avoidances_triggered"] += 1
                    return True

        return False

    def trigger_avoidance(self, situation: str) -> bool:
        """
        触发回避

        Args:
            situation: 情境描述

        Returns:
            是否触发回避
        """
        if not self.enable_avoidance:
            return False

        with self._lock:
            return self._should_avoid(situation)

    # ==================== 优雅降级 ====================

    def check_degradation(self) -> DegradationLevel:
        """检查是否需要降级"""
        if not self.enable_degradation:
            return DegradationLevel.FULL

        with self._lock:
            # 基于错误率
            if self._system_state.error_rate > self.DEGRADATION_THRESHOLD:
                self._trigger_degradation()
            elif self._system_state.error_rate > 0.1:
                return DegradationLevel.REDUCED
            else:
                return DegradationLevel.FULL

            return self._system_state.degradation_level

    def _trigger_degradation(self):
        """触发降级"""
        current = self._system_state.degradation_level

        # 逐级降级
        if current == DegradationLevel.FULL:
            self._system_state.degradation_level = DegradationLevel.REDUCED
        elif current == DegradationLevel.REDUCED:
            self._system_state.degradation_level = DegradationLevel.MINIMAL
        elif current == DegradationLevel.MINIMAL:
            self._system_state.degradation_level = DegradationLevel.EMERGENCY

        self._statistics["degradations_triggered"] += 1

    def get_degraded_functionality(
        self,
        original_function: Callable,
        fallback_function: Optional[Callable] = None
    ) -> Callable:
        """
        获取降级功能

        Args:
            original_function: 原始功能
            fallback_function: 回退功能

        Returns:
            降级后的功能
        """
        level = self.check_degradation()

        if level == DegradationLevel.FULL:
            return original_function

        if fallback_function:
            return fallback_function

        # 简单回退
        def degraded(*args, **kwargs):
            return None

        return degraded

    # ==================== 错误处理 ====================

    def _handle_error(self, error: CognitiveError):
        """处理错误"""
        # 创建恢复计划
        recovery_id = f"rec_{self._recovery_counter}"
        self._recovery_counter += 1

        # 选择恢复动作
        action = self._select_recovery_action(error)

        plan = RecoveryPlan(
            id=recovery_id,
            error_id=error.id,
            primary_action=action,
            estimated_success_rate=0.7
        )

        self._recovery_plans[recovery_id] = plan

        # 执行恢复
        self._execute_recovery(plan, error)

    def _select_recovery_action(self, error: CognitiveError) -> RecoveryAction:
        """选择恢复动作"""
        # 基于错误类型和严重程度
        if error.severity == ErrorSeverity.CRITICAL:
            return RecoveryAction.ESCALATE
        elif error.severity == ErrorSeverity.MAJOR:
            return RecoveryAction.FALLBACK
        elif error.error_type in [CognitiveErrorType.PERCEPTION, CognitiveErrorType.MEMORY]:
            return RecoveryAction.RETRY
        else:
            return RecoveryAction.DECOMPOSE

    def _execute_recovery(self, plan: RecoveryPlan, error: CognitiveError):
        """执行恢复"""
        try:
            # 简化实现
            plan.executed = True

            if plan.primary_action == RecoveryAction.RETRY:
                plan.execution_result = "重试成功" if random.random() > 0.3 else "重试失败"
            elif plan.primary_action == RecoveryAction.FALLBACK:
                plan.execution_result = "已使用回退方案"
            elif plan.primary_action == RecoveryAction.ESCALATE:
                plan.execution_result = "已升级处理"

            # 标记错误为已解决
            if "成功" in plan.execution_result:
                error.resolved = True
                error.resolution = plan.execution_result
                self._statistics["errors_resolved"] += 1
                self._statistics["recoveries_successful"] += 1

        except Exception:
            plan.execution_result = "恢复失败"

    # ==================== 统计和状态 ====================

    def get_statistics(self) -> Dict[str, Any]:
        """获取统计"""
        return {
            **self._statistics,
            "current_strategy": self._current_strategy.value,
            "system_state": {
                "degradation": self._system_state.degradation_level.value,
                "error_rate": self._system_state.error_rate,
                "success_rate": self._system_state.success_rate,
                "active_strategies": [s.value for s in self._system_state.active_strategies]
            },
            "total_errors": len(self._errors),
            "active_dissonances": sum(1 for d in self._dissonances.values() if not d.resolved),
            "total_experiences": len(self._experiences),
            "avoidance_patterns": len(self._avoidance_patterns)
        }

    def get_system_state(self) -> SystemState:
        """获取系统状态"""
        return self._system_state

    def __repr__(self) -> str:
        return (f"CognitiveExceptionHandler(errors={len(self._errors)}, "
                f"strategies={self._current_strategy.value}, "
                f"degradation={self._system_state.degradation_level.value})")
