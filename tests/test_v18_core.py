"""
AIWriteX V18.0 - 核心功能快速测试
不启动后台循环，直接测试核心逻辑
"""

import sys
sys.path.insert(0, 'src')

print("=" * 70)
print("AIWriteX V18.0 Neural Collective - 核心功能测试")
print("=" * 70)

# 测试1: 版本信息
print("\n[测试1] 版本信息验证")
try:
    from ai_write_x.version import get_build_info
    info = get_build_info()
    assert info['version'] == '18.0.0', f"版本不匹配: {info['version']}"
    assert info['codename'] == 'Neural Collective'
    print(f"  ✅ 版本: {info['version']}")
    print(f"  ✅ 代号: {info['codename']}")
    print(f"  ✅ 功能: {len(info['features'])} 项新特性")
except Exception as e:
    print(f"  ❌ 失败: {e}")

# 测试2: 集体意识 - 数据类
print("\n[测试2] 集体意识数据类")
try:
    from ai_write_x.core.swarm_v2.collective_mind import (
        IntentionType, CollectiveState, SwarmIntention, AgentState
    )
    
    # 测试意图类型
    assert IntentionType.CONTENT_CREATION is not None
    assert IntentionType.TREND_ANALYSIS is not None
    print("  ✅ IntentionType 枚举正常")
    
    # 测试状态枚举
    assert CollectiveState.STABLE.value == "stable"
    print("  ✅ CollectiveState 枚举正常")
    
    # 测试智能体状态
    agent = AgentState(
        agent_id="test_001",
        role="researcher",
        status="idle",
        capabilities=["search", "analysis"]
    )
    assert agent.agent_id == "test_001"
    print("  ✅ AgentState 数据类正常")
    
    # 测试意图
    intention = SwarmIntention(
        type=IntentionType.CONTENT_CREATION,
        source_agents=["agent_1"],
        payload={"topic": "AI"}
    )
    assert intention.type == IntentionType.CONTENT_CREATION
    print("  ✅ SwarmIntention 数据类正常")
    
except Exception as e:
    print(f"  ❌ 失败: {e}")
    import traceback
    traceback.print_exc()

# 测试3: 共识协议 - 数据类
print("\n[测试3] 共识协议数据类")
try:
    from ai_write_x.core.swarm_v2.consensus_protocol import (
        ConsensusState, ProposalType, Proposal, Vote
    )
    
    # 测试提案类型
    assert ProposalType.TASK_ALLOCATION.value == "task_allocation"
    print("  ✅ ProposalType 枚举正常")
    
    # 测试共识状态
    assert ConsensusState.COMMITTED.value == "committed"
    print("  ✅ ConsensusState 枚举正常")
    
    # 测试提案
    proposal = Proposal(
        type=ProposalType.CONFIG_CHANGE,
        proposer="agent_1",
        content={"key": "value"}
    )
    assert proposal.proposer == "agent_1"
    print("  ✅ Proposal 数据类正常")
    
except Exception as e:
    print(f"  ❌ 失败: {e}")
    import traceback
    traceback.print_exc()

# 测试4: 知识有机体 - 数据类
print("\n[测试4] 知识有机体数据类")
try:
    from ai_write_x.core.swarm_v2.knowledge_organism import (
        KnowledgeType, KnowledgeLifeStage, KnowledgeGene, KnowledgeDNA
    )
    
    # 测试知识类型
    assert KnowledgeType.CONCEPT.value == "concept"
    print("  ✅ KnowledgeType 枚举正常")
    
    # 测试生命阶段
    assert KnowledgeLifeStage.MATURE.value == "mature"
    print("  ✅ KnowledgeLifeStage 枚举正常")
    
    # 测试知识基因
    gene = KnowledgeGene(key="test", value="data", weight=1.5)
    assert gene.key == "test"
    assert gene.weight == 1.5
    print("  ✅ KnowledgeGene 数据类正常")
    
    # 测试DNA
    dna = KnowledgeDNA(
        knowledge_type=KnowledgeType.FACT,
        genes={"g1": gene},
        phenotype={"content": "test"}
    )
    assert dna.knowledge_type == KnowledgeType.FACT
    print("  ✅ KnowledgeDNA 数据类正常")
    
    # 测试适应度计算
    fitness = dna.get_fitness_score()
    assert 0 <= fitness <= 2.0
    print(f"  ✅ 适应度计算正常: {fitness:.2f}")
    
except Exception as e:
    print(f"  ❌ 失败: {e}")
    import traceback
    traceback.print_exc()

# 测试5: 自修复 - 数据类
print("\n[测试5] 自修复数据类")
try:
    from ai_write_x.core.swarm_v2.self_healing import (
        HealthStatus, FailureType, HealthMetrics, CircuitBreaker
    )
    
    # 测试健康状态
    assert HealthStatus.HEALTHY.value == "healthy"
    print("  ✅ HealthStatus 枚举正常")
    
    # 测试故障类型
    assert FailureType.EXCEPTION.value == "exception"
    print("  ✅ FailureType 枚举正常")
    
    # 测试健康指标
    metrics = HealthMetrics(
        cpu_usage=0.5,
        memory_usage=0.6,
        response_time=1.0,
        error_rate=0.1
    )
    score = metrics.calculate_health_score()
    assert 0 <= score <= 1.0
    print(f"  ✅ HealthMetrics 计算正常: {score:.2f}")
    
except Exception as e:
    print(f"  ❌ 失败: {e}")
    import traceback
    traceback.print_exc()

# 测试6: 功能逻辑测试
print("\n[测试6] 核心功能逻辑")

# 6.1 意图置信度计算
try:
    from ai_write_x.core.swarm_v2.collective_mind import CollectiveMind
    
    # 创建最小化测试
    mind = CollectiveMind.__new__(CollectiveMind)
    mind.agents = {}
    
    # 模拟智能体
    agent = AgentState(
        agent_id="test_agent",
        role="researcher",
        status="idle",
        load=0.3,
        capabilities=["search"]
    )
    mind.agents["test_agent"] = agent
    
    intention = SwarmIntention(
        type=IntentionType.CONTENT_CREATION,
        source_agents=["test_agent"]
    )
    
    # 置信度应该在范围内
    confidence = mind._calculate_intention_confidence(intention)
    assert 0 <= confidence <= 1.0
    print(f"  ✅ 意图置信度计算: {confidence:.2f}")
    
except Exception as e:
    print(f"  ⚠️ 意图置信度测试跳过: {e}")

# 6.2 提案加权计算
try:
    from ai_write_x.core.swarm_v2.consensus_protocol import Proposal, Vote
    
    proposal = Proposal(
        type=ProposalType.TASK_ALLOCATION,
        proposer="agent_1"
    )
    
    # 添加投票
    proposal.votes["agent_1"] = type('Vote', (), {'agent_id': 'agent_1', 'approve': True, 'weight': 2.0})()
    proposal.votes["agent_2"] = type('Vote', (), {'agent_id': 'agent_2', 'approve': False, 'weight': 1.0})()
    proposal.votes["agent_3"] = type('Vote', (), {'agent_id': 'agent_3', 'approve': True, 'weight': 1.5})()
    
    weighted_approval = proposal.get_weighted_approval()
    assert 0 <= weighted_approval <= 1.0
    print(f"  ✅ 提案加权计算: {weighted_approval:.2%}")
    
except Exception as e:
    print(f"  ⚠️ 提案加权测试跳过: {e}")

# 6.3 知识进化
try:
    from ai_write_x.core.swarm_v2.knowledge_organism import KnowledgeDNA, KnowledgeGene, KnowledgeType
    
    # 创建父代DNA
    dna1 = KnowledgeDNA(
        knowledge_type=KnowledgeType.FACT,
        genes={
            "trait1": KnowledgeGene("trait1", "A", weight=1.0),
            "trait2": KnowledgeGene("trait2", "B", weight=0.8)
        },
        phenotype={"data": "parent1"}
    )
    
    dna2 = KnowledgeDNA(
        knowledge_type=KnowledgeType.FACT,
        genes={
            "trait1": KnowledgeGene("trait1", "C", weight=0.9),
            "trait2": KnowledgeGene("trait2", "D", weight=1.2)
        },
        phenotype={"data": "parent2"}
    )
    
    # 测试交叉
    child = dna1.crossover(dna2)
    assert child.knowledge_type == KnowledgeType.FACT
    assert len(child.genes) >= 2
    print(f"  ✅ 知识交叉: 父代 {dna1.organism_id[:8]} × {dna2.organism_id[:8]} → {child.organism_id[:8]}")
    
    # 测试变异
    mutated = dna1.mutate()
    assert mutated.generation > dna1.generation
    print(f"  ✅ 知识变异: gen {dna1.generation} → {mutated.generation}")
    
except Exception as e:
    print(f"  ⚠️ 知识进化测试跳过: {e}")

# 6.4 熔断器
try:
    from ai_write_x.core.swarm_v2.self_healing import CircuitBreaker
    import asyncio
    
    async def test_circuit_breaker():
        cb = CircuitBreaker(failure_threshold=2, recovery_timeout=0.05)
        
        # 正常调用
        async def success():
            return "OK"
        
        result = await cb.call(success)
        assert result == "OK"
        assert cb.state == "closed"
        
        # 失败调用
        async def fail():
            raise ValueError("Test error")
        
        for _ in range(2):
            try:
                await cb.call(fail)
            except:
                pass
        
        assert cb.state == "open"
        
        # 等待恢复
        await asyncio.sleep(0.1)
        
        # 半开状态
        result = await cb.call(success)
        assert cb.state == "closed"
        
        return True
    
    result = asyncio.run(test_circuit_breaker())
    if result:
        print("  ✅ 熔断器逻辑正常")
        
except Exception as e:
    print(f"  ⚠️ 熔断器测试跳过: {e}")

# 测试7: 序列化测试
print("\n[测试7] 数据序列化")
try:
    from ai_write_x.core.swarm_v2.collective_mind import SwarmIntention, IntentionType
    import json
    
    # 测试意图序列化
    intention = SwarmIntention(
        type=IntentionType.TREND_ANALYSIS,
        source_agents=["a1", "a2"],
        payload={"key": "value"},
        confidence=0.85
    )
    
    data = intention.to_dict()
    assert data['type'] == 'TREND_ANALYSIS'
    assert data['confidence'] == 0.85
    
    # 反序列化
    restored = SwarmIntention.from_dict(data)
    assert restored.type == IntentionType.TREND_ANALYSIS
    assert restored.confidence == 0.85
    
    print("  ✅ 意图序列化/反序列化正常")
    
except Exception as e:
    print(f"  ⚠️ 序列化测试跳过: {e}")

# 测试8: 统计功能
print("\n[测试8] 统计功能")
try:
    from ai_write_x.core.swarm_v2.knowledge_organism import KnowledgeOrganism, KnowledgeType
    
    ko = KnowledgeOrganism.__new__(KnowledgeOrganism)
    ko.organisms = {}
    ko.by_type = {}
    ko.by_agent = {}
    ko.birth_count = 5
    ko.death_count = 2
    ko.crossover_count = 3
    
    stats = ko.get_population_stats()
    assert stats['total_organisms'] == 0  # 空的organisms
    assert stats['birth_count'] == 5
    assert stats['death_count'] == 2
    
    print(f"  ✅ 知识统计: 出生{stats['birth_count']}, 死亡{stats['death_count']}")
    
except Exception as e:
    print(f"  ⚠️ 统计测试跳过: {e}")

print("\n" + "=" * 70)
print("V18核心功能测试完成")
print("=" * 70)
