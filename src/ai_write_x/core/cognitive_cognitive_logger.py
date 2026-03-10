"""
认知日志 - 记录思维过程
├── 推理轨迹: 完整的思考路径
├── 决策依据: 每个决策的理由
├── 记忆访问: 记忆检索的历史
├── 注意力日志: 关注点变化记录
├── 元认知日志: 对自身的监控记录
└── 学习日志: 知识获取和更新记录
"""

import numpy as np
from typing import Dict, List, Optional, Any, Callable, Union
from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum, auto
from collections import deque
import threading
import time
import json
import hashlib


class LogLevel(Enum):
    """日志级别"""
    TRACE = "trace"         # 详细追踪
    DEBUG = "debug"         # 调试
    INFO = "info"           # 信息
    WARNING = "warning"     # 警告
    ERROR = "error"         # 错误
    CRITICAL = "critical"   # 关键


class ReasoningType(Enum):
    """推理类型"""
    DEDUCTIVE = "deductive"       # 演绎
    INDUCTIVE = "inductive"       # 归纳
    ABDUCTIVE = "abductive"       # 溯因
    ANALOGICAL = "analogical"     # 类比
    CAUSAL = "causal"             # 因果
    DEFAULT = "default"           # 默认


class DecisionType(Enum):
    """决策类型"""
    ACTION = "action"             # 行动决策
    BELIEF = "belief"             # 信念决策
    ATTENTION = "attention"       # 注意力决策
    MEMORY = "memory"             # 记忆决策
    LEARNING = "learning"         # 学习决策
    STRATEGY = "strategy"         # 策略决策


class AttentionPhase(Enum):
    """注意力阶段"""
    SELECTION = "selection"       # 选择
    FOCUS = "focus"               # 聚焦
    MAINTENANCE = "maintenance"   # 维持
    SHIFT = "shift"               # 切换
    RELEASE = "release"           # 释放


class MetaCognitiveState(Enum):
    """元认知状态"""
    MONITORING = "monitoring"     # 监控中
    EVALUATING = "evaluating"     # 评估中
    PLANNING = "planning"        # 计划中
    ADJUSTING = "adjusting"       # 调整中
    IDLE = "idle"                 # 空闲


@dataclass
class ReasoningStep:
    """推理步骤"""
    id: str
    step_number: int
    reasoning_type: ReasoningType
    premise: str                  # 前提
    inference: str                # 推理
    conclusion: str               # 结论
    confidence: float             # 置信度
    duration_ms: float            # 耗时
    timestamp: datetime
    context: Dict[str, Any] = field(default_factory=dict)


@dataclass
class ReasoningTrace:
    """推理轨迹"""
    id: str
    start_time: datetime
    end_time: Optional[datetime] = None
    reasoning_type: ReasoningType
    goal: str                      # 目标
    steps: List[ReasoningStep] = field(default_factory=list)
    final_conclusion: Optional[str] = None
    confidence: float = 0.0
    success: bool = True
    metadata: Dict[str, Any] = field(default_factory=dict)


@dataclass
class DecisionRecord:
    """决策记录"""
    id: str
    timestamp: datetime
    decision_type: DecisionType
    options: List[str] = field(default_factory=list)
    chosen: str
    reasons: List[str] = field(default_factory=list)
    evidence: Dict[str, Any] = field(default_factory=dict)
    confidence: float = 0.0
    outcome: Optional[str] = None
    outcome_confidence: float = 0.0
    duration_ms: float = 0.0


@dataclass
class MemoryAccess:
    """记忆访问"""
    id: str
    timestamp: datetime
    memory_id: Optional[str]
    memory_content: str
    access_type: str              # "recall", "encode", "consolidate", "forget"
    relevance_score: float        # 相关度
    access_duration_ms: float
    context: Dict[str, Any] = field(default_factory=dict)
    success: bool = True


@dataclass
class AttentionLog:
    """注意力日志"""
    id: str
    timestamp: datetime
    phase: AttentionPhase
    previous_focus: List[str] = field(default_factory=list)
    current_focus: List[str] = field(default_factory=list)
    triggered_by: str             # 触发源
    intensity: float = 1.0         # 强度
    duration_ms: float = 0.0
    context: Dict[str, Any] = field(default_factory=dict)


@dataclass
class MetaCognitiveLog:
    """元认知日志"""
    id: str
    timestamp: datetime
    state: MetaCognitiveState
    target: str                   # 监控目标
    observation: str              # 观察结果
    evaluation: Optional[str] = None  # 评估结果
    adjustment: Optional[str] = None   # 调整动作
    confidence: float = 0.0
    metadata: Dict[str, Any] = field(default_factory=dict)


@dataclass
class LearningLog:
    """学习日志"""
    id: str
    timestamp: datetime
    source: str                   # 来源
    content: str                  # 内容
    knowledge_type: str           # 知识类型
    integration_result: str       # 整合结果
    confidence_change: float = 0.0  # 置信度变化
    related_memories: List[str] = field(default_factory=list)
    success: bool = True
    metadata: Dict[str, Any] = field(default_factory=dict)


@dataclass
class CognitiveSession:
    """认知会话"""
    id: str
    start_time: datetime
    end_time: Optional[datetime] = None
    reasoning_traces: List[str] = field(default_factory=list)  # trace IDs
    decisions: List[str] = field(default_factory=list)        # decision IDs
    memory_accesses: List[str] = field(default_factory=list)   # access IDs
    attention_logs: List[str] = field(default_factory=list)   # log IDs
    meta_logs: List[str] = field(default_factory=list)        # meta IDs
    learning_logs: List[str] = field(default_factory=list)    # log IDs
    metadata: Dict[str, Any] = field(default_factory=dict)


class CognitiveLogger:
    """
    认知日志系统

    实现完整的思维过程记录:
    1. 推理轨迹: 完整的思考路径
    2. 决策依据: 每个决策的理由
    3. 记忆访问: 记忆检索的历史
    4. 注意力日志: 关注点变化记录
    5. 元认知日志: 对自身的监控记录
    6. 学习日志: 知识获取和更新记录
    """

    # 参数
    MAX_REASONING_TRACES = 500
    MAX_DECISIONS = 1000
    MAX_MEMORY_ACCESSES = 2000
    MAX_ATTENTION_LOGS = 1000
    MAX_META_LOGS = 500
    MAX_LEARNING_LOGS = 500

    def __init__(
        self,
        enable_reasoning: bool = True,
        enable_decisions: bool = True,
        enable_memory: bool = True,
        enable_attention: bool = True,
        enable_meta: bool = True,
        enable_learning: bool = True,
        log_level: LogLevel = LogLevel.INFO,
        session_timeout: int = 3600
    ):
        """
        初始化认知日志器

        Args:
            enable_reasoning: 启用推理轨迹
            enable_decisions: 启用决策记录
            enable_memory: 启用记忆访问
            enable_attention: 启用注意力日志
            enable_meta: 启用元认知日志
            enable_learning: 启用学习日志
            log_level: 日志级别
            session_timeout: 会话超时（秒）
        """
        self.enable_reasoning = enable_reasoning
        self.enable_decisions = enable_decisions
        self.enable_memory = enable_memory
        self.enable_attention = enable_attention
        self.enable_meta = enable_meta
        self.enable_learning = enable_learning
        self.log_level = log_level
        self.session_timeout = session_timeout

        # 推理轨迹
        self._reasoning_traces: Dict[str, ReasoningTrace] = {}
        self._current_trace: Optional[ReasoningTrace] = None
        self._trace_counter = 0

        # 决策
        self._decisions: Dict[str, DecisionRecord] = {}
        self._decision_counter = 0

        # 记忆访问
        self._memory_accesses: Dict[str, MemoryAccess] = {}
        self._access_counter = 0

        # 注意力
        self._attention_logs: Dict[str, AttentionLog] = {}
        self._attention_counter = 0

        # 元认知
        self._meta_logs: Dict[str, MetaCognitiveLog] = {}
        self._meta_counter = 0

        # 学习
        self._learning_logs: Dict[str, LearningLog] = {}
        self._learning_counter = 0

        # 会话
        self._sessions: Dict[str, CognitiveSession] = {}
        self._session_counter = 0
        self._current_session: Optional[CognitiveSession] = None
        self._last_activity: Optional[datetime] = None

        # 统计
        self._statistics = {
            "reasoning_traces": 0,
            "decisions": 0,
            "memory_accesses": 0,
            "attention_switches": 0,
            "meta_observations": 0,
            "learning_events": 0,
            "sessions_started": 0,
            "sessions_ended": 0
        }

        # 回调
        self._log_callbacks: Dict[str, List[Callable]] = {
            "reasoning": [],
            "decision": [],
            "memory": [],
            "attention": [],
            "meta": [],
            "learning": []
        }

        # 线程安全
        self._lock = threading.RLock()

    # ==================== 会话管理 ====================

    def start_session(self, metadata: Optional[Dict[str, Any]] = None) -> str:
        """
        开始会话

        Args:
            metadata: 元数据

        Returns:
            会话ID
        """
        with self._lock:
            # 结束当前会话
            if self._current_session:
                self.end_session()

            # 创建新会话
            session_id = f"session_{self._session_counter}"
            self._session_counter += 1

            session = CognitiveSession(
                id=session_id,
                start_time=datetime.now(),
                metadata=metadata or {}
            )

            self._sessions[session_id] = session
            self._current_session = session
            self._last_activity = datetime.now()
            self._statistics["sessions_started"] += 1

            return session_id

    def end_session(self) -> Optional[CognitiveSession]:
        """
        结束会话

        Returns:
            结束的会话
        """
        with self._lock:
            if not self._current_session:
                return None

            session = self._current_session
            session.end_time = datetime.now()

            self._current_session = None
            self._statistics["sessions_ended"] += 1

            # 检查超时
            self._check_session_timeout()

            return session

    def _check_session_timeout(self):
        """检查会话超时"""
        if not self._last_activity:
            return

        elapsed = (datetime.now() - self._last_activity).total_seconds()
        if elapsed > self.session_timeout and self._current_session:
            self.end_session()

    def _ensure_session(self):
        """确保有活动会话"""
        if not self._current_session:
            self.start_session()

    # ==================== 推理轨迹 ====================

    def start_reasoning_trace(
        self,
        reasoning_type: ReasoningType,
        goal: str,
        metadata: Optional[Dict[str, Any]] = None
    ) -> str:
        """
        开始推理轨迹

        Args:
            reasoning_type: 推理类型
            goal: 目标
            metadata: 元数据

        Returns:
            轨迹ID
        """
        if not self.enable_reasoning:
            return ""

        with self._lock:
            trace_id = f"trace_{self._trace_counter}"
            self._trace_counter += 1

            trace = ReasoningTrace(
                id=trace_id,
                start_time=datetime.now(),
                reasoning_type=reasoning_type,
                goal=goal,
                metadata=metadata or {}
            )

            self._reasoning_traces[trace_id] = trace
            self._current_trace = trace

            self._ensure_session()
            if self._current_session:
                self._current_session.reasoning_traces.append(trace_id)

            self._last_activity = datetime.now()

            return trace_id

    def add_reasoning_step(
        self,
        trace_id: str,
        premise: str,
        inference: str,
        conclusion: str,
        confidence: float = 0.5,
        reasoning_type: ReasoningType = ReasoningType.DEFAULT,
        context: Optional[Dict[str, Any]] = None
    ) -> Optional[str]:
        """
        添加推理步骤

        Args:
            trace_id: 轨迹ID
            premise: 前提
            inference: 推理
            conclusion: 结论
            confidence: 置信度
            reasoning_type: 推理类型
            context: 上下文

        Returns:
            步骤ID
        """
        if not self.enable_reasoning:
            return None

        with self._lock:
            if trace_id not in self._reasoning_traces:
                return None

            trace = self._reasoning_traces[trace_id]
            step_id = f"step_{trace_id}_{len(trace.steps)}"

            step = ReasoningStep(
                id=step_id,
                step_number=len(trace.steps),
                reasoning_type=reasoning_type,
                premise=premise,
                inference=inference,
                conclusion=conclusion,
                confidence=confidence,
                duration_ms=0.0,
                timestamp=datetime.now(),
                context=context or {}
            )

            trace.steps.append(step)

            # 触发回调
            self._trigger_callbacks("reasoning", step)

            self._last_activity = datetime.now()

            return step_id

    def end_reasoning_trace(
        self,
        trace_id: str,
        conclusion: str,
        confidence: float = 0.5,
        success: bool = True
    ):
        """
        结束推理轨迹

        Args:
            trace_id: 轨迹ID
            conclusion: 结论
            confidence: 置信度
            success: 是否成功
        """
        if not self.enable_reasoning:
            return

        with self._lock:
            if trace_id not in self._reasoning_traces:
                return

            trace = self._reasoning_traces[trace_id]
            trace.end_time = datetime.now()
            trace.final_conclusion = conclusion
            trace.confidence = confidence
            trace.success = success

            self._statistics["reasoning_traces"] += 1

            # 清理
            if self._current_trace and self._current_trace.id == trace_id:
                self._current_trace = None

            # 限制数量
            if len(self._reasoning_traces) > self.MAX_REASONING_TRACES:
                oldest = min(
                    self._reasoning_traces.values(),
                    key=lambda t: t.start_time
                )
                del self._reasoning_traces[oldest.id]

            self._last_activity = datetime.now()

    def get_reasoning_trace(self, trace_id: str) -> Optional[ReasoningTrace]:
        """获取推理轨迹"""
        return self._reasoning_traces.get(trace_id)

    def get_current_reasoning(self) -> Optional[ReasoningTrace]:
        """获取当前推理"""
        return self._current_trace

    # ==================== 决策记录 ====================

    def log_decision(
        self,
        decision_type: DecisionType,
        chosen: str,
        reasons: List[str],
        options: Optional[List[str]] = None,
        evidence: Optional[Dict[str, Any]] = None,
        confidence: float = 0.5,
        context: Optional[Dict[str, Any]] = None
    ) -> str:
        """
        记录决策

        Args:
            decision_type: 决策类型
            chosen: 选择
            reasons: 理由
            options: 选项
            evidence: 证据
            confidence: 置信度
            context: 上下文

        Returns:
            决策ID
        """
        if not self.enable_decisions:
            return ""

        with self._lock:
            decision_id = f"decision_{self._decision_counter}"
            self._decision_counter += 1

            decision = DecisionRecord(
                id=decision_id,
                timestamp=datetime.now(),
                decision_type=decision_type,
                options=options or [],
                chosen=chosen,
                reasons=reasons,
                evidence=evidence or {},
                confidence=confidence,
                context=context or {}
            )

            self._decisions[decision_id] = decision

            self._ensure_session()
            if self._current_session:
                self._current_session.decisions.append(decision_id)

            self._trigger_callbacks("decision", decision)
            self._statistics["decisions"] += 1
            self._last_activity = datetime.now()

            # 限制数量
            if len(self._decisions) > self.MAX_DECISIONS:
                oldest = min(
                    self._decisions.values(),
                    key=lambda d: d.timestamp
                )
                del self._decisions[oldest.id]

            return decision_id

    def update_decision_outcome(
        self,
        decision_id: str,
        outcome: str,
        outcome_confidence: float
    ):
        """
        更新决策结果

        Args:
            decision_id: 决策ID
            outcome: 结果
            outcome_confidence: 结果置信度
        """
        with self._lock:
            if decision_id not in self._decisions:
                return

            decision = self._decisions[decision_id]
            decision.outcome = outcome
            decision.outcome_confidence = outcome_confidence

    def get_recent_decisions(
        self,
        limit: int = 10,
        decision_type: Optional[DecisionType] = None
    ) -> List[DecisionRecord]:
        """
        获取最近决策

        Args:
            limit: 数量限制
            decision_type: 决策类型过滤

        Returns:
            决策列表
        """
        decisions = list(self._decisions.values())

        if decision_type:
            decisions = [d for d in decisions if d.decision_type == decision_type]

        decisions.sort(key=lambda d: d.timestamp, reverse=True)
        return decisions[:limit]

    # ==================== 记忆访问 ====================

    def log_memory_access(
        self,
        memory_content: str,
        access_type: str,
        relevance_score: float = 0.5,
        memory_id: Optional[str] = None,
        access_duration_ms: float = 0.0,
        context: Optional[Dict[str, Any]] = None,
        success: bool = True
    ) -> str:
        """
        记录记忆访问

        Args:
            memory_content: 记忆内容
            access_type: 访问类型
            relevance_score: 相关度
            memory_id: 记忆ID
            access_duration_ms: 访问耗时
            context: 上下文
            success: 是否成功

        Returns:
            访问ID
        """
        if not self.enable_memory:
            return ""

        with self._lock:
            access_id = f"mem_{self._access_counter}"
            self._access_counter += 1

            access = MemoryAccess(
                id=access_id,
                timestamp=datetime.now(),
                memory_id=memory_id,
                memory_content=memory_content[:100],  # 截断
                access_type=access_type,
                relevance_score=relevance_score,
                access_duration_ms=access_duration_ms,
                context=context or {},
                success=success
            )

            self._memory_accesses[access_id] = access

            self._ensure_session()
            if self._current_session:
                self._current_session.memory_accesses.append(access_id)

            self._trigger_callbacks("memory", access)
            self._statistics["memory_accesses"] += 1
            self._last_activity = datetime.now()

            # 限制数量
            if len(self._memory_accesses) > self.MAX_MEMORY_ACCESSES:
                oldest = min(
                    self._memory_accesses.values(),
                    key=lambda a: a.timestamp
                )
                del self._memory_accesses[oldest.id]

            return access_id

    def get_memory_access_pattern(
        self,
        time_window_seconds: int = 60
    ) -> Dict[str, Any]:
        """
        获取记忆访问模式

        Args:
            time_window_seconds: 时间窗口

        Returns:
            访问模式
        """
        with self._lock:
            now = datetime.now()
            cutoff = now.timestamp() - time_window_seconds

            recent = [
                a for a in self._memory_accesses.values()
                if a.timestamp.timestamp() > cutoff
            ]

            access_types = {}
            for access in recent:
                access_types[access.access_type] = access_types.get(access.access_type, 0) + 1

            return {
                "total_accesses": len(recent),
                "access_types": access_types,
                "avg_relevance": np.mean([a.relevance_score for a in recent]) if recent else 0,
                "success_rate": sum(1 for a in recent if a.success) / len(recent) if recent else 0
            }

    # ==================== 注意力日志 ====================

    def log_attention(
        self,
        phase: AttentionPhase,
        current_focus: List[str],
        triggered_by: str,
        previous_focus: Optional[List[str]] = None,
        intensity: float = 1.0,
        duration_ms: float = 0.0,
        context: Optional[Dict[str, Any]] = None
    ) -> str:
        """
        记录注意力

        Args:
            phase: 阶段
            current_focus: 当前聚焦
            triggered_by: 触发源
            previous_focus: 之前聚焦
            intensity: 强度
            duration_ms: 持续时间
            context: 上下文

        Returns:
            日志ID
        """
        if not self.enable_attention:
            return ""

        with self._lock:
            log_id = f"attention_{self._attention_counter}"
            self._attention_counter += 1

            log = AttentionLog(
                id=log_id,
                timestamp=datetime.now(),
                phase=phase,
                previous_focus=previous_focus or [],
                current_focus=current_focus,
                triggered_by=triggered_by,
                intensity=intensity,
                duration_ms=duration_ms,
                context=context or {}
            )

            self._attention_logs[log_id] = log

            self._ensure_session()
            if self._current_session:
                self._current_session.attention_logs.append(log_id)

            self._trigger_callbacks("attention", log)
            self._statistics["attention_switches"] += 1
            self._last_activity = datetime.now()

            # 限制数量
            if len(self._attention_logs) > self.MAX_ATTENTION_LOGS:
                oldest = min(
                    self._attention_logs.values(),
                    key=lambda l: l.timestamp
                )
                del self._attention_logs[oldest.id]

            return log_id

    def get_attention_shifts(
        self,
        time_window_seconds: int = 300
    ) -> List[AttentionLog]:
        """
        获取注意力切换

        Args:
            time_window_seconds: 时间窗口

        Returns:
            注意力切换列表
        """
        with self._lock:
            now = datetime.now()
            cutoff = now.timestamp() - time_window_seconds

            shifts = [
                log for log in self._attention_logs.values()
                if log.timestamp.timestamp() > cutoff and log.phase == AttentionPhase.SHIFT
            ]

            return sorted(shifts, key=lambda l: l.timestamp, reverse=True)

    # ==================== 元认知日志 ====================

    def log_meta_cognition(
        self,
        state: MetaCognitiveState,
        target: str,
        observation: str,
        evaluation: Optional[str] = None,
        adjustment: Optional[str] = None,
        confidence: float = 0.5,
        metadata: Optional[Dict[str, Any]] = None
    ) -> str:
        """
        记录元认知

        Args:
            state: 状态
            target: 目标
            observation: 观察
            evaluation: 评估
            adjustment: 调整
            confidence: 置信度
            metadata: 元数据

        Returns:
            日志ID
        """
        if not self.enable_meta:
            return ""

        with self._lock:
            log_id = f"meta_{self._meta_counter}"
            self._meta_counter += 1

            log = MetaCognitiveLog(
                id=log_id,
                timestamp=datetime.now(),
                state=state,
                target=target,
                observation=observation,
                evaluation=evaluation,
                adjustment=adjustment,
                confidence=confidence,
                metadata=metadata or {}
            )

            self._meta_logs[log_id] = log

            self._ensure_session()
            if self._current_session:
                self._current_session.meta_logs.append(log_id)

            self._trigger_callbacks("meta", log)
            self._statistics["meta_observations"] += 1
            self._last_activity = datetime.now()

            # 限制数量
            if len(self._meta_logs) > self.MAX_META_LOGS:
                oldest = min(
                    self._meta_logs.values(),
                    key=lambda l: l.timestamp
                )
                del self._meta_logs[oldest.id]

            return log_id

    def get_meta_cognitive_summary(
        self,
        time_window_seconds: int = 300
    ) -> Dict[str, Any]:
        """
        获取元认知摘要

        Args:
            time_window_seconds: 时间窗口

        Returns:
            摘要
        """
        with self._lock:
            now = datetime.now()
            cutoff = now.timestamp() - time_window_seconds

            recent = [
                log for log in self._meta_logs.values()
                if log.timestamp.timestamp() > cutoff
            ]

            states = {}
            for log in recent:
                states[log.state.value] = states.get(log.state.value, 0) + 1

            return {
                "total_observations": len(recent),
                "states": states,
                "avg_confidence": np.mean([log.confidence for log in recent]) if recent else 0
            }

    # ==================== 学习日志 ====================

    def log_learning(
        self,
        source: str,
        content: str,
        knowledge_type: str,
        integration_result: str,
        confidence_change: float = 0.0,
        related_memories: Optional[List[str]] = None,
        success: bool = True,
        metadata: Optional[Dict[str, Any]] = None
    ) -> str:
        """
        记录学习

        Args:
            source: 来源
            content: 内容
            knowledge_type: 知识类型
            integration_result: 整合结果
            confidence_change: 置信度变化
            related_memories: 相关记忆
            success: 是否成功
            metadata: 元数据

        Returns:
            日志ID
        """
        if not self.enable_learning:
            return ""

        with self._lock:
            log_id = f"learn_{self._learning_counter}"
            self._learning_counter += 1

            log = LearningLog(
                id=log_id,
                timestamp=datetime.now(),
                source=source,
                content=content[:100],  # 截断
                knowledge_type=knowledge_type,
                integration_result=integration_result,
                confidence_change=confidence_change,
                related_memories=related_memories or [],
                success=success,
                metadata=metadata or {}
            )

            self._learning_logs[log_id] = log

            self._ensure_session()
            if self._current_session:
                self._current_session.learning_logs.append(log_id)

            self._trigger_callbacks("learning", log)
            self._statistics["learning_events"] += 1
            self._last_activity = datetime.now()

            # 限制数量
            if len(self._learning_logs) > self.MAX_LEARNING_LOGS:
                oldest = min(
                    self._learning_logs.values(),
                    key=lambda l: l.timestamp
                )
                del self._learning_logs[oldest.id]

            return log_id

    def get_knowledge_growth(
        self,
        time_window_seconds: int = 3600
    ) -> Dict[str, Any]:
        """
        获取知识增长

        Args:
            time_window_seconds: 时间窗口

        Returns:
            知识增长统计
        """
        with self._lock:
            now = datetime.now()
            cutoff = now.timestamp() - time_window_seconds

            recent = [
                log for log in self._learning_logs.values()
                if log.timestamp.timestamp() > cutoff and log.success
            ]

            types = {}
            for log in recent:
                types[log.knowledge_type] = types.get(log.knowledge_type, 0) + 1

            return {
                "total_learned": len(recent),
                "knowledge_types": types,
                "avg_confidence_change": np.mean([log.confidence_change for log in recent]) if recent else 0,
                "success_rate": sum(1 for log in recent if log.success) / len(recent) if recent else 0
            }

    # ==================== 回调机制 ====================

    def register_callback(
        self,
        log_type: str,
        callback: Callable
    ):
        """
        注册回调

        Args:
            log_type: 日志类型
            callback: 回调函数
        """
        if log_type in self._log_callbacks:
            self._log_callbacks[log_type].append(callback)

    def _trigger_callbacks(self, log_type: str, data: Any):
        """触发回调"""
        for callback in self._log_callbacks.get(log_type, []):
            try:
                callback(data)
            except Exception:
                pass

    # ==================== 导出和查询 ====================

    def export_session(
        self,
        session_id: Optional[str] = None,
        include_details: bool = True
    ) -> Dict[str, Any]:
        """
        导出会话

        Args:
            session_id: 会话ID（默认当前）
            include_details: 是否包含详情

        Returns:
            导出数据
        """
        with self._lock:
            # 获取会话
            session = None
            if session_id:
                session = self._sessions.get(session_id)
            elif self._current_session:
                session = self._current_session

            if not session:
                return {}

            # 收集数据
            data = {
                "id": session.id,
                "start_time": session.start_time.isoformat(),
                "end_time": session.end_time.isoformat() if session.end_time else None,
                "metadata": session.metadata,
                "statistics": {
                    "reasoning_traces": len(session.reasoning_traces),
                    "decisions": len(session.decisions),
                    "memory_accesses": len(session.memory_accesses),
                    "attention_logs": len(session.attention_logs),
                    "meta_logs": len(session.meta_logs),
                    "learning_logs": len(session.learning_logs)
                }
            }

            if include_details:
                # 推理轨迹
                data["reasoning_traces"] = [
                    vars(self._reasoning_traces[tid])
                    for tid in session.reasoning_traces
                    if tid in self._reasoning_traces
                ]

                # 决策
                data["decisions"] = [
                    vars(self._decisions[did])
                    for did in session.decisions
                    if did in self._decisions
                ]

                # 记忆访问
                data["memory_accesses"] = [
                    vars(self._memory_accesses[aid])
                    for aid in session.memory_accesses
                    if aid in self._memory_accesses
                ]

                # 注意力
                data["attention_logs"] = [
                    vars(self._attention_logs[lid])
                    for lid in session.attention_logs
                    if lid in self._attention_logs
                ]

                # 元认知
                data["meta_logs"] = [
                    vars(self._meta_logs[lid])
                    for lid in session.meta_logs
                    if lid in self._meta_logs
                ]

                # 学习
                data["learning_logs"] = [
                    vars(self._learning_logs[lid])
                    for lid in session.learning_logs
                    if lid in self._learning_logs
                ]

            return data

    def get_summary(
        self,
        time_window_seconds: int = 3600
    ) -> Dict[str, Any]:
        """
        获取摘要

        Args:
            time_window_seconds: 时间窗口

        Returns:
            摘要
        """
        with self._lock:
            now = datetime.now()
            cutoff = now.timestamp() - time_window_seconds

            return {
                "active_session": self._current_session.id if self._current_session else None,
                "reasoning_traces": sum(
                    1 for t in self._reasoning_traces.values()
                    if t.start_time.timestamp() > cutoff
                ),
                "decisions": sum(
                    1 for d in self._decisions.values()
                    if d.timestamp.timestamp() > cutoff
                ),
                "memory_accesses": sum(
                    1 for a in self._memory_accesses.values()
                    if a.timestamp.timestamp() > cutoff
                ),
                "attention_switches": sum(
                    1 for log in self._attention_logs.values()
                    if log.timestamp.timestamp() > cutoff and log.phase == AttentionPhase.SHIFT
                ),
                "meta_observations": sum(
                    1 for log in self._meta_logs.values()
                    if log.timestamp.timestamp() > cutoff
                ),
                "learning_events": sum(
                    1 for log in self._learning_logs.values()
                    if log.timestamp.timestamp() > cutoff
                )
            }

    def get_statistics(self) -> Dict[str, Any]:
        """获取统计"""
        return {
            **self._statistics,
            "current_session": self._current_session.id if self._current_session else None,
            "total_traces": len(self._reasoning_traces),
            "total_decisions": len(self._decisions),
            "total_memory_accesses": len(self._memory_accesses),
            "total_attention_logs": len(self._attention_logs),
            "total_meta_logs": len(self._meta_logs),
            "total_learning_logs": len(self._learning_logs)
        }

    def clear_old_logs(self, older_than_hours: int = 24):
        """
        清理旧日志

        Args:
            older_than_hours: 保留小时数
        """
        with self._lock:
            cutoff = datetime.now().timestamp() - older_than_hours * 3600

            # 清理
            self._reasoning_traces = {
                k: v for k, v in self._reasoning_traces.items()
                if v.start_time.timestamp() > cutoff
            }

            self._decisions = {
                k: v for k, v in self._decisions.items()
                if v.timestamp.timestamp() > cutoff
            }

            self._memory_accesses = {
                k: v for k, v in self._memory_accesses.items()
                if v.timestamp.timestamp() > cutoff
            }

            self._attention_logs = {
                k: v for k, v in self._attention_logs.items()
                if v.timestamp.timestamp() > cutoff
            }

            self._meta_logs = {
                k: v for k, v in self._meta_logs.items()
                if v.timestamp.timestamp() > cutoff
            }

            self._learning_logs = {
                k: v for k, v in self._learning_logs.items()
                if v.timestamp.timestamp() > cutoff
            }

    def __repr__(self) -> str:
        return (f"CognitiveLogger(session={self._current_session.id if self._current_session else 'none'}, "
                f"traces={len(self._reasoning_traces)}, "
                f"decisions={len(self._decisions)})")
