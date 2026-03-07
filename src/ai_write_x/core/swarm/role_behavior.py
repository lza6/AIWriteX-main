"""
角色行为系统 (Role Behavior System)
定义不同角色的行为模式和决策逻辑
"""
from abc import ABC, abstractmethod
from typing import Dict, List, Any, Optional, Callable
from enum import Enum
from datetime import datetime
import random
import asyncio

from src.ai_write_x.core.swarm_protocol import SwarmCapabilities, SwarmTask
from src.ai_write_x.core.swarm.swarm_agent import AgentNode, AgentStatus
from src.ai_write_x.utils import log


class BehaviorState(str, Enum):
    """行为状态"""
    CONTEMPLATING = "contemplating"    # 思考中
    EXPLORING = "exploring"            # 探索中
    COLLABORATING = "collaborating"    # 协作中
    EXECUTING = "executing"             # 执行中
    EVALUATING = "evaluating"          # 评估中
    RESTING = "resting"                 # 休息中


class AgentRole(str, Enum):
    """Agent角色类型"""
    COORDINATOR = "coordinator"       # 协调者 - 任务分配和协调
    EXECUTOR = "executor"             # 执行者 - 任务执行
    EVALUATOR = "evaluator"           # 评估者 - 质量评估
    EXPLORER = "explorer"             # 探索者 - 新知识发现


class BehaviorTrigger:
    """行为触发器"""
    
    def __init__(
        self,
        name: str,
        condition: Callable[[Dict], bool],
        weight: float = 1.0
    ):
        self.name = name
        self.condition = condition
        self.weight = weight
        self.last_triggered: Optional[datetime] = None
    
    def can_trigger(self, context: Dict) -> bool:
        """检查是否可以触发"""
        # 冷却时间检查
        if self.last_triggered:
            elapsed = (datetime.now() - self.last_triggered).total_seconds()
            if elapsed < 2.0:  # 2秒冷却
                return False
        
        return self.condition(context)


class Behavior:
    """行为"""
    
    def __init__(
        self,
        name: str,
        action: Callable[[AgentNode, Dict], Any],
        duration_range: tuple = (1.0, 5.0),
        energy_cost: float = 0.2
    ):
        self.name = name
        self.action = action
        self.duration_range = duration_range
        self.energy_cost = energy_cost
    
    async def execute(self, agent: AgentNode, context: Dict) -> Any:
        """执行行为"""
        log.print_log(f"[{agent.name}] 执行行为: {self.name}", "debug")
        result = await self.action(agent, context)
        return result


class RoleBehavior(ABC):
    """角色行为基类"""
    
    def __init__(self, role_name: str):
        self.role_name = role_name
        self.behaviors: List[Behavior] = []
        self.triggers: List[BehaviorTrigger] = []
        self.current_state = BehaviorState.CONTEMPLATING
        self.energy = 1.0  # 能量值 0.0-1.0
    
    @abstractmethod
    def define_behaviors(self):
        """定义行为列表 - 子类实现"""
        pass
    
    @abstractmethod
    def define_triggers(self):
        """定义触发器 - 子类实现"""
        pass
    
    @abstractmethod
    def select_behavior(self, context: Dict) -> Optional[Behavior]:
        """选择行为 - 子类实现"""
        pass
    
    def can_act(self) -> bool:
        """检查是否可以行动"""
        return self.energy > 0.1
    
    def consume_energy(self, cost: float):
        """消耗能量"""
        self.energy = max(0.0, self.energy - cost)
    
    def restore_energy(self, amount: float = 0.1):
        """恢复能量"""
        self.energy = min(1.0, self.energy + amount)


class CoordinatorBehavior(RoleBehavior):
    """协调者行为 - 负责任务分配和协调"""
    
    def __init__(self):
        super().__init__("coordinator")
        self.define_behaviors()
        self.define_triggers()
    
    def define_behaviors(self):
        self.behaviors = [
            Behavior(
                name="分析任务",
                action=self._analyze_task,
                duration_range=(0.5, 2.0),
                energy_cost=0.15
            ),
            Behavior(
                name="分配任务",
                action=self._assign_task,
                duration_range=(0.3, 1.0),
                energy_cost=0.1
            ),
            Behavior(
                name="收集状态",
                action=self._collect_status,
                duration_range=(0.5, 1.5),
                energy_cost=0.1
            ),
            Behavior(
                name="协调冲突",
                action=self._resolve_conflict,
                duration_range=(1.0, 3.0),
                energy_cost=0.2
            )
        ]
    
    def define_triggers(self):
        self.triggers = [
            BehaviorTrigger(
                name="新任务到达",
                condition=lambda ctx: ctx.get("new_task", False),
                weight=1.0
            ),
            BehaviorTrigger(
                name="任务超时",
                condition=lambda ctx: ctx.get("task_timeout", False),
                weight=0.8
            ),
            BehaviorTrigger(
                name="Agent空闲",
                condition=lambda ctx: ctx.get("agent_idle", False),
                weight=0.5
            )
        ]
    
    def select_behavior(self, context: Dict) -> Optional[Behavior]:
        # 检查触发器
        for trigger in self.triggers:
            if trigger.can_trigger(context):
                if "分析" in trigger.name:
                    return self.behaviors[0]
                elif "分配" in trigger.name:
                    return self.behaviors[1]
        
        # 默认选择
        return random.choice(self.behaviors)
    
    async def _analyze_task(self, agent: AgentNode, context: Dict) -> Dict:
        await asyncio.sleep(0.1)
        return {"analysis": "任务分析完成", "subtasks": []}
    
    async def _assign_task(self, agent: AgentNode, context: Dict) -> Dict:
        await asyncio.sleep(0.1)
        return {"assignment": "任务已分配", "assigned_to": []}
    
    async def _collect_status(self, agent: AgentNode, context: Dict) -> Dict:
        await asyncio.sleep(0.1)
        return {"status": "状态收集完成"}
    
    async def _resolve_conflict(self, agent: AgentNode, context: Dict) -> Dict:
        await asyncio.sleep(0.1)
        return {"resolution": "冲突已解决"}


class ExecutorBehavior(RoleBehavior):
    """执行者行为 - 专注于任务执行"""
    
    def __init__(self):
        super().__init__("executor")
        self.define_behaviors()
        self.define_triggers()
    
    def define_behaviors(self):
        self.behaviors = [
            Behavior(
                name="执行任务",
                action=self._execute_task,
                duration_range=(1.0, 5.0),
                energy_cost=0.3
            ),
            Behavior(
                name="验证结果",
                action=self._verify_result,
                duration_range=(0.5, 2.0),
                energy_cost=0.15
            ),
            Behavior(
                name="报告进度",
                action=self._report_progress,
                duration_range=(0.2, 0.5),
                energy_cost=0.05
            )
        ]
    
    def define_triggers(self):
        self.triggers = [
            BehaviorTrigger(
                name="有任务分配",
                condition=lambda ctx: ctx.get("task_assigned", False),
                weight=1.0
            ),
            BehaviorTrigger(
                name="需要验证",
                condition=lambda ctx: ctx.get("needs_verification", False),
                weight=0.9
            )
        ]
    
    def select_behavior(self, context: Dict) -> Optional[Behavior]:
        if context.get("task_assigned"):
            return self.behaviors[0]
        if context.get("needs_verification"):
            return self.behaviors[1]
        return self.behaviors[2]
    
    async def _execute_task(self, agent: AgentNode, context: Dict) -> Dict:
        await asyncio.sleep(0.2)
        return {"execution": "任务执行完成"}
    
    async def _verify_result(self, agent: AgentNode, context: Dict) -> Dict:
        await asyncio.sleep(0.1)
        return {"verification": "结果验证通过"}
    
    async def _report_progress(self, agent: AgentNode, context: Dict) -> Dict:
        await asyncio.sleep(0.05)
        return {"progress": "进度已报告"}


class EvaluatorBehavior(RoleBehavior):
    """评估者行为 - 负责质量评估"""
    
    def __init__(self):
        super().__init__("evaluator")
        self.define_behaviors()
        self.define_triggers()
    
    def define_behaviors(self):
        self.behaviors = [
            Behavior(
                name="评估质量",
                action=self._evaluate_quality,
                duration_range=(1.0, 3.0),
                energy_cost=0.2
            ),
            Behavior(
                name="给出建议",
                action=self._give_suggestions,
                duration_range=(0.5, 2.0),
                energy_cost=0.15
            ),
            Behavior(
                name="评分",
                action=self._score,
                duration_range=(0.3, 1.0),
                energy_cost=0.1
            )
        ]
    
    def define_triggers(self):
        self.triggers = [
            BehaviorTrigger(
                name="需要评估",
                condition=lambda ctx: ctx.get("needs_evaluation", False),
                weight=1.0
            ),
            BehaviorTrigger(
                name="需要建议",
                condition=lambda ctx: ctx.get("needs_suggestion", False),
                weight=0.8
            )
        ]
    
    def select_behavior(self, context: Dict) -> Optional[Behavior]:
        if context.get("needs_evaluation"):
            return self.behaviors[0]
        if context.get("needs_suggestion"):
            return self.behaviors[1]
        return self.behaviors[2]
    
    async def _evaluate_quality(self, agent: AgentNode, context: Dict) -> Dict:
        await asyncio.sleep(0.1)
        return {"quality_score": random.uniform(0.7, 1.0)}
    
    async def _give_suggestions(self, agent: AgentNode, context: Dict) -> Dict:
        await asyncio.sleep(0.1)
        return {"suggestions": ["建议1", "建议2"]}
    
    async def _score(self, agent: AgentNode, context: Dict) -> Dict:
        await asyncio.sleep(0.05)
        return {"score": random.randint(70, 100)}


class ExplorerBehavior(RoleBehavior):
    """探索者行为 - 负责发现新任务和资源"""
    
    def __init__(self):
        super().__init__("explorer")
        self.define_behaviors()
        self.define_triggers()
    
    def define_behaviors(self):
        self.behaviors = [
            Behavior(
                name="搜索资源",
                action=self._search_resources,
                duration_range=(2.0, 5.0),
                energy_cost=0.25
            ),
            Behavior(
                name="发现机会",
                action=self._discover_opportunities,
                duration_range=(1.0, 3.0),
                energy_cost=0.2
            ),
            Behavior(
                name="建立连接",
                action=self._establish_connections,
                duration_range=(0.5, 2.0),
                energy_cost=0.15
            )
        ]
    
    def define_triggers(self):
        self.triggers = [
            BehaviorTrigger(
                name="空闲探索",
                condition=lambda ctx: ctx.get("idle", False) and ctx.get("energy", 1.0) > 0.5,
                weight=0.7
            ),
            BehaviorTrigger(
                name="发现新资源",
                condition=lambda ctx: ctx.get("new_resource_discovered", False),
                weight=1.0
            )
        ]
    
    def select_behavior(self, context: Dict) -> Optional[Behavior]:
        if context.get("idle"):
            return self.behaviors[0]
        if context.get("new_resource_discovered"):
            return self.behaviors[2]
        return self.behaviors[1]
    
    async def _search_resources(self, agent: AgentNode, context: Dict) -> Dict:
        await asyncio.sleep(0.2)
        return {"resources": ["资源1", "资源2", "资源3"]}
    
    async def _discover_opportunities(self, agent: AgentNode, context: Dict) -> Dict:
        await asyncio.sleep(0.1)
        return {"opportunities": ["机会1", "机会2"]}
    
    async def _establish_connections(self, agent: AgentNode, context: Dict) -> Dict:
        await asyncio.sleep(0.1)
        return {"connections": 3}


# 角色工厂
class RoleBehaviorFactory:
    """角色行为工厂"""
    
    _roles = {
        "coordinator": CoordinatorBehavior,
        "executor": ExecutorBehavior,
        "evaluator": EvaluatorBehavior,
        "explorer": ExplorerBehavior,
        "reasoning": CoordinatorBehavior,   # 推理型 = 协调者
        "creative": ExecutorBehavior,       # 创意型 = 执行者
        "research": ExplorerBehavior        # 研究型 = 探索者
    }
    
    @classmethod
    def create(cls, role_name: str) -> RoleBehavior:
        behavior_class = cls._roles.get(role_name.lower(), ExecutorBehavior)
        return behavior_class()
    
    @classmethod
    def register(cls, role_name: str, behavior_class: type):
        cls._roles[role_name.lower()] = behavior_class


class BehaviorOrchestrator:
    """行为编排器 - 管理Agent的行为执行"""
    
    def __init__(self, agent: AgentNode):
        self.agent = agent
        self.role_behavior: Optional[RoleBehavior] = None
        self.current_behavior: Optional[Behavior] = None
        self.behavior_history: List[Dict] = []
    
    def set_role(self, role_name: str):
        """设置角色"""
        self.role_behavior = RoleBehaviorFactory.create(role_name)
        log.print_log(f"[{self.agent.name}] 设置角色: {role_name}", "debug")
    
    async def tick(self, context: Dict):
        """行为Tick - 每帧调用"""
        if not self.role_behavior:
            return
        
        # 检查能量
        if not self.role_behavior.can_act():
            self.role_behavior.current_state = BehaviorState.RESTING
            self.role_behavior.restore_energy(0.05)
            return
        
        # 选择行为
        behavior = self.role_behavior.select_behavior(context)
        
        if behavior and behavior != self.current_behavior:
            # 执行新行为
            self.current_behavior = behavior
            result = await behavior.execute(self.agent, context)
            
            # 记录历史
            self.behavior_history.append({
                "behavior": behavior.name,
                "result": result,
                "timestamp": datetime.now().isoformat()
            })
            
            # 消耗能量
            self.role_behavior.consume_energy(behavior.energy_cost)
    
    def get_stats(self) -> Dict[str, Any]:
        """获取行为统计"""
        return {
            "role": self.role_behavior.role_name if self.role_behavior else "none",
            "state": self.role_behavior.current_state.value if self.role_behavior else "none",
            "energy": self.role_behavior.energy if self.role_behavior else 0,
            "current_behavior": self.current_behavior.name if self.current_behavior else "none",
            "history_size": len(self.behavior_history)
        }
