"""
蜂群代理基类 (Swarm Agent Base Class)
实现Agent节点的核心功能、状态管理和行为接口
"""
import asyncio
from abc import ABC, abstractmethod
from typing import Dict, List, Any, Optional, Callable
from datetime import datetime
from enum import Enum
import uuid
import json

from src.ai_write_x.core.swarm_protocol import (
    SwarmCapabilities, SwarmMessage, SwarmMessageType, SwarmTask
)
from src.ai_write_x.utils import log


class AgentStatus(str, Enum):
    """Agent状态枚举"""
    IDLE = "idle"                    # 空闲
    THINKING = "thinking"            # 思考中
    WORKING = "working"              #工作中
    WAITING = "waiting"              # 等待中
    VERIFYING = "verifying"          # 验证中
    COMPLETED = "completed"          # 已完成
    FAILED = "failed"                # 失败


class AgentNode(ABC):
    """蜂群代理节点基类"""
    
    def __init__(
        self,
        agent_id: str = None,
        name: str = "Agent",
        role: str = "general",
        capabilities: List[SwarmCapabilities] = None,
        memory_capacity: int = 100
    ):
        self.agent_id = agent_id or str(uuid.uuid4())[:8]
        self.name = name
        self.role = role
        self.capabilities = capabilities or []
        self.status = AgentStatus.IDLE
        
        # 记忆与状态
        self.short_term_memory: List[Dict] = []  # 短期记忆
        self.long_term_memory: Dict[str, Any] = {}  # 长期记忆
        self.memory_capacity = memory_capacity
        
        # 性能指标
        self.tasks_completed = 0
        self.tasks_failed = 0
        self.total_processing_time = 0.0
        self.success_rate = 1.0
        
        # 信息素
        self.pheromone_level = 1.0  # 信息素浓度
        self.last_active = datetime.now()
        
        # 回调函数
        self.on_message_received: Optional[Callable] = None
        self.on_status_changed: Optional[Callable] = None
        self.on_task_completed: Optional[Callable] = None
        
        # 任务队列
        self.task_queue: asyncio.Queue = asyncio.Queue()
        self._running = False
    
    @abstractmethod
    async def process_task(self, task: SwarmTask) -> Dict[str, Any]:
        """处理任务 - 子类必须实现"""
        pass
    
    @abstractmethod
    async def think(self, context: Dict[str, Any]) -> str:
        """思考 - 子类必须实现"""
        pass
    
    async def execute(self, task: SwarmTask) -> Dict[str, Any]:
        """执行任务的标准流程"""
        start_time = datetime.now()
        self.status = AgentStatus.THINKING
        self._notify_status_changed()
        
        try:
            # 思考阶段
            thought = await self.think({"task": task})
            log.print_log(f"[{self.name}] 思考: {thought[:100]}...", "debug")
            
            # 工作阶段
            self.status = AgentStatus.WORKING
            self._notify_status_changed()
            
            result = await self.process_task(task)
            
            # 完成阶段
            self.status = AgentStatus.COMPLETED
            self._notify_status_changed()
            
            # 更新统计
            elapsed = (datetime.now() - start_time).total_seconds()
            self.tasks_completed += 1
            self.total_processing_time += elapsed
            self.success_rate = self.tasks_completed / (self.tasks_completed + self.tasks_failed + 1)
            
            # 增强信息素
            self.pheromone_level = min(1.0, self.pheromone_level + 0.1)
            self.last_active = datetime.now()
            
            # 存储到记忆
            self._add_to_memory({
                "type": "task_completed",
                "task_id": task.task_id,
                "thought": thought,
                "result": result,
                "elapsed": elapsed,
                "timestamp": datetime.now().isoformat()
            })
            
            if self.on_task_completed:
                await self.on_task_completed(task, result)
            
            return {
                "status": "success",
                "agent_id": self.agent_id,
                "result": result,
                "thought": thought,
                "elapsed": elapsed
            }
            
        except Exception as e:
            self.status = AgentStatus.FAILED
            self.tasks_failed += 1
            self.success_rate = self.tasks_completed / (self.tasks_completed + self.tasks_failed + 1)
            
            # 降低信息素
            self.pheromone_level = max(0.1, self.pheromone_level - 0.2)
            
            log.print_log(f"[{self.name}] 任务失败: {e}", "error")
            
            return {
                "status": "failed",
                "agent_id": self.agent_id,
                "error": str(e)
            }
    
    async def receive_message(self, message: SwarmMessage) -> bool:
        """接收并处理蜂群消息"""
        try:
            # 更新记忆
            self._add_to_memory({
                "type": "message",
                "msg_type": message.msg_type,
                "from": message.sender_id,
                "content": message.content,
                "timestamp": datetime.now().isoformat()
            })
            
            # 根据消息类型处理
            if message.msg_type == SwarmMessageType.TASK_BROADCAST:
                # 新任务广播
                await self._handle_task_broadcast(message)
            elif message.msg_type == SwarmMessageType.CAPABILITY_QUERY:
                # 能力查询
                await self._handle_capability_query(message)
            elif message.msg_type == SwarmMessageType.CONSENSUS_SYNC:
                # 共识同步
                await self._handle_consensus_sync(message)
            
            if self.on_message_received:
                await self.on_message_received(message)
            
            return True
            
        except Exception as e:
            log.print_log(f"[{self.name}] 接收消息失败: {e}", "error")
            return False
    
    async def _handle_task_broadcast(self, message: SwarmMessage):
        """处理任务广播"""
        task_data = message.content.get("task")
        if task_data:
            log.print_log(f"[{self.name}] 收到新任务广播: {task_data.get('description', '')[:50]}", "debug")
    
    async def _handle_capability_query(self, message: SwarmMessage):
        """处理能力查询"""
        # 响应能力查询
        log.print_log(f"[{self.name}] 收到能力查询", "debug")
    
    async def _handle_consensus_sync(self, message: SwarmMessage):
        """处理共识同步"""
        consensus_data = message.content.get("data", {})
        self.long_term_memory.update(consensus_data)
    
    def _add_to_memory(self, item: Dict):
        """添加短期记忆"""
        self.short_term_memory.append(item)
        if len(self.short_term_memory) > self.memory_capacity:
            self.short_term_memory.pop(0)
    
    def store_long_term(self, key: str, value: Any):
        """存储长期记忆"""
        self.long_term_memory[key] = value
    
    def recall(self, key: str) -> Optional[Any]:
        """回忆长期记忆"""
        return self.long_term_memory.get(key)
    
    def _notify_status_changed(self):
        """通知状态变化"""
        if self.on_status_changed:
            try:
                self.on_status_changed(self.status)
            except Exception as e:
                log.print_log(f"状态变化回调失败: {e}", "warning")
    
    def get_stats(self) -> Dict[str, Any]:
        """获取Agent统计信息"""
        return {
            "agent_id": self.agent_id,
            "name": self.name,
            "role": self.role,
            "status": self.status.value,
            "capabilities": [c.value for c in self.capabilities],
            "tasks_completed": self.tasks_completed,
            "tasks_failed": self.tasks_failed,
            "success_rate": round(self.success_rate, 3),
            "avg_processing_time": round(self.total_processing_time / max(1, self.tasks_completed), 2),
            "pheromone_level": round(self.pheromone_level, 3),
            "memory_items": len(self.short_term_memory)
        }
    
    async def start(self):
        """启动Agent"""
        self._running = True
        log.print_log(f"🧠 [{self.name}] Agent 已启动", "info")
        
        while self._running:
            try:
                # 从队列获取任务
                task = await asyncio.wait_for(self.task_queue.get(), timeout=1.0)
                await self.execute(task)
            except asyncio.TimeoutError:
                continue
            except Exception as e:
                log.print_log(f"[{self.name}] 运行错误: {e}", "error")
    
    async def stop(self):
        """停止Agent"""
        self._running = False
        log.print_log(f"🧠 [{{self.name}}] Agent 已停止", "info")
    
    def __repr__(self):
        return f"AgentNode({self.name}, {self.role}, {self.status.value})"


class ReasoningAgent(AgentNode):
    """推理型Agent"""
    
    def __init__(self, agent_id: str = None, name: str = "ReasoningAgent", **kwargs):
        super().__init__(
            agent_id=agent_id,
            name=name,
            role="reasoning",
            capabilities=[SwarmCapabilities.REASONING, SwarmCapabilities.VERIFICATION],
            **kwargs
        )
    
    async def think(self, context: Dict[str, Any]) -> str:
        # 深度思考分析
        task = context.get("task")
        if hasattr(task, 'description'):
            desc = task.description[:50]
        else:
            desc = str(task)[:50]
        return f"深度推理分析任务: {desc}..."
    
    async def process_task(self, task: SwarmTask) -> Dict[str, Any]:
        # 模拟推理处理
        await asyncio.sleep(0.1)
        return {
            "reasoning_result": "分析完成",
            "confidence": 0.85,
            "evidence": ["证据1", "证据2"]
        }


class CreativeAgent(AgentNode):
    """创意型Agent"""
    
    def __init__(self, agent_id: str = None, name: str = "CreativeAgent", **kwargs):
        super().__init__(
            agent_id=agent_id,
            name=name,
            role="creative",
            capabilities=[SwarmCapabilities.CREATIVE_WRITING, SwarmCapabilities.IMAGE_DYNAMIC],
            **kwargs
        )
    
    async def think(self, context: Dict[str, Any]) -> str:
        return f"创意构思中..."
    
    async def process_task(self, task: SwarmTask) -> Dict[str, Any]:
        await asyncio.sleep(0.1)
        return {
            "creative_result": "创意内容生成完成",
            "style": "现代简约",
            "keywords": ["科技", "创新"]
        }


class ResearchAgent(AgentNode):
    """研究型Agent"""
    
    def __init__(self, agent_id: str = None, name: str = "ResearchAgent", **kwargs):
        super().__init__(
            agent_id=agent_id,
            name=name,
            role="research",
            capabilities=[SwarmCapabilities.RESEARCH, SwarmCapabilities.STRUCTURE_DESIGN],
            **kwargs
        )
    
    async def think(self, context: Dict[str, Any]) -> str:
        return f"搜索并整理信息..."
    
    async def process_task(self, task: SwarmTask) -> Dict[str, Any]:
        await asyncio.sleep(0.1)
        return {
            "research_result": "研究完成",
            "sources": ["source1", "source2"],
            "summary": "研究摘要"
        }
