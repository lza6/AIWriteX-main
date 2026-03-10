"""
AIWriteX V18.0 - Knowledge Organism Module
知识有机体 - 自适应知识进化系统

功能:
1. 知识DNA: 知识的基因编码表示
2. 知识进化: 基于使用频率的进化算法
3. 知识遗忘: 模拟记忆衰退机制
4. 知识迁移: 跨智能体知识传递

概念:
- 知识被视为"有机体"，有生命周期
- 频繁使用的知识会进化（增强）
- 长期不用的知识会遗忘（弱化）
- 相似知识会交配产生新组合
"""

import asyncio
import time
import json
import hashlib
from typing import Dict, List, Optional, Set, Any, Tuple
from dataclasses import dataclass, field, asdict
from datetime import datetime
from enum import Enum, auto
from collections import defaultdict
import numpy as np
from uuid import UUID, uuid4

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
            self.logger = logging.getLogger('knowledge')
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
    from src.ai_write_x.database.db_manager import get_session
    from sqlmodel import SQLModel, Field, select
except ImportError:
    def get_session():
        return None
    SQLModel = None
    Field = None
    select = None

lg = LogAdapter()


class KnowledgeType(Enum):
    """知识类型"""
    FACT = "fact"               # 事实知识
    PROCEDURE = "procedure"     # 程序性知识
    CONCEPT = "concept"         # 概念知识
    EXPERIENCE = "experience"   # 经验知识
    RELATION = "relation"       # 关系知识
    META = "meta"               # 元知识


class KnowledgeLifeStage(Enum):
    """知识生命阶段"""
    INFANT = "infant"           # 新生
    GROWING = "growing"         # 成长
    MATURE = "mature"           # 成熟
    AGING = "aging"             # 老化
    DORMANT = "dormant"         # 休眠
    EXTINCT = "extinct"         # 消亡


@dataclass
class KnowledgeGene:
    """知识基因 - 知识的基本单元"""
    key: str                    # 基因键
    value: Any                  # 基因值
    weight: float = 1.0         # 权重
    mutability: float = 0.1     # 变异率
    
    def mutate(self) -> 'KnowledgeGene':
        """基因变异"""
        if np.random.random() < self.mutability:
            # 小幅度随机变异
            new_weight = self.weight * (1.0 + np.random.normal(0, 0.1))
            new_weight = max(0.1, min(2.0, new_weight))
            return KnowledgeGene(
                key=self.key,
                value=self.value,
                weight=new_weight,
                mutability=self.mutability
            )
        return self
    
    def crossover(self, other: 'KnowledgeGene') -> 'KnowledgeGene':
        """基因交叉"""
        if self.key != other.key:
            return self
        
        # 加权平均
        total_weight = self.weight + other.weight
        new_weight = (self.weight * self.weight + other.weight * other.weight) / total_weight
        
        return KnowledgeGene(
            key=self.key,
            value=self.value if self.weight > other.weight else other.value,
            weight=new_weight,
            mutability=(self.mutability + other.mutability) / 2
        )


@dataclass
class KnowledgeDNA:
    """知识DNA - 知识的完整基因编码"""
    organism_id: str = field(default_factory=lambda: str(uuid4()))
    knowledge_type: KnowledgeType = KnowledgeType.FACT
    genes: Dict[str, KnowledgeGene] = field(default_factory=dict)
    
    # 元数据
    created_at: float = field(default_factory=time.time)
    generation: int = 0
    parent_ids: List[str] = field(default_factory=list)
    
    # 表现型 (实际知识内容)
    phenotype: Dict[str, Any] = field(default_factory=dict)
    
    def get_fitness_score(self) -> float:
        """计算适应度分数"""
        if not self.genes:
            return 0.0
        return np.mean([g.weight for g in self.genes.values()])
    
    def mutate(self) -> 'KnowledgeDNA':
        """DNA变异"""
        new_genes = {k: v.mutate() for k, v in self.genes.items()}
        return KnowledgeDNA(
            organism_id=str(uuid4()),
            knowledge_type=self.knowledge_type,
            genes=new_genes,
            generation=self.generation + 1,
            parent_ids=[self.organism_id],
            phenotype=self.phenotype.copy()
        )
    
    def crossover(self, other: 'KnowledgeDNA') -> 'KnowledgeDNA':
        """DNA交叉 (交配)"""
        # 合并基因
        new_genes = {}
        all_keys = set(self.genes.keys()) | set(other.genes.keys())
        
        for key in all_keys:
            if key in self.genes and key in other.genes:
                # 两者都有，进行交叉
                new_genes[key] = self.genes[key].crossover(other.genes[key])
            elif key in self.genes:
                new_genes[key] = self.genes[key]
            else:
                new_genes[key] = other.genes[key]
        
        # 合并表现型
        new_phenotype = {**self.phenotype, **other.phenotype}
        
        return KnowledgeDNA(
            organism_id=str(uuid4()),
            knowledge_type=self.knowledge_type,
            genes=new_genes,
            generation=max(self.generation, other.generation) + 1,
            parent_ids=[self.organism_id, other.organism_id],
            phenotype=new_phenotype
        )
    
    def to_dict(self) -> Dict[str, Any]:
        """序列化"""
        return {
            "organism_id": self.organism_id,
            "knowledge_type": self.knowledge_type.value,
            "genes": {k: asdict(v) for k, v in self.genes.items()},
            "created_at": self.created_at,
            "generation": self.generation,
            "parent_ids": self.parent_ids,
            "phenotype": self.phenotype,
            "fitness": self.get_fitness_score()
        }
    
    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> 'KnowledgeDNA':
        """反序列化"""
        genes = {
            k: KnowledgeGene(**v) 
            for k, v in data.get("genes", {}).items()
        }
        return cls(
            organism_id=data["organism_id"],
            knowledge_type=KnowledgeType(data["knowledge_type"]),
            genes=genes,
            created_at=data["created_at"],
            generation=data["generation"],
            parent_ids=data.get("parent_ids", []),
            phenotype=data.get("phenotype", {})
        )


@dataclass
class KnowledgeOrganismState:
    """知识有机体状态"""
    dna: KnowledgeDNA
    
    # 生命状态
    stage: KnowledgeLifeStage = KnowledgeLifeStage.INFANT
    health: float = 1.0  # 0-1健康度
    energy: float = 1.0  # 0-1能量
    
    # 使用统计
    access_count: int = 0
    last_accessed: float = field(default_factory=time.time)
    creation_time: float = field(default_factory=time.time)
    
    # 关系网络
    related_organisms: Set[str] = field(default_factory=set)
    symbiotic_partners: Set[str] = field(default_factory=set)
    
    # 位置信息 (知识空间中的坐标)
    embedding: Optional[np.ndarray] = None
    
    def update_stage(self):
        """更新生命阶段"""
        age = time.time() - self.creation_time
        activity = self.access_count / max(age / 86400, 1)  # 日均访问
        
        if age < 3600:  # < 1小时
            self.stage = KnowledgeLifeStage.INFANT
        elif activity > 10:  # 高频使用
            self.stage = KnowledgeLifeStage.MATURE
        elif activity > 1:  # 正常使用
            self.stage = KnowledgeLifeStage.GROWING
        elif age > 86400 * 7:  # > 7天未使用
            self.stage = KnowledgeLifeStage.AGING
        elif self.health < 0.3:
            self.stage = KnowledgeLifeStage.DORMANT
        elif self.health < 0.1:
            self.stage = KnowledgeLifeStage.EXTINCT
    
    def get_priority(self) -> float:
        """获取优先级分数"""
        # 基于健康、能量、近期访问计算
        recency = 1.0 / (1.0 + (time.time() - self.last_accessed) / 3600)
        usage = min(self.access_count / 100, 1.0)
        
        stage_multiplier = {
            KnowledgeLifeStage.INFANT: 0.8,
            KnowledgeLifeStage.GROWING: 1.2,
            KnowledgeLifeStage.MATURE: 1.5,
            KnowledgeLifeStage.AGING: 0.6,
            KnowledgeLifeStage.DORMANT: 0.2,
            KnowledgeLifeStage.EXTINCT: 0.0
        }
        
        return (self.health * 0.3 + self.energy * 0.2 + 
                recency * 0.3 + usage * 0.2) * stage_multiplier[self.stage]


class KnowledgeOrganism:
    """
    知识有机体管理系统 - V18核心组件
    
    将知识视为生命体进行管理:
    - 出生: 新知识创建
    - 成长: 频繁使用增强
    - 繁殖: 与其他知识交配
    - 死亡: 长期不用遗忘
    """
    
    def __init__(self):
        # 知识有机体存储
        self.organisms: Dict[str, KnowledgeOrganismState] = {}
        self.by_type: Dict[KnowledgeType, Set[str]] = defaultdict(set)
        self.by_agent: Dict[str, Set[str]] = defaultdict(set)
        
        # 进化参数
        self.mutation_rate = 0.05
        self.crossover_rate = 0.1
        self.decay_rate = 0.01  # 每小时衰减
        self.extinction_threshold = 0.05
        
        # 统计
        self.birth_count = 0
        self.death_count = 0
        self.crossover_count = 0
        
        lg.print_log("🧬 KnowledgeOrganism V18.0 initialized", "info")
    
    async def start(self):
        """启动知识有机体系统"""
        asyncio.create_task(self._life_cycle_loop())
        asyncio.create_task(self._evolution_loop())
        lg.print_log("🧬 KnowledgeOrganism started", "success")
    
    # ========== 知识生命周期 ==========
    
    async def create_organism(self, 
                             content: Dict[str, Any],
                             knowledge_type: KnowledgeType = KnowledgeType.FACT,
                             agent_id: Optional[str] = None,
                             parent_ids: Optional[List[str]] = None) -> str:
        """创建新知识有机体"""
        # 构建DNA
        genes = self._content_to_genes(content)
        dna = KnowledgeDNA(
            knowledge_type=knowledge_type,
            genes=genes,
            phenotype=content,
            parent_ids=parent_ids or []
        )
        
        # 创建状态
        organism = KnowledgeOrganismState(
            dna=dna,
            stage=KnowledgeLifeStage.INFANT,
            health=1.0,
            energy=1.0
        )
        
        self.organisms[dna.organism_id] = organism
        self.by_type[knowledge_type].add(dna.organism_id)
        
        if agent_id:
            self.by_agent[agent_id].add(dna.organism_id)
        
        self.birth_count += 1
        
        lg.print_log(f"🌱 Knowledge organism born: {dna.organism_id[:8]}... "
                    f"({knowledge_type.value})", "info")
        
        return dna.organism_id
    
    def _content_to_genes(self, content: Dict[str, Any]) -> Dict[str, KnowledgeGene]:
        """将内容转换为基因"""
        genes = {}
        
        for key, value in content.items():
            gene = KnowledgeGene(
                key=key,
                value=value,
                weight=1.0,
                mutability=0.1
            )
            genes[key] = gene
        
        return genes
    
    async def access_organism(self, organism_id: str, 
                             agent_id: Optional[str] = None) -> Optional[KnowledgeDNA]:
        """访问知识有机体 (增强其健康)"""
        if organism_id not in self.organisms:
            return None
        
        organism = self.organisms[organism_id]
        
        # 更新统计
        organism.access_count += 1
        organism.last_accessed = time.time()
        
        # 增强健康
        organism.health = min(1.0, organism.health + 0.05)
        organism.energy = min(1.0, organism.energy + 0.03)
        
        # 更新阶段
        organism.update_stage()
        
        # 记录访问者
        if agent_id:
            self.by_agent[agent_id].add(organism_id)
        
        return organism.dna
    
    async def kill_organism(self, organism_id: str, reason: str = ""):
        """销毁知识有机体"""
        if organism_id not in self.organisms:
            return
        
        organism = self.organisms[organism_id]
        organism.stage = KnowledgeLifeStage.EXTINCT
        organism.health = 0.0
        
        # 清理索引
        self.by_type[organism.dna.knowledge_type].discard(organism_id)
        
        for agent_set in self.by_agent.values():
            agent_set.discard(organism_id)
        
        self.death_count += 1
        
        lg.print_log(f"💀 Knowledge organism extinct: {organism_id[:8]}... "
                    f"({reason})", "warning")
    
    # ========== 知识进化 ==========
    
    async def _evolution_loop(self):
        """进化循环"""
        while True:
            try:
                await self._perform_evolution()
                await asyncio.sleep(300)  # 每5分钟进化一次
            except Exception as e:
                lg.print_log(f"Evolution error: {e}", "error")
    
    async def _perform_evolution(self):
        """执行进化操作"""
        # 1. 选择适配度高的有机体进行繁殖
        mature_organisms = [
            (oid, org) for oid, org in self.organisms.items()
            if org.stage in [KnowledgeLifeStage.MATURE, KnowledgeLifeStage.GROWING]
            and org.health > 0.7
        ]
        
        if len(mature_organisms) < 2:
            return
        
        # 按适配度排序
        mature_organisms.sort(
            key=lambda x: x[1].dna.get_fitness_score(),
            reverse=True
        )
        
        # 选择前10%进行交配
        elite_count = max(2, len(mature_organisms) // 10)
        elites = mature_organisms[:elite_count]
        
        # 两两交配
        for i in range(0, len(elites)-1, 2):
            _, org1 = elites[i]
            _, org2 = elites[i+1]
            
            if np.random.random() < self.crossover_rate:
                await self._crossover(org1, org2)
        
        # 2. 随机变异
        for oid, organism in list(self.organisms.items())[:10]:
            if np.random.random() < self.mutation_rate:
                new_dna = organism.dna.mutate()
                organism.dna = new_dna
                organism.generation = new_dna.generation
    
    async def _crossover(self, org1: KnowledgeOrganismState, 
                        org2: KnowledgeOrganismState) -> Optional[str]:
        """两个有机体交配产生后代"""
        # 检查类型兼容性
        if org1.dna.knowledge_type != org2.dna.knowledge_type:
            return None
        
        # DNA交叉
        child_dna = org1.dna.crossover(org2.dna)
        
        # 创建新有机体
        child = KnowledgeOrganismState(
            dna=child_dna,
            stage=KnowledgeLifeStage.INFANT,
            health=0.8,  # 出生时健康度略低
            energy=0.5
        )
        
        self.organisms[child_dna.organism_id] = child
        self.by_type[child_dna.knowledge_type].add(child_dna.organism_id)
        
        # 继承关系
        org1.related_organisms.add(org2.dna.organism_id)
        org2.related_organisms.add(org1.dna.organism_id)
        
        self.crossover_count += 1
        
        lg.print_log(f"🔄 Knowledge crossover: {org1.dna.organism_id[:8]} × "
                    f"{org2.dna.organism_id[:8]} → {child_dna.organism_id[:8]}", "info")
        
        return child_dna.organism_id
    
    # ========== 生命循环 ==========
    
    async def _life_cycle_loop(self):
        """生命周期维护循环"""
        while True:
            try:
                await self._update_life_cycle()
                await asyncio.sleep(60)  # 每分钟更新一次
            except Exception as e:
                lg.print_log(f"Life cycle error: {e}", "error")
    
    async def _update_life_cycle(self):
        """更新所有有机体的生命周期"""
        current_time = time.time()
        
        for organism_id, organism in list(self.organisms.items()):
            # 能量自然衰减
            hours_since_access = (current_time - organism.last_accessed) / 3600
            energy_decay = self.decay_rate * hours_since_access
            organism.energy = max(0.0, organism.energy - energy_decay)
            
            # 健康度衰减 (老化的知识)
            if organism.stage == KnowledgeLifeStage.AGING:
                organism.health *= 0.95
            
            # 更新阶段
            organism.update_stage()
            
            # 检查消亡
            if organism.stage == KnowledgeLifeStage.EXTINCT:
                if organism_id in self.organisms:
                    del self.organisms[organism_id]
                    self.death_count += 1
    
    # ========== 知识迁移 ==========
    
    async def migrate_knowledge(self, organism_id: str, 
                               from_agent: str, 
                               to_agent: str) -> bool:
        """迁移知识从一个智能体到另一个"""
        if organism_id not in self.organisms:
            return False
        
        # 更新归属
        if from_agent in self.by_agent:
            self.by_agent[from_agent].discard(organism_id)
        
        self.by_agent[to_agent].add(organism_id)
        
        # 增加能量 (迁移刺激)
        organism = self.organisms[organism_id]
        organism.energy = min(1.0, organism.energy + 0.1)
        
        lg.print_log(f"📤 Knowledge migrated: {organism_id[:8]}... "
                    f"{from_agent} → {to_agent}", "info")
        
        return True
    
    async def share_knowledge(self, organism_id: str,
                             source_agent: str,
                             target_agents: List[str]) -> List[str]:
        """分享知识给多个智能体 (创建副本)"""
        if organism_id not in self.organisms:
            return []
        
        source_org = self.organisms[organism_id]
        new_ids = []
        
        for target in target_agents:
            if target == source_agent:
                continue
            
            # 创建副本 (轻微变异)
            new_dna = source_org.dna.mutate()
            new_org = KnowledgeOrganismState(
                dna=new_dna,
                stage=KnowledgeLifeStage.INFANT,
                health=0.9,
                energy=0.7
            )
            
            self.organisms[new_dna.organism_id] = new_org
            self.by_type[new_dna.knowledge_type].add(new_dna.organism_id)
            self.by_agent[target].add(new_dna.organism_id)
            
            # 建立共生关系
            source_org.symbiotic_partners.add(new_dna.organism_id)
            new_org.symbiotic_partners.add(organism_id)
            
            new_ids.append(new_dna.organism_id)
        
        lg.print_log(f"📤 Knowledge shared: {organism_id[:8]}... → "
                    f"{len(new_ids)} agents", "info")
        
        return new_ids
    
    # ========== 查询接口 ==========
    
    def get_organism(self, organism_id: str) -> Optional[KnowledgeOrganismState]:
        """获取知识有机体"""
        return self.organisms.get(organism_id)
    
    def get_by_type(self, knowledge_type: KnowledgeType) -> List[KnowledgeOrganismState]:
        """按类型获取"""
        ids = self.by_type.get(knowledge_type, set())
        return [self.organisms[oid] for oid in ids if oid in self.organisms]
    
    def get_by_agent(self, agent_id: str) -> List[KnowledgeOrganismState]:
        """按智能体获取"""
        ids = self.by_agent.get(agent_id, set())
        return [self.organisms[oid] for oid in ids if oid in self.organisms]
    
    def search_knowledge(self, query: str, 
                        top_k: int = 10) -> List[Tuple[KnowledgeOrganismState, float]]:
        """搜索知识 (简化版，可接入向量检索)"""
        results = []
        query_lower = query.lower()
        
        for organism in self.organisms.values():
            # 简单文本匹配
            phenotype_str = json.dumps(organism.dna.phenotype).lower()
            
            if query_lower in phenotype_str:
                # 计算相关度分数
                relevance = organism.get_priority()
                if query_lower in phenotype_str[:100]:  # 标题匹配
                    relevance *= 1.5
                
                results.append((organism, relevance))
        
        # 排序返回top_k
        results.sort(key=lambda x: x[1], reverse=True)
        return results[:top_k]
    
    def get_population_stats(self) -> Dict[str, Any]:
        """获取种群统计"""
        stage_counts = defaultdict(int)
        type_counts = defaultdict(int)
        
        for org in self.organisms.values():
            stage_counts[org.stage.value] += 1
            type_counts[org.dna.knowledge_type.value] += 1
        
        return {
            "total_organisms": len(self.organisms),
            "birth_count": self.birth_count,
            "death_count": self.death_count,
            "crossover_count": self.crossover_count,
            "by_stage": dict(stage_counts),
            "by_type": dict(type_counts),
            "avg_fitness": np.mean([
                org.dna.get_fitness_score() 
                for org in self.organisms.values()
            ]) if self.organisms else 0.0
        }
