"""
信息素通信系统 (Pheromone Communication System)
实现蜂群代理间的信息素-based 通信机制
"""
from enum import Enum
import asyncio
from typing import Dict, List, Any, Optional, Callable, Set
from datetime import datetime, timedelta
from collections import defaultdict
import uuid
import json
import math

from src.ai_write_x.core.swarm_protocol import (
    SwarmMessage, SwarmMessageType, SwarmCapabilities
)
from src.ai_write_x.utils import log


class PheromoneType(str, Enum):
    """信息素类型"""
    TRAIL = "trail"              # 路径信息素 - 指引方向
    ATTRACTION = "attraction"    # 吸引信息素 - 吸引其他Agent
    ALERT = "alert"              # 警报信息素 - 警告危险
    TASK = "task"                # 任务信息素 - 标记任务
    CONSENSUS = "consensus"      # 共识信息素 - 共享知识


class Pheromone:
    """信息素"""
    
    def __init__(
        self,
        p_type: PheromoneType,
        strength: float = 1.0,
        source_id: str = None,
        target_id: str = None,
        location: tuple = None,
        content: Any = None,
        ttl: float = 60.0
    ):
        self.id = str(uuid.uuid4())
        self.type = p_type
        self.strength = strength  # 0.0 - 1.0
        self.source_id = source_id
        self.target_id = target_id
        self.location = location or (0, 0)
        self.content = content
        self.created_at = datetime.now()
        self.ttl = ttl  # 存活时间(秒)
    
    @property
    def is_expired(self) -> bool:
        return (datetime.now() - self.created_at).total_seconds() > self.ttl
    
    @property
    def decay_factor(self) -> float:
        """计算衰减因子"""
        age = (datetime.now() - self.created_at).total_seconds()
        return math.exp(-0.05 * age)  # 指数衰减
    
    @property
    def effective_strength(self) -> float:
        """有效强度"""
        return self.strength * self.decay_factor


class PheromoneSpace:
    """信息素空间 - 管理整个蜂群的信息素"""
    
    def __init__(self, decay_rate: float = 0.02):
        self.decay_rate = decay_rate
        self.pheromones: Dict[str, Pheromone] = {}
        self.agent_positions: Dict[str, tuple] = {}  # Agent位置
        self._lock = asyncio.Lock()
    
    async def emit(
        self,
        p_type: PheromoneType,
        source_id: str,
        strength: float = 1.0,
        target_id: str = None,
        location: tuple = None,
        content: Any = None,
        ttl: float = 60.0
    ) -> str:
        """发射信息素"""
        async with self._lock:
            pheromone = Pheromone(
                p_type=p_type,
                strength=strength,
                source_id=source_id,
                target_id=target_id,
                location=location,
                content=content,
                ttl=ttl
            )
            self.pheromones[pheromone.id] = pheromone
            log.print_log(f"[信息素] {source_id} 发射 {p_type} 强度={strength:.2f}", "debug")
            return pheromone.id
    
    async def sense(
        self,
        agent_id: str,
        p_types: List[PheromoneType] = None,
        radius: float = 100.0,
        location: tuple = None
    ) -> List[Pheromone]:
        """感知信息素"""
        async with self._lock:
            agent_loc = location or self.agent_positions.get(agent_id, (0, 0))
            p_types = p_types or list(PheromoneType)
            
            sensed = []
            for p in self.pheromones.values():
                if p.is_expired:
                    continue
                if p.type not in p_types:
                    continue
                
                # 计算距离
                dist = math.sqrt(
                    (p.location[0] - agent_loc[0])**2 +
                    (p.location[1] - agent_loc[1])**2
                )
                
                if dist <= radius:
                    sensed.append(p)
            
            return sensed
    
    async def decay_all(self):
        """衰减所有信息素"""
        async with self._lock:
            expired = [pid for pid, p in self.pheromones.items() if p.is_expired]
            for pid in expired:
                del self.pheromones[pid]
            
            # 衰减未过期的
            for p in self.pheromones.values():
                p.strength *= (1 - self.decay_rate)
                if p.strength < 0.01:
                    del self.pheromones[p.id]
    
    async def update_agent_position(self, agent_id: str, location: tuple):
        """更新Agent位置"""
        async with self._lock:
            self.agent_positions[agent_id] = location
    
    def get_stats(self) -> Dict[str, Any]:
        """获取统计信息"""
        by_type = defaultdict(int)
        for p in self.pheromones.values():
            by_type[p.type] += 1
        
        return {
            "total_pheromones": len(self.pheromones),
            "by_type": dict(by_type),
            "agent_positions": len(self.agent_positions)
        }


class PheromoneComm:
    """信息素通信管理器"""
    
    def __init__(self, max_hops: int = 5):
        self.max_hops = max_hops
        self.pheromone_space = PheromoneSpace()
        self.message_history: List[SwarmMessage] = []
        self.subscriptions: Dict[str, Set[str]] = defaultdict(set)  # agent_id -> message_types
        self._running = False
        self._tasks: List[asyncio.Task] = []
    
    async def start(self):
        """启动通信系统"""
        self._running = True
        # 启动衰减任务
        self._tasks.append(asyncio.create_task(self._decay_loop()))
        log.print_log("📡 信息素通信系统已启动", "info")
    
    async def stop(self):
        """停止通信系统"""
        self._running = False
        for task in self._tasks:
            task.cancel()
        self._tasks.clear()
        log.print_log("📡 信息素通信系统已停止", "info")
    
    async def _decay_loop(self):
        """衰减循环"""
        while self._running:
            try:
                await asyncio.sleep(1.0)
                await self.pheromone_space.decay_all()
            except asyncio.CancelledError:
                break
            except Exception as e:
                log.print_log(f"衰减循环错误: {e}", "error")
    
    async def broadcast_task(
        self,
        agent_id: str,
        task_description: str,
        required_capabilities: List[SwarmCapabilities] = None,
        location: tuple = None
    ) -> str:
        """广播任务"""
        # 发射任务信息素
        pheromone_id = await self.pheromone_space.emit(
            p_type=PheromoneType.TASK,
            source_id=agent_id,
            strength=1.0,
            location=location,
            content={
                "description": task_description,
                "capabilities": [c.value for c in (required_capabilities or [])]
            },
            ttl=30.0
        )
        
        # 创建消息
        message = SwarmMessage(
            msg_type=SwarmMessageType.TASK_BROADCAST,
            sender_id=agent_id,
            content={
                "description": task_description,
                "required_capabilities": [c.value for c in (required_capabilities or [])],
                "pheromone_id": pheromone_id
            },
            priority=3
        )
        
        self.message_history.append(message)
        log.print_log(f"[广播] {agent_id} 广播任务: {task_description[:30]}...", "debug")
        
        return message.message_id
    
    async def emit_attraction(
        self,
        agent_id: str,
        target_agent_id: str,
        strength: float = 0.8,
        reason: str = ""
    ):
        """发射吸引信息素"""
        await self.pheromone_space.emit(
            p_type=PheromoneType.ATTRACTION,
            source_id=agent_id,
            target_id=target_agent_id,
            strength=strength,
            content={"reason": reason}
        )
    
    async def emit_alert(
        self,
        agent_id: str,
        alert_type: str,
        severity: float = 1.0,
        location: tuple = None
    ):
        """发射警报信息素"""
        await self.pheromone_space.emit(
            p_type=PheromoneType.ALERT,
            source_id=agent_id,
            strength=severity,
            location=location,
            content={"alert_type": alert_type, "severity": severity}
        )
    
    async def share_consensus(
        self,
        agent_id: str,
        knowledge: Dict[str, Any]
    ):
        """共享共识知识"""
        # 发射共识信息素
        await self.pheromone_space.emit(
            p_type=PheromoneType.CONSENSUS,
            source_id=agent_id,
            strength=0.7,
            content=knowledge,
            ttl=120.0
        )
        
        # 创建共识同步消息
        message = SwarmMessage(
            msg_type=SwarmMessageType.CONSENSUS_SYNC,
            sender_id=agent_id,
            content={"data": knowledge},
            priority=2
        )
        
        self.message_history.append(message)
        log.print_log(f"[共识] {agent_id} 共享知识", "debug")
    
    async def subscribe(
        self,
        agent_id: str,
        message_types: List[SwarmMessageType]
    ):
        """订阅消息类型"""
        for msg_type in message_types:
            self.subscriptions[agent_id].add(msg_type.value)
        log.print_log(f"[订阅] {agent_id} 订阅 {len(message_types)} 种消息类型", "debug")
    
    async def unsubscribe(self, agent_id: str):
        """取消订阅"""
        if agent_id in self.subscriptions:
            del self.subscriptions[agent_id]
    
    async def get_messages_for_agent(
        self,
        agent_id: str,
        msg_types: List[SwarmMessageType] = None
    ) -> List[SwarmMessage]:
        """获取Agent的消息"""
        msg_types = msg_types or []
        filtered = []
        
        for msg in self.message_history[-100:]:  # 最近100条
            # 检查订阅
            if agent_id in self.subscriptions:
                if msg.msg_type.value not in self.subscriptions[agent_id]:
                    continue
            
            # 检查类型过滤
            if msg_types and msg.msg_type not in msg_types:
                continue
            
            # 检查目标
            if msg.target_id and msg.target_id != agent_id:
                continue
            
            filtered.append(msg)
        
        return filtered
    
    async def find_nearest_agent(
        self,
        from_agent_id: str,
        capability: SwarmCapabilities = None,
        radius: float = 200.0
    ) -> Optional[str]:
        """查找最近的Agent"""
        agents = await self.get_active_agents(from_agent_id, radius)
        
        if not agents:
            return None
        
        # 如果需要特定能力，过滤
        if capability:
            agents = [a for a in agents if capability in getattr(a, 'capabilities', [])]
        
        return agents[0] if agents else None
    
    async def get_active_agents(
        self,
        exclude_agent_id: str = None,
        radius: float = None
    ) -> List[str]:
        """获取活跃Agent列表"""
        positions = self.pheromone_space.agent_positions
        
        if exclude_agent_id:
            positions = {k: v for k, v in positions.items() if k != exclude_agent_id}
        
        return list(positions.keys())
    
    def get_stats(self) -> Dict[str, Any]:
        """获取通信统计"""
        return {
            "pheromone_space": self.pheromone_space.get_stats(),
            "message_history_size": len(self.message_history),
            "subscriptions": len(self.subscriptions),
            "max_hops": self.max_hops
        }


# 全局实例
_global_comm: Optional[PheromoneComm] = None


def get_pheromone_comm() -> PheromoneComm:
    """获取全局信息素通信实例"""
    global _global_comm
    if _global_comm is None:
        _global_comm = PheromoneComm()
    return _global_comm
