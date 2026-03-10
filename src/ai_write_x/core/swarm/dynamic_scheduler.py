"""
动态调度策略系统 V3 (Dynamic Scheduler V3)

解决痛点:
3. 调度策略静态 → 实现多目标优化、动态策略选择、长期目标优化

核心特性:
- 多目标优化 (负载均衡、延迟、成功率、资源利用率)
- 动态策略选择 (基于当前环境状态)
- 长期目标优化 (强化学习 + 进化算法)
- 策略组合与自适应权重
"""
import asyncio
from typing import Dict, List, Any, Optional, Tuple, Callable
from datetime import datetime, timedelta
from dataclasses import dataclass, field
from enum import Enum
from collections import defaultdict, deque
import numpy as np
import random
import json

from src.ai_write_x.utils import log


class ObjectiveType(Enum):
    """优化目标类型"""
    LOAD_BALANCE = "load_balance"      # 负载均衡
    MIN_LATENCY = "min_latency"        # 最小延迟
    MAX_SUCCESS = "max_success"        # 最大成功率
    RESOURCE_EFF = "resource_eff"      # 资源效率
    FAIRNESS = "fairness"              # 公平性
    COST_MIN = "cost_min"              # 成本最小化


class SchedulingPolicy(Enum):
    """调度策略"""
    ROUND_ROBIN = "round_robin"
    LEAST_LOADED = "least_loaded"
    SKILL_MATCH = "skill_match"
    PHEROMONE_AWARE = "pheromone_aware"
    PREDICTIVE = "predictive"
    MULTI_OBJECTIVE = "multi_objective"
    Q_LEARNING = "q_learning"


@dataclass
class AgentCapabilities:
    """Agent能力"""
    cpu_capacity: float = 1.0
    memory_capacity: float = 1.0
    skills: List[str] = field(default_factory=list)
    specialties: List[str] = field(default_factory=list)
    cost_per_task: float = 1.0


@dataclass
class AgentState:
    """Agent状态"""
    agent_id: str
    cpu_usage: float = 0.0
    memory_usage: float = 0.0
    active_tasks: int = 0
    task_queue_size: int = 0
    avg_response_time: float = 0.0
    success_rate: float = 1.0
    last_updated: datetime = field(default_factory=datetime.now)
    capabilities: AgentCapabilities = field(default_factory=AgentCapabilities)
    
    @property
    def load_score(self) -> float:
        """综合负载分数"""
        return (
            0.3 * self.cpu_usage +
            0.2 * self.memory_usage +
            0.2 * min(self.task_queue_size / 50.0, 1.0) +
            0.15 * min(self.avg_response_time / 5.0, 1.0) +
            0.15 * (1.0 - self.success_rate)
        )
    
    @property
    def available_capacity(self) -> float:
        """可用容量"""
        return max(0.0, 1.0 - self.load_score)


@dataclass
class TaskRequirements:
    """任务需求"""
    cpu_demand: float = 0.1
    memory_demand: float = 0.1
    required_skills: List[str] = field(default_factory=list)
    priority: int = 5  # 1-10
    deadline: Optional[datetime] = None
    estimated_duration: float = 60.0  # 秒


@dataclass
class SchedulingDecision:
    """调度决策"""
    agent_id: str
    policy_used: SchedulingPolicy
    objective_scores: Dict[ObjectiveType, float]
    confidence: float
    estimated_completion_time: float


class MultiObjectiveOptimizer:
    """
    多目标优化器
    使用加权目标和帕累托最优概念
    """
    
    def __init__(self):
        # 目标权重 (动态调整)
        self.objective_weights: Dict[ObjectiveType, float] = {
            ObjectiveType.LOAD_BALANCE: 0.25,
            ObjectiveType.MIN_LATENCY: 0.25,
            ObjectiveType.MAX_SUCCESS: 0.20,
            ObjectiveType.RESOURCE_EFF: 0.20,
            ObjectiveType.FAIRNESS: 0.10
        }
        
        # 历史性能记录
        self.objective_history: Dict[ObjectiveType, deque] = {
            obj: deque(maxlen=100) for obj in ObjectiveType
        }
    
    def evaluate_objectives(
        self,
        agent_state: AgentState,
        task_req: TaskRequirements,
        all_states: List[AgentState]
    ) -> Dict[ObjectiveType, float]:
        """评估所有目标"""
        
        # 1. 负载均衡目标 (越低越好)
        avg_load = np.mean([s.load_score for s in all_states])
        load_balance_score = 1.0 - abs(agent_state.load_score - avg_load)
        
        # 2. 延迟目标 (响应时间越短越好)
        latency_score = 1.0 - min(agent_state.avg_response_time / 10.0, 1.0)
        
        # 3. 成功率目标
        success_score = agent_state.success_rate
        
        # 4. 资源效率 (资源利用率接近最优)
        optimal_util = 0.7
        resource_eff_score = 1.0 - abs(agent_state.load_score - optimal_util)
        
        # 5. 公平性 (基于历史任务分配)
        fairness_score = 1.0  # 简化处理
        
        return {
            ObjectiveType.LOAD_BALANCE: load_balance_score,
            ObjectiveType.MIN_LATENCY: latency_score,
            ObjectiveType.MAX_SUCCESS: success_score,
            ObjectiveType.RESOURCE_EFF: resource_eff_score,
            ObjectiveType.FAIRNESS: fairness_score
        }
    
    def compute_utility(self, objective_scores: Dict[ObjectiveType, float]) -> float:
        """计算综合效用"""
        utility = sum(
            self.objective_weights[obj] * score 
            for obj, score in objective_scores.items()
        )
        return utility
    
    def adapt_weights(self, recent_performance: Dict[ObjectiveType, float]):
        """根据最近性能自适应调整目标权重"""
        # 如果某个目标表现差，增加其权重
        for obj, perf in recent_performance.items():
            self.objective_history[obj].append(perf)
            
            if len(self.objective_history[obj]) >= 20:
                recent_avg = np.mean(list(self.objective_history[obj])[-20:])
                
                # 性能差于阈值，增加权重
                if recent_avg < 0.6:
                    self.objective_weights[obj] = min(
                        self.objective_weights[obj] * 1.1, 0.5
                    )
                # 性能很好，可以适当降低权重
                elif recent_avg > 0.9:
                    self.objective_weights[obj] = max(
                        self.objective_weights[obj] * 0.95, 0.05
                    )
        
        # 归一化权重
        total = sum(self.objective_weights.values())
        for obj in self.objective_weights:
            self.objective_weights[obj] /= total


class PolicySelector:
    """
    策略选择器
    根据环境状态动态选择最优调度策略
    """
    
    def __init__(self):
        self.policy_performance: Dict[SchedulingPolicy, deque] = {
            policy: deque(maxlen=50) for policy in SchedulingPolicy
        }
        self.policy_weights: Dict[SchedulingPolicy, float] = {
            policy: 1.0 / len(SchedulingPolicy) for policy in SchedulingPolicy
        }
        self.exploration_rate = 0.2
    
    def select_policy(
        self,
        system_load: float,
        agent_count: int,
        task_urgency: float
    ) -> SchedulingPolicy:
        """
        根据系统状态选择策略
        
        Args:
            system_load: 系统整体负载 0-1
            agent_count: Agent数量
            task_urgency: 任务紧急程度 0-1
        """
        # 探索
        if random.random() < self.exploration_rate:
            return random.choice(list(SchedulingPolicy))
        
        # 利用：基于启发式规则选择
        if system_load < 0.3:
            # 低负载：使用简单策略
            return SchedulingPolicy.ROUND_ROBIN
        elif system_load > 0.8:
            # 高负载：使用预测性策略
            return SchedulingPolicy.PREDICTIVE
        elif task_urgency > 0.8:
            # 紧急任务：选择最快响应
            return SchedulingPolicy.LEAST_LOADED
        elif agent_count > 10:
            # Agent多：使用多目标优化
            return SchedulingPolicy.MULTI_OBJECTIVE
        else:
            # 默认：基于性能的加权选择
            return self._weighted_policy_selection()
    
    def _weighted_policy_selection(self) -> SchedulingPolicy:
        """基于历史性能的加权选择"""
        policies = list(self.policy_weights.keys())
        weights = [self.policy_weights[p] for p in policies]
        
        return random.choices(policies, weights=weights, k=1)[0]
    
    def update_policy_performance(self, policy: SchedulingPolicy, reward: float):
        """更新策略性能记录"""
        self.policy_performance[policy].append(reward)
        
        # 更新权重
        if len(self.policy_performance[policy]) >= 10:
            avg_perf = np.mean(list(self.policy_performance[policy])[-10:])
            self.policy_weights[policy] = max(avg_perf, 0.01)
            
            # 归一化
            total = sum(self.policy_weights.values())
            for p in self.policy_weights:
                self.policy_weights[p] /= total


class LongTermOptimizer:
    """
    长期目标优化器
    使用进化算法优化调度参数
    """
    
    def __init__(self, population_size: int = 20):
        self.population_size = population_size
        self.generation = 0
        self.population: List[Dict[str, float]] = []
        self.fitness_scores: List[float] = []
        
        # 初始化种群
        self._init_population()
    
    def _init_population(self):
        """初始化参数种群"""
        for _ in range(self.population_size):
            individual = {
                "load_balance_weight": random.uniform(0.1, 0.5),
                "latency_weight": random.uniform(0.1, 0.5),
                "success_weight": random.uniform(0.1, 0.5),
                "resource_weight": random.uniform(0.1, 0.5),
                "threshold_overload": random.uniform(0.7, 0.9),
                "threshold_underload": random.uniform(0.1, 0.3),
                "rebalance_aggressiveness": random.uniform(0.3, 0.8)
            }
            self.population.append(individual)
            self.fitness_scores.append(0.0)
    
    def get_best_params(self) -> Dict[str, float]:
        """获取当前最优参数"""
        if not self.fitness_scores:
            return self.population[0]
        
        best_idx = np.argmax(self.fitness_scores)
        return self.population[best_idx]
    
    def evaluate_fitness(
        self,
        params: Dict[str, float],
        historical_outcomes: List[Dict[str, float]]
    ) -> float:
        """
        评估参数适应度
        
        考虑：
        - 平均负载均衡度
        - 平均响应时间
        - 成功率
        - 资源利用率
        """
        if not historical_outcomes:
            return 0.5
        
        avg_load_balance = np.mean([o.get("load_std", 0.3) for o in historical_outcomes])
        avg_latency = np.mean([o.get("avg_latency", 1.0) for o in historical_outcomes])
        avg_success = np.mean([o.get("success_rate", 0.9) for o in historical_outcomes])
        
        # 综合适应度
        fitness = (
            params["load_balance_weight"] * (1.0 - avg_load_balance) +
            params["latency_weight"] * (1.0 - min(avg_latency / 5.0, 1.0)) +
            params["success_weight"] * avg_success +
            params["resource_weight"] * 0.8  # 假设资源利用率
        )
        
        return fitness
    
    def evolve(self, historical_outcomes: List[Dict[str, float]]):
        """进化一代"""
        # 评估适应度
        for i, individual in enumerate(self.population):
            self.fitness_scores[i] = self.evaluate_fitness(individual, historical_outcomes)
        
        # 选择 (锦标赛选择)
        selected = self._tournament_selection()
        
        # 交叉
        offspring = self._crossover(selected)
        
        # 变异
        offspring = self._mutate(offspring)
        
        # 替换
        self.population = offspring
        self.generation += 1
        
        log.print_log(
            f"[LongTermOptimizer] 第{self.generation}代进化完成，"
            f"最佳适应度: {max(self.fitness_scores):.4f}",
            "info"
        )
    
    def _tournament_selection(self, tournament_size: int = 3) -> List[Dict[str, float]]:
        """锦标赛选择"""
        selected = []
        for _ in range(self.population_size):
            tournament_idx = random.sample(range(self.population_size), tournament_size)
            winner_idx = max(tournament_idx, key=lambda i: self.fitness_scores[i])
            selected.append(self.population[winner_idx].copy())
        return selected
    
    def _crossover(
        self,
        parents: List[Dict[str, float]],
        crossover_rate: float = 0.8
    ) -> List[Dict[str, float]]:
        """交叉操作"""
        offspring = []
        
        for i in range(0, len(parents), 2):
            parent1 = parents[i]
            parent2 = parents[(i + 1) % len(parents)]
            
            if random.random() < crossover_rate:
                child1, child2 = {}, {}
                for key in parent1:
                    if random.random() < 0.5:
                        child1[key] = parent1[key]
                        child2[key] = parent2[key]
                    else:
                        child1[key] = parent2[key]
                        child2[key] = parent1[key]
                offspring.extend([child1, child2])
            else:
                offspring.extend([parent1.copy(), parent2.copy()])
        
        return offspring[:self.population_size]
    
    def _mutate(
        self,
        population: List[Dict[str, float]],
        mutation_rate: float = 0.1
    ) -> List[Dict[str, float]]:
        """变异操作"""
        for individual in population:
            if random.random() < mutation_rate:
                key = random.choice(list(individual.keys()))
                individual[key] += random.uniform(-0.1, 0.1)
                individual[key] = np.clip(individual[key], 0.01, 1.0)
        
        return population


class DynamicScheduler:
    """
    动态调度器 V3
    
    核心功能：
    1. 多目标优化调度
    2. 动态策略选择
    3. 长期目标优化
    """
    
    def __init__(self):
        self.multi_objective_optimizer = MultiObjectiveOptimizer()
        self.policy_selector = PolicySelector()
        self.long_term_optimizer = LongTermOptimizer()
        
        # Agent状态
        self.agent_states: Dict[str, AgentState] = {}
        
        # 调度历史
        self.scheduling_history: deque = deque(maxlen=1000)
        self.outcome_history: deque = deque(maxlen=500)
        
        # 统计
        self.stats = {
            "total_scheduled": 0,
            "policy_usage": defaultdict(int),
            "objective_achievements": defaultdict(list)
        }
    
    def register_agent(self, agent_id: str, capabilities: AgentCapabilities):
        """注册Agent"""
        self.agent_states[agent_id] = AgentState(
            agent_id=agent_id,
            capabilities=capabilities
        )
        log.print_log(f"[DynamicScheduler] Agent {agent_id} 已注册", "info")
    
    def update_agent_state(self, agent_id: str, **kwargs):
        """更新Agent状态"""
        if agent_id in self.agent_states:
            for key, value in kwargs.items():
                if hasattr(self.agent_states[agent_id], key):
                    setattr(self.agent_states[agent_id], key, value)
            self.agent_states[agent_id].last_updated = datetime.now()
    
    async def schedule(
        self,
        task_req: TaskRequirements,
        available_agents: Optional[List[str]] = None
    ) -> Optional[SchedulingDecision]:
        """
        执行调度
        
        Args:
            task_req: 任务需求
            available_agents: 可用Agent列表 (None表示所有)
        Returns:
            SchedulingDecision
        """
        # 确定可用Agent
        if available_agents is None:
            available_agents = list(self.agent_states.keys())
        
        available_states = [
            self.agent_states[aid] for aid in available_agents 
            if aid in self.agent_states
        ]
        
        if not available_states:
            return None
        
        # 计算系统状态
        system_load = np.mean([s.load_score for s in available_states])
        task_urgency = task_req.priority / 10.0
        
        # 选择策略
        policy = self.policy_selector.select_policy(
            system_load, len(available_states), task_urgency
        )
        
        # 执行策略
        if policy == SchedulingPolicy.MULTI_OBJECTIVE:
            decision = self._execute_multi_objective(task_req, available_states)
        elif policy == SchedulingPolicy.LEAST_LOADED:
            decision = self._execute_least_loaded(task_req, available_states)
        elif policy == SchedulingPolicy.SKILL_MATCH:
            decision = self._execute_skill_match(task_req, available_states)
        elif policy == SchedulingPolicy.PREDICTIVE:
            decision = self._execute_predictive(task_req, available_states)
        else:
            decision = self._execute_round_robin(task_req, available_states)
        
        if decision:
            decision.policy_used = policy
            self.stats["total_scheduled"] += 1
            self.stats["policy_usage"][policy.value] += 1
            self.scheduling_history.append({
                "timestamp": datetime.now(),
                "agent_id": decision.agent_id,
                "policy": policy.value,
                "scores": decision.objective_scores
            })
        
        return decision
    
    def _execute_multi_objective(
        self,
        task_req: TaskRequirements,
        states: List[AgentState]
    ) -> SchedulingDecision:
        """执行多目标优化调度"""
        best_agent = None
        best_utility = -float('inf')
        best_scores = {}
        
        for state in states:
            # 评估所有目标
            scores = self.multi_objective_optimizer.evaluate_objectives(
                state, task_req, states
            )
            
            # 计算综合效用
            utility = self.multi_objective_optimizer.compute_utility(scores)
            
            # 技能匹配奖励
            if task_req.required_skills:
                matching_skills = set(task_req.required_skills) & set(state.capabilities.skills)
                skill_bonus = len(matching_skills) / len(task_req.required_skills)
                utility += skill_bonus * 0.3
            
            if utility > best_utility:
                best_utility = utility
                best_agent = state
                best_scores = scores
        
        return SchedulingDecision(
            agent_id=best_agent.agent_id if best_agent else states[0].agent_id,
            policy_used=SchedulingPolicy.MULTI_OBJECTIVE,
            objective_scores=best_scores,
            confidence=min(best_utility, 1.0),
            estimated_completion_time=best_agent.avg_response_time if best_agent else 1.0
        )
    
    def _execute_least_loaded(
        self,
        task_req: TaskRequirements,
        states: List[AgentState]
    ) -> SchedulingDecision:
        """执行最低负载调度"""
        sorted_states = sorted(states, key=lambda s: s.load_score)
        best = sorted_states[0]
        
        return SchedulingDecision(
            agent_id=best.agent_id,
            policy_used=SchedulingPolicy.LEAST_LOADED,
            objective_scores={ObjectiveType.LOAD_BALANCE: 1.0 - best.load_score},
            confidence=1.0 - best.load_score,
            estimated_completion_time=best.avg_response_time
        )
    
    def _execute_skill_match(
        self,
        task_req: TaskRequirements,
        states: List[AgentState]
    ) -> SchedulingDecision:
        """执行技能匹配调度"""
        best_agent = None
        best_score = -1.0
        
        for state in states:
            if task_req.required_skills:
                matching = len(set(task_req.required_skills) & set(state.capabilities.skills))
                score = matching / len(task_req.required_skills)
            else:
                score = 1.0 - state.load_score
            
            if score > best_score:
                best_score = score
                best_agent = state
        
        return SchedulingDecision(
            agent_id=best_agent.agent_id if best_agent else states[0].agent_id,
            policy_used=SchedulingPolicy.SKILL_MATCH,
            objective_scores={ObjectiveType.RESOURCE_EFF: best_score},
            confidence=best_score,
            estimated_completion_time=best_agent.avg_response_time if best_agent else 1.0
        )
    
    def _execute_predictive(
        self,
        task_req: TaskRequirements,
        states: List[AgentState]
    ) -> SchedulingDecision:
        """执行预测性调度"""
        # 选择预测负载最低的Agent
        best_agent = min(states, key=lambda s: s.load_score + s.task_queue_size * 0.01)
        
        return SchedulingDecision(
            agent_id=best_agent.agent_id,
            policy_used=SchedulingPolicy.PREDICTIVE,
            objective_scores={ObjectiveType.MIN_LATENCY: 1.0 - best_agent.load_score},
            confidence=1.0 - best_agent.load_score,
            estimated_completion_time=best_agent.avg_response_time
        )
    
    def _execute_round_robin(
        self,
        task_req: TaskRequirements,
        states: List[AgentState]
    ) -> SchedulingDecision:
        """执行轮询调度"""
        idx = self.stats["total_scheduled"] % len(states)
        agent = states[idx]
        
        return SchedulingDecision(
            agent_id=agent.agent_id,
            policy_used=SchedulingPolicy.ROUND_ROBIN,
            objective_scores={ObjectiveType.FAIRNESS: 1.0},
            confidence=0.5,
            estimated_completion_time=agent.avg_response_time
        )
    
    def report_outcome(
        self,
        agent_id: str,
        task_duration: float,
        success: bool,
        latency: float
    ):
        """报告任务执行结果"""
        outcome = {
            "timestamp": datetime.now(),
            "agent_id": agent_id,
            "duration": task_duration,
            "success": success,
            "latency": latency
        }
        self.outcome_history.append(outcome)
        
        # 更新策略性能
        if self.scheduling_history:
            last_decision = self.scheduling_history[-1]
            reward = 1.0 if success else 0.0
            reward -= latency / 10.0  # 延迟惩罚
            
            policy = SchedulingPolicy(last_decision.get("policy", "round_robin"))
            self.policy_selector.update_policy_performance(policy, reward)
        
        # 触发长期优化
        if len(self.outcome_history) % 50 == 0:
            historical = self._compute_historical_metrics()
            self.long_term_optimizer.evolve(historical)
            
            # 应用优化后的参数
            best_params = self.long_term_optimizer.get_best_params()
            self._apply_optimized_params(best_params)
    
    def _compute_historical_metrics(self) -> List[Dict[str, float]]:
        """计算历史指标"""
        if len(self.outcome_history) < 10:
            return []
        
        # 按时间窗口聚合
        metrics = []
        window_size = 20
        
        outcomes = list(self.outcome_history)
        for i in range(0, len(outcomes) - window_size + 1, window_size):
            window = outcomes[i:i + window_size]
            
            # 计算负载标准差
            agent_loads = defaultdict(list)
            for decision in self.scheduling_history:
                if i <= len(outcomes) - len(self.scheduling_history) + self.scheduling_history.index(decision) < i + window_size:
                    agent_loads[decision.get("agent_id")].append(decision.get("scores", {}).get("load_balance", 0.5))
            
            load_std = np.std([np.mean(loads) for loads in agent_loads.values()]) if agent_loads else 0.3
            
            metrics.append({
                "load_std": load_std,
                "avg_latency": np.mean([o["latency"] for o in window]),
                "success_rate": np.mean([1.0 if o["success"] else 0.0 for o in window])
            })
        
        return metrics
    
    def _apply_optimized_params(self, params: Dict[str, float]):
        """应用优化后的参数"""
        self.multi_objective_optimizer.objective_weights[ObjectiveType.LOAD_BALANCE] = params["load_balance_weight"]
        self.multi_objective_optimizer.objective_weights[ObjectiveType.MIN_LATENCY] = params["latency_weight"]
        self.multi_objective_optimizer.objective_weights[ObjectiveType.MAX_SUCCESS] = params["success_weight"]
        self.multi_objective_optimizer.objective_weights[ObjectiveType.RESOURCE_EFF] = params["resource_weight"]
        
        log.print_log(f"[DynamicScheduler] 应用优化参数: {params}", "info")
    
    def get_stats(self) -> Dict[str, Any]:
        """获取统计信息"""
        return {
            "total_scheduled": self.stats["total_scheduled"],
            "policy_usage": dict(self.stats["policy_usage"]),
            "current_objective_weights": {
                obj.value: weight 
                for obj, weight in self.multi_objective_optimizer.objective_weights.items()
            },
            "best_evolved_params": self.long_term_optimizer.get_best_params(),
            "evolution_generation": self.long_term_optimizer.generation
        }


# 全局实例
_global_scheduler: Optional[DynamicScheduler] = None


def get_dynamic_scheduler() -> DynamicScheduler:
    """获取全局动态调度器"""
    global _global_scheduler
    if _global_scheduler is None:
        _global_scheduler = DynamicScheduler()
    return _global_scheduler
