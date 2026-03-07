"""
蜂群意识层 (Swarm Consciousness Layer)
实现蜂群 Agent 集体的意识、记忆与决策能力

核心组件:
1. 集体记忆图谱 (Collective Memory Graph) - 基于图的分布式知识存储
2. 涌现智能引擎 (Emergent Intelligence Engine) - 从交互中涌现智能
3. 共识机制 (Consensus Mechanism) - BFT共识实现
"""
import asyncio
from enum import Enum
from typing import Dict, List, Any, Optional, Set, Tuple
from datetime import datetime, timedelta
from collections import defaultdict
import uuid
import json
import hashlib
import math
import random

from src.ai_write_x.utils import log


class MemoryNodeType(str, Enum):
    """记忆节点类型"""
    ENTITY = "entity"           # 实体
    CONCEPT = "concept"        # 概念
    EVENT = "event"            # 事件
    RELATION = "relation"      # 关系
    AGENT = "agent"            # Agent
    TASK = "task"              # 任务


class MemoryEdgeType(str, Enum):
    """记忆边类型"""
    CAUSAL = "causal"          # 因果关系
    ASSOCIATIVE = "associative" # 关联关系
    TEMPORAL = "temporal"      # 时序关系
    SIMILAR = "similar"         # 相似关系
    CONTRADICTS = "contradicts" # 矛盾关系


class MemoryNode:
    """记忆节点"""
    
    def __init__(
        self,
        node_id: str = None,
        node_type: MemoryNodeType = MemoryNodeType.CONCEPT,
        content: Any = None,
        embedding: List[float] = None,
        importance: float = 0.5,
        decay_rate: float = 0.01
    ):
        self.id = node_id or str(uuid.uuid4())[:12]
        self.node_type = node_type
        self.content = content
        self.embedding = embedding or []
        self.importance = importance
        self.decay_rate = decay_rate
        
        # 元数据
        self.created_at = datetime.now()
        self.last_accessed = datetime.now()
        self.access_count = 0
        
        # 活跃度 (用于衰减)
        self.activation = 1.0
        
        # 来源追踪
        self.source_agents: Set[str] = set()
    
    def access(self):
        """访问节点 - 增强激活"""
        self.last_accessed = datetime.now()
        self.access_count += 1
        self.activation = min(1.0, self.activation + 0.1)
    
    def decay(self):
        """时间衰减"""
        elapsed = (datetime.now() - self.last_accessed).total_seconds()
        self.activation = max(0.0, self.activation - self.decay_rate * elapsed / 3600)
    
    def to_dict(self) -> Dict:
        return {
            "id": self.id,
            "type": self.node_type.value,
            "content": self.content,
            "importance": self.importance,
            "activation": self.activation,
            "access_count": self.access_count,
            "created_at": self.created_at.isoformat()
        }


class MemoryEdge:
    """记忆边"""
    
    def __init__(
        self,
        source_id: str,
        target_id: str,
        edge_type: MemoryEdgeType = MemoryEdgeType.ASSOCIATIVE,
        weight: float = 0.5,
        confidence: float = 0.8
    ):
        self.id = f"{source_id}->{edge_type.value}->{target_id}"
        self.source_id = source_id
        self.target_id = target_id
        self.edge_type = edge_type
        self.weight = weight
        self.confidence = confidence
        self.created_at = datetime.now()
        self.strength = 1.0
    
    def strengthen(self, amount: float = 0.1):
        """强化边"""
        self.strength = min(1.0, self.strength + amount)
        self.weight = min(1.0, self.weight + amount * 0.1)
    
    def weaken(self, amount: float = 0.05):
        """弱化边"""
        self.strength = max(0.0, self.strength - amount)
        self.weight = max(0.0, self.weight - amount * 0.05)


class CollectiveMemoryGraph:
    """
    集体记忆图谱
    
    基于图的分布式知识存储:
    - 节点表示概念/实体/事件
    - 边表示关系
    - 支持语义检索
    - 自动衰减与强化
    """
    
    def __init__(
        self,
        max_nodes: int = 10000,
        embedding_dim: int = 384,
        decay_interval: float = 3600.0  # 1小时
    ):
        self.max_nodes = max_nodes
        self.embedding_dim = embedding_dim
        
        # 图结构
        self.nodes: Dict[str, MemoryNode] = {}
        self.edges: Dict[str, MemoryEdge] = {}
        
        # 索引
        self.type_index: Dict[MemoryNodeType, Set[str]] = defaultdict(set)
        self.agent_nodes: Dict[str, Set[str]] = defaultdict(set)  # agent_id -> node_ids
        
        # 统计
        self.total_accesses = 0
        self.last_decay = datetime.now()
        self.decay_interval = timedelta(seconds=decay_interval)
        
        self._lock = asyncio.Lock()
    
    async def add_node(
        self,
        node_type: MemoryNodeType,
        content: Any,
        agent_id: str = None,
        embedding: List[float] = None,
        importance: float = 0.5
    ) -> str:
        """添加记忆节点"""
        async with self._lock:
            # 检查容量
            if len(self.nodes) >= self.max_nodes:
                await self._evict_low_activation()
            
            node = MemoryNode(
                node_type=node_type,
                content=content,
                embedding=embedding,
                importance=importance
            )
            
            if agent_id:
                node.source_agents.add(agent_id)
                self.agent_nodes[agent_id].add(node.id)
            
            self.nodes[node.id] = node
            self.type_index[node_type].add(node.id)
            
            log.print_log(
                f"[记忆图] 添加节点 {node_type.value}: {str(content)[:30]}...",
                "debug"
            )
            
            return node.id
    
    async def add_edge(
        self,
        source_id: str,
        target_id: str,
        edge_type: MemoryEdgeType = MemoryEdgeType.ASSOCIATIVE,
        weight: float = 0.5,
        confidence: float = 0.8
    ) -> Optional[str]:
        """添加记忆边"""
        async with self._lock:
            if source_id not in self.nodes or target_id not in self.nodes:
                return None
            
            edge = MemoryEdge(source_id, target_id, edge_type, weight, confidence)
            self.edges[edge.id] = edge
            
            # 强化相关节点
            self.nodes[source_id].access()
            self.nodes[target_id].access()
            
            return edge.id
    
    async def connect_by_similarity(
        self,
        node_id: str,
        top_k: int = 3,
        similarity_threshold: float = 0.7
    ) -> List[str]:
        """通过相似度连接节点"""
        async with self._lock:
            if node_id not in self.nodes:
                return []
            
            source_node = self.nodes[node_id]
            if not source_node.embedding:
                return []
            
            # 计算相似度
            similarities = []
            for nid, node in self.nodes.items():
                if nid == node_id or not node.embedding:
                    continue
                
                sim = self._cosine_similarity(source_node.embedding, node.embedding)
                if sim >= similarity_threshold:
                    similarities.append((nid, sim))
            
            # 取top-k
            similarities.sort(key=lambda x: x[1], reverse=True)
            connected = []
            
            for nid, sim in similarities[:top_k]:
                await self.add_edge(
                    node_id, nid,
                    MemoryEdgeType.SIMILAR,
                    weight=sim,
                    confidence=sim
                )
                connected.append(nid)
            
            return connected
    
    def _cosine_similarity(self, a: List[float], b: List[float]) -> float:
        """余弦相似度"""
        if not a or not b or len(a) != len(b):
            return 0.0
        
        dot = sum(x * y for x, y in zip(a, b))
        norm_a = math.sqrt(sum(x * x for x in a))
        norm_b = math.sqrt(sum(x * x for x in b))
        
        if norm_a == 0 or norm_b == 0:
            return 0.0
        
        return dot / (norm_a * norm_b)
    
    async def recall(
        self,
        query: str = None,
        node_type: MemoryNodeType = None,
        agent_id: str = None,
        limit: int = 10
    ) -> List[MemoryNode]:
        """检索记忆"""
        async with self._lock:
            candidates = set()
            
            # 按类型筛选
            if node_type:
                candidates = self.type_index.get(node_type, set()).copy()
            else:
                candidates = set(self.nodes.keys())
            
            # 按Agent筛选
            if agent_id:
                agent_node_ids = self.agent_nodes.get(agent_id, set())
                candidates &= agent_node_ids
            
            # 按激活度排序
            node_list = [self.nodes[nid] for nid in candidates]
            node_list.sort(key=lambda n: (n.activation * n.importance), reverse=True)
            
            # 访问节点
            for node in node_list[:limit]:
                node.access()
            
            self.total_accesses += limit
            
            return node_list[:limit]
    
    async def _evict_low_activation(self):
        """驱逐低激活节点"""
        if not self.nodes:
            return
        
        # 按激活度排序，驱逐最低的10%
        sorted_nodes = sorted(
            self.nodes.items(),
            key=lambda x: x[1].activation * x[1].importance
        )
        
        evict_count = max(1, len(self.nodes) // 10)
        for nid, node in sorted_nodes[:evict_count]:
            # 保留重要节点
            if node.importance > 0.8:
                continue
            del self.nodes[nid]
            self.type_index[node.node_type].discard(nid)
        
        log.print_log(f"[记忆图] 驱逐了 {evict_count} 个低激活节点", "debug")
    
    async def decay_all(self):
        """衰减所有节点"""
        now = datetime.now()
        if now - self.last_decay < self.decay_interval:
            return
        
        async with self._lock:
            for node in self.nodes.values():
                node.decay()
            
            # 移除过弱的边
            weak_edges = [
                eid for eid, edge in self.edges.items()
                if edge.strength < 0.1
            ]
            for eid in weak_edges:
                del self.edges[eid]
        
        self.last_decay = now
    
    async def get_path(
        self,
        start_id: str,
        end_id: str,
        max_depth: int = 3
    ) -> List[List[str]]:
        """查找两点间的所有路径"""
        paths = []
        
        def dfs(current: str, target: str, path: List[str], visited: Set[str]):
            if current == target:
                paths.append(path.copy())
                return
            if len(path) >= max_depth:
                return
            if current in visited:
                return
            
            visited.add(current)
            
            # 查找出边
            for edge in self.edges.values():
                if edge.source_id == current:
                    path.append(edge.target_id)
                    dfs(edge.target_id, target, path, visited)
                    path.pop()
            
            visited.remove(current)
        
        dfs(start_id, end_id, [], set())
        return paths
    
    def get_stats(self) -> Dict[str, Any]:
        """获取统计信息"""
        return {
            "total_nodes": len(self.nodes),
            "total_edges": len(self.edges),
            "by_type": {
                t.value: len(ids) for t, ids in self.type_index.items()
            },
            "active_agents": len(self.agent_nodes),
            "total_accesses": self.total_accesses,
            "avg_activation": sum(n.activation for n in self.nodes.values()) / max(1, len(self.nodes))
        }


class EmergentIntelligence:
    """
    涌现智能引擎
    
    从蜂群交互中涌现智能:
    - 模式识别
    - 趋势预测
    - 知识蒸馏
    - 集体决策
    """
    
    def __init__(
        self,
        memory_graph: CollectiveMemoryGraph,
        pattern_window: int = 100
    ):
        self.memory = memory_graph
        self.pattern_window = pattern_window
        
        # 交互历史
        self.interaction_history: List[Dict] = []
        
        # 检测到的模式
        self.detected_patterns: Dict[str, Any] = {}
        
        # 趋势分数
        self.trend_scores: Dict[str, float] = {}
        
        self._lock = asyncio.Lock()
    
    async def record_interaction(
        self,
        agent_id: str,
        action: str,
        target: str,
        outcome: str = "success"
    ):
        """记录Agent交互"""
        async with self._lock:
            interaction = {
                "agent_id": agent_id,
                "action": action,
                "target": target,
                "outcome": outcome,
                "timestamp": datetime.now()
            }
            
            self.interaction_history.append(interaction)
            
            # 维护窗口大小
            if len(self.interaction_history) > self.pattern_window:
                self.interaction_history.pop(0)
            
            # 检测模式
            await self._detect_patterns()
    
    async def _detect_patterns(self):
        """检测交互模式"""
        if len(self.interaction_history) < 10:
            return
        
        # 简单模式: 频繁的Agent-动作对
        action_counts: Dict[Tuple[str, str], int] = defaultdict(int)
        
        for interaction in self.interaction_history:
            key = (interaction["agent_id"], interaction["action"])
            action_counts[key] += 1
        
        # 更新检测到的模式
        self.detected_patterns = {
            f"{agent}:{action}": count / len(self.interaction_history)
            for (agent, action), count in action_counts.items()
            if count >= 3
        }
    
    async def predict_trend(
        self,
        entity_id: str
    ) -> float:
        """预测趋势分数"""
        async with self._lock:
            # 基于历史交互计算趋势
            recent = [
                i for i in self.interaction_history
                if i["target"] == entity_id
                and (datetime.now() - i["timestamp"]).total_seconds() < 3600
            ]
            
            if not recent:
                return 0.0
            
            # 加权分数
            total = sum(1 for i in recent if i["outcome"] == "success")
            trend = total / len(recent)
            
            self.trend_scores[entity_id] = trend
            return trend
    
    async def distill_knowledge(
        self,
        topic: str
    ) -> Dict[str, Any]:
        """知识蒸馏 - 从交互中提取知识"""
        async with self._lock:
            relevant = [
                i for i in self.interaction_history
                if topic.lower() in str(i.get("target", "")).lower()
            ]
            
            if not relevant:
                return {"knowledge": None, "confidence": 0.0}
            
            # 统计成功模式
            success_actions = defaultdict(int)
            for i in relevant:
                if i["outcome"] == "success":
                    success_actions[i["action"]] += 1
            
            # 返回最成功的动作
            best_action = max(success_actions.items(), key=lambda x: x[1])
            
            return {
                "knowledge": {
                    "recommended_action": best_action[0],
                    "success_rate": best_action[1] / max(1, len(relevant))
                },
                "confidence": min(1.0, len(relevant) / 20),
                "sample_size": len(relevant)
            }
    
    def get_stats(self) -> Dict[str, Any]:
        """获取统计信息"""
        return {
            "interaction_count": len(self.interaction_history),
            "detected_patterns": len(self.detected_patterns),
            "top_patterns": dict(sorted(
                self.detected_patterns.items(),
                key=lambda x: x[1],
                reverse=True
            )[:5]),
            "trend_entities": len(self.trend_scores)
        }


class ConsensusState(str, Enum):
    """共识状态"""
    IDLE = "idle"
    PROPOSING = "proposing"
    VOTING = "voting"
    COMMITTED = "committed"
    REJECTED = "rejected"


class BFTConsensus:
    """
    BFT共识机制 (简化版)
    
    实现:
    - 提案阶段
    - 投票阶段
    - 提交/回滚
    """
    
    def __init__(
        self,
        f: int = None,  # 允许的故障节点数
        timeout: float = 10.0
    ):
        self.f = f  # 自动计算: (n-1)/3
        self.timeout = timeout
        
        # 共识状态
        self.state = ConsensusState.IDLE
        
        # 提案
        self.current_proposal: Optional[Dict] = None
        self.proposal_hash: Optional[str] = None
        
        # 投票
        self.votes: Dict[str, str] = {}  # agent_id -> vote
        
        # 提交记录
        self.commited_values: Dict[str, Any] = {}
        
        self._lock = asyncio.Lock()
    
    def _calculate_f(self, n: int):
        """计算允许的故障节点数"""
        self.f = max(1, (n - 1) // 3)
    
    async def propose(
        self,
        proposer_id: str,
        value: Any
    ) -> str:
        """发起提案"""
        async with self._lock:
            # 生成提案哈希
            value_str = json.dumps(value, sort_keys=True, default=str)
            proposal_hash = hashlib.sha256(value_str.encode()).hexdigest()[:16]
            
            self.current_proposal = {
                "proposer": proposer_id,
                "value": value,
                "hash": proposal_hash,
                "timestamp": datetime.now()
            }
            self.proposal_hash = proposal_hash
            self.state = ConsensusState.PROPOSING
            self.votes = {}
            
            log.print_log(f"[BFT] {proposer_id} 发起提案 {proposal_hash}", "debug")
            
            return proposal_hash
    
    async def vote(
        self,
        agent_id: str,
        approve: bool
    ) -> bool:
        """投票"""
        async with self._lock:
            if self.state != ConsensusState.PROPOSING:
                return False
            
            self.votes[agent_id] = "approve" if approve else "reject"
            
            # 检查是否可以提交
            return await self._check_commit()
    
    async def _check_commit(self) -> bool:
        """检查是否满足提交条件"""
        if not self.votes:
            return False
        
        approve_count = sum(1 for v in self.votes.values() if v == "approve")
        total = len(self.votes)
        
        # 需要超过2/3同意
        if approve_count > total * 2 / 3:
            await self._commit()
            return True
        
        # 超过1/3反对则拒绝
        reject_count = sum(1 for v in self.votes.values() if v == "reject")
        if reject_count > total / 3:
            self.state = ConsensusState.REJECTED
            return False
        
        return False
    
    async def _commit(self):
        """提交共识值"""
        if self.current_proposal:
            self.commited_values[self.proposal_hash] = self.current_proposal["value"]
            self.state = ConsensusState.COMMITTED
            
            log.print_log(
                f"[BFT] 共识提交: {self.proposal_hash} "
                f"(同意: {sum(1 for v in self.votes.values() if v == 'approve')})",
                "info"
            )
    
    async def get_consensus(
        self,
        proposal_hash: str
    ) -> Optional[Any]:
        """获取已共识的值"""
        return self.commited_values.get(proposal_hash)
    
    def reset(self):
        """重置共识状态"""
        self.state = ConsensusState.IDLE
        self.current_proposal = None
        self.proposal_hash = None
        self.votes = {}
    
    def get_stats(self) -> Dict[str, Any]:
        """获取统计信息"""
        return {
            "state": self.state.value,
            "proposal_hash": self.proposal_hash,
            "votes": len(self.votes),
            "approve_count": sum(1 for v in self.votes.values() if v == "approve"),
            "commited_count": len(self.commited_values),
            "f": self.f
        }


class SwarmConsciousness:
    """
    蜂群意识层 - 整合所有意识组件
    """
    
    def __init__(
        self,
        max_nodes: int = 10000
    ):
        self.memory_graph = CollectiveMemoryGraph(max_nodes=max_nodes)
        self.emergent_intelligence = EmergentIntelligence(self.memory_graph)
        self.consensus = BFTConsensus()
        
        # 同步配置
        self.sync_interval = 60.0
        self._running = False
        self._sync_task: Optional[asyncio.Task] = None
    
    async def start(self):
        """启动意识层"""
        self._running = True
        self._sync_task = asyncio.create_task(self._sync_loop())
        log.print_log("🧠 蜂群意识层已启动", "info")
    
    async def stop(self):
        """停止意识层"""
        self._running = False
        if self._sync_task:
            self._sync_task.cancel()
            try:
                await self._sync_task
            except asyncio.CancelledError:
                pass
        log.print_log("🧠 蜂群意识层已停止", "info")
    
    async def _sync_loop(self):
        """同步循环"""
        while self._running:
            try:
                await asyncio.sleep(self.sync_interval)
                await self.memory_graph.decay_all()
            except asyncio.CancelledError:
                break
            except Exception as e:
                log.print_log(f"意识层同步错误: {e}", "error")
    
    async def remember(
        self,
        content: Any,
        node_type: MemoryNodeType,
        agent_id: str,
        importance: float = 0.5
    ) -> str:
        """记忆"""
        return await self.memory_graph.add_node(
            node_type=node_type,
            content=content,
            agent_id=agent_id,
            importance=importance
        )
    
    async def recall(
        self,
        query: str = None,
        node_type: MemoryNodeType = None,
        agent_id: str = None,
        limit: int = 10
    ) -> List[MemoryNode]:
        """回忆"""
        return await self.memory_graph.recall(query, node_type, agent_id, limit)
    
    async def think(
        self,
        agent_id: str,
        action: str,
        target: str,
        outcome: str = "success"
    ):
        """思考 - 记录交互并涌现智能"""
        await self.emergent_intelligence.record_interaction(
            agent_id, action, target, outcome
        )
    
    async def achieve_consensus(
        self,
        proposer_id: str,
        value: Any
    ) -> Optional[str]:
        """达成共识"""
        return await self.consensus.propose(proposer_id, value)
    
    async def vote(
        self,
        agent_id: str,
        approve: bool
    ) -> bool:
        """投票"""
        return await self.consensus.vote(agent_id, approve)
    
    def get_stats(self) -> Dict[str, Any]:
        """获取统计信息"""
        return {
            "memory": self.memory_graph.get_stats(),
            "emergent": self.emergent_intelligence.get_stats(),
            "consensus": self.consensus.get_stats()
        }


# 全局实例
_global_consciousness: Optional[SwarmConsciousness] = None


def get_swarm_consciousness() -> SwarmConsciousness:
    """获取全局蜂群意识实例"""
    global _global_consciousness
    if _global_consciousness is None:
        _global_consciousness = SwarmConsciousness()
    return _global_consciousness
