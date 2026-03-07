import asyncio
from typing import List, Dict, Any
from src.ai_write_x.core.swarm_protocol import SwarmCapabilities, SwarmMessageType, SwarmMessage
from src.ai_write_x.core.collaboration_hub import get_collaboration_hub
from src.ai_write_x.core.agent_factory import AgentFactory
from src.ai_write_x.core.base_framework import AgentConfig
from src.ai_write_x.utils import log

class SwarmSpawner:
    """
    V18.0 蜂群 Agent 动态衍生器
    
    支持 Agent 之间的对等衍生：
    1. Agent 发现任务过于复杂时，请求衍生具备特定能力的新子 Agent
    2. 自动化 Agent 角色演化
    """
    
    def __init__(self):
        self.factory = AgentFactory()
        self.hub = get_collaboration_hub()

    async def spawn_specialized_agent(self, parent_id: str, required_caps: List[SwarmCapabilities]) -> str:
        """动态衍生一个具备特定能力的专业 Agent"""
        new_agent_id = f"swarm_{parent_id}_{len(required_caps)}"
        
        # 构造 Agent 配置
        config = AgentConfig(
            name=new_agent_id,
            role=f"Swarm Specialist ({', '.join(required_caps)})",
            goal=f"协助 {parent_id} 完成具有高度专业性要求的蜂群子任务",
            backstory=f"由 Agent {parent_id} 动态衍生。专注于以下核心能力：{required_caps}",
            tools=[], # 默认继承通用工具或按需分发
            capabilities=required_caps,
            swarm_metadata={"parent_agent": parent_id}
        )
        
        # 创建 Agent 实例 (这里简化了创建过程，实际会接入执行层)
        agent = self.factory.create_agent(config)
        
        # 在蜂群中注册新 Agent
        self.hub.allocator.register_agent(new_agent_id, required_caps)
        
        log.print_log(f"[Swarm] Agent {parent_id} 成功衍生了子 Agent: {new_agent_id}", "success")
        return new_agent_id
