"""
去中心化通信系统 V3 (Decentralized Communication V3)

解决痛点:
1. Agent间通信耦合度高 → 实现事件总线、去中心化消息传递

核心特性:
- 基于事件总线的发布-订阅模式
- 去中心化消息路由 (无单点故障)
- 消息持久化与重试机制
- 动态Agent发现
"""
import asyncio
from typing import Dict, List, Any, Optional, Callable, Set, Tuple, Coroutine
from datetime import datetime, timedelta
from dataclasses import dataclass, field
from enum import Enum
from collections import defaultdict, deque
import uuid
import json
import random

from src.ai_write_x.utils import log


class MessagePriority(Enum):
    """消息优先级"""
    CRITICAL = 0
    HIGH = 1
    NORMAL = 2
    LOW = 3


class MessageType(Enum):
    """消息类型"""
    TASK_ASSIGN = "task_assign"
    TASK_COMPLETE = "task_complete"
    TASK_FAILED = "task_failed"
    HEARTBEAT = "heartbeat"
    STATUS_UPDATE = "status_update"
    CAPABILITY_AD = "capability_ad"
    CONSENSUS_PREPARE = "consensus_prepare"
    CONSENSUS_VOTE = "consensus_vote"
    CONSENSUS_COMMIT = "consensus_commit"
    KNOWLEDGE_SHARE = "knowledge_share"
    QUERY_REQUEST = "query_request"
    QUERY_RESPONSE = "query_response"
    JOIN_CLUSTER = "join_cluster"
    LEAVE_CLUSTER = "leave_cluster"
    LOAD_REPORT = "load_report"
    REBALANCE_REQUEST = "rebalance_request"


@dataclass
class Message:
    """消息"""
    msg_type: MessageType
    sender_id: str
    payload: Dict[str, Any]
    msg_id: str = field(default_factory=lambda: str(uuid.uuid4())[:8])
    timestamp: datetime = field(default_factory=datetime.now)
    priority: MessagePriority = MessagePriority.NORMAL
    ttl: int = 3
    trace: List[str] = field(default_factory=list)
    
    def to_dict(self) -> Dict:
        return {
            "msg_id": self.msg_id,
            "msg_type": self.msg_type.value,
            "sender_id": self.sender_id,
            "payload": self.payload,
            "timestamp": self.timestamp.isoformat(),
            "priority": self.priority.value,
            "ttl": self.ttl,
            "trace": self.trace
        }


@dataclass
class AgentInfo:
    """Agent信息"""
    agent_id: str
    capabilities: List[str] = field(default_factory=list)
    specialties: List[str] = field(default_factory=list)
    load_score: float = 0.0
    last_heartbeat: datetime = field(default_factory=datetime.now)
    is_active: bool = True
    address: Optional[str] = None


class EventBus:
    """事件总线 - 发布订阅模式"""
    
    def __init__(self):
        self._subscribers: Dict[MessageType, List[Tuple[str, Callable]]] = defaultdict(list)
        self._message_history: deque = deque(maxlen=10000)
        self._seen_messages: Set[str] = set()
        self._message_queue: asyncio.PriorityQueue = asyncio.PriorityQueue()
        self._stats = {"published": 0, "delivered": 0, "dropped": 0}
        self._processing = False
        self._msg_counter = 0  # 用于解决相同优先级的消息比较问题
    
    def subscribe(self, agent_id: str, msg_type: MessageType, callback: Callable):
        self._subscribers[msg_type].append((agent_id, callback))
    
    def unsubscribe(self, agent_id: str, msg_type: Optional[MessageType] = None):
        if msg_type:
            self._subscribers[msg_type] = [(aid, cb) for aid, cb in self._subscribers[msg_type] if aid != agent_id]
        else:
            for mt in self._subscribers:
                self._subscribers[mt] = [(aid, cb) for aid, cb in self._subscribers[mt] if aid != agent_id]
    
    async def publish(self, message: Message) -> bool:
        if message.msg_id in self._seen_messages:
            self._stats["dropped"] += 1
            return False
        
        self._seen_messages.add(message.msg_id)
        if len(self._seen_messages) > 10000:
            self._seen_messages = set(list(self._seen_messages)[-5000:])
        
        self._message_history.append(message)
        # 放入优先级队列 - 使用 (priority, counter, message) 元组确保可比较
        self._msg_counter += 1
        priority_val = message.priority.value
        await self._message_queue.put((priority_val, self._msg_counter, message))
        self._stats["published"] += 1
        return True
    
    async def start_processing(self):
        self._processing = True
        while self._processing:
            try:
                # 解包元组 (priority, counter, message)
                item = await asyncio.wait_for(self._message_queue.get(), timeout=1.0)
                if len(item) == 3:
                    priority, counter, message = item
                else:
                    message = item
                await self._deliver(message)
            except asyncio.TimeoutError:
                continue
            except Exception as e:
                log.print_log(f"[EventBus] 消息处理错误: {e}", "error")
    
    async def _deliver(self, message: Message):
        subscribers = self._subscribers.get(message.msg_type, [])
        if not subscribers:
            return
        
        message.trace.append(f"bus_{datetime.now().timestamp()}")
        
        tasks = []
        for agent_id, callback in subscribers:
            if agent_id != message.sender_id or message.msg_type in [MessageType.CONSENSUS_PREPARE, MessageType.CONSENSUS_VOTE]:
                tasks.append(self._safe_callback(callback, message))
        
        if tasks:
            await asyncio.gather(*tasks, return_exceptions=True)
            self._stats["delivered"] += len(tasks)
    
    async def _safe_callback(self, callback: Callable, message: Message):
        try:
            await callback(message)
        except Exception as e:
            log.print_log(f"[EventBus] 回调错误: {e}", "error")
    
    def stop_processing(self):
        self._processing = False
    
    def get_stats(self) -> Dict:
        return {**self._stats, "queue_size": self._message_queue.qsize()}


class GossipProtocol:
    """流言协议 - 去中心化信息传播"""
    
    def __init__(self, fanout: int = 3):
        self.fanout = fanout
        self.agent_neighbors: Dict[str, Set[str]] = defaultdict(set)
        self._seen_gossips: Set[str] = set()
    
    def add_neighbor(self, agent_id: str, neighbor_id: str):
        self.agent_neighbors[agent_id].add(neighbor_id)
    
    def remove_neighbor(self, agent_id: str, neighbor_id: str):
        self.agent_neighbors[agent_id].discard(neighbor_id)
    
    def get_random_neighbors(self, agent_id: str, n: Optional[int] = None) -> List[str]:
        neighbors = list(self.agent_neighbors[agent_id])
        if not neighbors:
            return []
        n = n or min(self.fanout, len(neighbors))
        return random.sample(neighbors, min(n, len(neighbors)))
    
    async def gossip(self, sender_id: str, message: Message, publish_fn):
        gossip_key = f"{message.msg_id}_{sender_id}"
        if gossip_key in self._seen_gossips:
            return
        
        self._seen_gossips.add(gossip_key)
        if len(self._seen_gossips) > 50000:
            self._seen_gossips = set(list(self._seen_gossips)[-25000:])
        
        neighbors = self.get_random_neighbors(sender_id)
        
        for neighbor_id in neighbors:
            forwarded = Message(
                msg_type=message.msg_type,
                sender_id=message.sender_id,
                payload=message.payload,
                msg_id=message.msg_id,
                priority=message.priority,
                ttl=message.ttl - 1,
                trace=message.trace + [sender_id]
            )
            
            if forwarded.ttl > 0:
                await publish_fn(forwarded)


class DecentralizedCommManager:
    """去中心化通信管理器"""
    
    def __init__(self, agent_id: str):
        self.agent_id = agent_id
        self.event_bus = EventBus()
        self.gossip = GossipProtocol(fanout=3)
        self.discovered_agents: Dict[str, AgentInfo] = {}
        self._retry_queue: deque = deque(maxlen=1000)
        self._max_retries = 3
        self._running = False
        self._tasks: List[asyncio.Task] = []
        self._heartbeat_interval = 10.0
        self._agent_timeout = 30.0
        
        log.print_log(f"[DecentralizedComm] Agent {agent_id} 通信管理器已初始化", "success")
    
    async def start(self):
        if self._running:
            return
        
        self._running = True
        
        bus_task = asyncio.create_task(self.event_bus.start_processing())
        self._tasks.append(bus_task)
        
        heartbeat_task = asyncio.create_task(self._heartbeat_loop())
        self._tasks.append(heartbeat_task)
        
        await self.broadcast(Message(
            msg_type=MessageType.JOIN_CLUSTER,
            sender_id=self.agent_id,
            payload={"capabilities": [], "timestamp": datetime.now().isoformat()},
            priority=MessagePriority.HIGH
        ))
        
        log.print_log(f"[DecentralizedComm] Agent {self.agent_id} 通信系统已启动", "success")
    
    async def stop(self):
        self._running = False
        
        await self.broadcast(Message(
            msg_type=MessageType.LEAVE_CLUSTER,
            sender_id=self.agent_id,
            payload={"reason": "graceful_shutdown"},
            priority=MessagePriority.HIGH
        ))
        
        for task in self._tasks:
            task.cancel()
        
        self.event_bus.stop_processing()
        log.print_log(f"[DecentralizedComm] Agent {self.agent_id} 通信系统已停止", "info")
    
    def register_handler(self, msg_type: MessageType, handler: Callable):
        async def wrapped(message: Message):
            if message.sender_id != self.agent_id:
                self._update_agent_activity(message.sender_id)
            await handler(message)
        
        self.event_bus.subscribe(self.agent_id, msg_type, wrapped)
    
    async def send(self, target_id: str, msg_type: MessageType, payload: Dict, priority: MessagePriority = MessagePriority.NORMAL, retry: bool = True) -> bool:
        message = Message(
            msg_type=msg_type,
            sender_id=self.agent_id,
            payload={**payload, "target_id": target_id},
            priority=priority
        )
        
        if target_id not in self.discovered_agents:
            await self.gossip.gossip(self.agent_id, message, self.event_bus.publish)
            if retry:
                self._retry_queue.append({"message": message, "target_id": target_id, "retries": 0, "next_retry": datetime.now() + timedelta(seconds=5)})
            return False
        
        return await self.event_bus.publish(message)
    
    async def broadcast(self, message: Message, use_gossip: bool = True) -> bool:
        if use_gossip and message.ttl > 0:
            await self.gossip.gossip(self.agent_id, message, self.event_bus.publish)
        return await self.event_bus.publish(message)
    
    def _update_agent_activity(self, agent_id: str):
        if agent_id in self.discovered_agents:
            self.discovered_agents[agent_id].last_heartbeat = datetime.now()
            self.discovered_agents[agent_id].is_active = True
    
    async def _heartbeat_loop(self):
        while self._running:
            try:
                await asyncio.sleep(self._heartbeat_interval)
                await self.broadcast(Message(
                    msg_type=MessageType.HEARTBEAT,
                    sender_id=self.agent_id,
                    payload={"load_score": 0.0, "timestamp": datetime.now().isoformat()},
                    priority=MessagePriority.LOW
                ))
            except asyncio.CancelledError:
                break
            except Exception as e:
                log.print_log(f"[DecentralizedComm] 心跳错误: {e}", "error")
    
    def handle_join_cluster(self, message: Message):
        agent_id = message.sender_id
        if agent_id != self.agent_id:
            self.discovered_agents[agent_id] = AgentInfo(
                agent_id=agent_id,
                capabilities=message.payload.get("capabilities", []),
                specialties=message.payload.get("specialties", [])
            )
            self.gossip.add_neighbor(self.agent_id, agent_id)
            log.print_log(f"[DecentralizedComm] 发现新Agent: {agent_id}", "info")
    
    def handle_leave_cluster(self, message: Message):
        agent_id = message.sender_id
        if agent_id in self.discovered_agents:
            self.discovered_agents[agent_id].is_active = False
            self.gossip.remove_neighbor(self.agent_id, agent_id)
    
    def get_active_agents(self) -> List[str]:
        return [aid for aid, info in self.discovered_agents.items() if info.is_active]
    
    def get_stats(self) -> Dict:
        return {
            "agent_id": self.agent_id,
            "discovered_agents": len(self.discovered_agents),
            "active_agents": len(self.get_active_agents()),
            "event_bus_stats": self.event_bus.get_stats()
        }


_comm_managers: Dict[str, DecentralizedCommManager] = {}

def get_comm_manager(agent_id: str) -> DecentralizedCommManager:
    global _comm_managers
    if agent_id not in _comm_managers:
        _comm_managers[agent_id] = DecentralizedCommManager(agent_id)
    return _comm_managers[agent_id]