"""
AIWriteX V18.0 - Neural Collective 简化测试套件
"""

import asyncio
import sys
sys.path.insert(0, 'src')

# 测试1: 基础导入测试
print("=" * 60)
print("测试 1: 基础模块导入")
print("=" * 60)

try:
    from ai_write_x.core.swarm_v2.collective_mind import CollectiveMind, CollectiveState, IntentionType
    print("✅ collective_mind 导入成功")
except Exception as e:
    print(f"❌ collective_mind 导入失败: {e}")

try:
    from ai_write_x.core.swarm_v2.consensus_protocol import ConsensusProtocol, ConsensusState, ProposalType
    print("✅ consensus_protocol 导入成功")
except Exception as e:
    print(f"❌ consensus_protocol 导入失败: {e}")

try:
    from ai_write_x.core.swarm_v2.knowledge_organism import KnowledgeOrganism, KnowledgeType, KnowledgeLifeStage
    print("✅ knowledge_organism 导入成功")
except Exception as e:
    print(f"❌ knowledge_organism 导入失败: {e}")

try:
    from ai_write_x.core.swarm_v2.self_healing import SelfHealing, HealthStatus, CircuitBreaker
    print("✅ self_healing 导入成功")
except Exception as e:
    print(f"❌ self_healing 导入失败: {e}")

# 测试2: 集体意识基础功能
print("\n" + "=" * 60)
print("测试 2: 集体意识基础功能")
print("=" * 60)

async def test_collective_mind():
    try:
        mind = CollectiveMind()
        await mind.start()
        
        # 测试智能体注册
        agent = await mind.register_agent("test_agent_1", "researcher", ["search", "analysis"])
        print(f"✅ 智能体注册成功: {agent.agent_id}")
        
        # 测试心跳
        await mind.heartbeat("test_agent_1", {"load": 0.5, "cpu": 0.3, "memory": 0.4})
        print(f"✅ 心跳更新成功")
        
        # 测试统计信息
        stats = mind.get_stats()
        print(f"✅ 统计信息: {stats}")
        
        await mind.stop()
        return True
    except Exception as e:
        print(f"❌ 集体意识测试失败: {e}")
        import traceback
        traceback.print_exc()
        return False

result = asyncio.run(test_collective_mind())

# 测试3: 共识协议基础功能
print("\n" + "=" * 60)
print("测试 3: 共识协议基础功能")
print("=" * 60)

async def test_consensus():
    try:
        from ai_write_x.core.swarm_v2.collective_mind import CollectiveMind
        mind = CollectiveMind()
        await mind.start()
        
        consensus = ConsensusProtocol(mind)
        await consensus.start()
        
        # 注册测试智能体
        for i in range(3):
            await mind.register_agent(f"voter_{i}", "worker", ["vote"])
        
        # 创建提案
        proposal = await consensus.create_proposal(
            ProposalType.TASK_ALLOCATION,
            "voter_0",
            {"task": "test_task", "priority": "high"},
            "测试提案"
        )
        print(f"✅ 提案创建成功: {proposal.id[:8]}")
        
        # 提交投票
        await consensus.submit_vote(proposal.id, "voter_1", True, weight=1.0)
        await consensus.submit_vote(proposal.id, "voter_2", True, weight=1.0)
        print(f"✅ 投票提交成功")
        
        # 检查统计
        stats = consensus.get_stats()
        print(f"✅ 共识统计: {stats}")
        
        await mind.stop()
        return True
    except Exception as e:
        print(f"❌ 共识协议测试失败: {e}")
        import traceback
        traceback.print_exc()
        return False

result = asyncio.run(test_consensus())

# 测试4: 知识有机体基础功能
print("\n" + "=" * 60)
print("测试 4: 知识有机体基础功能")
print("=" * 60)

async def test_knowledge():
    try:
        ko = KnowledgeOrganism()
        await ko.start()
        
        # 创建知识
        content = {
            "title": "测试知识",
            "data": ["知识点1", "知识点2"],
            "metadata": {"author": "test"}
        }
        
        organism_id = await ko.create_organism(
            content,
            KnowledgeType.CONCEPT,
            agent_id="test_agent"
        )
        print(f"✅ 知识有机体创建成功: {organism_id[:8]}")
        
        # 访问知识
        dna = await ko.access_organism(organism_id, "test_agent_2")
        print(f"✅ 知识访问成功")
        
        # 查询知识
        results = ko.search_knowledge("测试", top_k=5)
        print(f"✅ 知识查询成功: 找到 {len(results)} 个结果")
        
        # 统计
        stats = ko.get_population_stats()
        print(f"✅ 知识统计: {stats}")
        
        return True
    except Exception as e:
        print(f"❌ 知识有机体测试失败: {e}")
        import traceback
        traceback.print_exc()
        return False

result = asyncio.run(test_knowledge())

# 测试5: 自修复基础功能
print("\n" + "=" * 60)
print("测试 5: 自修复基础功能")
print("=" * 60)

async def test_self_healing():
    try:
        from ai_write_x.core.swarm_v2.collective_mind import CollectiveMind
        mind = CollectiveMind()
        await mind.start()
        
        healing = SelfHealing(mind)
        await healing.start()
        
        # 注册智能体
        await mind.register_agent("health_agent", "monitor", ["health_check"])
        
        # 创建检查点
        checkpoint_id = await healing.create_checkpoint()
        print(f"✅ 检查点创建成功: {checkpoint_id}")
        
        # 获取系统健康
        health = healing.get_system_health()
        print(f"✅ 系统健康状态: {health}")
        
        # 测试熔断器
        cb = CircuitBreaker(failure_threshold=3, recovery_timeout=0.1)
        
        async def success_func():
            return "success"
        
        result = await cb.call(success_func)
        print(f"✅ 熔断器测试成功: {result}")
        
        await mind.stop()
        return True
    except Exception as e:
        print(f"❌ 自修复测试失败: {e}")
        import traceback
        traceback.print_exc()
        return False

result = asyncio.run(test_self_healing())

# 测试6: 版本信息
print("\n" + "=" * 60)
print("测试 6: 版本信息验证")
print("=" * 60)

try:
    from ai_write_x.version import get_build_info
    info = get_build_info()
    print(f"版本: {info['version']}")
    print(f"代号: {info['codename']}")
    print(f"功能: {', '.join(info['features'])}")
    
    if info['version'] == '18.0.0':
        print("✅ 版本验证成功")
    else:
        print(f"❌ 版本不匹配: 期望 18.0.0, 实际 {info['version']}")
except Exception as e:
    print(f"❌ 版本测试失败: {e}")

print("\n" + "=" * 60)
print("测试完成")
print("=" * 60)
