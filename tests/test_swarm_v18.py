"""
AIWriteX V18.0 - Neural Collective 测试套件
全面测试自治智能体群体系统
"""

import asyncio
import sys
import time
import unittest
from datetime import datetime
from uuid import uuid4

# 直接导入，不依赖src.ai_write_x
sys.path.insert(0, 'src')
sys.path.insert(0, '.')

# 直接导入V18模块
import importlib.util
spec = importlib.util.spec_from_file_location("collective_mind", "src/ai_write_x/core/swarm_v2/collective_mind.py")
collective_mind_module = importlib.util.module_from_spec(spec)
spec.loader.exec_module(collective_mind_module)

# 导入各个模块
from ai_write_x.core.swarm_v2.collective_mind import (
    CollectiveMind, CollectiveState, SwarmIntention, IntentionType, AgentState
)
from ai_write_x.core.swarm_v2.consensus_protocol import (
    ConsensusProtocol, ConsensusState, Proposal, ProposalType, Vote
)
from ai_write_x.core.swarm_v2.knowledge_organism import (
    KnowledgeOrganism, KnowledgeDNA, KnowledgeType, KnowledgeLifeStage, KnowledgeGene, KnowledgeOrganismState
)
from ai_write_x.core.swarm_v2.self_healing import (
    SelfHealing, HealthStatus, CircuitBreaker, FailureType, FailureEvent, HealthMetrics, RecoveryAction
)



class TestCollectiveMind(unittest.IsolatedAsyncioTestCase):
    """测试集体意识中枢"""
    
    async def asyncSetUp(self):
        self.mind = CollectiveMind()
        await self.mind.start()
    
    async def asyncTearDown(self):
        await self.mind.stop()
    
    async def test_singleton_pattern(self):
        """测试单例模式"""
        mind2 = await CollectiveMind.get_instance()
        self.assertEqual(self.mind, mind2)
    
    async def test_agent_registration(self):
        """测试智能体注册"""
        agent = await self.mind.register_agent(
            "agent_001", "researcher", ["search", "analysis"]
        )
        self.assertEqual(agent.agent_id, "agent_001")
        self.assertEqual(agent.role, "researcher")
        self.assertIn("agent_001", self.mind.agents)
    
    async def test_agent_unregistration(self):
        """测试智能体注销"""
        await self.mind.register_agent("agent_002", "writer", ["writing"])
        await self.mind.unregister_agent("agent_002")
        self.assertNotIn("agent_002", self.mind.agents)
    
    async def test_heartbeat(self):
        """测试心跳机制"""
        await self.mind.register_agent("agent_003", "reviewer", ["review"])
        await self.mind.heartbeat("agent_003", {"load": 0.5, "cpu": 0.3})
        
        agent = self.mind.agents["agent_003"]
        self.assertEqual(agent.load, 0.5)
        self.assertEqual(agent.cpu_usage, 0.3)
    
    async def test_intention_submission(self):
        """测试意图提交"""
        intention = SwarmIntention(
            type=IntentionType.CONTENT_CREATION,
            source_agents=["agent_001"],
            payload={"topic": "AI技术"}
        )
        
        intention_id = await self.mind.submit_intention(intention)
        self.assertIsNotNone(intention_id)
        self.assertEqual(len(self.mind.intentions), 1)
    
    async def test_intention_confidence(self):
        """测试意图置信度计算"""
        await self.mind.register_agent("agent_004", "coordinator", ["coordination"])
        
        intention = SwarmIntention(
            type=IntentionType.TREND_ANALYSIS,
            source_agents=["agent_004"],
            confidence=0.0  # 将由系统计算
        )
        
        await self.mind.submit_intention(intention)
        self.assertGreater(intention.confidence, 0.0)
    
    async def test_knowledge_sync(self):
        """测试知识同步"""
        knowledge = {
            "topic": "机器学习",
            "insights": ["深度学习", "强化学习"],
            "confidence": 0.95
        }
        
        await self.mind.sync_knowledge("agent_001", knowledge)
        self.assertIn("agent_001", self.mind.knowledge_graph)
    
    async def test_knowledge_query(self):
        """测试知识查询"""
        await self.mind.sync_knowledge("agent_005", {"content": "Python编程技巧"})
        results = self.mind.query_knowledge("Python")
        self.assertGreater(len(results), 0)
    
    async def test_event_subscription(self):
        """测试事件订阅"""
        events_received = []
        
        async def event_handler(event):
            events_received.append(event)
        
        self.mind.subscribe("test_event", event_handler)
        await self.mind._broadcast_event("test_event", {"data": "test"})
        
        # 等待事件处理
        await asyncio.sleep(0.1)
        self.assertEqual(len(events_received), 1)
    
    async def test_stats_collection(self):
        """测试统计信息收集"""
        stats = self.mind.get_stats()
        self.assertIn("state", stats)
        self.assertIn("total_agents", stats)
        self.assertIn("alive_agents", stats)


class TestConsensusProtocol(unittest.IsolatedAsyncioTestCase):
    """测试分布式共识协议"""
    
    async def asyncSetUp(self):
        self.mind = CollectiveMind()
        await self.mind.start()
        self.consensus = ConsensusProtocol(self.mind)
        await self.consensus.start()
    
    async def asyncTearDown(self):
        await self.mind.stop()
    
    async def test_proposal_creation(self):
        """测试提案创建"""
        proposal = await self.consensus.create_proposal(
            ProposalType.TASK_ALLOCATION,
            "agent_001",
            {"task": "write_article", "priority": "high"},
            "分配写作任务"
        )
        
        self.assertIsNotNone(proposal.id)
        self.assertEqual(proposal.type, ProposalType.TASK_ALLOCATION)
        self.assertIn(proposal.id, self.consensus.proposals)
    
    async def test_vote_submission(self):
        """测试投票提交"""
        proposal = await self.consensus.create_proposal(
            ProposalType.CONFIG_CHANGE,
            "agent_001",
            {"config": "new_setting"}
        )
        
        success = await self.consensus.submit_vote(
            proposal.id, "agent_002", True, weight=1.5
        )
        self.assertTrue(success)
        self.assertEqual(len(proposal.votes), 1)
    
    async def test_weighted_approval(self):
        """测试加权赞成计算"""
        proposal = Proposal(
            type=ProposalType.KNOWLEDGE_MERGE,
            proposer="agent_001"
        )
        
        proposal.votes["agent_001"] = type('Vote', (), {
            'agent_id': 'agent_001', 'approve': True, 'weight': 2.0
        })()
        proposal.votes["agent_002"] = type('Vote', (), {
            'agent_id': 'agent_002', 'approve': False, 'weight': 1.0
        })()
        
        ratio = proposal.get_weighted_approval()
        self.assertAlmostEqual(ratio, 2.0/3.0, places=2)
    
    async def test_conflict_detection(self):
        """测试冲突检测"""
        p1 = await self.consensus.create_proposal(
            ProposalType.TASK_ALLOCATION,
            "agent_001",
            {"assigned_agents": ["agent_A", "agent_B"]}
        )
        
        p2 = await self.consensus.create_proposal(
            ProposalType.TASK_ALLOCATION,
            "agent_002",
            {"assigned_agents": ["agent_B", "agent_C"]}  # 冲突: agent_B
        )
        
        conflicts = await self.consensus.detect_conflicts()
        self.assertGreater(len(conflicts), 0)
    
    async def test_view_change(self):
        """测试视图变更"""
        # 注册多个智能体
        for i in range(5):
            await self.mind.register_agent(f"agent_{i}", "worker", ["compute"])
        
        old_leader = self.consensus.current_view.leader_id
        await self.consensus.initiate_view_change("test")
        
        # 领导者应该改变
        self.assertNotEqual(self.consensus.current_view.leader_id, old_leader)
        self.assertEqual(self.consensus.current_view.view_number, 1)


class TestKnowledgeOrganism(unittest.IsolatedAsyncioTestCase):
    """测试知识有机体"""
    
    async def asyncSetUp(self):
        self.ko = KnowledgeOrganism()
        await self.ko.start()
    
    async def asyncTearDown(self):
        pass  # 清理在测试中处理
    
    async def test_organism_creation(self):
        """测试知识有机体创建"""
        content = {
            "title": "深度学习基础",
            "concepts": ["神经网络", "反向传播"],
            "difficulty": "medium"
        }
        
        organism_id = await self.ko.create_organism(
            content,
            KnowledgeType.CONCEPT,
            agent_id="agent_001"
        )
        
        self.assertIsNotNone(organism_id)
        self.assertIn(organism_id, self.ko.organisms)
    
    async def test_organism_access(self):
        """测试知识访问"""
        content = {"data": "测试数据"}
        oid = await self.ko.create_organism(content, KnowledgeType.FACT)
        
        dna = await self.ko.access_organism(oid, "agent_002")
        self.assertIsNotNone(dna)
        
        organism = self.ko.get_organism(oid)
        self.assertEqual(organism.access_count, 1)
        self.assertGreater(organism.health, 0.9)  # 访问增强健康
    
    async def test_knowledge_evolution(self):
        """测试知识进化"""
        content = {"gen": 0}
        oid = await self.ko.create_organism(content, KnowledgeType.FACT)
        
        organism = self.ko.get_organism(oid)
        original_fitness = organism.dna.get_fitness_score()
        
        # 多次访问提升适应度
        for _ in range(10):
            await self.ko.access_organism(oid)
        
        organism.update_stage()
        # 访问后健康度应该提升
        self.assertGreaterEqual(organism.health, 0.9)
    
    async def test_knowledge_crossover(self):
        """测试知识交叉"""
        c1 = {"trait": "A", "value": 1}
        c2 = {"trait": "B", "value": 2}
        
        oid1 = await self.ko.create_organism(c1, KnowledgeType.FACT)
        oid2 = await self.ko.create_organism(c2, KnowledgeType.FACT)
        
        org1 = self.ko.get_organism(oid1)
        org2 = self.ko.get_organism(oid2)
        
        # 提升成熟度以允许交叉
        org1.stage = KnowledgeLifeStage.MATURE
        org1.health = 0.8
        org2.stage = KnowledgeLifeStage.MATURE
        org2.health = 0.8
        
        child_id = await self.ko._crossover(org1, org2)
        self.assertIsNotNone(child_id)
        self.assertIn(child_id, self.ko.organisms)
    
    async def test_knowledge_migration(self):
        """测试知识迁移"""
        content = {"portable": True}
        oid = await self.ko.create_organism(content, KnowledgeType.FACT, "agent_A")
        
        success = await self.ko.migrate_knowledge(oid, "agent_A", "agent_B")
        self.assertTrue(success)
        
        # 检查agent_B是否拥有该知识
        agent_b_knowledge = self.ko.get_by_agent("agent_B")
        self.assertEqual(len(agent_b_knowledge), 1)
    
    async def test_knowledge_search(self):
        """测试知识搜索"""
        await self.ko.create_organism(
            {"title": "Python教程", "content": "学习Python编程"},
            KnowledgeType.PROCEDURE
        )
        await self.ko.create_organism(
            {"title": "Java教程", "content": "学习Java编程"},
            KnowledgeType.PROCEDURE
        )
        
        results = self.ko.search_knowledge("Python", top_k=5)
        self.assertGreater(len(results), 0)
        
        # 第一个结果应该与Python相关
        first_result, score = results[0]
        self.assertIn("Python", str(first_result.dna.phenotype))
    
    async def test_population_stats(self):
        """测试种群统计"""
        stats = self.ko.get_population_stats()
        self.assertIn("total_organisms", stats)
        self.assertIn("by_stage", stats)
        self.assertIn("by_type", stats)


class TestSelfHealing(unittest.IsolatedAsyncioTestCase):
    """测试自修复机制"""
    
    async def asyncSetUp(self):
        self.mind = CollectiveMind()
        await self.mind.start()
        self.healing = SelfHealing(self.mind)
        await self.healing.start()
    
    async def asyncTearDown(self):
        await self.mind.stop()
    
    async def test_health_metrics_calculation(self):
        """测试健康指标计算"""
        from ai_write_x.core.swarm_v2.self_healing import HealthMetrics
        
        metrics = HealthMetrics(
            cpu_usage=0.5,
            memory_usage=0.6,
            response_time=1.0,
            error_rate=0.1
        )
        
        score = metrics.calculate_health_score()
        self.assertGreater(score, 0.0)
        self.assertLessEqual(score, 1.0)
    
    async def test_health_status_determination(self):
        """测试健康状态判定"""
        from ai_write_x.core.swarm_v2.self_healing import HealthMetrics
        
        # 健康状态
        healthy = HealthMetrics(cpu_usage=0.2, memory_usage=0.3)
        healthy.calculate_health_score()
        status = self.healing._determine_health_status(healthy)
        self.assertEqual(status, HealthStatus.HEALTHY)
        
        # 警告状态
        warning = HealthMetrics(cpu_usage=0.8, memory_usage=0.5)
        warning.calculate_health_score()
        status = self.healing._determine_health_status(warning)
        self.assertEqual(status, HealthStatus.WARNING)
    
    async def test_circuit_breaker(self):
        """测试熔断器"""
        cb = CircuitBreaker(failure_threshold=3, recovery_timeout=0.1)
        
        # 正常调用
        async def success_func():
            return "success"
        
        result = await cb.call(success_func)
        self.assertEqual(result, "success")
        
        # 失败调用触发熔断
        async def fail_func():
            raise Exception("Test error")
        
        for _ in range(3):
            try:
                await cb.call(fail_func)
            except:
                pass
        
        # 熔断器应该打开
        self.assertEqual(cb.state, "open")
        
        # 等待恢复
        await asyncio.sleep(0.2)
        
        # 半开状态下的成功调用应该关闭熔断器
        result = await cb.call(success_func)
        self.assertEqual(cb.state, "closed")
    
    async def test_failure_reporting(self):
        """测试故障报告"""
        await self.mind.register_agent("agent_001", "worker", ["compute"])
        
        try:
            raise ValueError("Test error")
        except Exception as e:
            from ai_write_x.core.swarm_v2.self_healing import FailureType
            await self.healing.report_failure(
                "agent_001",
                FailureType.EXCEPTION,
                e,
                {"context": "testing"}
            )
        
        self.assertEqual(len(self.healing.failure_history), 1)
        self.assertEqual(self.healing.total_failures, 1)
    
    async def test_checkpoint_creation(self):
        """测试检查点创建"""
        await self.mind.register_agent("agent_001", "worker", ["compute"])
        
        checkpoint_id = await self.healing.create_checkpoint()
        self.assertIsNotNone(checkpoint_id)
        self.assertEqual(len(self.healing.checkpoints), 1)
    
    async def test_system_health(self):
        """测试系统健康查询"""
        health = self.healing.get_system_health()
        self.assertIn("status", health)
        self.assertIn("health_score", health)
        self.assertIn("agent_count", health)


class TestIntegration(unittest.IsolatedAsyncioTestCase):
    """集成测试 - 测试模块间协作"""
    
    async def asyncSetUp(self):
        self.mind = CollectiveMind()
        await self.mind.start()
        self.consensus = ConsensusProtocol(self.mind)
        self.ko = KnowledgeOrganism()
        self.healing = SelfHealing(self.mind)
        
        await asyncio.gather(
            self.consensus.start(),
            self.ko.start(),
            self.healing.start()
        )
    
    async def asyncTearDown(self):
        await self.mind.stop()
    
    async def test_full_workflow(self):
        """测试完整工作流"""
        # 1. 注册智能体
        for i in range(5):
            await self.mind.register_agent(
                f"agent_{i}",
                "researcher",
                ["search", "analysis"]
            )
        
        # 2. 提交意图
        intention = SwarmIntention(
            type=IntentionType.CONTENT_CREATION,
            source_agents=["agent_0", "agent_1"],
            payload={"topic": "AI发展趋势"}
        )
        await self.mind.submit_intention(intention)
        
        # 3. 创建知识
        knowledge_id = await self.ko.create_organism(
            {"research": "AI趋势分析", "data": ["趋势1", "趋势2"]},
            KnowledgeType.RESEARCH,
            "agent_0"
        )
        
        # 4. 提交提案
        proposal = await self.consensus.create_proposal(
            ProposalType.TASK_ALLOCATION,
            "agent_0",
            {"task": "撰写文章", "knowledge_id": knowledge_id}
        )
        
        # 5. 投票
        for i in range(3):
            await self.consensus.submit_vote(
                proposal.id, f"agent_{i}", True, weight=1.0
            )
        
        # 6. 验证状态
        stats = self.mind.get_stats()
        self.assertEqual(stats["total_agents"], 5)
        
        ko_stats = self.ko.get_population_stats()
        self.assertEqual(ko_stats["total_organisms"], 1)
        
        await asyncio.sleep(0.5)  # 等待处理
    
    async def test_emergence_detection(self):
        """测试涌现检测"""
        # 注册多个智能体并设置工作状态
        for i in range(5):
            await self.mind.register_agent(f"agent_{i}", "worker", ["compute"])
            await self.mind.update_agent_state(f"agent_{i}", {
                "status": "working",
                "current_task": f"task_{i}"
            })
        
        # 等待涌现检测
        await asyncio.sleep(6)
        
        # 应该检测到协作涌现
        patterns = self.mind.get_recent_patterns()
        self.assertGreater(len(patterns), 0)


def run_tests():
    """运行所有测试"""
    loader = unittest.TestLoader()
    suite = unittest.TestSuite()
    
    # 添加所有测试类
    suite.addTests(loader.loadTestsFromTestCase(TestCollectiveMind))
    suite.addTests(loader.loadTestsFromTestCase(TestConsensusProtocol))
    suite.addTests(loader.loadTestsFromTestCase(TestKnowledgeOrganism))
    suite.addTests(loader.loadTestsFromTestCase(TestSelfHealing))
    suite.addTests(loader.loadTestsFromTestCase(TestIntegration))
    
    # 运行测试
    runner = unittest.TextTestRunner(verbosity=2)
    result = runner.run(suite)
    
    return result.wasSuccessful()


if __name__ == "__main__":
    success = run_tests()
    sys.exit(0 if success else 1)
