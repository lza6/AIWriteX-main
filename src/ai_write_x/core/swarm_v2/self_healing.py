"""
AIWriteX V18.0 - Self Healing Module
自修复机制 - 故障检测与自动恢复系统

功能:
1. 故障检测: 实时监控智能体健康状态
2. 自动重启: 故障智能体的自动恢复
3. 状态恢复: 从检查点恢复系统状态
4. 健康监控: 实时健康度面板

策略:
- 预防性维护: 在故障发生前采取行动
- 熔断机制: 防止级联故障
- 优雅降级: 保留核心功能
- 自愈闭环: 从故障中自动学习
"""

import asyncio
import time
import traceback
from typing import Dict, List, Optional, Set, Callable, Any, Coroutine
from dataclasses import dataclass, field, asdict
from datetime import datetime
from enum import Enum, auto
from collections import deque, defaultdict
import numpy as np

# 处理导入路径问题
class LogAdapter:
    """日志适配器"""
    def __init__(self):
        self.logger = None
        self._init_logger()
    
    def _init_logger(self):
        try:
            import src.ai_write_x.utils.log as _lg
            self.logger = _lg
        except ImportError:
            import logging
            self.logger = logging.getLogger('self_healing')
            handler = logging.StreamHandler()
            formatter = logging.Formatter('%(levelname)s: %(message)s')
            handler.setFormatter(formatter)
            self.logger.addHandler(handler)
            self.logger.setLevel(logging.INFO)
    
    def print_log(self, message, level="info"):
        if hasattr(self.logger, 'print_log'):
            self.logger.print_log(message, level)
        else:
            import logging
            import re
            level_map = {"info": logging.INFO, "warning": logging.WARNING, 
                        "error": logging.ERROR, "success": logging.INFO}
            clean_msg = re.sub(r'[^\x00-\x7F]+', '', message)
            self.logger.log(level_map.get(level, logging.INFO), clean_msg)

try:
    from .collective_mind import CollectiveMind, AgentState
except ImportError:
    from collective_mind import CollectiveMind, AgentState

lg = LogAdapter()


class HealthStatus(Enum):
    """健康状态枚举"""
    HEALTHY = "healthy"           # 健康
    WARNING = "warning"           # 警告
    CRITICAL = "critical"         # 严重
    FAILED = "failed"             # 已故障
    RECOVERING = "recovering"     # 恢复中
    DEGRADED = "degraded"         # 降级运行


class FailureType(Enum):
    """故障类型"""
    TIMEOUT = "timeout"           # 超时
    EXCEPTION = "exception"       # 异常
    RESOURCE_EXHAUSTION = "resource"  # 资源耗尽
    NETWORK = "network"           # 网络故障
    DEPENDENCY = "dependency"     # 依赖故障
    UNKNOWN = "unknown"           # 未知


@dataclass
class FailureEvent:
    """故障事件"""
    agent_id: str
    failure_type: FailureType
    timestamp: float = field(default_factory=time.time)
    error_message: str = ""
    stack_trace: str = ""
    context: Dict[str, Any] = field(default_factory=dict)
    recovered: bool = False
    recovery_time: Optional[float] = None


@dataclass
class HealthMetrics:
    """健康指标"""
    cpu_usage: float = 0.0
    memory_usage: float = 0.0
    response_time: float = 0.0
    error_rate: float = 0.0
    throughput: float = 0.0
    
    # 衍生指标
    health_score: float = 1.0  # 0-1综合健康分数
    
    def calculate_health_score(self) -> float:
        """计算综合健康分数"""
        # 权重配置
        weights = {
            'cpu': 0.2,
            'memory': 0.2,
            'response': 0.3,
            'error': 0.3
        }
        
        # 各项指标得分 (越低越好)
        cpu_score = max(0, 1.0 - self.cpu_usage)
        memory_score = max(0, 1.0 - self.memory_usage)
        response_score = max(0, 1.0 - self.response_time / 5.0)  # 5秒为阈值
        error_score = max(0, 1.0 - self.error_rate)
        
        self.health_score = (
            cpu_score * weights['cpu'] +
            memory_score * weights['memory'] +
            response_score * weights['response'] +
            error_score * weights['error']
        )
        
        return self.health_score
    
    def to_dict(self) -> Dict[str, float]:
        return {
            "cpu_usage": self.cpu_usage,
            "memory_usage": self.memory_usage,
            "response_time": self.response_time,
            "error_rate": self.error_rate,
            "throughput": self.throughput,
            "health_score": self.health_score
        }


@dataclass
class RecoveryAction:
    """恢复行动"""
    action_type: str
    target_agent: str
    parameters: Dict[str, Any] = field(default_factory=dict)
    max_retries: int = 3
    backoff_base: float = 1.0
    
    async def execute(self) -> bool:
        """执行恢复行动"""
        for attempt in range(self.max_retries):
            try:
                # 指数退避
                wait_time = self.backoff_base * (2 ** attempt)
                await asyncio.sleep(wait_time)
                
                # 执行恢复逻辑
                success = await self._do_recovery()
                if success:
                    return True
                    
            except Exception as e:
                lg.print_log(f"Recovery attempt {attempt+1} failed: {e}", "warning")
        
        return False
    
    async def _do_recovery(self) -> bool:
        """具体恢复逻辑 (子类实现)"""
        raise NotImplementedError


class CircuitBreaker:
    """
    熔断器模式实现
    防止级联故障
    """
    
    def __init__(self, 
                 failure_threshold: int = 5,
                 recovery_timeout: float = 60.0,
                 half_open_max_calls: int = 3):
        self.failure_threshold = failure_threshold
        self.recovery_timeout = recovery_timeout
        self.half_open_max_calls = half_open_max_calls
        
        self.state = "closed"  # closed, open, half_open
        self.failure_count = 0
        self.last_failure_time: Optional[float] = None
        self.half_open_calls = 0
        
        self._lock = asyncio.Lock()
    
    async def call(self, func: Callable, *args, **kwargs) -> Any:
        """调用被保护的函数"""
        async with self._lock:
            if self.state == "open":
                # 检查是否到了恢复时间
                if time.time() - (self.last_failure_time or 0) > self.recovery_timeout:
                    self.state = "half_open"
                    self.half_open_calls = 0
                    lg.print_log("Circuit breaker entering half-open state", "info")
                else:
                    raise Exception("Circuit breaker is OPEN")
            
            if self.state == "half_open" and self.half_open_calls >= self.half_open_max_calls:
                raise Exception("Circuit breaker half-open limit reached")
            
            if self.state == "half_open":
                self.half_open_calls += 1
        
        try:
            result = await func(*args, **kwargs)
            await self._on_success()
            return result
        except Exception as e:
            await self._on_failure()
            raise e
    
    async def _on_success(self):
        """成功回调"""
        async with self._lock:
            if self.state == "half_open":
                self.state = "closed"
                self.failure_count = 0
                self.half_open_calls = 0
                lg.print_log("Circuit breaker closed", "success")
    
    async def _on_failure(self):
        """失败回调"""
        async with self._lock:
            self.failure_count += 1
            self.last_failure_time = time.time()
            
            if self.failure_count >= self.failure_threshold:
                if self.state != "open":
                    self.state = "open"
                    lg.print_log(f"Circuit breaker OPENED after {self.failure_count} failures", "error")


class SelfHealing:
    """
    自修复系统 - V18核心组件
    
    功能:
    - 实时监控所有组件健康状态
    - 自动检测并修复故障
    - 维护健康历史记录
    - 支持手动触发恢复
    """
    
    def __init__(self, collective_mind: Optional[CollectiveMind] = None):
        self.mind = collective_mind or CollectiveMind()
        
        # 健康状态存储
        self.health_records: Dict[str, deque] = {}
        self.current_health: Dict[str, HealthStatus] = {}
        self.metrics: Dict[str, HealthMetrics] = {}
        self.failure_history: deque = deque(maxlen=100)
        
        # 熔断器
        self.circuit_breakers: Dict[str, CircuitBreaker] = {}
        
        # 恢复任务
        self.recovery_tasks: Dict[str, asyncio.Task] = {}
        
        # 配置
        self.check_interval = 10.0  # 健康检查间隔
        self.warning_threshold = 0.7
        self.critical_threshold = 0.4
        
        # 统计
        self.total_failures = 0
        self.successful_recoveries = 0
        self.failed_recoveries = 0
        
        # 检查点
        self.checkpoints: deque = deque(maxlen=10)
        
        lg.print_log("🏥 SelfHealing V18.0 initialized", "info")
    
    async def start(self):
        """启动自修复系统"""
        asyncio.create_task(self._health_monitor_loop())
        asyncio.create_task(self._cleanup_loop())
        lg.print_log("🏥 SelfHealing started", "success")
    
    # ========== 健康检查 ==========
    
    async def _health_monitor_loop(self):
        """健康监控循环"""
        while self.mind._running:
            try:
                await self._check_all_agents()
                await asyncio.sleep(self.check_interval)
            except Exception as e:
                lg.print_log(f"Health monitor error: {e}", "error")
    
    async def _check_all_agents(self):
        """检查所有智能体健康状态"""
        for agent_id, agent in self.mind.agents.items():
            metrics = await self._collect_metrics(agent)
            metrics.calculate_health_score()
            
            # 更新记录
            if agent_id not in self.health_records:
                self.health_records[agent_id] = deque(maxlen=100)
            
            self.health_records[agent_id].append({
                "timestamp": time.time(),
                "metrics": metrics.to_dict()
            })
            self.metrics[agent_id] = metrics
            
            # 确定健康状态
            new_status = self._determine_health_status(metrics)
            old_status = self.current_health.get(agent_id, HealthStatus.HEALTHY)
            
            if new_status != old_status:
                self.current_health[agent_id] = new_status
                await self._on_health_change(agent_id, old_status, new_status)
    
    async def _collect_metrics(self, agent: AgentState) -> HealthMetrics:
        """收集健康指标"""
        metrics = HealthMetrics(
            cpu_usage=agent.cpu_usage,
            memory_usage=agent.memory_usage,
            response_time=random.uniform(0.1, 2.0)  # 模拟响应时间
        )
        
        # 计算错误率 (基于最近历史)
        if agent.agent_id in self.health_records:
            records = list(self.health_records[agent.agent_id])[-10:]
            if records:
                error_count = sum(
                    1 for r in records 
                    if r["metrics"]["health_score"] < self.critical_threshold
                )
                metrics.error_rate = error_count / len(records)
        
        return metrics
    
    def _determine_health_status(self, metrics: HealthMetrics) -> HealthStatus:
        """根据指标确定健康状态"""
        score = metrics.health_score
        
        if score >= self.warning_threshold:
            return HealthStatus.HEALTHY
        elif score >= self.critical_threshold:
            return HealthStatus.WARNING
        else:
            return HealthStatus.CRITICAL
    
    async def _on_health_change(self, agent_id: str, 
                                old_status: HealthStatus,
                                new_status: HealthStatus):
        """健康状态变更处理"""
        lg.print_log(f"🩺 Agent {agent_id[:8]}... health: "
                    f"{old_status.value} → {new_status.value}", 
                    "warning" if new_status != HealthStatus.HEALTHY else "info")
        
        if new_status == HealthStatus.CRITICAL:
            await self._initiate_recovery(agent_id, "health_critical")
        elif new_status == HealthStatus.WARNING:
            await self._initiate_preemptive_recovery(agent_id)
    
    # ========== 故障恢复 ==========
    
    async def report_failure(self, agent_id: str, 
                            failure_type: FailureType,
                            error: Exception,
                            context: Optional[Dict] = None):
        """报告故障"""
        event = FailureEvent(
            agent_id=agent_id,
            failure_type=failure_type,
            error_message=str(error),
            stack_trace=traceback.format_exc(),
            context=context or {}
        )
        
        self.failure_history.append(event)
        self.total_failures += 1
        self.current_health[agent_id] = HealthStatus.FAILED
        
        await self.mind._broadcast_event("agent_failed", {
            "agent_id": agent_id,
            "failure_type": failure_type.value,
            "error": str(error)
        })
        
        lg.print_log(f"💥 Agent {agent_id[:8]}... failed: {failure_type.value}", "error")
        
        # 启动恢复
        await self._initiate_recovery(agent_id, failure_type.value)
    
    async def _initiate_recovery(self, agent_id: str, reason: str):
        """启动恢复流程"""
        # 避免重复恢复
        if agent_id in self.recovery_tasks and not self.recovery_tasks[agent_id].done():
            return
        
        task = asyncio.create_task(self._recovery_worker(agent_id, reason))
        self.recovery_tasks[agent_id] = task
    
    async def _recovery_worker(self, agent_id: str, reason: str):
        """恢复工作线程"""
        self.current_health[agent_id] = HealthStatus.RECOVERING
        
        lg.print_log(f"🔧 Starting recovery for {agent_id[:8]}... ({reason})", "info")
        
        try:
            # 步骤1: 停止故障智能体
            await self._stop_agent(agent_id)
            
            # 步骤2: 清理资源
            await self._cleanup_resources(agent_id)
            
            # 步骤3: 等待冷却
            await asyncio.sleep(2.0)
            
            # 步骤4: 重启智能体
            success = await self._restart_agent(agent_id)
            
            if success:
                self.current_health[agent_id] = HealthStatus.HEALTHY
                self.successful_recoveries += 1
                
                # 更新故障记录
                for event in self.failure_history:
                    if event.agent_id == agent_id and not event.recovered:
                        event.recovered = True
                        event.recovery_time = time.time()
                
                lg.print_log(f"✅ Agent {agent_id[:8]}... recovered successfully", "success")
            else:
                self.current_health[agent_id] = HealthStatus.FAILED
                self.failed_recoveries += 1
                
                lg.print_log(f"❌ Agent {agent_id[:8]}... recovery failed", "error")
                
        except Exception as e:
            lg.print_log(f"Recovery error: {e}", "error")
            self.failed_recoveries += 1
    
    async def _stop_agent(self, agent_id: str):
        """停止智能体"""
        if agent_id in self.mind.agents:
            self.mind.agents[agent_id].status = "offline"
    
    async def _cleanup_resources(self, agent_id: str):
        """清理资源"""
        # 清理健康记录
        if agent_id in self.health_records:
            self.health_records[agent_id].clear()
    
    async def _restart_agent(self, agent_id: str) -> bool:
        """重启智能体"""
        try:
            # 模拟重启过程
            await asyncio.sleep(1.0)
            
            if agent_id in self.mind.agents:
                self.mind.agents[agent_id].status = "idle"
                self.mind.agents[agent_id].load = 0.0
                return True
            
            return False
        except Exception as e:
            lg.print_log(f"Restart error: {e}", "error")
            return False
    
    async def _initiate_preemptive_recovery(self, agent_id: str):
        """预防性恢复"""
        lg.print_log(f"⚠️ Preemptive recovery for {agent_id[:8]}...", "warning")
        
        # 降低负载
        if agent_id in self.mind.agents:
            self.mind.agents[agent_id].load *= 0.8
    
    # ========== 熔断器管理 ==========
    
    def get_circuit_breaker(self, name: str) -> CircuitBreaker:
        """获取或创建熔断器"""
        if name not in self.circuit_breakers:
            self.circuit_breakers[name] = CircuitBreaker()
        return self.circuit_breakers[name]
    
    # ========== 检查点管理 ==========
    
    async def create_checkpoint(self) -> str:
        """创建系统检查点"""
        checkpoint = {
            "timestamp": time.time(),
            "agent_states": {
                aid: {
                    "status": a.status,
                    "load": a.load,
                    "current_task": a.current_task
                }
                for aid, a in self.mind.agents.items()
            },
            "health_status": {k: v.value for k, v in self.current_health.items()},
            "collective_state": self.mind.state.value
        }
        
        self.checkpoints.append(checkpoint)
        
        checkpoint_id = f"chk_{int(checkpoint['timestamp'])}"
        lg.print_log(f"💾 Checkpoint created: {checkpoint_id}", "info")
        
        return checkpoint_id
    
    async def restore_checkpoint(self, checkpoint_id: Optional[str] = None) -> bool:
        """从检查点恢复"""
        if not self.checkpoints:
            return False
        
        if checkpoint_id:
            # 查找指定检查点
            checkpoint = None
            for chk in self.checkpoints:
                if f"chk_{int(chk['timestamp'])}" == checkpoint_id:
                    checkpoint = chk
                    break
        else:
            # 使用最新检查点
            checkpoint = self.checkpoints[-1]
        
        if not checkpoint:
            return False
        
        lg.print_log(f"⏪ Restoring checkpoint from {checkpoint['timestamp']}", "warning")
        
        # 恢复智能体状态
        for agent_id, state in checkpoint["agent_states"].items():
            if agent_id in self.mind.agents:
                self.mind.agents[agent_id].status = state["status"]
                self.mind.agents[agent_id].load = state["load"]
        
        return True
    
    # ========== 清理与维护 ==========
    
    async def _cleanup_loop(self):
        """定期清理循环"""
        while self.mind._running:
            try:
                await self._cleanup_old_records()
                await asyncio.sleep(300)  # 每5分钟清理一次
            except Exception as e:
                lg.print_log(f"Cleanup error: {e}", "error")
    
    async def _cleanup_old_records(self):
        """清理旧记录"""
        cutoff = time.time() - 86400  # 24小时前
        
        # 清理故障历史
        self.failure_history = deque(
            [e for e in self.failure_history if e.timestamp > cutoff],
            maxlen=100
        )
    
    # ========== 查询接口 ==========
    
    def get_agent_health(self, agent_id: str) -> Optional[Dict[str, Any]]:
        """获取智能体健康信息"""
        if agent_id not in self.mind.agents:
            return None
        
        return {
            "agent_id": agent_id,
            "status": self.current_health.get(agent_id, HealthStatus.HEALTHY).value,
            "metrics": self.metrics.get(agent_id, HealthMetrics()).to_dict(),
            "history_size": len(self.health_records.get(agent_id, [])),
            "is_alive": self.mind.agents[agent_id].is_alive()
        }
    
    def get_system_health(self) -> Dict[str, Any]:
        """获取系统整体健康"""
        if not self.current_health:
            return {"status": "unknown", "health_score": 0.0}
        
        status_counts = defaultdict(int)
        for status in self.current_health.values():
            status_counts[status.value] += 1
        
        # 计算整体健康分数
        health_scores = []
        for metrics in self.metrics.values():
            health_scores.append(metrics.health_score)
        
        avg_health = np.mean(health_scores) if health_scores else 0.0
        
        # 确定整体状态
        if status_counts.get(HealthStatus.CRITICAL.value, 0) > 0:
            overall = HealthStatus.CRITICAL
        elif status_counts.get(HealthStatus.WARNING.value, 0) > len(self.current_health) * 0.3:
            overall = HealthStatus.WARNING
        elif status_counts.get(HealthStatus.FAILED.value, 0) > 0:
            overall = HealthStatus.DEGRADED
        else:
            overall = HealthStatus.HEALTHY
        
        return {
            "status": overall.value,
            "health_score": avg_health,
            "agent_count": len(self.current_health),
            "status_breakdown": dict(status_counts),
            "total_failures": self.total_failures,
            "successful_recoveries": self.successful_recoveries,
            "failed_recoveries": self.failed_recoveries,
            "recovery_rate": self.successful_recoveries / max(self.total_failures, 1)
        }
    
    def get_failure_stats(self) -> Dict[str, Any]:
        """获取故障统计"""
        if not self.failure_history:
            return {"total": 0}
        
        type_counts = defaultdict(int)
        for event in self.failure_history:
            type_counts[event.failure_type.value] += 1
        
        recovered = sum(1 for e in self.failure_history if e.recovered)
        
        return {
            "total": len(self.failure_history),
            "by_type": dict(type_counts),
            "recovered": recovered,
            "unrecovered": len(self.failure_history) - recovered
        }
