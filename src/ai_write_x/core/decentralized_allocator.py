import asyncio
from typing import Dict, List, Any, Optional
from datetime import datetime
import uuid

from src.ai_write_x.core.swarm_protocol import SwarmTask, AgentBid, SwarmMessageType, SwarmMessage, SwarmCapabilities
from src.ai_write_x.utils import log

class DecentralizedAllocator:
    """
    V18.0 去中心化任务分配器
    
    实现 Agent 蜂群的自组织任务匹配：
    1. 接收任务广播
    2. 收集来自各 Agent 的 Bid (竞价)
    3. 执行匹配算法 (基于能力匹配度、负载和预估时间)
    4. 确认中标者并建立协作链路
    """
    
    def __init__(self):
        self.active_tasks: Dict[str, SwarmTask] = {}
        self.agent_registry: Dict[str, List[SwarmCapabilities]] = {}
        self._lock = asyncio.Lock()

    async def broadcast_task(self, task_description: str, required_caps: List[SwarmCapabilities]) -> str:
        """广播一个新任务到蜂群"""
        task = SwarmTask(
            description=task_description,
            required_capabilities=required_caps
        )
        async with self._lock:
            self.active_tasks[task.task_id] = task
        
        log.print_log(f"[Swarm] 广播任务: {task.task_id} | 所需能力: {required_caps}", "info")
        return task.task_id

    async def submit_bid(self, task_id: str, bid: AgentBid):
        """接收 Agent 的投标"""
        async with self._lock:
            if task_id not in self.active_tasks:
                log.print_log(f"[Swarm] 投标失败: 找不到任务 {task_id}", "warning")
                return
            
            task = self.active_tasks[task_id]
            if task.status != "pending":
                return
            
            task.bids.append(bid)
            log.print_log(f"[Swarm] Agent {bid.agent_id} 为任务 {task_id} 投递了竞价: {bid.bid_value}", "info")

    async def resolve_task(self, task_id: str) -> Optional[str]:
        """
        执行匹配算法，选择中标 Agent
        """
        async with self._lock:
            if task_id not in self.active_tasks:
                return None
            
            task = self.active_tasks[task_id]
            if not task.bids:
                log.print_log(f"[Swarm] 任务 {task_id} 无人应标，请检查 Agent 能力池", "warning")
                return None
            
            # 简单评分算法：bid_value 越高越好，estimated_time 越短越好
            # Score = (bid_value * 0.7) + ((1 / max(1, estimated_time)) * 0.3)
            best_bid = None
            best_score = -1.0
            
            for bid in task.bids:
                score = bid.bid_value * 0.7 + (1.0 / max(1, bid.estimated_time)) * 0.3
                if score > best_score:
                    best_score = score
                    best_bid = bid
            
            if best_bid:
                task.winner_agent_id = best_bid.agent_id
                task.status = "allocated"
                log.print_log(f"[Swarm] 任务 {task_id} 已分配。中标者: {best_bid.agent_id} | 分数: {best_score:.2f}", "success")
                return best_bid.agent_id
                
            return None

    def register_agent(self, agent_id: str, capabilities: List[SwarmCapabilities]):
        """Agent 上线注册能力"""
        self.agent_registry[agent_id] = capabilities
        log.print_log(f"[Swarm] Agent {agent_id} 已注册蜂群能力: {capabilities}", "success")
