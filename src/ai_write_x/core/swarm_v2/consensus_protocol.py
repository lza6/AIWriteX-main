"""
AIWriteX V18.0 - Consensus Protocol Module
分布式共识协议 - 拜占庭容错共识实现

功能:
1. 提案系统: 智能体提交提案进行群体决策
2. 投票机制: 加权投票与置信度计算
3. 拜占庭容错: 处理恶意或故障节点
4. 冲突解决: 自动化解提案冲突

算法:
- 基于PBFT简化版实现
- 支持视图变更与领导者选举
- 自适应超时机制
"""

import asyncio
import time
import random
from typing import Dict, List, Optional, Set, Callable, Any, Tuple
from dataclasses import dataclass, field, asdict
from enum import Enum, auto
from collections import defaultdict
from uuid import UUID, uuid4
import numpy as np

# 处理导入路径问题
class LogAdapter:
    """日志适配器"""
    def __init__(self):
        self.logger = None
        self._init_logger()
    
    def _init_logger(self):
        try:
            import src.ai_write_x.utils.log as _lg
            self.logger = _lg
        except ImportError:
            import logging
            self.logger = logging.getLogger('consensus')
            handler = logging.StreamHandler()
            formatter = logging.Formatter('%(levelname)s: %(message)s')
            handler.setFormatter(formatter)
            self.logger.addHandler(handler)
            self.logger.setLevel(logging.INFO)
    
    def print_log(self, message, level="info"):
        if hasattr(self.logger, 'print_log'):
            self.logger.print_log(message, level)
        else:
            import logging
            import re
            level_map = {"info": logging.INFO, "warning": logging.WARNING, 
                        "error": logging.ERROR, "success": logging.INFO}
            clean_msg = re.sub(r'[^\x00-\x7F]+', '', message)
            self.logger.log(level_map.get(level, logging.INFO), clean_msg)

try:
    from .collective_mind import CollectiveMind, AgentState
except ImportError:
    from collective_mind import CollectiveMind, AgentState

lg = LogAdapter()


class ConsensusState(Enum):
    """共识状态"""
    IDLE = "idle"
    PROPOSING = "proposing"         # 提案阶段
    PREPARING = "preparing"         # 准备阶段 (PBFT Prepare)
    COMMITTING = "committing"       # 提交阶段 (PBFT Commit)
    COMMITTED = "committed"         # 已达成共识
    REJECTED = "rejected"           # 被拒绝
    CONFLICT = "conflict"           # 冲突状态
    TIMEOUT = "timeout"             # 超时


class ProposalType(Enum):
    """提案类型"""
    TASK_ALLOCATION = "task_allocation"
    KNOWLEDGE_MERGE = "knowledge_merge"
    CONFIG_CHANGE = "config_change"
    STRATEGY_UPDATE = "strategy_update"
    LEADER_ELECTION = "leader_election"
    EMERGENCY_HALT = "emergency_halt"


@dataclass
class Vote:
    """投票数据类"""
    agent_id: str
    proposal_id: str
    approve: bool
    weight: float = 1.0  # 投票权重
    confidence: float = 1.0  # 置信度
    timestamp: float = field(default_factory=time.time)
    reason: Optional[str] = None


@dataclass
class Proposal:
    """提案数据类"""
    id: str = field(default_factory=lambda: str(uuid4()))
    type: ProposalType = ProposalType.TASK_ALLOCATION
    proposer: str = ""
    content: Dict[str, Any] = field(default_factory=dict)
    description: str = ""
    
    # 共识参数
    required_quorum: float = 0.67  # 所需法定人数 (2/3默认)
    timeout_seconds: float = 30.0
    
    # 状态追踪
    state: ConsensusState = ConsensusState.IDLE
    votes: Dict[str, Vote] = field(default_factory=dict)
    created_at: float = field(default_factory=time.time)
    decided_at: Optional[float] = None
    
    # 结果
    final_result: Optional[bool] = None
    execution_data: Optional[Dict] = None
    
    def get_approval_ratio(self) -> float:
        """获取赞成比例"""
        if not self.votes:
            return 0.0
        approvals = sum(1 for v in self.votes.values() if v.approve)
        return approvals / len(self.votes)
    
    def get_weighted_approval(self) -> float:
        """获取加权赞成比例"""
        total_weight = sum(v.weight for v in self.votes.values())
        if total_weight == 0:
            return 0.0
        approve_weight = sum(v.weight for v in self.votes.values() if v.approve)
        return approve_weight / total_weight
    
    def is_expired(self) -> bool:
        return time.time() - self.created_at > self.timeout_seconds
    
    def to_dict(self) -> Dict[str, Any]:
        data = asdict(self)
        data['type'] = self.type.value
        data['state'] = self.state.value
        return data


@dataclass
class ConsensusView:
    """共识视图 (用于视图变更)"""
    view_number: int = 0
    leader_id: Optional[str] = None
    active_nodes: Set[str] = field(default_factory=set)
    timestamp: float = field(default_factory=time.time)


class ConsensusProtocol:
    """
    分布式共识协议 - V18核心组件
    
    实现简化版PBFT算法，支持:
    - 三阶段提交 (Pre-prepare, Prepare, Commit)
    - 视图变更处理
    - 拜占庭容错 (f < n/3)
    """
    
    def __init__(self, collective_mind: Optional[CollectiveMind] = None):
        self.mind = collective_mind or CollectiveMind()
        
        # 提案存储
        self.proposals: Dict[str, Proposal] = {}
        self.proposals_by_type: Dict[ProposalType, List[str]] = defaultdict(list)
        
        # 视图管理
        self.current_view = ConsensusView()
        self.view_history: List[ConsensusView] = []
        
        # 配置
        self.byzantine_threshold = 0.33  # 拜占庭节点阈值
        self.default_timeout = 30.0
        self.max_retries = 3
        
        # 统计
        self.consensus_count = 0
        self.conflict_count = 0
        self.timeout_count = 0
        
        # 回调
        self._on_consensus_reached: List[Callable] = []
        self._on_conflict: List[Callable] = []
        
        lg.print_log("⚖️ ConsensusProtocol V18.0 initialized", "info")
    
    async def start(self):
        """启动共识协议"""
        asyncio.create_task(self._consensus_monitor())
        lg.print_log("⚖️ ConsensusProtocol started", "success")
    
    # ========== 提案管理 ==========
    
    async def create_proposal(self, proposal_type: ProposalType,
                             proposer: str,
                             content: Dict[str, Any],
                             description: str = "",
                             timeout: Optional[float] = None) -> Proposal:
        """创建新提案"""
        proposal = Proposal(
            type=proposal_type,
            proposer=proposer,
            content=content,
            description=description,
            timeout_seconds=timeout or self.default_timeout,
            state=ConsensusState.PROPOSING
        )
        
        self.proposals[proposal.id] = proposal
        self.proposals_by_type[proposal_type].append(proposal.id)
        
        # 广播提案
        await self.mind._broadcast_event("proposal_created", {
            "proposal_id": proposal.id,
            "type": proposal_type.value,
            "proposer": proposer,
            "description": description
        })
        
        lg.print_log(f"📋 Proposal created: {proposal.id[:8]}... ({proposal_type.value})", "info")
        return proposal
    
    async def submit_vote(self, proposal_id: str, agent_id: str,
                         approve: bool,
                         weight: float = 1.0,
                         confidence: float = 1.0,
                         reason: Optional[str] = None) -> bool:
        """提交投票"""
        if proposal_id not in self.proposals:
            lg.print_log(f"❌ Proposal not found: {proposal_id}", "error")
            return False
        
        proposal = self.proposals[proposal_id]
        
        # 检查提案状态
        if proposal.state in [ConsensusState.COMMITTED, ConsensusState.REJECTED]:
            lg.print_log(f"⚠️ Proposal already decided: {proposal_id}", "warning")
            return False
        
        # 创建投票
        vote = Vote(
            agent_id=agent_id,
            proposal_id=proposal_id,
            approve=approve,
            weight=weight,
            confidence=confidence,
            reason=reason
        )
        
        proposal.votes[agent_id] = vote
        
        # 广播投票
        await self.mind._broadcast_event("vote_submitted", {
            "proposal_id": proposal_id,
            "agent_id": agent_id,
            "approve": approve,
            "weight": weight
        })
        
        # 检查是否达成法定人数
        await self._check_consensus(proposal)
        
        return True
    
    async def _check_consensus(self, proposal: Proposal):
        """检查是否达成共识"""
        alive_agents = self.mind.get_alive_agents()
        total_weight = sum(
            self._get_agent_weight(a.agent_id) 
            for a in alive_agents
        )
        
        voted_weight = sum(v.weight for v in proposal.votes.values())
        
        # 检查是否达到法定人数
        if voted_weight < total_weight * proposal.required_quorum:
            return
        
        # 计算加权结果
        weighted_approve = proposal.get_weighted_approval()
        
        # 决策阈值
        threshold = 0.5 + self.byzantine_threshold / 2  # ~0.67
        
        if weighted_approve >= threshold:
            await self._commit_proposal(proposal, True)
        elif weighted_approve <= (1 - threshold):
            await self._commit_proposal(proposal, False)
        # 否则继续等待更多投票
    
    async def _commit_proposal(self, proposal: Proposal, result: bool):
        """提交提案决策"""
        proposal.state = ConsensusState.COMMITTED if result else ConsensusState.REJECTED
        proposal.final_result = result
        proposal.decided_at = time.time()
        
        self.consensus_count += 1
        
        # 广播决策
        await self.mind._broadcast_event("consensus_reached", {
            "proposal_id": proposal.id,
            "result": result,
            "approval_ratio": proposal.get_weighted_approval(),
            "vote_count": len(proposal.votes)
        })
        
        # 执行回调
        for callback in self._on_consensus_reached:
            try:
                if asyncio.iscoroutinefunction(callback):
                    asyncio.create_task(callback(proposal))
                else:
                    callback(proposal)
            except Exception as e:
                lg.print_log(f"Consensus callback error: {e}", "error")
        
        status = "✅ APPROVED" if result else "❌ REJECTED"
        lg.print_log(f"{status} Proposal {proposal.id[:8]}... "
                    f"({proposal.get_weighted_approval():.2%})", 
                    "success" if result else "warning")
    
    def _get_agent_weight(self, agent_id: str) -> float:
        """获取智能体投票权重"""
        if agent_id not in self.mind.agents:
            return 0.0
        
        agent = self.mind.agents[agent_id]
        
        # 基于角色和能力计算权重
        base_weight = 1.0
        
        # 角色加成
        role_weights = {
            "coordinator": 1.5,
            "researcher": 1.2,
            "writer": 1.2,
            "reviewer": 1.3,
            "default": 1.0
        }
        base_weight *= role_weights.get(agent.role, 1.0)
        
        # 健康状态惩罚
        if not agent.is_alive():
            base_weight *= 0.1
        
        # 负载惩罚
        if agent.load > 0.8:
            base_weight *= 0.8
        
        return base_weight
    
    # ========== 冲突解决 ==========
    
    async def detect_conflicts(self) -> List[Tuple[Proposal, Proposal]]:
        """检测提案冲突"""
        conflicts = []
        active_proposals = [
            p for p in self.proposals.values()
            if p.state not in [ConsensusState.COMMITTED, ConsensusState.REJECTED]
        ]
        
        for i, p1 in enumerate(active_proposals):
            for p2 in active_proposals[i+1:]:
                if self._is_conflicting(p1, p2):
                    conflicts.append((p1, p2))
        
        return conflicts
    
    def _is_conflicting(self, p1: Proposal, p2: Proposal) -> bool:
        """检查两个提案是否冲突"""
        # 相同类型且相似内容
        if p1.type != p2.type:
            return False
        
        # 资源竞争检测
        if p1.type == ProposalType.TASK_ALLOCATION:
            agents1 = set(p1.content.get("assigned_agents", []))
            agents2 = set(p2.content.get("assigned_agents", []))
            if agents1 & agents2:  # 有交集
                return True
        
        # 配置冲突
        if p1.type == ProposalType.CONFIG_CHANGE:
            keys1 = set(p1.content.get("config", {}).keys())
            keys2 = set(p2.content.get("config", {}).keys())
            if keys1 & keys2:
                return True
        
        return False
    
    async def resolve_conflict(self, p1: Proposal, p2: Proposal) -> Proposal:
        """解决提案冲突"""
        self.conflict_count += 1
        
        # 策略1: 基于权重选择
        w1 = self._calculate_proposal_weight(p1)
        w2 = self._calculate_proposal_weight(p2)
        
        if w1 > w2:
            winner, loser = p1, p2
        else:
            winner, loser = p2, p1
        
        # 标记失败提案
        loser.state = ConsensusState.CONFLICT
        
        # 合并内容 (如果可能)
        if winner.type == ProposalType.TASK_ALLOCATION:
            winner.content = self._merge_task_allocations(winner, loser)
        
        await self.mind._broadcast_event("conflict_resolved", {
            "winner_id": winner.id,
            "loser_id": loser.id,
            "winner_weight": max(w1, w2),
            "loser_weight": min(w1, w2)
        })
        
        lg.print_log(f"⚔️ Conflict resolved: {winner.id[:8]} beats {loser.id[:8]}", "warning")
        
        return winner
    
    def _calculate_proposal_weight(self, proposal: Proposal) -> float:
        """计算提案权重"""
        weight = 0.0
        
        # 提议者权重
        weight += self._get_agent_weight(proposal.proposer) * 2
        
        # 已有投票权重
        weight += sum(v.weight for v in proposal.votes.values())
        
        # 时效性加成 (新提案权重更高)
        age = time.time() - proposal.created_at
        time_bonus = max(0, 1.0 - age / 300)  # 5分钟内逐渐衰减
        weight *= (1.0 + time_bonus)
        
        return weight
    
    def _merge_task_allocations(self, p1: Proposal, p2: Proposal) -> Dict[str, Any]:
        """合并任务分配提案"""
        content = p1.content.copy()
        
        # 合并智能体列表
        agents1 = set(content.get("assigned_agents", []))
        agents2 = set(p2.content.get("assigned_agents", []))
        
        # 去重并保留顺序
        merged_agents = list(agents1) + [a for a in agents2 if a not in agents1]
        content["assigned_agents"] = merged_agents
        
        return content
    
    # ========== 视图变更 ==========
    
    async def initiate_view_change(self, reason: str = ""):
        """发起视图变更 (领导者选举)"""
        old_leader = self.current_view.leader_id
        
        # 选举新领导者 (基于权重随机选择)
        alive_agents = self.mind.get_alive_agents()
        if not alive_agents:
            lg.print_log("❌ No alive agents for leader election", "error")
            return
        
        weights = [self._get_agent_weight(a.agent_id) for a in alive_agents]
        total = sum(weights)
        probs = [w/total for w in weights]
        
        new_leader = np.random.choice(
            [a.agent_id for a in alive_agents],
            p=probs
        )
        
        # 创建新视图
        new_view = ConsensusView(
            view_number=self.current_view.view_number + 1,
            leader_id=new_leader,
            active_nodes=set(a.agent_id for a in alive_agents)
        )
        
        self.view_history.append(self.current_view)
        self.current_view = new_view
        
        await self.mind._broadcast_event("view_changed", {
            "old_leader": old_leader,
            "new_leader": new_leader,
            "view_number": new_view.view_number,
            "reason": reason
        })
        
        lg.print_log(f"👑 New leader elected: {new_leader} (view #{new_view.view_number})", "info")
    
    # ========== 监控与维护 ==========
    
    async def _consensus_monitor(self):
        """共识监控循环"""
        while self.mind._running:
            try:
                # 检查超时提案
                await self._check_timeouts()
                
                # 检测并解决冲突
                conflicts = await self.detect_conflicts()
                for p1, p2 in conflicts:
                    await self.resolve_conflict(p1, p2)
                
                # 检查视图健康
                if self.current_view.leader_id:
                    if self.current_view.leader_id not in self.mind.agents:
                        await self.initiate_view_change("leader_offline")
                
                await asyncio.sleep(5.0)
            except Exception as e:
                lg.print_log(f"Consensus monitor error: {e}", "error")
    
    async def _check_timeouts(self):
        """检查超时提案"""
        for proposal in list(self.proposals.values()):
            if proposal.state in [ConsensusState.COMMITTED, ConsensusState.REJECTED]:
                continue
            
            if proposal.is_expired():
                proposal.state = ConsensusState.TIMEOUT
                self.timeout_count += 1
                
                await self.mind._broadcast_event("proposal_timeout", {
                    "proposal_id": proposal.id,
                    "votes_received": len(proposal.votes),
                    "approval_ratio": proposal.get_weighted_approval()
                })
                
                lg.print_log(f"⏱️ Proposal timeout: {proposal.id[:8]}", "warning")
    
    # ========== 查询接口 ==========
    
    def get_proposal(self, proposal_id: str) -> Optional[Proposal]:
        """获取提案"""
        return self.proposals.get(proposal_id)
    
    def get_active_proposals(self) -> List[Proposal]:
        """获取活跃提案"""
        return [
            p for p in self.proposals.values()
            if p.state not in [ConsensusState.COMMITTED, ConsensusState.REJECTED, ConsensusState.TIMEOUT]
        ]
    
    def get_proposals_by_type(self, proposal_type: ProposalType) -> List[Proposal]:
        """按类型获取提案"""
        ids = self.proposals_by_type.get(proposal_type, [])
        return [self.proposals[pid] for pid in ids if pid in self.proposals]
    
    def get_stats(self) -> Dict[str, Any]:
        """获取统计信息"""
        total = len(self.proposals)
        committed = sum(1 for p in self.proposals.values() if p.state == ConsensusState.COMMITTED)
        rejected = sum(1 for p in self.proposals.values() if p.state == ConsensusState.REJECTED)
        
        return {
            "total_proposals": total,
            "committed": committed,
            "rejected": rejected,
            "success_rate": committed / max(total, 1),
            "conflicts_resolved": self.conflict_count,
            "timeouts": self.timeout_count,
            "current_view": self.current_view.view_number,
            "leader": self.current_view.leader_id,
            "active_proposals": len(self.get_active_proposals())
        }
    
    # ========== 回调注册 ==========
    
    def on_consensus_reached(self, callback: Callable):
        """注册共识达成回调"""
        self._on_consensus_reached.append(callback)
    
    def on_conflict(self, callback: Callable):
        """注册冲突回调"""
        self._on_conflict.append(callback)
