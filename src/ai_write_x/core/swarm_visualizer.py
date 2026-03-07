from typing import Dict, List, Any
from datetime import datetime
import json

from src.ai_write_x.core.collaboration_hub import get_collaboration_hub
from src.ai_write_x.core.swarm_state_manager import SwarmStateManager

class SwarmVisualizer:
    """
    V18.0 蜂群可视化驱动器
    
    为前端实时拓扑图提供数据接口：
    1. 生成 Cytoscape.js 兼容的拓扑结构
    2. 提供 Agent 节点间的协作关系链路
    3. 实时聚合任务状态
    """
    
    def __init__(self, state_manager: SwarmStateManager):
        self.hub = get_collaboration_hub()
        self.state_manager = state_manager

    async def get_topology_data(self) -> Dict[str, Any]:
        """生成前端可视化的拓扑 JSON 数据"""
        snapshot = await self.state_manager.get_swarm_snapshot()
        nodes = []
        edges = []
        
        # 1. 转换 Agent 节点 (优先从实时快照获取)
        snapshot_nodes = snapshot.get("nodes", {})
        
        # 获取所有已注册的 Agent (为了在没有心跳时也能显示展示)
        all_registered_agents = self.hub.allocator.agent_registry
        
        for agent_id, capabilities in all_registered_agents.items():
            status = "idle"
            load = 0.0
            
            # 汉化状态映射
            status_map = {
                "idle": "休眠中",
                "active": "就绪",
                "executing": "协同中",
                "busy": "负载中"
            }
            display_status = status_map.get(status, status)
            
            nodes.append({
                "data": {
                    "id": agent_id,
                    "label": f"{agent_id}\n({display_status})",
                    "type": "agent",
                    "load": load,
                    "status": status,
                    "capabilities": [c.value if hasattr(c, 'value') else str(c) for c in capabilities]
                }
            })
            
        # 转换活跃任务为节点
        tasks = self.hub.allocator.active_tasks
        for tid, task in tasks.items():
            nodes.append({
                "data": {
                    "id": tid,
                    "label": task.description[:15] + "...",
                    "type": "task",
                    "status": task.status
                }
            })
            
            # 如果已分配，添加 Agent -> Task 的边
            if task.winner_agent_id:
                edges.append({
                    "data": {
                        "id": f"e_{task.winner_agent_id}_{tid}",
                        "source": task.winner_agent_id,
                        "target": tid,
                        "label": "协作执行"
                    }
                })

        return {
            "elements": {
                "nodes": nodes,
                "edges": edges
            },
            "stats": {
                "node_count": len(nodes),
                "edge_count": len(edges),
                "consensus_digest": self.hub.memory.get_topology_digest()
            }
        }
