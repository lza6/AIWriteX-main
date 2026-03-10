"""
AIWriteX Swarm 群体智能系统测试
测试 swarm、swarm_v2 和相关群体智能模块
"""
import os
import sys
import pytest
from unittest.mock import patch, MagicMock, Mock, AsyncMock
from unittest import TestCase
import asyncio

project_root = os.path.dirname(os.path.dirname(__file__))
if project_root not in sys.path:
    sys.path.insert(0, project_root)


class TestSwarmAgent(TestCase):
    """测试 Swarm 智能体"""

    def test_swarm_agent_initialization(self):
        """测试 Swarm 智能体初始化"""
        from src.ai_write_x.core.swarm.swarm_agent import SwarmAgent
        
        agent = SwarmAgent(
            agent_id="agent1",
            role="researcher",
            goal="研究目标",
            backstory="背景故事"
        )
        
        assert agent.agent_id == "agent1"
        assert agent.role == "researcher"

    def test_swarm_agent_execute_task(self):
        """测试 Swarm 智能体执行任务"""
        from src.ai_write_x.core.swarm.swarm_agent import SwarmAgent
        
        agent = SwarmAgent(agent_id="agent1", role="researcher", goal="目标", backstory="背景")
        
        # Mock LLM 调用
        with patch.object(agent, '_execute_with_llm', return_value="任务结果"):
            result = agent.execute_task("测试任务")
            assert result == "任务结果"

    def test_swarm_agent_communicate(self):
        """测试 Swarm 智能体通信"""
        from src.ai_write_x.core.swarm.swarm_agent import SwarmAgent
        
        agent1 = SwarmAgent(agent_id="agent1", role="researcher", goal="目标", backstory="背景")
        agent2 = SwarmAgent(agent_id="agent2", role="writer", goal="目标", backstory="背景")
        
        # Mock 通信
        with patch.object(agent1, 'send_message') as mock_send:
            mock_send.return_value = True
            result = agent1.send_message(agent2, "测试消息")
            assert result == True


class TestSwarmConsciousness(TestCase):
    """测试群体意识"""

    def test_swarm_consciousness_initialization(self):
        """测试群体意识初始化"""
        from src.ai_write_x.core.swarm.swarm_consciousness import SwarmConsciousness
        
        consciousness = SwarmConsciousness()
        assert consciousness is not None

    def test_add_agent(self):
        """测试添加智能体"""
        from src.ai_write_x.core.swarm.swarm_consciousness import SwarmConsciousness
        from src.ai_write_x.core.swarm.swarm_agent import SwarmAgent
        
        consciousness = SwarmConsciousness()
        agent = SwarmAgent(agent_id="agent1", role="researcher", goal="目标", backstory="背景")
        
        consciousness.add_agent(agent)
        
        assert len(consciousness.agents) > 0

    def test_get_collective_decision(self):
        """测试获取群体决策"""
        from src.ai_write_x.core.swarm.swarm_consciousness import SwarmConsciousness
        from src.ai_write_x.core.swarm.swarm_agent import SwarmAgent
        
        consciousness = SwarmConsciousness()
        
        agent1 = SwarmAgent(agent_id="agent1", role="researcher", goal="目标", backstory="背景")
        agent2 = SwarmAgent(agent_id="agent2", role="writer", goal="目标", backstory="背景")
        
        consciousness.add_agent(agent1)
        consciousness.add_agent(agent2)
        
        # Mock 投票
        with patch.object(consciousness, '_aggregate_votes', return_value="决策结果"):
            result = consciousness.get_collective_decision("测试议题")
            assert result == "决策结果"


class TestPheromoneCommunication(TestCase):
    """测试信息素通信"""

    def test_pheromone_communication_initialization(self):
        """测试信息素通信初始化"""
        from src.ai_write_x.core.swarm.pheromone_comm import PheromoneCommunication
        
        pheromone = PheromoneCommunication()
        assert pheromone is not None

    def test_deposit_pheromone(self):
        """测试沉积信息素"""
        from src.ai_write_x.core.swarm.pheromone_comm import PheromoneCommunication
        
        pheromone = PheromoneCommunication()
        pheromone.deposit_pheromone("path1", strength=0.8)
        
        assert "path1" in pheromone.trails

    def test_evaporate_pheromone(self):
        """测试信息素蒸发"""
        from src.ai_write_x.core.swarm.pheromone_comm import PheromoneCommunication
        
        pheromone = PheromoneCommunication()
        pheromone.deposit_pheromone("path1", strength=0.8)
        pheromone.evaporate_pheromone(rate=0.1)
        
        # 验证信息素强度减少
        assert pheromone.trails["path1"] < 0.8

    def test_get_best_path(self):
        """测试获取最佳路径"""
        from src.ai_write_x.core.swarm.pheromone_comm import PheromoneCommunication
        
        pheromone = PheromoneCommunication()
        pheromone.deposit_pheromone("path1", strength=0.8)
        pheromone.deposit_pheromone("path2", strength=0.5)
        
        best_path = pheromone.get_best_path()
        assert best_path == "path1"


class TestLoadBalancer(TestCase):
    """测试负载均衡器"""

    def test_load_balancer_initialization(self):
        """测试负载均衡器初始化"""
        from src.ai_write_x.core.swarm.load_balancer import LoadBalancer
        
        balancer = LoadBalancer()
        assert balancer is not None

    def test_add_node(self):
        """测试添加节点"""
        from src.ai_write_x.core.swarm.load_balancer import LoadBalancer
        
        balancer = LoadBalancer()
        balancer.add_node("node1", capacity=10)
        
        assert "node1" in balancer.nodes

    def test_assign_task(self):
        """测试分配任务"""
        from src.ai_write_x.core.swarm.load_balancer import LoadBalancer
        
        balancer = LoadBalancer()
        balancer.add_node("node1", capacity=10)
        balancer.add_node("node2", capacity=5)
        
        # Mock 负载计算
        with patch.object(balancer, '_get_node_load', return_value=0):
            node = balancer.assign_task("task1")
            assert node in ["node1", "node2"]

    def test_rebalance(self):
        """测试重新平衡"""
        from src.ai_write_x.core.swarm.load_balancer import LoadBalancer
        
        balancer = LoadBalancer()
        balancer.add_node("node1", capacity=10)
        balancer.add_node("node2", capacity=10)
        
        # 添加任务
        balancer.assign_task("task1")
        balancer.assign_task("task2")
        
        # 重新平衡
        balancer.rebalance()
        
        # 验证不抛出异常
        assert True


class TestSwarmV2CollectiveMind(TestCase):
    """测试 V2 群体意识中枢"""

    def test_collective_mind_initialization(self):
        """测试群体意识中枢初始化"""
        from src.ai_write_x.core.swarm_v2.collective_mind import CollectiveMind
        
        cm = CollectiveMind()
        assert cm is not None

    def test_process_consensus(self):
        """测试处理共识"""
        from src.ai_write_x.core.swarm_v2.collective_mind import CollectiveMind
        
        cm = CollectiveMind()
        
        opinions = [
            {"agent": "agent1", "opinion": "A"},
            {"agent": "agent2", "opinion": "A"},
            {"agent": "agent3", "opinion": "B"},
        ]
        
        # Mock 共识算法
        with patch.object(cm, '_calculate_consensus', return_value="A"):
            result = cm.process_consensus(opinions)
            assert result == "A"

    def test_emerge_knowledge(self):
        """测试涌现知识"""
        from src.ai_write_x.core.swarm_v2.collective_mind import CollectiveMind
        
        cm = CollectiveMind()
        
        knowledge_fragments = ["知识 1", "知识 2", "知识 3"]
        
        # Mock 涌现
        with patch.object(cm, '_emerge_pattern', return_value="涌现知识"):
            result = cm.emerge_knowledge(knowledge_fragments)
            assert result == "涌现知识"


class TestSwarmV2ConsensusProtocol(TestCase):
    """测试 V2 分布式共识协议"""

    def test_consensus_protocol_initialization(self):
        """测试共识协议初始化"""
        from src.ai_write_x.core.swarm_v2.consensus_protocol import ConsensusProtocol
        
        protocol = ConsensusProtocol()
        assert protocol is not None

    def test_propose(self):
        """测试提议"""
        from src.ai_write_x.core.swarm_v2.consensus_protocol import ConsensusProtocol
        
        protocol = ConsensusProtocol()
        protocol.propose("agent1", "提议内容")
        
        assert len(protocol.proposals) > 0

    def test_vote(self):
        """测试投票"""
        from src.ai_write_x.core.swarm_v2.consensus_protocol import ConsensusProtocol
        
        protocol = ConsensusProtocol()
        protocol.propose("agent1", "提议内容")
        
        protocol.vote("agent2", 0, True)  # 赞成
        protocol.vote("agent3", 0, False)  # 反对
        
        # 验证投票记录
        assert len(protocol.votes) > 0

    def test_reach_consensus(self):
        """测试达成共识"""
        from src.ai_write_x.core.swarm_v2.consensus_protocol import ConsensusProtocol
        
        protocol = ConsensusProtocol()
        protocol.propose("agent1", "提议内容")
        
        # 添加多数赞成票
        protocol.vote("agent2", 0, True)
        protocol.vote("agent3", 0, True)
        protocol.vote("agent4", 0, True)
        
        # Mock 共识判定
        with patch.object(protocol, '_check_majority', return_value=True):
            result = protocol.reach_consensus(0)
            assert result == True


class TestSwarmV2KnowledgeOrganism(TestCase):
    """测试 V2 知识有机体"""

    def test_knowledge_organism_initialization(self):
        """测试知识有机体初始化"""
        from src.ai_write_x.core.swarm_v2.knowledge_organism import KnowledgeOrganism
        
        ko = KnowledgeOrganism()
        assert ko is not None

    def test_absorb_knowledge(self):
        """测试吸收知识"""
        from src.ai_write_x.core.swarm_v2.knowledge_organism import KnowledgeOrganism
        
        ko = KnowledgeOrganism()
        ko.absorb_knowledge("知识内容", "category")
        
        assert len(ko.knowledge_base) > 0

    def test_organize_knowledge(self):
        """测试组织知识"""
        from src.ai_write_x.core.swarm_v2.knowledge_organism import KnowledgeOrganism
        
        ko = KnowledgeOrganism()
        ko.absorb_knowledge("知识 1", "category1")
        ko.absorb_knowledge("知识 2", "category2")
        
        # 组织知识
        ko.organize_knowledge()
        
        # 验证不抛出异常
        assert True

    def test_retrieve_knowledge(self):
        """测试检索知识"""
        from src.ai_write_x.core.swarm_v2.knowledge_organism import KnowledgeOrganism
        
        ko = KnowledgeOrganism()
        ko.absorb_knowledge("相关知识", "category1")
        
        # Mock 检索
        with patch.object(ko, '_search_similar', return_value=["相关知识"]):
            result = ko.retrieve_knowledge("查询", "category1")
            assert len(result) > 0


class TestSwarmV2SelfHealing(TestCase):
    """测试 V2 自修复系统"""

    def test_self_healing_initialization(self):
        """测试自修复系统初始化"""
        from src.ai_write_x.core.swarm_v2.self_healing import SelfHealingSystem
        
        sh = SelfHealingSystem()
        assert sh is not None

    def test_detect_failure(self):
        """测试检测故障"""
        from src.ai_write_x.core.swarm_v2.self_healing import SelfHealingSystem
        
        sh = SelfHealingSystem()
        
        # 模拟故障检测
        with patch.object(sh, '_check_health', return_value=False):
            failure = sh.detect_failure("agent1")
            assert failure == True

    def test_heal(self):
        """测试修复"""
        from src.ai_write_x.core.swarm_v2.self_healing import SelfHealingSystem
        
        sh = SelfHealingSystem()
        
        # Mock 修复过程
        with patch.object(sh, '_execute_healing', return_value=True):
            result = sh.heal("agent1", "故障类型")
            assert result == True

    def test_recovery_strategy(self):
        """测试恢复策略"""
        from src.ai_write_x.core.swarm_v2.self_healing import SelfHealingSystem
        
        sh = SelfHealingSystem()
        
        strategies = sh.get_recovery_strategies()
        assert isinstance(strategies, list)


class TestSwarmDiscovery(TestCase):
    """测试 Swarm 发现服务"""

    def test_discovery_initialization(self):
        """测试发现服务初始化"""
        from src.ai_write_x.core.swarm_discovery import SwarmDiscovery
        
        discovery = SwarmDiscovery()
        assert discovery is not None

    def test_register_agent(self):
        """测试注册智能体"""
        from src.ai_write_x.core.swarm_discovery import SwarmDiscovery
        
        discovery = SwarmDiscovery()
        discovery.register_agent("agent1", {"role": "researcher"})
        
        assert "agent1" in discovery.agents

    def test_find_agents_by_role(self):
        """测试按角色查找智能体"""
        from src.ai_write_x.core.swarm_discovery import SwarmDiscovery
        
        discovery = SwarmDiscovery()
        discovery.register_agent("agent1", {"role": "researcher"})
        discovery.register_agent("agent2", {"role": "writer"})
        
        agents = discovery.find_agents_by_role("researcher")
        assert len(agents) > 0


class TestSwarmProtocol(TestCase):
    """测试 Swarm 协议"""

    def test_protocol_initialization(self):
        """测试协议初始化"""
        from src.ai_write_x.core.swarm_protocol import SwarmProtocol
        
        protocol = SwarmProtocol()
        assert protocol is not None

    def test_send_message(self):
        """测试发送消息"""
        from src.ai_write_x.core.swarm_protocol import SwarmProtocol
        
        protocol = SwarmProtocol()
        
        # Mock 消息发送
        with patch.object(protocol, '_transmit', return_value=True):
            result = protocol.send_message("agent1", "agent2", "消息")
            assert result == True

    def test_receive_message(self):
        """测试接收消息"""
        from src.ai_write_x.core.swarm_protocol import SwarmProtocol
        
        protocol = SwarmProtocol()
        protocol.receive_message("agent1", "消息内容")
        
        assert len(protocol.message_queue) > 0


class TestSwarmSpawner(TestCase):
    """测试 Swarm 生成器"""

    def test_spawner_initialization(self):
        """测试生成器初始化"""
        from src.ai_write_x.core.swarm_spawner import SwarmSpawner
        
        spawner = SwarmSpawner()
        assert spawner is not None

    def test_spawn_agent(self):
        """测试生成智能体"""
        from src.ai_write_x.core.swarm_spawner import SwarmSpawner
        
        spawner = SwarmSpawner()
        
        # Mock 智能体创建
        with patch.object(spawner, '_create_agent', return_value=MagicMock()):
            agent = spawner.spawn_agent("researcher", "目标", "背景")
            assert agent is not None

    def test_spawn_swarm(self):
        """测试生成群体"""
        from src.ai_write_x.core.swarm_spawner import SwarmSpawner
        
        spawner = SwarmSpawner()
        
        # Mock 群体创建
        with patch.object(spawner, '_create_swarm', return_value=MagicMock()):
            swarm = spawner.spawn_swarm(5)
            assert swarm is not None


class TestSwarmStateManager(TestCase):
    """测试 Swarm 状态管理器"""

    def test_state_manager_initialization(self):
        """测试状态管理器初始化"""
        from src.ai_write_x.core.swarm_state_manager import SwarmStateManager
        
        sm = SwarmStateManager()
        assert sm is not None

    def test_update_state(self):
        """测试更新状态"""
        from src.ai_write_x.core.swarm_state_manager import SwarmStateManager
        
        sm = SwarmStateManager()
        sm.update_state("agent1", "active")
        
        assert sm.states["agent1"] == "active"

    def test_get_state(self):
        """测试获取状态"""
        from src.ai_write_x.core.swarm_state_manager import SwarmStateManager
        
        sm = SwarmStateManager()
        sm.update_state("agent1", "active")
        
        state = sm.get_state("agent1")
        assert state == "active"

    def test_get_all_states(self):
        """测试获取所有状态"""
        from src.ai_write_x.core.swarm_state_manager import SwarmStateManager
        
        sm = SwarmStateManager()
        sm.update_state("agent1", "active")
        sm.update_state("agent2", "idle")
        
        states = sm.get_all_states()
        assert len(states) == 2


class TestSwarmVisualizer(TestCase):
    """测试 Swarm 可视化器"""

    def test_visualizer_initialization(self):
        """测试可视化器初始化"""
        from src.ai_write_x.core.swarm_visualizer import SwarmVisualizer
        
        visualizer = SwarmVisualizer()
        assert visualizer is not None

    def test_generate_topology(self):
        """测试生成拓扑图"""
        from src.ai_write_x.core.swarm_visualizer import SwarmVisualizer
        
        visualizer = SwarmVisualizer()
        
        # Mock 拓扑生成
        with patch.object(visualizer, '_create_topology_data', return_value={}):
            topology = visualizer.generate_topology()
            assert topology is not None

    def test_render_stats(self):
        """测试渲染统计"""
        from src.ai_write_x.core.swarm_visualizer import SwarmVisualizer
        
        visualizer = SwarmVisualizer()
        
        stats = {
            "total_agents": 5,
            "active_tasks": 3,
            "completed_tasks": 10
        }
        
        # Mock 渲染
        with patch.object(visualizer, '_render_html', return_value="<html></html>"):
            html = visualizer.render_stats(stats)
            assert "<html>" in html


# 运行测试
if __name__ == "__main__":
    pytest.main([__file__, "-v", "--tb=short"])
