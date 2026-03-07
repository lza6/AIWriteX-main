"""
负载均衡器 (Load Balancer)
实现任务在多个Agent间的智能分配
"""
import asyncio
from typing import Dict, List, Any, Optional, Callable
from datetime import datetime, timedelta
from enum import Enum
import random
import math

from src.ai_write_x.core.swarm_protocol import (
    SwarmCapabilities, SwarmTask, AgentBid
)
from src.ai_write_x.core.swarm.swarm_agent import AgentNode, AgentStatus
from src.ai_write_x.utils import log


class LoadBalanceStrategy(str, Enum):
    """负载均衡策略"""
    ROUND_ROBIN = "round_robin"          # 轮询
    LEAST_LOADED = "least_loaded"        # 最低负载
    SKILL_MATCH = "skill_match"           # 技能匹配
    PHEROMONE_AWARE = "pheromone_aware"   # 信息素感知
    HYBRID = "hybrid"                     # 混合策略


class AgentMetrics:
    """Agent性能指标"""
    
    def __init__(self, agent_id: str):
        self.agent_id = agent_id
        self.current_load = 0  # 当前任务数
        self.total_tasks = 0
        self.success_count = 0
        self.fail_count = 0
        self.total_latency = 0.0
        self.avg_latency = 0.0
        self.success_rate = 1.0
        self.last_task_time: Optional[datetime] = None
        self.capabilities: List[SwarmCapabilities] = []
        self.pheromone_level = 1.0
    
    def add_task(self, latency: float = 0.0):
        """添加任务"""
        self.current_load += 1
        self.total_tasks += 1
        self.total_latency += latency
        self.avg_latency = self.total_latency / max(1, self.total_tasks)
        self.last_task_time = datetime.now()
    
    def complete_task(self, success: bool = True, latency: float = 0.0):
        """完成任务"""
        self.current_load = max(0, self.current_load - 1)
        if success:
            self.success_count += 1
        else:
            self.fail_count += 1
        self.success_rate = self.success_count / max(1, self.total_tasks)
    
    def get_score(self, strategy: LoadBalanceStrategy = LoadBalanceStrategy.HYBRID) -> float:
        """获取评分"""
        if strategy == LoadBalanceStrategy.LEAST_LOADED:
            # 越低越好
            return self.current_load
        elif strategy == LoadBalanceStrategy.SKILL_MATCH:
            # 成功率加权
            return self.success_rate * 100
        elif strategy == LoadBalanceStrategy.PHEROMONE_AWARD:
            # 信息素级别
            return self.pheromone_level
        else:
            # 混合评分 (越低越好)
            load_factor = self.current_load * 10
            latency_factor = self.avg_latency
            success_factor = (1 - self.success_rate) * 50
            return load_factor + latency_factor + success_factor
    
    def can_accept_task(self) -> bool:
        """是否可以接受任务"""
        # 如果当前负载 >= 3，不接受新任务
        return self.current_load < 3
    
    def to_dict(self) -> Dict:
        return {
            "agent_id": self.agent_id,
            "current_load": self.current_load,
            "total_tasks": self.total_tasks,
            "success_rate": round(self.success_rate, 3),
            "avg_latency": round(self.avg_latency, 3),
            "pheromone_level": round(self.pheromone_level, 3)
        }


class LoadBalancer:
    """负载均衡器"""
    
    def __init__(
        self,
        strategy: LoadBalanceStrategy = LoadBalanceStrategy.HYBRID,
        max_concurrent_per_agent: int = 3
    ):
        self.strategy = strategy
        self.max_concurrent = max_concurrent_per_agent
        self.agent_metrics: Dict[str, AgentMetrics] = {}
        self.agent_instances: Dict[str, AgentNode] = {}
        self.round_robin_index = 0
        self._lock = asyncio.Lock()
    
    def register_agent(self, agent: AgentNode):
        """注册Agent"""
        metrics = AgentMetrics(agent.agent_id)
        metrics.capabilities = agent.capabilities
        metrics.pheromone_level = agent.pheromone_level
        
        self.agent_metrics[agent.agent_id] = metrics
        self.agent_instances[agent.agent_id] = agent
        
        log.print_log(f"[负载均衡] 注册Agent: {agent.agent_id}", "debug")
    
    def unregister_agent(self, agent_id: str):
        """注销Agent"""
        if agent_id in self.agent_metrics:
            del self.agent_metrics[agent_id]
        if agent_id in self.agent_instances:
            del self.agent_instances[agent_id]
        log.print_log(f"[负载均衡] 注销Agent: {agent_id}", "debug")
    
    def update_agent_status(self, agent_id: str, pheromone_level: float = None):
        """更新Agent状态"""
        if agent_id in self.agent_metrics:
            if pheromone_level is not None:
                self.agent_metrics[agent_id].pheromone_level = pheromone_level
    
    async def select_agent(
        self,
        required_capabilities: List[SwarmCapabilities] = None,
        exclude_agents: List[str] = None
    ) -> Optional[str]:
        """选择最佳Agent"""
        async with self._lock:
            exclude_agents = exclude_agents or []
            
            # 过滤可用Agent
            candidates = []
            for agent_id, metrics in self.agent_metrics.items():
                if agent_id in exclude_agents:
                    continue
                if not metrics.can_accept_task():
                    continue
                candidates.append(agent_id)
            
            if not candidates:
                return None
            
            # 根据策略选择
            if self.strategy == LoadBalanceStrategy.ROUND_ROBIN:
                return self._round_robin_select(candidates)
            elif self.strategy == LoadBalanceStrategy.LEAST_LOADED:
                return self._least_loaded_select(candidates)
            elif self.strategy == LoadBalanceStrategy.SKILL_MATCH:
                return self._skill_match_select(candidates, required_capabilities)
            elif self.strategy == LoadBalanceStrategy.PHEROMONE_AWARE:
                return self._pheromone_select(candidates)
            else:  # HYBRID
                return self._hybrid_select(candidates, required_capabilities)
    
    def _round_robin_select(self, candidates: List[str]) -> str:
        """轮询选择"""
        agent_id = candidates[self.round_robin_index % len(candidates)]
        self.round_robin_index += 1
        return agent_id
    
    def _least_loaded_select(self, candidates: List[str]) -> str:
        """最低负载选择"""
        min_load = float('inf')
        selected = candidates[0]
        
        for agent_id in candidates:
            load = self.agent_metrics[agent_id].current_load
            if load < min_load:
                min_load = load
                selected = agent_id
        
        return selected
    
    def _skill_match_select(
        self,
        candidates: List[str],
        required_capabilities: List[SwarmCapabilities]
    ) -> str:
        """技能匹配选择"""
        if not required_capabilities:
            return random.choice(candidates)
        
        # 评分候选者
        scored = []
        for agent_id in candidates:
            metrics = self.agent_metrics[agent_id]
            # 计算技能匹配度
            capability_score = 0
            for cap in required_capabilities:
                if cap in metrics.capabilities:
                    capability_score += 1
            
            capability_score = capability_score / len(required_capabilities)
            # 综合评分 = 技能匹配度 * 成功率
            score = capability_score * metrics.success_rate
            scored.append((agent_id, score))
        
        # 按评分排序，选择最高的
        scored.sort(key=lambda x: x[1], reverse=True)
        return scored[0][0]
    
    def _pheromone_select(self, candidates: List[str]) -> str:
        """信息素感知选择"""
        max_pheromone = -1.0
        selected = candidates[0]
        
        for agent_id in candidates:
            pheromone = self.agent_metrics[agent_id].pheromone_level
            if pheromone > max_pheromone:
                max_pheromone = pheromone
                selected = agent_id
        
        return selected
    
    def _hybrid_select(
        self,
        candidates: List[str],
        required_capabilities: List[SwarmCapabilities]
    ) -> str:
        """混合策略选择"""
        best_score = float('inf')
        selected = candidates[0]
        
        for agent_id in candidates:
            metrics = self.agent_metrics[agent_id]
            
            # 计算各因素得分
            load_score = metrics.current_load * 10
            latency_score = metrics.avg_latency * 5
            success_penalty = (1 - metrics.success_rate) * 30
            pheromone_bonus = metrics.pheromone_level * 5
            
            # 技能匹配加分
            skill_bonus = 0
            if required_capabilities:
                for cap in required_capabilities:
                    if cap in metrics.capabilities:
                        skill_bonus += 20
            
            # 综合得分
            total_score = load_score + latency_score + success_penalty - pheromone_bonus - skill_bonus
            
            if total_score < best_score:
                best_score = total_score
                selected = agent_id
        
        return selected
    
    async def assign_task(self, agent_id: str, task_id: str) -> bool:
        """分配任务"""
        async with self._lock:
            if agent_id not in self.agent_metrics:
                return False
            
            self.agent_metrics[agent_id].add_task()
            log.print_log(f"[负载均衡] 分配任务 {task_id} -> {agent_id}", "debug")
            return True
    
    async def complete_task(
        self,
        agent_id: str,
        task_id: str,
        success: bool = True,
        latency: float = 0.0
    ):
        """完成任务回调"""
        async with self._lock:
            if agent_id in self.agent_metrics:
                self.agent_metrics[agent_id].complete_task(success, latency)
                log.print_log(f"[负载均衡] 任务 {task_id} 完成, Agent={agent_id}, 成功={success}", "debug")
    
    async def rebalance(self) -> Dict[str, Any]:
        """重新平衡负载"""
        async with self._lock:
            rebalanced = []
            
            # 找出过载的Agent
            overloaded = []
            for agent_id, metrics in self.agent_metrics.items():
                if metrics.current_load > self.max_concurrent:
                    overloaded.append(agent_id)
            
            # 尝试将任务转移到空闲Agent
            for overloaded_id in overloaded:
                metrics = self.agent_metrics[overloaded_id]
                if metrics.current_load > 0:
                    # 找到最空闲的Agent
                    candidates = [
                        a for a in self.agent_metrics.keys()
                        if a != overloaded_id and self.agent_metrics[a].current_load < metrics.current_load
                    ]
                    
                    if candidates:
                        target_id = self._least_loaded_select(candidates)
                        # 记录重平衡
                        rebalanced.append({
                            "from": overloaded_id,
                            "to": target_id,
                            "task_count": 1
                        })
            
            return {"rebalanced": rebalanced, "count": len(rebalanced)}
    
    def get_stats(self) -> Dict[str, Any]:
        """获取统计"""
        total_load = sum(m.current_load for m in self.agent_metrics.values())
        total_capacity = len(self.agent_metrics) * self.max_concurrent
        
        agent_stats = [m.to_dict() for m in self.agent_metrics.values()]
        
        return {
            "strategy": self.strategy.value,
            "total_agents": len(self.agent_metrics),
            "total_load": total_load,
            "total_capacity": total_capacity,
            "utilization": round(total_load / max(1, total_capacity), 3),
            "agents": agent_stats
        }
    
    async def get_agent_load_report(self) -> Dict[str, Any]:
        """获取负载报告"""
        async with self._lock:
            report = {
                "timestamp": datetime.now().isoformat(),
                "agents": []
            }
            
            for agent_id, metrics in self.agent_metrics.items():
                agent_info = {
                    "agent_id": agent_id,
                    "load": f"{metrics.current_load}/{self.max_concurrent}",
                    "utilization": round(metrics.current_load / self.max_concurrent, 2),
                    "success_rate": round(metrics.success_rate, 3),
                    "avg_latency": round(metrics.avg_latency, 2),
                    "can_accept": metrics.can_accept_task()
                }
                report["agents"].append(agent_info)
            
            # 按负载排序
            report["agents"].sort(key=lambda x: x["utilization"], reverse=True)
            
            return report


class TaskQueueManager:
    """任务队列管理器"""
    
    def __init__(self, load_balancer: LoadBalancer):
        self.load_balancer = load_balancer
        self.pending_tasks: asyncio.Queue = asyncio.Queue()
        self.running_tasks: Dict[str, str] = {}  # task_id -> agent_id
        self.completed_tasks: Dict[str, Any] = {}
    
    async def submit_task(
        self,
        task: SwarmTask,
        required_capabilities: List[SwarmCapabilities] = None
    ) -> Optional[str]:
        """提交任务"""
        # 选择最佳Agent
        agent_id = await self.load_balancer.select_agent(required_capabilities)
        
        if not agent_id:
            # 没有可用Agent，加入队列
            await self.pending_tasks.put(task)
            log.print_log(f"[任务队列] 任务 {task.task_id} 加入等待队列", "debug")
            return None
        
        # 分配任务
        success = await self.load_balancer.assign_task(agent_id, task.task_id)
        
        if success:
            self.running_tasks[task.task_id] = agent_id
            # 将任务交给Agent执行
            agent = self.load_balancer.agent_instances.get(agent_id)
            if agent:
                await agent.task_queue.put(task)
            
            return agent_id
        
        return None
    
    async def task_completed(
        self,
        task_id: str,
        success: bool = True,
        latency: float = 0.0
    ):
        """任务完成"""
        if task_id in self.running_tasks:
            agent_id = self.running_tasks.pop(task_id)
            await self.load_balancer.complete_task(agent_id, task_id, success, latency)
            
            # 检查等待队列
            try:
                task = self.pending_tasks.get_nowait()
                await self.submit_task(task)
            except asyncio.QueueEmpty:
                pass
    
    async def get_queue_status(self) -> Dict[str, Any]:
        """获取队列状态"""
        return {
            "pending": self.pending_tasks.qsize(),
            "running": len(self.running_tasks),
            "completed": len(self.completed_tasks)
        }
