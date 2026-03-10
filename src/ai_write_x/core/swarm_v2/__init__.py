"""
AIWriteX V18.0 - Neural Collective Swarm System
自治智能体群体系统 - 集体意识网络

核心组件:
- CollectiveMind: 群体意识中枢，维护全局状态
- ConsensusProtocol: 分布式共识协议
- KnowledgeOrganism: 知识有机体管理系统
- SelfHealing: 自修复与故障恢复
"""

from .collective_mind import CollectiveMind, CollectiveState, SwarmIntention
from .consensus_protocol import ConsensusProtocol, ConsensusState, Proposal
from .knowledge_organism import KnowledgeOrganism, KnowledgeDNA
from .self_healing import SelfHealing, HealthStatus

__version__ = "18.0.0"
__all__ = [
    "CollectiveMind",
    "CollectiveState", 
    "SwarmIntention",
    "ConsensusProtocol",
    "ConsensusState",
    "Proposal",
    "KnowledgeOrganism",
    "KnowledgeDNA",
    "SelfHealing",
    "HealthStatus",
]
