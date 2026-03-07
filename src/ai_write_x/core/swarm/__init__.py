"""
蜂群系统 (Swarm System)
统一导出所有蜂群组件
"""
# 代理基类
from src.ai_write_x.core.swarm.swarm_agent import (
    AgentNode,
    ReasoningAgent,
    CreativeAgent,
    ResearchAgent,
    AgentStatus
)

# 信息素通信
from src.ai_write_x.core.swarm.pheromone_comm import (
    PheromoneType,
    Pheromone,
    PheromoneSpace,
    PheromoneComm,
    get_pheromone_comm
)

# 神经形态信息素 V2
from src.ai_write_x.core.swarm.neuro_pheromone_v2 import (
    NeurotransmitterType,
    SpikePattern,
    Synapse,
    Neuron,
    NeuralPheromone,
    NeuroPheromoneSpace,
    NeuroPheromoneComm,
    get_neuro_pheromone_comm
)

# 角色行为
from src.ai_write_x.core.swarm.role_behavior import (
    AgentRole,
    BehaviorState,
    RoleBehavior,
)

# 负载均衡
from src.ai_write_x.core.swarm.load_balancer import (
    LoadBalanceStrategy,
    LoadBalancer,
)

# 预测性负载均衡器 V2
from src.ai_write_x.core.swarm.predictive_balancer import (
    LoadMetric,
    TransformerPredictor,
    PPOScheduler,
    PredictiveLoadBalancer,
    get_predictive_balancer
)

# 蜂群意识层
from src.ai_write_x.core.swarm.swarm_consciousness import (
    MemoryNodeType,
    MemoryEdgeType,
    CollectiveMemoryGraph,
    EmergentIntelligence,
    BFTConsensus,
    SwarmConsciousness,
    get_swarm_consciousness
)

# 异步工作流
from src.ai_write_x.core.swarm.async_workflow import (
    TaskStatus,
    AsyncTask,
    TaskGraph,
    ParallelExecutor,
    AsyncSwarmWorkflow,
    create_workflow,
    get_workflow
)

__all__ = [
    # 代理
    "AgentNode",
    "ReasoningAgent",
    "CreativeAgent", 
    "ResearchAgent",
    "AgentStatus",
    
    # 信息素
    "PheromoneType",
    "Pheromone",
    "PheromoneSpace",
    "PheromoneComm",
    "get_pheromone_comm",
    
    # 神经形态信息素 V2
    "NeurotransmitterType",
    "SpikePattern",
    "Synapse",
    "Neuron",
    "NeuralPheromone",
    "NeuroPheromoneSpace",
    "NeuroPheromoneComm",
    "get_neuro_pheromone_comm",
    
    # 角色
    "AgentRole",
    "RoleBehavior",
    "get_role_behavior",
    
    # 负载均衡
    "LoadBalancingStrategy",
    "LoadBalancer",
    "get_load_balancer",
    
    # 预测性负载均衡
    "LoadMetric",
    "LoadPredictor",
    "PPOScheduler",
    "PredictiveLoadBalancer",
    "get_predictive_balancer",
    
    # 意识层
    "MemoryNodeType",
    "MemoryEdgeType",
    "CollectiveMemoryGraph",
    "EmergentIntelligence",
    "BFTConsensus",
    "SwarmConsciousness",
    "get_swarm_consciousness",
    
    # 异步工作流
    "TaskStatus",
    "AsyncTask",
    "TaskGraph",
    "ParallelExecutor",
    "AsyncSwarmWorkflow",
    "create_workflow",
    "get_workflow",
]
