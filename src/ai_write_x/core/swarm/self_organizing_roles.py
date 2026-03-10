"""
动态自组织角色系统 V3 (Self-Organizing Roles V3)

解决痛点:
2. 缺乏真正的自组织能力 → 实现动态角色分配、角色演化、基于性能的role-switching

核心特性:
- 基于性能的动态角色分配
- 角色演化机制 (角色可以随时间变化)
- 角色胜任力评估
- 紧急角色调整
"""
import asyncio
from typing import Dict, List, Any, Optional, Callable, Set
from datetime import datetime, timedelta
from dataclasses import dataclass, field
from enum import Enum
from collections import defaultdict, deque
import numpy as np
import random

from src.ai_write_x.utils import log


class AgentRole(str, Enum):
    """Agent角色类型"""
    COORDINATOR = "coordinator"       # 协调者 - 任务分配和协调
    EXECUTOR = "executor"             # 执行者 - 任务执行
    EVALUATOR = "evaluator"           # 评估者 - 质量评估
    EXPLORER = "explorer"             # 探索者 - 新知识发现
    ARCHIVER = "archiver"             # 归档者 - 知识整理
    MEDIATOR = "mediator"             # 调解者 - 冲突解决


@dataclass
class RoleMetrics:
    """角色绩效指标"""
    role: AgentRole
    tasks_completed: int = 0
    tasks_failed: int = 0
    avg_quality_score: float = 0.0
    avg_response_time: float = 0.0
    collaboration_score: float = 0.0
    
    @property
    def success_rate(self) -> float:
        total = self.tasks_completed + self.tasks_failed
        return self.tasks_completed / total if total > 0 else 0.0
    
    @property
    def performance_score(self) -> float:
        return (
            0.4 * self.success_rate +
            0.3 * self.avg_quality_score +
            0.2 * (1.0 - min(self.avg_response_time / 60.0, 1.0)) +
            0.1 * self.collaboration_score
        )


@dataclass
class AgentProfile:
    """Agent档案 - 存储Agent能力和历史表现"""
    agent_id: str
    base_capabilities: List[str] = field(default_factory=list)
    specialties: List[str] = field(default_factory=list)
    experience_level: float = 0.5  # 0-1 经验水平
    
    # 角色历史
    role_history: deque = field(default_factory=lambda: deque(maxlen=50))
    current_role: AgentRole = AgentRole.EXECUTOR
    
    # 各角色绩效
    role_performance: Dict[AgentRole, RoleMetrics] = field(default_factory=dict)
    
    # 能力评分
    skill_scores: Dict[str, float] = field(default_factory=dict)
    
    # 负载和状态
    current_load: float = 0.0
    last_active: datetime = field(default_factory=datetime.now)
    
    def __post_init__(self):
        if not self.role_performance:
            for role in AgentRole:
                self.role_performance[role] = RoleMetrics(role=role)


class RoleEligibility:
    """角色Eligibility评分"""
    
    @staticmethod
    def evaluate_coordinator(profile: AgentProfile) -> float:
        """评估是否适合做协调者"""
        score = 0.0
        
        # 沟通能力 (基于历史协作分数)
        collab = profile.role_performance.get(AgentRole.COORDINATOR, RoleMetrics(AgentRole.COORDINATOR)).collaboration_score
        score += collab * 0.4
        
        # 决策能力 (基于成功率)
        success = profile.role_performance.get(AgentRole.COORDINATOR, RoleMetrics(AgentRole.COORDINATOR)).success_rate
        score += success * 0.3
        
        # 经验水平
        score += profile.experience_level * 0.3
        
        return score
    
    @staticmethod
    def evaluate_executor(profile: AgentProfile) -> float:
        """评估是否适合做执行者"""
        score = 0.0
        
        # 执行成功率
        success = profile.role_performance.get(AgentRole.EXECUTOR, RoleMetrics(AgentRole.EXECUTOR)).success_rate
        score += success * 0.4
        
        # 响应时间
        resp_time = profile.role_performance.get(AgentRole.EXECUTOR, RoleMetrics(AgentRole.EXECUTOR)).avg_response_time
        score += (1.0 - min(resp_time / 30.0, 1.0)) * 0.3
        
        # 质量评分
        quality = profile.role_performance.get(AgentRole.EXECUTOR, RoleMetrics(AgentRole.EXECUTOR)).avg_quality_score
        score += quality * 0.3
        
        return score
    
    @staticmethod
    def evaluate_evaluator(profile: AgentProfile) -> float:
        """评估是否适合做评估者"""
        score = 0.0
        
        # 质量判断准确性
        quality = profile.role_performance.get(AgentRole.EVALUATOR, RoleMetrics(AgentRole.EVALUATOR)).avg_quality_score
        score += quality * 0.5
        
        # 客观性 (基于协作)
        collab = profile.role_performance.get(AgentRole.EVALUATOR, RoleMetrics(AgentRole.EVALUATOR)).collaboration_score
        score += collab * 0.3
        
        # 经验
        score += profile.experience_level * 0.2
        
        return score
    
    @staticmethod
    def evaluate_explorer(profile: AgentProfile) -> float:
        """评估是否适合做探索者"""
        score = 0.0
        
        # 探索成功率
        success = profile.role_performance.get(AgentRole.EXPLORER, RoleMetrics(AgentRole.EXPLORER)).success_rate
        score += success * 0.4
        
        # 知识广度
        score += min(len(profile.base_capabilities) / 10.0, 1.0) * 0.3
        
        # 好奇心指标 (基于探索任务完成数)
        explore_completed = profile.role_performance.get(AgentRole.EXPLORER, RoleMetrics(AgentRole.EXPLORER)).tasks_completed
        score += min(explore_completed / 20.0, 1.0) * 0.3
        
        return score
    
    @staticmethod
    def evaluate_archiver(profile: AgentProfile) -> float:
        """评估是否适合做归档者"""
        # 归档需要细心和组织能力
        quality = profile.role_performance.get(AgentRole.ARCHIVER, RoleMetrics(AgentRole.ARCHIVER)).avg_quality_score
        collab = profile.role_performance.get(AgentRole.ARCHIVER, RoleMetrics(AgentRole.ARCHIVER)).collaboration_score
        
        return quality * 0.6 + collab * 0.4
    
    @staticmethod
    def evaluate_mediator(profile: AgentProfile) -> float:
        """评估是否适合做调解者"""
        # 调解需要经验和沟通能力
        collab = profile.role_performance.get(AgentRole.MEDIATOR, RoleMetrics(AgentRole.MEDIATOR)).collaboration_score
        experience = profile.experience_level
        
        return collab * 0.5 + experience * 0.5
    
    @classmethod
    def evaluate_all(cls, profile: AgentProfile) -> Dict[AgentRole, float]:
        """评估所有角色的适合度"""
        return {
            AgentRole.COORDINATOR: cls.evaluate_coordinator(profile),
            AgentRole.EXECUTOR: cls.evaluate_executor(profile),
            AgentRole.EVALUATOR: cls.evaluate_evaluator(profile),
            AgentRole.EXPLORER: cls.evaluate_explorer(profile),
            AgentRole.ARCHIVER: cls.evaluate_archiver(profile),
            AgentRole.MEDIATOR: cls.evaluate_mediator(profile)
        }


class RoleSwitchingMechanism:
    """角色切换机制"""
    
    def __init__(
        self,
        switch_cooldown: int = 300,  # 秒
        min_performance_gap: float = 0.15,  # 最小性能差距才切换
        enable_emergency_switch: bool = True
    ):
        self.switch_cooldown = switch_cooldown
        self.min_performance_gap = min_performance_gap
        self.enable_emergency_switch = enable_emergency_switch
        
        # 上次切换时间
        self.last_switch_time: Dict[str, datetime] = {}
        
        # 切换历史
        self.switch_history: deque = deque(maxlen=500)
    
    def should_switch(
        self,
        agent_id: str,
        current_role: AgentRole,
        eligible_roles: Dict[AgentRole, float],
        current_load: float = 0.0
    ) -> Optional[AgentRole]:
        """
        判断是否应该切换角色
        
        Returns:
            新角色 或 None (不切换)
        """
        now = datetime.now()
        
        # 检查冷却时间
        if agent_id in self.last_switch_time:
            time_since_switch = (now - self.last_switch_time[agent_id]).total_seconds()
            if time_since_switch < self.switch_cooldown:
                return None
        
        # 紧急切换: 负载过高
        if self.enable_emergency_switch and current_load > 0.9:
            # 切换到执行者以处理紧急任务
            return AgentRole.EXECUTOR
        
        # 找出最佳角色
        if not eligible_roles:
            return None
        
        best_role = max(eligible_roles.items(), key=lambda x: x[1])
        current_score = eligible_roles.get(current_role, 0.0)
        
        # 检查性能差距
        if best_role[1] - current_score > self.min_performance_gap:
            self.last_switch_time[agent_id] = now
            
            # 记录切换
            self.switch_history.append({
                "agent_id": agent_id,
                "from_role": current_role,
                "to_role": best_role[0],
                "score_gap": best_role[1] - current_score,
                "timestamp": now
            })
            
            log.print_log(
                f"[RoleSwitch] Agent {agent_id} 角色切换: {current_role.value} -> {best_role[0].value} "
                f"(差距: {best_role[1] - current_score:.3f})",
                "info"
            )
            
            return best_role[0]
        
        return None


class DynamicRoleAssigner:
    """
    动态角色分配器
    
    功能:
    1. 基于能力评估分配角色
    2. 角色负载均衡
    3. 动态角色调整
    4. 角色演化追踪
    """
    
    def __init__(self):
        # Agent档案
        self.agent_profiles: Dict[str, AgentProfile] = {}
        
        # 角色分配记录
        self.role_assignment: Dict[AgentRole, Set[str]] = {role: set() for role in AgentRole}
        
        # 角色切换机制
        self.switching_mechanism = RoleSwitchingMechanism()
        
        # 角色数量约束
        self.role_constraints = {
            AgentRole.COORDINATOR: (1, 2),
            AgentRole.EXECUTOR: (2, 10),
            AgentRole.EVALUATOR: (1, 3),
            AgentRole.EXPLORER: (1, 3),
            AgentRole.ARCHIVER: (1, 2),
            AgentRole.MEDIATOR: (1, 2)
        }
        
        # 统计
        self.stats = {
            "total_assignments": 0,
            "total_switches": 0,
            "role_distribution": {role.value: 0 for role in AgentRole}
        }
    
    def register_agent(
        self,
        agent_id: str,
        capabilities: List[str],
        specialties: List[str] = None,
        initial_role: AgentRole = None
    ):
        """注册新Agent"""
        profile = AgentProfile(
            agent_id=agent_id,
            base_capabilities=capabilities,
            specialties=specialties or [],
            current_role=initial_role or AgentRole.EXECUTOR
        )
        
        self.agent_profiles[agent_id] = profile
        self.role_assignment[profile.current_role].add(agent_id)
        
        self.stats["total_assignments"] += 1
        self.stats["role_distribution"][profile.current_role.value] += 1
        
        log.print_log(f"[DynamicRoles] Agent {agent_id} 注册，初始角色: {profile.current_role.value}", "info")
    
    def report_task_result(
        self,
        agent_id: str,
        role: AgentRole,
        success: bool,
        quality_score: float = 0.5,
        response_time: float = 0.0,
        collaboration_score: float = 0.5
    ):
        """报告任务结果，更新绩效"""
        if agent_id not in self.agent_profiles:
            return
        
        profile = self.agent_profiles[agent_id]
        
        if role not in profile.role_performance:
            profile.role_performance[role] = RoleMetrics(role=role)
        
        metrics = profile.role_performance[role]
        
        # 更新指标
        if success:
            metrics.tasks_completed += 1
        else:
            metrics.tasks_failed += 1
        
        # 移动平均更新
        n = metrics.tasks_completed + metrics.tasks_failed
        metrics.avg_quality_score = metrics.avg_quality_score * (n-1)/n + quality_score / n
        metrics.avg_response_time = metrics.avg_response_time * (n-1)/n + response_time / n
        metrics.collaboration_score = metrics.collaboration_score * (n-1)/n + collaboration_score / n
    
    async def rebalance_roles(self) -> Dict[str, AgentRole]:
        """
        重新平衡角色分配
        
        Returns:
            {agent_id: new_role} 切换映射
        """
        changes = {}
        
        # 1. 评估所有Agent的角色适合度
        eligibility_scores: Dict[str, Dict[AgentRole, float]] = {}
        
        for agent_id, profile in self.agent_profiles.items():
            eligibility_scores[agent_id] = RoleEligibility.evaluate_all(profile)
        
        # 2. 检查角色数量约束
        for role, (min_count, max_count) in self.role_constraints.items():
            current_count = len(self.role_assignment[role])
            
            # 角色不足: 强制分配
            if current_count < min_count:
                # 找出最适合该角色的Agent
                candidates = []
                for agent_id, scores in eligibility_scores.items():
                    if profile := self.agent_profiles.get(agent_id):
                        if profile.current_role != role:
                            candidates.append((agent_id, scores.get(role, 0.0)))
                
                candidates.sort(key=lambda x: x[1], reverse=True)
                
                # 分配直到满足最小数量
                needed = min_count - current_count
                for agent_id, _ in candidates[:needed]:
                    new_role = self._switch_role(agent_id, role)
                    if new_role:
                        changes[agent_id] = new_role
            
            # 角色过多: 考虑重新分配
            elif current_count > max_count:
                # 找出性能最差的Agent
                underperformers = []
                for agent_id in list(self.role_assignment[role]):
                    if profile := self.agent_profiles.get(agent_id):
                        score = eligibility_scores[agent_id].get(role, 0.0)
                        underperformers.append((agent_id, score))
                
                underperformers.sort(key=lambda x: x[1])
                
                # 移除超额的
                excess = current_count - max_count
                for agent_id, _ in underperformers[:excess]:
                    # 找最佳替代角色
                    best_alt = max(
                        eligibility_scores[agent_id].items(),
                        key=lambda x: x[1]
                    )
                    if best_alt[1] > 0.3:  # 阈值
                        new_role = self._switch_role(agent_id, best_alt[0])
                        if new_role:
                            changes[agent_id] = new_role
        
        # 3. 个体角色切换检查
        for agent_id, profile in self.agent_profiles.items():
            eligible = eligibility_scores.get(agent_id, {})
            
            new_role = self.switching_mechanism.should_switch(
                agent_id,
                profile.current_role,
                eligible,
                profile.current_load
            )
            
            if new_role and new_role != profile.current_role:
                switched = self._switch_role(agent_id, new_role)
                if switched:
                    changes[agent_id] = switched
                    self.stats["total_switches"] += 1
        
        return changes
    
    def _switch_role(self, agent_id: str, new_role: AgentRole) -> Optional[AgentRole]:
        """执行角色切换"""
        profile = self.agent_profiles.get(agent_id)
        if not profile:
            return None
        
        old_role = profile.current_role
        
        # 检查目标角色是否已达上限
        max_count = self.role_constraints.get(new_role, (1, 10))[1]
        if len(self.role_assignment[new_role]) >= max_count:
            return None
        
        # 执行切换
        self.role_assignment[old_role].discard(agent_id)
        self.role_assignment[new_role].add(agent_id)
        
        # 更新档案
        profile.current_role = new_role
        profile.role_history.append({
            "role": new_role,
            "timestamp": datetime.now()
        })
        
        self.stats["role_distribution"][old_role.value] -= 1
        self.stats["role_distribution"][new_role.value] += 1
        
        log.print_log(f"[DynamicRoles] Agent {agent_id} 角色切换: {old_role.value} -> {new_role.value}", "success")
        
        return new_role
    
    def get_role_distribution(self) -> Dict[str, int]:
        """获取当前角色分布"""
        return {role.value: len(agents) for role, agents in self.role_assignment.items()}
    
    def get_agent_role(self, agent_id: str) -> Optional[AgentRole]:
        """获取Agent当前角色"""
        profile = self.agent_profiles.get(agent_id)
        return profile.current_role if profile else None
    
    def get_agent_performance(self, agent_id: str) -> Optional[Dict]:
        """获取Agent绩效详情"""
        profile = self.agent_profiles.get(agent_id)
        if not profile:
            return None
        
        return {
            "agent_id": agent_id,
            "current_role": profile.current_role.value,
            "experience_level": profile.experience_level,
            "role_performance": {
                role.value: {
                    "success_rate": metrics.success_rate,
                    "performance_score": metrics.performance_score,
                    "avg_quality": metrics.avg_quality_score
                }
                for role, metrics in profile.role_performance.items()
            },
            "eligibility": {
                role.value: score
                for role, score in RoleEligibility.evaluate_all(profile).items()
            }
        }
    
    def get_stats(self) -> Dict:
        """获取统计信息"""
        return {
            **self.stats,
            "role_distribution": self.get_role_distribution(),
            "total_agents": len(self.agent_profiles)
        }


# 全局实例
_global_role_assigner: Optional[DynamicRoleAssigner] = None


def get_dynamic_role_assigner() -> DynamicRoleAssigner:
    """获取全局动态角色分配器"""
    global _global_role_assigner
    if _global_role_assigner is None:
        _global_role_assigner = DynamicRoleAssigner()
    return _global_role_assigner


def create_agent_with_role(
    agent_id: str,
    capabilities: List[str],
    role: AgentRole = None
) -> AgentProfile:
    """创建带角色的Agent"""
    assigner = get_dynamic_role_assigner()
    assigner.register_agent(agent_id, capabilities, initial_role=role)
    return assigner.agent_profiles[agent_id]