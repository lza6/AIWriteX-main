import asyncio
import json
from datetime import datetime
from typing import Dict, Any, List
from src.ai_write_x.core.collaboration_hub import get_collaboration_hub
from src.ai_write_x.utils import log

class SwarmStateManager:
    """
    V18.0 蜂群状态同步管理器
    
    实现大规模并发下的 Agent 状态实时同步：
    1. 维护全局 Agent 活跃状态表
    2. 处理状态心跳与离线判定
    3. 同步任务执行进度到内存共识
    """
    
    def __init__(self):
        self.hub = get_collaboration_hub()
        self.agent_stats: Dict[str, Dict[str, Any]] = {}
        self._lock = asyncio.Lock()

    async def update_agent_status(self, agent_id: str, status: str, load_percentage: float):
        """更新 Agent 状态心跳"""
        async with self._lock:
            self.agent_stats[agent_id] = {
                "status": status,
                "load": load_percentage,
                "last_seen": datetime.now().isoformat()
            }
            # 同步关键状态到共识记忆，供其他节点查询及负载平衡
            if load_percentage > 90:
                await self.hub.sync_swarm_memory(f"node_load_{agent_id}", "critical", agent_id, 0.9)

    async def get_swarm_snapshot(self) -> Dict[str, Any]:
        """获取蜂群实时全景快照"""
        async with self._lock:
            return {
                "active_nodes": len(self.agent_stats),
                "nodes": self.agent_stats,
                "timestamp": datetime.now().isoformat()
            }

    async def cleanup_offline_agents(self, timeout_seconds: int = 60):
        """清理长时间未响应的 Agent"""
        now = datetime.now()
        async with self._lock:
            to_remove = []
            for agent_id, data in self.agent_stats.items():
                last_seen = datetime.fromisoformat(data["last_seen"])
                if (now - last_seen).total_seconds() > timeout_seconds:
                    to_remove.append(agent_id)
            
            for agent_id in to_remove:
                del self.agent_stats[agent_id]
                log.print_log(f"[Swarm] 节点 {agent_id} 已从活跃列表中移除 (超时)", "warning")
