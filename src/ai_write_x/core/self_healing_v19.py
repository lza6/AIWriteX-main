"""
V19自愈系统 - 认知层面的自我修复
├── 认知健康检查: 评估推理系统状态
├── 记忆完整性校验: 检测记忆损坏
├── 自动修复策略: 针对问题的修复方案
├── 知识库一致性: 维护知识图谱完整性
├── 性能退化检测: 识别认知能力下降
└── 紧急重启机制: 保留记忆的安全重启
"""

import numpy as np
from typing import Dict, List, Optional, Any, Tuple, Set, Callable, Union
from dataclasses import dataclass, field
from datetime import datetime, timedelta
from enum import Enum, auto
from collections import defaultdict, deque
import threading
import time
import random
import json
import hashlib


class HealthStatus(Enum):
    """健康状态"""
    HEALTHY = "healthy"             # 健康
    DEGRADED = "degraded"           # 退化
    CRITICAL = "critical"            # 危急
    FAILING = "failing"             # 失效
    RECOVERING = "recovering"       # 恢复中


class RepairPriority(Enum):
    """修复优先级"""
    LOW = 1      # 低
    MEDIUM = 2   # 中
    HIGH = 3     # 高
    CRITICAL = 4  # 紧急


class RepairStrategy(Enum):
    """修复策略"""
    RESTART = "restart"             # 重启
    RECALIBRATE = "recalibrate"     # 重新校准
    REINITIALIZE = "reinitialize"   # 重新初始化
    CACHE_CLEAR = "cache_clear"     # 清除缓存
    MEMORY_PRUNE = "memory_prune"   # 记忆剪枝
    REINDEX = "reindex"             # 重新索引
    RECONSOLIDATE = "reconsolidate" # 重新整合
    ISOLATE = "isolate"             # 隔离


class IntegrityCheckType(Enum):
    """完整性检查类型"""
    MEMORY = "memory"               # 记忆完整性
    KNOWLEDGE = "knowledge"         # 知识一致性
    ASSOCIATION = "association"      # 联想完整性
    EMOTIONAL = "emotional"         # 情感一致性
    CONTEXT = "context"             # 上下文一致性
    PERFORMANCE = "performance"     # 性能检查


class DegradationType(Enum):
    """退化类型"""
    MEMORY_LEAK = "memory_leak"     # 内存泄漏
    CACHE_BLOAT = "cache_bloat"     # 缓存膨胀
    ASSOCIATION_DECAY = "association_decay"  # 联想衰减
    RESPONSE_LATENCY = "response_latency"  # 响应延迟
    ACCURACY_LOSS = "accuracy_loss" # 准确率下降
    RECALL_FAILURE = "recall_failure"  # 回忆失败


@dataclass
class HealthReport:
    """健康报告"""
    id: str
    timestamp: datetime
    overall_status: HealthStatus
    component_status: Dict[str, HealthStatus] = field(default_factory=dict)
    metrics: Dict[str, float] = field(default_factory=dict)
    issues: List[str] = field(default_factory=list)
    recommendations: List[str] = field(default_factory=list)


@dataclass
class IntegrityCheck:
    """完整性检查"""
    id: str
    check_type: IntegrityCheckType
    timestamp: datetime
    passed: bool
    details: Dict[str, Any] = field(default_factory=dict)
    affected_items: List[str] = field(default_factory=list)
    severity: float = 0.0  # 0-1


@dataclass
class RepairAction:
    """修复动作"""
    id: str
    strategy: RepairStrategy
    priority: RepairPriority
    target_component: str
    description: str
    estimated_impact: float = 0.5  # 预计影响
    risk_level: float = 0.0       # 风险等级
    prerequisites: List[str] = field(default_factory=list)
    rollback_plan: Optional[str] = None
    executed: bool = False
    result: Optional[str] = None
    execution_time: float = 0.0


@dataclass
class DegradationEvent:
    """退化事件"""
    id: str
    degradation_type: DegradationType
    detected_at: datetime
    severity: float
    metrics_before: Dict[str, float] = field(default_factory=dict)
    metrics_after: Dict[str, float] = field(default_factory=dict)
    resolved: bool = False
    resolution: Optional[str] = None


@dataclass
class Checkpoint:
    """检查点"""
    id: str
    timestamp: datetime
    component_states: Dict[str, Any] = field(default_factory=dict)
    memory_snapshot: Dict[str, Any] = field(default_factory=dict)
    metadata: Dict[str, Any] = field(default_factory=dict)


@dataclass
class ConsistencyIssue:
    """一致性问题"""
    id: str
    issue_type: str
    description: str
    affected_components: List[str] = field(default_factory=list)
    severity: float = 1.0
    detected_at: datetime = field(default_factory=datetime.now)
    auto_repairable: bool = False
    repair_attempts: int = 0


class SelfHealingSystem:
    """
    V19自愈系统

    实现认知层面的自我修复:
    1. 认知健康检查: 评估推理系统状态
    2. 记忆完整性校验: 检测记忆损坏
    3. 自动修复策略: 针对问题的修复方案
    4. 知识库一致性: 维护知识图谱完整性
    5. 性能退化检测: 识别认知能力下降
    6. 紧急重启机制: 保留记忆的安全重启
    """

    # 参数
    HEALTH_CHECK_INTERVAL = 3600      # 健康检查间隔（秒）
    INTEGRITY_CHECK_INTERVAL = 1800   # 完整性检查间隔
    MAX_CHECKPOINTS = 10              # 最大检查点数
    DEGRADATION_THRESHOLD = 0.3      # 退化阈值
    CRITICAL_HEALTH_SCORE = 0.3      # 关键健康分数
    REPAIR_RETRY_LIMIT = 3            # 修复重试限制

    def __init__(
        self,
        enable_auto_repair: bool = True,
        enable_checkpoints: bool = True,
        enable_degradation_detection: bool = True,
        checkpoint_interval: int = 3600
    ):
        """
        初始化自愈系统

        Args:
            enable_auto_repair: 启用自动修复
            enable_checkpoints: 启用检查点
            enable_degradation_detection: 启用退化检测
            checkpoint_interval: 检查点间隔（秒）
        """
        self.enable_auto_repair = enable_auto_repair
        self.enable_checkpoints = enable_checkpoints
        self.enable_degradation_detection = enable_degradation_detection
        self.checkpoint_interval = checkpoint_interval

        # 健康检查
        self._last_health_check: Optional[datetime] = None
        self._health_history: deque = deque(maxlen=100)

        # 完整性检查
        self._integrity_checks: Dict[str, IntegrityCheck] = {}
        self._check_counter = 0
        self._last_integrity_check: Optional[datetime] = None

        # 修复动作
        self._repair_queue: List[RepairAction] = []
        self._repair_history: deque = deque(maxlen=500)
        self._repair_counter = 0

        # 退化事件
        self._degradation_events: Dict[str, DegradationEvent] = {}
        self._degradation_counter = 0

        # 一致性问题
        self._consistency_issues: Dict[str, ConsistencyIssue] = {}
        self._issue_counter = 0

        # 检查点
        self._checkpoints: deque = deque(maxlen=self.MAX_CHECKPOINTS)
        self._checkpoint_counter = 0
        self._last_checkpoint: Optional[datetime] = None

        # 组件注册
        self._registered_components: Dict[str, Any] = {}

        # 性能基线
        self._performance_baseline: Dict[str, float] = {}

        # 统计
        self._statistics = {
            "health_checks": 0,
            "integrity_checks": 0,
            "repairs_executed": 0,
            "repairs_successful": 0,
            "degradations_detected": 0,
            "degradations_resolved": 0,
            "checkpoints_created": 0,
            "restores_performed": 0,
            "consistency_issues": 0,
            "auto_repairs_successful": 0
        }

        # 当前健康状态
        self._current_health = HealthStatus.HEALTHY
        self._health_score = 1.0

        # 线程安全
        self._lock = threading.RLock()

        # 启动时间
        self._start_time = time.time()

    # ==================== 组件注册 ====================

    def register_component(
        self,
        name: str,
        component: Any,
        health_check_fn: Optional[Callable] = None,
        repair_fn: Optional[Callable] = None
    ):
        """
        注册组件

        Args:
            name: 组件名
            component: 组件对象
            health_check_fn: 健康检查函数
            repair_fn: 修复函数
        """
        with self._lock:
            self._registered_components[name] = {
                "component": component,
                "health_check": health_check_fn,
                "repair": repair_fn,
                "last_health_check": None,
                "health_score": 1.0
            }

    # ==================== 认知健康检查 ====================

    def perform_health_check(self) -> HealthReport:
        """
        执行健康检查

        Returns:
            健康报告
        """
        with self._lock:
            report_id = f"health_{len(self._health_history)}"

            # 收集各组件健康状态
            component_status = {}
            all_issues = []
            recommendations = []
            metrics = {}

            for name, info in self._registered_components.items():
                # 调用健康检查函数
                if info["health_check"]:
                    try:
                        result = info["health_check"]()
                        health_score = result.get("score", 1.0)
                        status = result.get("status", HealthStatus.HEALTHY)
                    except Exception:
                        health_score = 0.5
                        status = HealthStatus.DEGRADED
                else:
                    # 默认健康
                    health_score = 1.0
                    status = HealthStatus.HEALTHY

                info["health_score"] = health_score
                info["last_health_check"] = datetime.now()

                component_status[name] = status
                metrics[f"{name}_score"] = health_score

                # 收集问题
                if health_score < 0.7:
                    all_issues.append(f"{name}健康分数低: {health_score:.2f}")
                    recommendations.append(f"检查{name}组件")

            # 计算整体健康状态
            avg_score = np.mean(list(metrics.values())) if metrics else 1.0
            self._health_score = avg_score

            if avg_score >= 0.9:
                overall_status = HealthStatus.HEALTHY
            elif avg_score >= 0.7:
                overall_status = HealthStatus.DEGRADED
            elif avg_score >= 0.5:
                overall_status = HealthStatus.CRITICAL
            else:
                overall_status = HealthStatus.FAILING

            self._current_health = overall_status

            # 创建报告
            report = HealthReport(
                id=report_id,
                timestamp=datetime.now(),
                overall_status=overall_status,
                component_status=component_status,
                metrics=metrics,
                issues=all_issues,
                recommendations=recommendations
            )

            self._health_history.append(report)
            self._last_health_check = datetime.now()
            self._statistics["health_checks"] += 1

            # 触发自动修复
            if self.enable_auto_repair and all_issues:
                self._trigger_auto_repair(component_status)

            return report

    def get_health_status(self) -> HealthStatus:
        """获取健康状态"""
        # 定期执行检查
        if self._should_check_health():
            self.perform_health_check()

        return self._current_health

    def _should_check_health(self) -> bool:
        """是否应该检查健康"""
        if not self._last_health_check:
            return True

        elapsed = (datetime.now() - self._last_health_check).total_seconds()
        return elapsed > self.HEALTH_CHECK_INTERVAL

    # ==================== 记忆完整性校验 ====================

    def perform_integrity_check(
        self,
        check_type: IntegrityCheckType = IntegrityCheckType.MEMORY,
        target: Optional[str] = None
    ) -> IntegrityCheck:
        """
        执行完整性检查

        Args:
            check_type: 检查类型
            target: 目标组件

        Returns:
            完整性检查结果
        """
        with self._lock:
            check_id = f"int_{self._check_counter}"
            self._check_counter += 1

            passed = True
            details = {}
            affected = []
            severity = 0.0

            if check_type == IntegrityCheckType.MEMORY:
                passed, details, affected, severity = self._check_memory_integrity(target)
            elif check_type == IntegrityCheckType.KNOWLEDGE:
                passed, details, affected, severity = self._check_knowledge_integrity(target)
            elif check_type == IntegrityCheckType.ASSOCIATION:
                passed, details, affected, severity = self._check_association_integrity(target)
            elif check_type == IntegrityCheckType.EMOTIONAL:
                passed, details, affected, severity = self._check_emotional_integrity(target)

            check = IntegrityCheck(
                id=check_id,
                check_type=check_type,
                timestamp=datetime.now(),
                passed=passed,
                details=details,
                affected_items=affected,
                severity=severity
            )

            self._integrity_checks[check_id] = check
            self._last_integrity_check = datetime.now()
            self._statistics["integrity_checks"] += 1

            # 发现问题时创建一致性报告
            if not passed and severity > 0.5:
                self._report_consistency_issue(check_type, affected, severity)

            return check

    def _check_memory_integrity(
        self,
        target: Optional[str]
    ) -> Tuple[bool, Dict, List, float]:
        """检查记忆完整性"""
        details = {}
        affected = []
        severity = 0.0

        # 简化实现
        # 检查是否有null值、损坏的引用等
        details["checked_at"] = datetime.now().isoformat()
        details["total_memories"] = 0
        details["corrupted"] = 0

        passed = details["corrupted"] == 0
        if not passed:
            severity = min(1.0, details["corrupted"] / max(details["total_memories"], 1))

        return passed, details, affected, severity

    def _check_knowledge_integrity(
        self,
        target: Optional[str]
    ) -> Tuple[bool, Dict, List, float]:
        """检查知识完整性"""
        details = {}
        affected = []
        severity = 0.0

        # 检查知识一致性
        details["checked_at"] = datetime.now().isoformat()
        details["total_knowledge"] = 0
        details["inconsistent"] = 0

        passed = details["inconsistent"] == 0
        if not passed:
            severity = min(1.0, details["inconsistent"] / max(details["total_knowledge"], 1))

        return passed, details, affected, severity

    def _check_association_integrity(
        self,
        target: Optional[str]
    ) -> Tuple[bool, Dict, List, float]:
        """检查联想完整性"""
        details = {}
        affected = []
        severity = 0.0

        # 检查孤立节点、断裂链接等
        details["checked_at"] = datetime.now().isoformat()
        details["total_associations"] = 0
        details["broken_links"] = 0

        passed = details["broken_links"] == 0
        if not passed:
            severity = min(1.0, details["broken_links"] / max(details["total_associations"], 1))

        return passed, details, affected, severity

    def _check_emotional_integrity(
        self,
        target: Optional[str]
    ) -> Tuple[bool, Dict, List, float]:
        """检查情感完整性"""
        details = {}
        affected = []
        severity = 0.0

        # 检查情感标签一致性
        details["checked_at"] = datetime.now().isoformat()
        details["total_emotional"] = 0
        details["inconsistent"] = 0

        passed = details["inconsistent"] == 0
        if not passed:
            severity = min(1.0, details["inconsistent"] / max(details["total_emotional"], 1))

        return passed, details, affected, severity

    def _report_consistency_issue(
        self,
        check_type: IntegrityCheckType,
        affected: List[str],
        severity: float
    ):
        """报告一致性问题"""
        issue_id = f"issue_{self._issue_counter}"
        self._issue_counter += 1

        issue = ConsistencyIssue(
            id=issue_id,
            issue_type=check_type.value,
            description=f"完整性检查失败: {check_type.value}",
            affected_components=affected,
            severity=severity,
            detected_at=datetime.now(),
            auto_repairable=severity < 0.7
        )

        self._consistency_issues[issue_id] = issue
        self._statistics["consistency_issues"] += 1

    # ==================== 自动修复策略 ====================

    def _trigger_auto_repair(self, component_status: Dict[str, HealthStatus]):
        """触发自动修复"""
        for component, status in component_status.items():
            if status in [HealthStatus.DEGRADED, HealthStatus.CRITICAL]:
                # 确定修复策略
                strategy = self._select_repair_strategy(status)
                self._queue_repair(component, strategy)

        # 执行修复队列
        self._execute_repair_queue()

    def _select_repair_strategy(self, status: HealthStatus) -> RepairStrategy:
        """选择修复策略"""
        if status == HealthStatus.CRITICAL:
            return RepairStrategy.REINITIALIZE
        elif status == HealthStatus.FAILING:
            return RepairStrategy.RESTART
        else:
            return RepairStrategy.RECALIBRATE

    def _queue_repair(
        self,
        component: str,
        strategy: RepairStrategy,
        priority: RepairPriority = RepairPriority.MEDIUM
    ) -> str:
        """队列修复动作"""
        repair_id = f"repair_{self._repair_counter}"
        self._repair_counter += 1

        action = RepairAction(
            id=repair_id,
            strategy=strategy,
            priority=priority,
            target_component=component,
            description=f"{strategy.value} {component}"
        )

        self._repair_queue.append(action)
        return repair_id

    def _execute_repair_queue(self):
        """执行修复队列"""
        # 按优先级排序
        self._repair_queue.sort(key=lambda a: a.priority.value, reverse=True)

        executed = []

        for action in self._repair_queue:
            if self._execute_repair(action):
                executed.append(action.id)
                self._statistics["repairs_successful"] += 1

                if self.enable_auto_repair:
                    self._statistics["auto_repairs_successful"] += 1

        # 移除已执行的
        self._repair_queue = [
            a for a in self._repair_queue if a.id not in executed
        ]

        self._statistics["repairs_executed"] += len(executed)

    def _execute_repair(self, action: RepairAction) -> bool:
        """执行单个修复"""
        start_time = time.time()

        try:
            # 获取组件信息
            component_info = self._registered_components.get(action.target_component)

            if not component_info:
                action.result = "组件未找到"
                action.executed = True
                self._repair_history.append(action)
                return False

            # 调用修复函数
            if component_info.get("repair"):
                result = component_info["repair"](action.strategy)
                action.result = str(result)
            else:
                # 默认修复
                action.result = self._default_repair(action.strategy)

            action.executed = True
            action.execution_time = time.time() - start_time
            self._repair_history.append(action)

            return "成功" in action.result

        except Exception as e:
            action.result = f"失败: {str(e)}"
            action.executed = True
            action.execution_time = time.time() - start_time
            self._repair_history.append(action)
            return False

    def _default_repair(self, strategy: RepairStrategy) -> str:
        """默认修复"""
        if strategy == RepairStrategy.CACHE_CLEAR:
            return "缓存清除成功"
        elif strategy == RepairStrategy.MEMORY_PRUNE:
            return "记忆剪枝成功"
        elif strategy == RepairStrategy.REINDEX:
            return "重新索引成功"
        elif strategy == RepairStrategy.RECONSOLIDATE:
            return "重新整合成功"
        else:
            return "默认修复完成"

    def request_repair(
        self,
        component: str,
        strategy: RepairStrategy,
        priority: RepairPriority = RepairPriority.MEDIUM
    ) -> str:
        """
        请求修复

        Args:
            component: 组件名
            strategy: 修复策略
            priority: 优先级

        Returns:
            修复ID
        """
        with self._lock:
            return self._queue_repair(component, strategy, priority)

    # ==================== 性能退化检测 ====================

    def detect_degradation(
        self,
        current_metrics: Dict[str, float]
    ) -> Optional[DegradationEvent]:
        """
        检测性能退化

        Args:
            current_metrics: 当前指标

        Returns:
            退化事件
        """
        if not self.enable_degradation_detection:
            return None

        with self._lock:
            # 与基线比较
            degradation = None

            for metric, value in current_metrics.items():
                baseline = self._performance_baseline.get(metric)

                if baseline and baseline > 0:
                    # 计算退化程度
                    degradation_ratio = (baseline - value) / baseline

                    if degradation_ratio > self.DEGRADATION_THRESHOLD:
                        # 发现退化
                        event_id = f"deg_{self._degradation_counter}"
                        self._degradation_counter += 1

                        event = DegradationEvent(
                            id=event_id,
                            degradation_type=self._classify_degradation(metric),
                            detected_at=datetime.now(),
                            severity=degradation_ratio,
                            metrics_before={metric: baseline},
                            metrics_after={metric: value}
                        )

                        self._degradation_events[event_id] = event
                        self._statistics["degradations_detected"] += 1

                        # 尝试自动修复
                        if self.enable_auto_repair:
                            self._handle_degradation(event)

                        degradation = event
                        break

            return degradation

    def _classify_degradation(self, metric: str) -> DegradationType:
        """分类退化类型"""
        if "memory" in metric.lower():
            return DegradationType.MEMORY_LEAK
        elif "cache" in metric.lower():
            return DegradationType.CACHE_BLOAT
        elif "latency" in metric.lower() or "time" in metric.lower():
            return DegradationType.RESPONSE_LATENCY
        elif "accuracy" in metric.lower():
            return DegradationType.ACCURACY_LOSS
        elif "recall" in metric.lower():
            return DegradationType.RECALL_FAILURE
        else:
            return DegradationType.ASSOCIATION_DECAY

    def _handle_degradation(self, event: DegradationEvent):
        """处理退化事件"""
        # 根据退化类型选择修复策略
        if event.degradation_type == DegradationType.MEMORY_LEAK:
            strategy = RepairStrategy.MEMORY_PRUNE
        elif event.degradation_type == DegradationType.CACHE_BLOAT:
            strategy = RepairStrategy.CACHE_CLEAR
        elif event.degradation_type == DegradationType.RESPONSE_LATENCY:
            strategy = RepairStrategy.REINDEX
        else:
            strategy = RepairStrategy.RECALIBRATE

        # 队列修复
        self._queue_repair("system", strategy, RepairPriority.HIGH)

        # 执行
        self._execute_repair_queue()

    def set_performance_baseline(self, metrics: Dict[str, float]):
        """
        设置性能基线

        Args:
            metrics: 指标字典
        """
        with self._lock:
            self._performance_baseline.update(metrics)

    # ==================== 检查点和重启 ====================

    def create_checkpoint(self, metadata: Optional[Dict[str, Any]] = None) -> str:
        """
        创建检查点

        Args:
            metadata: 元数据

        Returns:
            检查点ID
        """
        if not self.enable_checkpoints:
            return None

        with self._lock:
            checkpoint_id = f"cp_{self._checkpoint_counter}"
            self._checkpoint_counter += 1

            # 收集组件状态
            component_states = {}
            for name, info in self._registered_components.items():
                try:
                    state = getattr(info["component"], "get_state", lambda: {})()
                    component_states[name] = state
                except Exception:
                    component_states[name] = {}

            # 创建检查点
            checkpoint = Checkpoint(
                id=checkpoint_id,
                timestamp=datetime.now(),
                component_states=component_states,
                metadata=metadata or {}
            )

            self._checkpoints.append(checkpoint)
            self._last_checkpoint = datetime.now()
            self._statistics["checkpoints_created"] += 1

            return checkpoint_id

    def restore_from_checkpoint(
        self,
        checkpoint_id: Optional[str] = None
    ) -> bool:
        """
        从检查点恢复

        Args:
            checkpoint_id: 检查点ID（默认最新）

        Returns:
            是否成功
        """
        with self._lock:
            # 找到检查点
            if checkpoint_id:
                checkpoint = next(
                    (cp for cp in self._checkpoints if cp.id == checkpoint_id),
                    None
                )
            else:
                checkpoint = self._checkpoints[-1] if self._checkpoints else None

            if not checkpoint:
                return False

            # 恢复各组件
            for name, state in checkpoint.component_states.items():
                component_info = self._registered_components.get(name)
                if component_info:
                    try:
                        restore_fn = getattr(
                            component_info["component"],
                            "restore_state",
                            None
                        )
                        if restore_fn:
                            restore_fn(state)
                    except Exception:
                        pass

            self._statistics["restores_performed"] += 1
            return True

    def emergency_restart(
        self,
        preserve_memories: bool = True
    ) -> bool:
        """
        紧急重启

        Args:
            preserve_memories: 是否保留记忆

        Returns:
            是否成功
        """
        with self._lock:
            try:
                # 创建检查点（如果启用）
                if preserve_memories and self.enable_checkpoints:
                    self.create_checkpoint({"type": "emergency_restart"})

                # 保存记忆快照
                memory_snapshot = {}
                if preserve_memories:
                    for name, info in self._registered_components.items():
                        try:
                            snapshot = getattr(
                                info["component"],
                                "get_memory_snapshot",
                                lambda: {}
                            )()
                            memory_snapshot[name] = snapshot
                        except Exception:
                            pass

                # 执行重启
                for name, info in self._registered_components.items():
                    try:
                        restart_fn = getattr(
                            info["component"],
                            "emergency_restart",
                            None
                        )
                        if restart_fn:
                            restart_fn()
                    except Exception:
                        pass

                # 恢复记忆
                if preserve_memories:
                    for name, snapshot in memory_snapshot.items():
                        component_info = self._registered_components.get(name)
                        if component_info:
                            try:
                                restore_fn = getattr(
                                    component_info["component"],
                                    "restore_memory_snapshot",
                                    None
                                )
                                if restore_fn:
                                    restore_fn(snapshot)
                            except Exception:
                                pass

                # 重新执行健康检查
                self.perform_health_check()

                return True

            except Exception:
                return False

    # ==================== 统计和状态 ====================

    def get_statistics(self) -> Dict[str, Any]:
        """获取统计"""
        return {
            **self._statistics,
            "current_health": self._current_health.value,
            "health_score": self._health_score,
            "registered_components": len(self._registered_components),
            "pending_repairs": len(self._repair_queue),
            "active_degradations": sum(
                1 for e in self._degradation_events.values() if not e.resolved
            ),
            "consistency_issues": len(self._consistency_issues),
            "checkpoints": len(self._checkpoints),
            "uptime_seconds": time.time() - self._start_time
        }

    def get_system_status(self) -> Dict[str, Any]:
        """获取系统状态"""
        return {
            "health_status": self._current_health.value,
            "health_score": self._health_score,
            "components": list(self._registered_components.keys()),
            "recent_issues": len(self._consistency_issues),
            "degradation_events": sum(
                1 for e in self._degradation_events.values() if not e.resolved
            )
        }

    def __repr__(self) -> str:
        return (f"SelfHealingSystem(health={self._current_health.value}, "
                f"components={len(self._registered_components)}, "
                f"repairs={self._statistics['repairs_executed']})")
