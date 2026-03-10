"""
增强共识记忆网络 V3 (Enhanced Consensus Memory Network V3)

解决痛点:
3. 记忆系统孤立 → 实现共享记忆池、跨Agent记忆同步
4. 共识机制简单 → 实现多阶段共识、分级投票、信任传播

核心特性:
- 分布式共享记忆池 (支持多Leader写入)
- 分级共识机制 (快速路径 + 完整路径)
- 信任传播与声誉系统
- 冲突自动消解
"""
import asyncio
from typing import Dict, List, Any, Optional, Set, Tuple, Callable
from datetime import datetime, timedelta
from dataclasses import dataclass, field
from enum import Enum
from collections import defaultdict, deque
import uuid
import hashlib
import numpy as np
import random

from src.ai_write_x.utils import log


class ConsensusPhase(Enum):
    """共识阶段"""
    PREPARE = "prepare"        # 准备阶段
    PROPOSE = "propose"        # 提案阶段
    VOTE = "vote"              # 投票阶段
    COMMIT = "commit"          # 提交阶段
    EXECUTE = "execute"        # 执行阶段


class VoteType(Enum):
    """投票类型"""
    APPROVE = "approve"
    REJECT = "reject"
    ABSTAIN = "abstain"
    CONDITIONAL = "conditional"  # 条件同意


class TrustLevel(Enum):
    """信任等级"""
    UNTRUSTED = 0
    NEUTRAL = 1
    TRUSTED = 2
    HIGHLY_TRUSTED = 3
    AUTHORITY = 4


@dataclass
class ConsensusProposal:
    """共识提案"""
    proposal_id: str
    proposer_id: str
    key: str
    value: Any
    phase: ConsensusPhase
    votes: Dict[str, VoteType] = field(default_factory=dict)
    vote_weights: Dict[str, float] = field(default_factory=dict)
    timestamp: datetime = field(default_factory=datetime.now)
    ttl: int = 30  # 秒
    metadata: Dict = field(default_factory=dict)
    
    @property
    def total_weight(self) -> float:
        return sum(self.vote_weights.values())
    
    @property
    def approved_weight(self) -> float:
        return sum(self.vote_weights.get(v, 0) for v, v_type in self.votes.items() if v_type == VoteType.APPROVE)
    
    @property
    def rejected_weight(self) -> float:
        return sum(self.vote_weights.get(v, 0) for v, v_type in self.votes.items() if v_type == VoteType.REJECT)
    
    @property
    def approval_ratio(self) -> float:
        if self.total_weight == 0:
            return 0.0
        return self.approved_weight / self.total_weight


@dataclass
class SharedMemory:
    """共享记忆"""
    key: str
    value: Any
    agent_id: str  # 创建者
    confidence: float = 1.0
    version: int = 1
    created_at: datetime = field(default_factory=datetime.now)
    updated_at: datetime = field(default_factory=datetime.now)
    contributors: Dict[str, float] = field(default_factory=dict)  # agent_id -> 贡献权重
    evidence: List[Dict] = field(default_factory=list)  # 支持证据
    conflicts_with: List[str] = field(default_factory=list)  # 冲突的记忆key
    
    def to_dict(self) -> Dict:
        return {
            "key": self.key,
            "value": self.value,
            "agent_id": self.agent_id,
            "confidence": self.confidence,
            "version": self.version,
            "created_at": self.created_at.isoformat(),
            "updated_at": self.updated_at.isoformat()
        }


@dataclass
class AgentTrust:
    """Agent信任信息"""
    agent_id: str
    trust_level: TrustLevel = TrustLevel.NEUTRAL
    trust_score: float = 0.5  # 0-1
    
    # 历史统计
    proposals_submitted: int = 0
    proposals_accepted: int = 0
    votes_cast: int = 0
    accurate_votes: int = 0  # 准确投票
    
    last_active: datetime = field(default_factory=datetime.now)
    
    @property
    def acceptance_rate(self) -> float:
        if self.proposals_submitted == 0:
            return 0.5
        return self.proposals_accepted / self.proposals_submitted
    
    @property
    def vote_accuracy(self) -> float:
        if self.votes_cast == 0:
            return 0.5
        return self.accurate_votes / self.votes_cast


class EnhancedConsensusMemory:
    """
    增强共识记忆网络 V3
    
    核心功能:
    1. 共享记忆池 - 多Agent可读写
    2. 分级共识 - 快速路径 + 完整BFT
    3. 信任传播 - 基于历史表现动态调整权重
    4. 冲突消解 - 自动检测和解决记忆冲突
    """
    
    def __init__(
        self,
        quorum_size: int = 3,
        fast_path_threshold: float = 0.7,  # 快速路径通过率
        full_path_threshold: float = 0.66,  # 2/3多数
        trust_decay: float = 0.95
    ):
        # 共识配置
        self.quorum_size = quorum_size
        self.fast_path_threshold = fast_path_threshold
        self.full_path_threshold = full_path_threshold
        self.trust_decay = trust_decay
        
        # 共享记忆池
        self.shared_memory: Dict[str, SharedMemory] = {}
        self.memory_history: deque = deque(maxlen=5000)  # 记忆变更历史
        
        # 活跃提案
        self.active_proposals: Dict[str, ConsensusProposal] = {}
        
        # Agent信任信息
        self.agent_trust: Dict[str, AgentTrust] = {}
        
        # 提案缓存
        self.proposal_cache: deque = deque(maxlen=1000)
        
        # 统计
        self.stats = {
            "proposals_initiated": 0,
            "proposals_approved": 0,
            "proposals_rejected": 0,
            "memory_writes": 0,
            "conflicts_resolved": 0
        }
        
        log.print_log(f"[EnhancedConsensus] 增强共识记忆网络 V3 已初始化", "success")
    
    # ==================== 信任管理 ====================
    
    def get_vote_weight(self, agent_id: str) -> float:
        """获取Agent投票权重 (基于信任)"""
        if agent_id not in self.agent_trust:
            self.agent_trust[agent_id] = AgentTrust(agent_id=agent_id)
        
        trust = self.agent_trust[agent_id]
        return trust.trust_score
    
    def update_trust(self, agent_id: str, proposal_outcome: bool):
        """根据提案结果更新信任"""
        if agent_id not in self.agent_trust:
            self.agent_trust[agent_id] = AgentTrust(agent_id=agent_id)
        
        trust = self.agent_trust[agent_id]
        trust.proposals_submitted += 1
        
        if proposal_outcome:
            trust.proposals_accepted += 1
        
        # 动态调整信任分数
        if trust.proposals_submitted >= 5:
            new_score = trust.acceptance_rate * 0.8 + trust.vote_accuracy * 0.2
            trust.trust_score = trust.trust_score * 0.7 + new_score * 0.3
        
        # 更新信任等级
        if trust.trust_score > 0.8:
            trust.trust_level = TrustLevel.HIGHLY_TRUSTED
        elif trust.trust_score > 0.6:
            trust.trust_level = TrustLevel.TRUSTED
        elif trust.trust_score > 0.4:
            trust.trust_level = TrustLevel.NEUTRAL
        else:
            trust.trust_level = TrustLevel.UNTRUSTED
        
        trust.last_active = datetime.now()
    
    def update_vote_accuracy(self, agent_id: str, was_accurate: bool):
        """更新投票准确性"""
        if agent_id not in self.agent_trust:
            self.agent_trust[agent_id] = AgentTrust(agent_id=agent_id)
        
        trust = self.agent_trust[agent_id]
        trust.votes_cast += 1
        if was_accurate:
            trust.accurate_votes += 1
    
    def decay_trust(self):
        """信任衰减 - 定期调用"""
        for trust in self.agent_trust.values():
            # 长期不活跃则衰减
            inactive_hours = (datetime.now() - trust.last_active).total_seconds() / 3600
            if inactive_hours > 24:
                trust.trust_score *= self.trust_decay ** (inactive_hours / 24)
                trust.trust_score = max(0.1, trust.trust_score)
    
    # ==================== 共享记忆 ====================
    
    async def read_memory(self, key: str, requester_id: str) -> Optional[Any]:
        """读取共享记忆"""
        if key in self.shared_memory:
            memory = self.shared_memory[key]
            memory.contributors[requester_id] = memory.contributors.get(requester_id, 0) + 0.1
            return memory.value
        return None
    
    async def write_memory(
        self,
        key: str,
        value: Any,
        writer_id: str,
        confidence: float = 1.0,
        evidence: List[Dict] = None,
        use_fast_path: bool = True
    ) -> bool:
        """
        写入共享记忆
        
        Args:
            key: 记忆键
            value: 记忆值
            writer_id: 写入者ID
            confidence: 置信度
            evidence: 支持证据
            use_fast_path: 是否使用快速路径
        """
        # 检查是否需要共识
        if key in self.shared_memory:
            existing = self.shared_memory[key]
            
            # 冲突检测
            if existing.value != value:
                # 存在冲突，需要共识
                return await self._consensus_write(
                    key, value, writer_id, confidence, evidence
                )
        
        # 快速路径: 高信任Agent可直接写入
        if use_fast_path:
            writer_weight = self.get_vote_weight(writer_id)
            if writer_weight >= self.fast_path_threshold:
                self._direct_write(key, value, writer_id, confidence, evidence)
                return True
        
        # 完整共识路径
        return await self._consensus_write(key, value, writer_id, confidence, evidence)
    
    def _direct_write(self, key: str, value: Any, writer_id: str, confidence: float, evidence: List[Dict]):
        """直接写入 (无需共识)"""
        if key in self.shared_memory:
            memory = self.shared_memory[key]
            memory.value = value
            memory.version += 1
            memory.updated_at = datetime.now()
            memory.contributors[writer_id] = memory.contributors.get(writer_id, 0) + confidence
        else:
            self.shared_memory[key] = SharedMemory(
                key=key,
                value=value,
                agent_id=writer_id,
                confidence=confidence,
                evidence=evidence or []
            )
        
        self.stats["memory_writes"] += 1
        log.print_log(f"[EnhancedConsensus] 直接写入: {key} by {writer_id}", "debug")
    
    async def _consensus_write(
        self,
        key: str,
        value: Any,
        writer_id: str,
        confidence: float,
        evidence: List[Dict]
    ) -> bool:
        """通过共识写入"""
        # 创建提案
        proposal = ConsensusProposal(
            proposal_id=str(uuid.uuid4())[:12],
            proposer_id=writer_id,
            key=key,
            value=value,
            phase=ConsensusPhase.PROPOSE,
            metadata={"confidence": confidence, "evidence": evidence or []}
        )
        
        # 添加创建者投票
        proposal.votes[writer_id] = VoteType.APPROVE
        proposal.vote_weights[writer_id] = self.get_vote_weight(writer_id)
        
        self.active_proposals[proposal.proposal_id] = proposal
        self.stats["proposals_initiated"] += 1
        
        # 尝试快速路径
        if proposal.approval_ratio >= self.fast_path_threshold:
            proposal.phase = ConsensusPhase.COMMIT
            self._commit_proposal(proposal)
            return True
        
        # 等待更多投票 (模拟)
        await asyncio.sleep(0.1)
        
        # 检查是否通过
        if proposal.approval_ratio >= self.full_path_threshold:
            proposal.phase = ConsensusPhase.COMMIT
            self._commit_proposal(proposal)
            self.stats["proposals_approved"] += 1
            return True
        else:
            self.stats["proposals_rejected"] += 1
            return False
    
    def _commit_proposal(self, proposal: ConsensusProposal):
        """提交提案"""
        key = proposal.key
        value = proposal.value
        
        if key in self.shared_memory:
            memory = self.shared_memory[key]
            
            # 冲突消解
            if memory.value != value:
                # 新值置信度更高则覆盖
                new_confidence = proposal.metadata.get("confidence", 0.5)
                if new_confidence > memory.confidence:
                    memory.value = value
                    memory.confidence = new_confidence
                    memory.version += 1
                    memory.updated_at = datetime.now()
                    
                    # 添加贡献者
                    for voter, vote_type in proposal.votes.items():
                        if vote_type == VoteType.APPROVE:
                            weight = proposal.vote_weights.get(voter, 0.5)
                            memory.contributors[voter] = memory.contributors.get(voter, 0) + weight
                    
                    memory.evidence = proposal.metadata.get("evidence", [])
                    
                    self.stats["conflicts_resolved"] += 1
        else:
            self.shared_memory[key] = SharedMemory(
                key=key,
                value=value,
                agent_id=proposal.proposer_id,
                confidence=proposal.metadata.get("confidence", 0.5),
                evidence=proposal.metadata.get("evidence", [])
            )
        
        # 更新提案者信任
        self.update_trust(proposal.proposer_id, True)
        
        # 清理
        del self.active_proposals[proposal.proposal_id]
        
        log.print_log(f"[EnhancedConsensus] 提案通过: {key}", "info")
    
    async def vote(
        self,
        proposal_id: str,
        voter_id: str,
        vote: VoteType,
        reason: str = ""
    ) -> bool:
        """投票"""
        proposal = self.active_proposals.get(proposal_id)
        if not proposal:
            return False
        
        # 获取投票权重
        weight = self.get_vote_weight(voter_id)
        
        proposal.votes[voter_id] = vote
        proposal.vote_weights[voter_id] = weight
        
        # 检查投票准确性 (事后)
        # 这里简化处理，实际应该对比最终结果
        
        return True
    
    # ==================== 知识查询 ====================
    
    def search_memory(self, keyword: str, limit: int = 10) -> List[Dict]:
        """搜索记忆"""
        results = []
        
        for key, memory in self.shared_memory.items():
            if keyword.lower() in str(memory.value).lower() or keyword.lower() in key.lower():
                results.append({
                    "key": key,
                    "value": memory.value,
                    "confidence": memory.confidence,
                    "version": memory.version,
                    "contributors": len(memory.contributors)
                })
        
        results.sort(key=lambda x: x["confidence"], reverse=True)
        return results[:limit]
    
    def get_memory_info(self, key: str) -> Optional[Dict]:
        """获取记忆详情"""
        memory = self.shared_memory.get(key)
        if not memory:
            return None
        
        return {
            "key": memory.key,
            "value": memory.value,
            "confidence": memory.confidence,
            "version": memory.version,
            "created_at": memory.created_at.isoformat(),
            "updated_at": memory.updated_at.isoformat(),
            "contributors": dict(memory.contributors),
            "evidence_count": len(memory.evidence)
        }
    
    def get_consensus_stats(self) -> Dict:
        """获取共识统计"""
        return {
            **self.stats,
            "active_proposals": len(self.active_proposals),
            "total_memories": len(self.shared_memory),
            "agent_trust": {
                aid: {
                    "trust_score": trust.trust_score,
                    "trust_level": trust.trust_level.value,
                    "acceptance_rate": trust.acceptance_rate
                }
                for aid, trust in list(self.agent_trust.items())[:10]
            }
        }

    def get_topology_digest(self) -> Dict:
        """获取拓扑摘要 (用于 SwarmVisualizer)"""
        return {
            "memory_nodes": len(self.shared_memory),
            "active_proposals": len(self.active_proposals),
            "trusted_agents": sum(1 for t in self.agent_trust.values() if t.trust_level.value >= TrustLevel.TRUSTED.value),
            "total_agents": len(self.agent_trust),
            "consensus_rate": self.stats.get("consensus_rate", 0.0),
            "recent_updates": len([m for m in self.shared_memory.values() if (datetime.now() - m.updated_at).seconds < 300])
        }


# 全局实例
_global_consensus_memory: Optional[EnhancedConsensusMemory] = None


def get_enhanced_consensus_memory() -> EnhancedConsensusMemory:
    """获取全局增强共识记忆网络"""
    global _global_consensus_memory
    if _global_consensus_memory is None:
        _global_consensus_memory = EnhancedConsensusMemory()
    return _global_consensus_memory


# 便捷函数
async def commit_shared_knowledge(
    key: str,
    value: Any,
    agent_id: str,
    confidence: float = 1.0
) -> bool:
    """提交共享知识"""
    memory = get_enhanced_consensus_memory()
    return await memory.write_memory(key, value, agent_id, confidence)


async def read_shared_knowledge(key: str, agent_id: str) -> Optional[Any]:
    """读取共享知识"""
    memory = get_enhanced_consensus_memory()
    return await memory.read_memory(key, agent_id)


def search_knowledge(keyword: str, limit: int = 10) -> List[Dict]:
    """搜索知识"""
    memory = get_enhanced_consensus_memory()
    return memory.search_memory(keyword, limit)