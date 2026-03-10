"""
AIWriteX V18.0 - Collective Mind Module
集体意识中枢 - 群体智能的"大脑"

功能:
1. 群体状态管理: 维护所有智能体的实时状态
2. 意图识别: 从群体行为中识别集体意图
3. 知识同步: 全局知识图谱的同步与分发
4. 事件广播: WebSocket事件总线

架构:
- 采用Observer模式实现事件订阅
- 使用状态机管理群体生命周期
- 支持水平扩展的分片存储
"""

import asyncio
import json
import time
import hashlib
from typing import Dict, List, Set, Optional, Callable, Any, AsyncIterator
from dataclasses import dataclass, field, asdict
from datetime import datetime
from enum import Enum, auto
from collections import defaultdict
import numpy as np
from uuid import UUID, uuid4

# 处理导入路径问题
try:
    from sqlmodel import SQLModel, Field, select
except ImportError:
    SQLModel = None
    Field = None
    select = None

# 日志适配器
class LogAdapter:
    """日志适配器，提供统一的print_log接口"""
    def __init__(self):
        self.logger = None
        self._init_logger()
    
    def _init_logger(self):
        try:
            import src.ai_write_x.utils.log as _lg
            self.logger = _lg
        except ImportError:
            import logging
            self.logger = logging.getLogger('swarm_v2')
            handler = logging.StreamHandler()
            formatter = logging.Formatter('%(levelname)s: %(message)s')
            handler.setFormatter(formatter)
            self.logger.addHandler(handler)
            self.logger.setLevel(logging.INFO)
    
    def print_log(self, message, level="info"):
        """统一的日志输出接口"""
        if hasattr(self.logger, 'print_log'):
            self.logger.print_log(message, level)
        else:
            # 标准logging适配
            level_map = {
                "info": logging.INFO,
                "warning": logging.WARNING,
                "error": logging.ERROR,
                "success": logging.INFO,
                "debug": logging.DEBUG
            }
            log_level = level_map.get(level, logging.INFO)
            
            # 移除emoji前缀用于标准日志
            import re
            clean_msg = re.sub(r'[^\x00-\x7F]+', '', message)
            self.logger.log(log_level, clean_msg)

try:
    from src.ai_write_x.database.db_manager import get_session
except ImportError:
    def get_session():
        return None

lg = LogAdapter()


class IntentionType(Enum):
    """群体意图类型"""
    CONTENT_CREATION = auto()      # 内容创作
    TREND_ANALYSIS = auto()        # 趋势分析
    KNOWLEDGE_DISCOVERY = auto()   # 知识发现
    TASK_ORCHESTRATION = auto()    # 任务编排
    LEARNING = auto()              # 群体学习
    EXPLORATION = auto()           # 探索发现
    CONSENSUS = auto()             # 达成共识
    RECOVERY = auto()              # 故障恢复


@dataclass
class SwarmIntention:
    """群体意图数据类"""
    id: str = field(default_factory=lambda: str(uuid4()))
    type: IntentionType = IntentionType.CONTENT_CREATION
    confidence: float = 0.0  # 0-1置信度
    source_agents: List[str] = field(default_factory=list)
    target_agents: List[str] = field(default_factory=list)
    payload: Dict[str, Any] = field(default_factory=dict)
    created_at: float = field(default_factory=time.time)
    expires_at: Optional[float] = None
    priority: int = 5  # 1-10, 数字越小优先级越高
    
    def is_expired(self) -> bool:
        if self.expires_at is None:
            return False
        return time.time() > self.expires_at
    
    def to_dict(self) -> Dict[str, Any]:
        data = asdict(self)
        data['type'] = self.type.name
        return data
    
    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> 'SwarmIntention':
        data = data.copy()
        data['type'] = IntentionType[data['type']]
        return cls(**data)


class CollectiveState(Enum):
    """群体状态枚举"""
    INITIALIZING = "initializing"
    EMERGING = "emerging"           # 涌现形成中
    STABLE = "stable"               # 稳定运行
    ADAPTING = "adapting"           # 自适应调整
    DISSOLVING = "dissolving"       # 群体解散
    RECOVERING = "recovering"       # 恢复中


@dataclass 
class AgentState:
    """单个智能体状态"""
    agent_id: str
    role: str
    status: str  # idle, working, error, offline
    current_task: Optional[str] = None
    load: float = 0.0  # 0-1负载
    last_heartbeat: float = field(default_factory=time.time)
    capabilities: List[str] = field(default_factory=list)
    position: tuple = field(default_factory=lambda: (0.0, 0.0, 0.0))  # 3D空间位置
    memory_usage: float = 0.0
    cpu_usage: float = 0.0
    
    def is_alive(self, timeout: float = 30.0) -> bool:
        return (time.time() - self.last_heartbeat) < timeout


@dataclass
class EmergencePattern:
    """涌现行为模式"""
    pattern_id: str = field(default_factory=lambda: str(uuid4()))
    name: str = ""
    description: str = ""
    agent_count_threshold: int = 3
    confidence_threshold: float = 0.7
    detected_at: float = field(default_factory=time.time)
    participating_agents: List[str] = field(default_factory=list)
    metrics: Dict[str, float] = field(default_factory=dict)


class CollectiveMind:
    """
    集体意识中枢 - V18核心组件
    
    单例模式确保全局只有一个意识中枢实例
    """
    _instance: Optional['CollectiveMind'] = None
    _lock = asyncio.Lock()
    
    def __new__(cls):
        if cls._instance is None:
            cls._instance = super().__new__(cls)
            cls._instance._initialized = False
        return cls._instance
    
    def __init__(self):
        if self._initialized:
            return
            
        self._initialized = True
        self.state = CollectiveState.INITIALIZING
        self.agents: Dict[str, AgentState] = {}
        self.intentions: List[SwarmIntention] = []
        self.patterns: List[EmergencePattern] = []
        self.knowledge_graph: Dict[str, Any] = {}
        
        # 事件系统
        self._subscribers: Dict[str, List[Callable]] = defaultdict(list)
        self._event_queue: asyncio.Queue = asyncio.Queue()
        self._running = False
        
        # 历史记录
        self._state_history: List[Dict] = []
        self._max_history = 1000
        
        # 分片存储
        self._shards: Dict[str, Any] = {}
        self._shard_count = 4
        
        lg.print_log("🧠 CollectiveMind V18.0 initialized", "info")
    
    @classmethod
    async def get_instance(cls) -> 'CollectiveMind':
        """异步获取单例实例"""
        async with cls._lock:
            if cls._instance is None:
                cls._instance = cls()
            return cls._instance
    
    async def start(self):
        """启动集体意识中枢"""
        if self._running:
            return
            
        self._running = True
        self.state = CollectiveState.EMERGING
        
        # 启动后台任务
        asyncio.create_task(self._heartbeat_loop())
        asyncio.create_task(self._intention_processor())
        asyncio.create_task(self._pattern_detector())
        asyncio.create_task(self._event_dispatcher())
        
        lg.print_log("🚀 CollectiveMind started", "success")
    
    async def stop(self):
        """停止集体意识中枢"""
        self._running = False
        self.state = CollectiveState.DISSOLVING
        lg.print_log("🛑 CollectiveMind stopped", "warning")
    
    # ========== 智能体管理 ==========
    
    async def register_agent(self, agent_id: str, role: str, 
                            capabilities: List[str]) -> AgentState:
        """注册新智能体"""
        agent = AgentState(
            agent_id=agent_id,
            role=role,
            status="idle",
            capabilities=capabilities
        )
        self.agents[agent_id] = agent
        
        await self._broadcast_event("agent_joined", {
            "agent_id": agent_id,
            "role": role,
            "total_agents": len(self.agents)
        })
        
        lg.print_log(f"🤖 Agent registered: {agent_id} ({role})", "info")
        return agent
    
    async def unregister_agent(self, agent_id: str):
        """注销智能体"""
        if agent_id in self.agents:
            del self.agents[agent_id]
            await self._broadcast_event("agent_left", {
                "agent_id": agent_id,
                "total_agents": len(self.agents)
            })
    
    async def update_agent_state(self, agent_id: str, 
                                  updates: Dict[str, Any]) -> bool:
        """更新智能体状态"""
        if agent_id not in self.agents:
            return False
            
        agent = self.agents[agent_id]
        for key, value in updates.items():
            if hasattr(agent, key):
                setattr(agent, key, value)
        
        agent.last_heartbeat = time.time()
        return True
    
    async def heartbeat(self, agent_id: str, metrics: Dict[str, float]):
        """处理智能体心跳"""
        if agent_id in self.agents:
            agent = self.agents[agent_id]
            agent.last_heartbeat = time.time()
            agent.load = metrics.get('load', agent.load)
            agent.memory_usage = metrics.get('memory', agent.memory_usage)
            agent.cpu_usage = metrics.get('cpu', agent.cpu_usage)
    
    def get_alive_agents(self, timeout: float = 30.0) -> List[AgentState]:
        """获取存活智能体列表"""
        return [a for a in self.agents.values() if a.is_alive(timeout)]
    
    def get_agents_by_role(self, role: str) -> List[AgentState]:
        """按角色获取智能体"""
        return [a for a in self.agents.values() if a.role == role]
    
    def get_agents_by_capability(self, capability: str) -> List[AgentState]:
        """按能力获取智能体"""
        return [a for a in self.agents.values() 
                if capability in a.capabilities]
    
    # ========== 意图管理 ==========
    
    async def submit_intention(self, intention: SwarmIntention) -> str:
        """提交群体意图"""
        # 计算意图置信度
        intention.confidence = self._calculate_intention_confidence(intention)
        
        self.intentions.append(intention)
        
        # 按优先级排序
        self.intentions.sort(key=lambda x: x.priority)
        
        await self._broadcast_event("intention_submitted", {
            "intention_id": intention.id,
            "type": intention.type.name,
            "confidence": intention.confidence,
            "priority": intention.priority
        })
        
        lg.print_log(f"🎯 Intention submitted: {intention.type.name} "
                    f"(confidence: {intention.confidence:.2f})", "info")
        return intention.id
    
    def _calculate_intention_confidence(self, intention: SwarmIntention) -> float:
        """计算意图置信度"""
        if not intention.source_agents:
            return 0.0
        
        # 基于来源智能体的可信度计算
        valid_sources = 0
        total_weight = 0
        
        for agent_id in intention.source_agents:
            if agent_id in self.agents:
                agent = self.agents[agent_id]
                if agent.is_alive():
                    valid_sources += 1
                    # 负载越低，权重越高
                    weight = 1.0 - agent.load
                    total_weight += weight
        
        if valid_sources == 0:
            return 0.0
        
        # 综合计算：来源数量、权重平均、一致性
        coverage = valid_sources / max(len(self.agents), 1)
        avg_weight = total_weight / valid_sources
        
        confidence = (coverage * 0.4 + avg_weight * 0.6)
        return min(confidence, 1.0)
    
    def get_active_intentions(self) -> List[SwarmIntention]:
        """获取活跃意图"""
        return [i for i in self.intentions if not i.is_expired()]
    
    def get_intentions_by_type(self, intention_type: IntentionType) -> List[SwarmIntention]:
        """按类型获取意图"""
        return [i for i in self.intentions 
                if i.type == intention_type and not i.is_expired()]
    
    # ========== 涌现检测 ==========
    
    async def _pattern_detector(self):
        """涌现模式检测器 - 后台任务"""
        while self._running:
            try:
                await self._detect_emergence_patterns()
                await asyncio.sleep(5.0)  # 每5秒检测一次
            except Exception as e:
                lg.print_log(f"Pattern detection error: {e}", "error")
    
    async def _detect_emergence_patterns(self):
        """检测涌现行为模式"""
        alive_agents = self.get_alive_agents()
        
        if len(alive_agents) < 3:
            return
        
        # 检测协作模式
        working_agents = [a for a in alive_agents if a.status == "working"]
        if len(working_agents) >= 3:
            pattern = EmergencePattern(
                name="Collaborative_Surge",
                description=f"{len(working_agents)} agents working simultaneously",
                agent_count_threshold=3,
                participating_agents=[a.agent_id for a in working_agents],
                metrics={
                    "avg_load": np.mean([a.load for a in working_agents]),
                    "coordination_score": len(working_agents) / len(alive_agents)
                }
            )
            self.patterns.append(pattern)
            
            await self._broadcast_event("emergence_detected", {
                "pattern": pattern.name,
                "agents": pattern.participating_agents,
                "metrics": pattern.metrics
            })
        
        # 检测学习模式
        learning_agents = [a for a in alive_agents 
                          if "learning" in a.current_task.lower() 
                          if a.current_task]
        if len(learning_agents) >= 2:
            pattern = EmergencePattern(
                name="Collective_Learning",
                description="Multiple agents in learning mode",
                participating_agents=[a.agent_id for a in learning_agents]
            )
            self.patterns.append(pattern)
    
    def get_recent_patterns(self, count: int = 10) -> List[EmergencePattern]:
        """获取最近的涌现模式"""
        return sorted(self.patterns, 
                     key=lambda p: p.detected_at, 
                     reverse=True)[:count]
    
    # ========== 知识管理 ==========
    
    async def sync_knowledge(self, agent_id: str, knowledge: Dict[str, Any]):
        """同步智能体知识到全局图谱"""
        # 计算知识哈希
        knowledge_str = json.dumps(knowledge, sort_keys=True)
        knowledge_hash = hashlib.sha256(knowledge_str.encode()).hexdigest()[:16]
        
        # 更新全局知识图谱
        self.knowledge_graph[agent_id] = {
            "hash": knowledge_hash,
            "data": knowledge,
            "updated_at": time.time()
        }
        
        # 广播知识更新
        await self._broadcast_event("knowledge_synced", {
            "agent_id": agent_id,
            "hash": knowledge_hash,
            "graph_size": len(self.knowledge_graph)
        })
    
    def get_collective_knowledge(self) -> Dict[str, Any]:
        """获取集体知识图谱"""
        return self.knowledge_graph.copy()
    
    def query_knowledge(self, query: str) -> List[Dict[str, Any]]:
        """查询集体知识"""
        results = []
        query_lower = query.lower()
        
        for agent_id, knowledge in self.knowledge_graph.items():
            data = knowledge.get("data", {})
            # 简单字符串匹配，实际可接入向量检索
            if query_lower in json.dumps(data).lower():
                results.append({
                    "agent_id": agent_id,
                    "knowledge": data,
                    "updated_at": knowledge.get("updated_at")
                })
        
        return results
    
    # ========== 事件系统 ==========
    
    def subscribe(self, event_type: str, callback: Callable):
        """订阅事件"""
        self._subscribers[event_type].append(callback)
    
    def unsubscribe(self, event_type: str, callback: Callable):
        """取消订阅"""
        if event_type in self._subscribers:
            if callback in self._subscribers[event_type]:
                self._subscribers[event_type].remove(callback)
    
    async def _broadcast_event(self, event_type: str, data: Dict[str, Any]):
        """广播事件"""
        event = {
            "type": event_type,
            "data": data,
            "timestamp": time.time()
        }
        await self._event_queue.put(event)
    
    async def _event_dispatcher(self):
        """事件分发器 - 后台任务"""
        while self._running:
            try:
                event = await asyncio.wait_for(
                    self._event_queue.get(), 
                    timeout=1.0
                )
                
                event_type = event["type"]
                if event_type in self._subscribers:
                    for callback in self._subscribers[event_type]:
                        try:
                            if asyncio.iscoroutinefunction(callback):
                                asyncio.create_task(callback(event))
                            else:
                                callback(event)
                        except Exception as e:
                            lg.print_log(f"Event handler error: {e}", "error")
                
                # 也发送给通配符订阅者
                if "*" in self._subscribers:
                    for callback in self._subscribers["*"]:
                        try:
                            if asyncio.iscoroutinefunction(callback):
                                asyncio.create_task(callback(event))
                            else:
                                callback(event)
                        except Exception as e:
                            lg.print_log(f"Wildcard handler error: {e}", "error")
                            
            except asyncio.TimeoutError:
                continue
            except Exception as e:
                lg.print_log(f"Event dispatcher error: {e}", "error")
    
    # ========== 后台任务 ==========
    
    async def _heartbeat_loop(self):
        """心跳循环 - 检查智能体存活"""
        while self._running:
            try:
                dead_agents = []
                for agent_id, agent in self.agents.items():
                    if not agent.is_alive(timeout=60.0):
                        dead_agents.append(agent_id)
                
                for agent_id in dead_agents:
                    lg.print_log(f"💀 Agent timeout: {agent_id}", "warning")
                    await self.unregister_agent(agent_id)
                
                # 更新群体状态
                await self._update_collective_state()
                
                await asyncio.sleep(10.0)
            except Exception as e:
                lg.print_log(f"Heartbeat error: {e}", "error")
    
    async def _update_collective_state(self):
        """更新群体状态"""
        alive_count = len(self.get_alive_agents())
        total_count = len(self.agents)
        
        if total_count == 0:
            new_state = CollectiveState.INITIALIZING
        elif alive_count < total_count * 0.5:
            new_state = CollectiveState.RECOVERING
        elif self.state == CollectiveState.EMERGING and alive_count >= 3:
            new_state = CollectiveState.STABLE
        elif alive_count == total_count:
            new_state = CollectiveState.STABLE
        else:
            new_state = CollectiveState.ADAPTING
        
        if new_state != self.state:
            old_state = self.state
            self.state = new_state
            
            await self._broadcast_event("state_changed", {
                "from": old_state.value,
                "to": new_state.value,
                "alive_agents": alive_count,
                "total_agents": total_count
            })
            
            lg.print_log(f"🔄 Collective state: {old_state.value} → {new_state.value}", "info")
    
    async def _intention_processor(self):
        """意图处理器 - 处理过期意图"""
        while self._running:
            try:
                # 清理过期意图
                expired = [i for i in self.intentions if i.is_expired()]
                for intention in expired:
                    self.intentions.remove(intention)
                    await self._broadcast_event("intention_expired", {
                        "intention_id": intention.id,
                        "type": intention.type.name
                    })
                
                await asyncio.sleep(30.0)
            except Exception as e:
                lg.print_log(f"Intention processor error: {e}", "error")
    
    # ========== 统计与监控 ==========
    
    def get_stats(self) -> Dict[str, Any]:
        """获取统计信息"""
        alive_agents = self.get_alive_agents()
        
        return {
            "state": self.state.value,
            "total_agents": len(self.agents),
            "alive_agents": len(alive_agents),
            "active_intentions": len(self.get_active_intentions()),
            "total_patterns": len(self.patterns),
            "knowledge_nodes": len(self.knowledge_graph),
            "avg_load": np.mean([a.load for a in alive_agents]) if alive_agents else 0.0,
            "timestamp": time.time()
        }
    
    def get_state_snapshot(self) -> Dict[str, Any]:
        """获取完整状态快照"""
        return {
            "collective_state": self.state.value,
            "agents": {aid: asdict(a) for aid, a in self.agents.items()},
            "intentions": [i.to_dict() for i in self.intentions],
            "patterns": [asdict(p) for p in self.patterns[-10:]],  # 最近10个模式
            "stats": self.get_stats()
        }
