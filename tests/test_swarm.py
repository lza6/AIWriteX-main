"""
蜂群系统测试
"""
import asyncio
import sys
import random
sys.path.insert(0, 'C:/Users/Administrator.DESKTOP-EGNE9ND/Desktop/AIxs/AIWriteX-main')

from src.ai_write_x.core.swarm.swarm_agent import (
    AgentNode, ReasoningAgent, CreativeAgent, ResearchAgent
)
from src.ai_write_x.core.swarm.pheromone_comm import (
    PheromoneComm, PheromoneType, get_pheromone_comm
)
from src.ai_write_x.core.swarm.role_behavior import (
    RoleBehaviorFactory, BehaviorOrchestrator
)
from src.ai_write_x.core.swarm.load_balancer import (
    LoadBalancer, LoadBalanceStrategy, TaskQueueManager
)
from src.ai_write_x.core.swarm_protocol import (
    SwarmTask, SwarmCapabilities
)


async def test_agents():
    """测试Agent"""
    print("\n=== 测试 Agent ===")
    
    # 创建不同类型Agent
    reasoning = ReasoningAgent(name="Reasoner-1")
    creative = CreativeAgent(name="Creative-1")
    research = ResearchAgent(name="Research-1")
    
    print(f"创建Agent: {reasoning}")
    print(f"能力: {[c.value for c in reasoning.capabilities]}")
    
    # 创建测试任务
    task = SwarmTask(
        description="测试任务：分析这篇新闻文章",
        required_capabilities=[SwarmCapabilities.REASONING]
    )
    
    # 执行任务
    result = await reasoning.execute(task)
    print(f"执行结果: {result['status']}")
    print(f"Agent统计: {reasoning.get_stats()}")


async def test_pheromone_comm():
    """测试信息素通信"""
    print("\n=== 测试 信息素通信 ===")
    
    comm = PheromoneComm()
    await comm.start()
    
    # 广播任务
    msg_id = await comm.broadcast_task(
        agent_id="agent-1",
        task_description="测试任务",
        required_capabilities=[SwarmCapabilities.CREATIVE_WRITING],
        location=(100, 100)
    )
    print(f"广播消息ID: {msg_id}")
    
    # 发射吸引信息素
    await comm.emit_attraction(
        agent_id="agent-1",
        target_agent_id="agent-2",
        strength=0.8,
        reason="协同工作"
    )
    
    # 共享共识
    await comm.share_consensus(
        agent_id="agent-1",
        knowledge={"key": "value", "insight": "测试知识"}
    )
    
    # 获取统计
    stats = comm.get_stats()
    print(f"通信统计: {stats}")
    
    await comm.stop()


async def test_role_behavior():
    """测试角色行为"""
    print("\n=== 测试 角色行为 ===")
    
    # 创建Agent
    agent = ReasoningAgent(name="Agent-RB")
    
    # 创建行为编排器
    orchestrator = BehaviorOrchestrator(agent)
    orchestrator.set_role("executor")
    
    print(f"角色: {orchestrator.role_behavior.role_name}")
    print(f"状态: {orchestrator.role_behavior.current_state}")
    
    # 执行行为
    for i in range(3):
        context = {"task_assigned": True, "iteration": i}
        await orchestrator.tick(context)
        await asyncio.sleep(0.1)
    
    print(f"行为统计: {orchestrator.get_stats()}")


async def test_load_balancer():
    """测试负载均衡"""
    print("\n=== 测试 负载均衡 ===")
    
    # 创建负载均衡器
    lb = LoadBalancer(strategy=LoadBalanceStrategy.HYBRID)
    
    # 注册Agent
    agents = [
        ReasoningAgent(name="Reasoner-1"),
        CreativeAgent(name="Creative-1"),
        ResearchAgent(name="Research-1")
    ]
    
    for agent in agents:
        lb.register_agent(agent)
    
    print(f"注册了 {len(agents)} 个Agent")
    
    # 选择Agent
    selected = await lb.select_agent(
        required_capabilities=[SwarmCapabilities.REASONING]
    )
    print(f"选择的Agent: {selected}")
    
    # 创建任务队列
    tqm = TaskQueueManager(lb)
    
    # 提交任务
    task = SwarmTask(
        description="测试任务",
        required_capabilities=[SwarmCapabilities.CREATIVE_WRITING]
    )
    
    agent_id = await tqm.submit_task(task, [SwarmCapabilities.CREATIVE_WRITING])
    print(f"任务分配给: {agent_id}")
    
    # 获取负载报告
    report = await lb.get_agent_load_report()
    print(f"负载报告: {report}")
    
    # 获取统计
    stats = lb.get_stats()
    print(f"负载统计: {stats}")


async def test_full_integration():
    """完整集成测试"""
    print("\n=== 完整集成测试 ===")
    
    # 1. 初始化组件
    comm = PheromoneComm()
    await comm.start()
    
    lb = LoadBalancer(strategy=LoadBalanceStrategy.HYBRID)
    tqm = TaskQueueManager(lb)
    
    # 2. 创建Agent
    agents = [
        ReasoningAgent(name="Reasoner-1"),
        ReasoningAgent(name="Reasoner-2"),
        CreativeAgent(name="Creative-1"),
        ResearchAgent(name="Research-1"),
    ]
    
    for agent in agents:
        lb.register_agent(agent)
        # 设置位置
        await comm.pheromone_space.update_agent_position(
            agent.agent_id, 
            (random.random() * 200, random.random() * 200)
        )
    
    print(f"创建 {len(agents)} 个Agent")
    
    # 3. 广播任务
    task = SwarmTask(
        description="撰写一篇科技新闻报道",
        required_capabilities=[SwarmCapabilities.CREATIVE_WRITING, SwarmCapabilities.RESEARCH]
    )
    
    await comm.broadcast_task(
        agent_id="system",
        task_description=task.description,
        required_capabilities=task.required_capabilities
    )
    
    # 4. 分配任务
    agent_id = await tqm.submit_task(task, task.required_capabilities)
    print(f"任务分配给: {agent_id}")
    
    # 等待执行
    await asyncio.sleep(0.5)
    
    # 5. 获取状态报告
    report = await lb.get_agent_load_report()
    print("\n负载报告:")
    for a in report["agents"]:
        print(f"  {a['agent_id']}: {a['load']} (成功率: {a['success_rate']})")
    
    # 6. 获取通信统计
    comm_stats = comm.get_stats()
    print(f"\n信息素统计: {comm_stats['pheromone_space']['total_pheromones']} 个信息素")
    
    # 清理
    await comm.stop()
    
    print("\n✅ 集成测试完成")


async def main():
    """主函数"""
    import random
    
    print("🧪 开始蜂群系统测试...")
    
    await test_agents()
    await test_pheromone_comm()
    await test_role_behavior()
    await test_load_balancer()
    await test_full_integration()
    
    print("\n🎉 所有测试完成!")


if __name__ == "__main__":
    asyncio.run(main())
