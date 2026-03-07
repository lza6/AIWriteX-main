from enum import Enum
from typing import List, Dict, Any, Optional
from pydantic import BaseModel, Field
from datetime import datetime
import uuid

class SwarmMessageType(str, Enum):
    """蜂群消息类型"""
    TASK_BROADCAST = "task_broadcast"      # 广播新任务
    AGENT_BID = "agent_bid"                # Agent 竞价/投标
    BID_ACCEPTED = "bid_accepted"          # 竞价被接受/任务确认
    CAPABILITY_QUERY = "capability_query"  # 查询 Agent 能力
    CONSENSUS_SYNC = "consensus_sync"      # 共识记忆同步
    AGENT_HEARTBEAT = "agent_heartbeat"    # Agent 存活心跳
    DYNAMIC_SPAWN = "dynamic_spawn"        # 动态派生新 Agent
    TASK_EVOLUTION = "task_evolution"      # 任务自我演化演进

class SwarmCapabilities(str, Enum):
    """Agent 能力标签"""
    REASONING = "reasoning"                # 高级推理
    CREATIVE_WRITING = "creative_writing"  # 创意写作
    RESEARCH = "research"                  # 深度联网研究
    VERIFICATION = "verification"          # 事实核查与质量校验
    STRUCTURE_DESIGN = "structure_design"  # 结构设计
    SEO_OPTIMIZATION = "seo_optimization"  # SEO 优化
    IMAGE_DYNAMIC = "image_dynamic"        # 动态图像生成与审美

class AgentBid(BaseModel):
    """Agent 投标信息"""
    agent_id: str
    bid_value: float = Field(..., description="竞价分数(0.0-1.0)，基于匹配度和计算开销")
    capabilities: List[SwarmCapabilities]
    estimated_time: float = Field(..., description="预计完成时间(秒)")
    metadata: Dict[str, Any] = {}

class SwarmMessage(BaseModel):
    """蜂群统一消息包装"""
    message_id: str = Field(default_factory=lambda: str(uuid.uuid4()))
    timestamp: datetime = Field(default_factory=datetime.now)
    msg_type: SwarmMessageType
    sender_id: str
    target_id: Optional[str] = None         # None 表示广播
    content: Dict[str, Any]
    priority: int = 1                       # 1-5，5最高
    hops: int = 0                           # 传播跳数

class SwarmTask(BaseModel):
    """蜂群任务模型"""
    task_id: str = Field(default_factory=lambda: str(uuid.uuid1()))
    description: str
    required_capabilities: List[SwarmCapabilities]
    status: str = "pending"
    parent_task_id: Optional[str] = None
    sub_tasks: List[str] = []
    winner_agent_id: Optional[str] = None
    bids: List[AgentBid] = []
    creation_time: datetime = Field(default_factory=datetime.now)
    deadline: Optional[datetime] = None

class SwarmState(BaseModel):
    """蜂群全局/局部状态快照"""
    active_agents: Dict[str, List[SwarmCapabilities]]
    pending_tasks_count: int
    consensus_version: str
    topology_hash: str
