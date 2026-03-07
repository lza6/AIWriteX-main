import asyncio
from typing import List, Dict, Any, Optional
from src.ai_write_x.core.swarm_protocol import SwarmCapabilities
from src.ai_write_x.core.collaboration_hub import get_collaboration_hub
from src.ai_write_x.utils import log

class SwarmDiscovery:
    """
    V18.0 蜂群自发现机制
    
    实现 Agent 之间的自动探测与连接：
    1. 持续扫描活跃 Agent 及其能力
    2. 建立 P2P 协作链路
    3. 动态负载感知
    """
    
    def __init__(self):
        self.hub = get_collaboration_hub()

    async def scan_swarm_nodes(self) -> List[str]:
        """扫描当前蜂群中的所有活跃节点"""
        nodes = list(self.hub.allocator.agent_registry.keys())
        log.print_log(f"[Swarm] 发现活跃节点: {len(nodes)} 个", "info")
        return nodes

    async def find_specialist(self, required_cap: SwarmCapabilities) -> Optional[str]:
        """在蜂群中根据能力寻找专家 Agent"""
        for agent_id, caps in self.hub.allocator.agent_registry.items():
            if required_cap in caps:
                log.print_log(f"[Swarm] 找到专家 Agent: {agent_id} (能力: {required_cap})", "success")
                return agent_id
        return None

    def broadcast_presence(self, agent_id: str, caps: List[SwarmCapabilities]):
        """Agent 广播自己的存在和能力"""
        self.hub.allocator.register_agent(agent_id, caps)
