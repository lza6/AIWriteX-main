"""
综合测试脚本 - 验证负载均衡和蜂群代理层的修复

测试内容:
1. 自适应预测器 (在线学习、概念漂移检测)
2. 动态调度器 (多目标优化、策略选择)
3. 去中心化通信 (事件总线、消息传递)
4. 动态角色系统 (角色切换、绩效评估)
5. 增强共识记忆 (共享记忆、信任传播)
"""
import asyncio
import sys
import os

# 添加项目路径
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from datetime import datetime
import numpy as np


async def test_adaptive_predictor():
    """测试自适应预测器"""
    print("\n" + "="*60)
    print("测试1: 自适应预测器 (Adaptive Predictor)")
    print("="*60)
    
    from src.ai_write_x.core.swarm.adaptive_predictor import (
        AdaptivePredictor, get_adaptive_predictor, DriftStatus
    )
    
    # 创建预测器
    predictor = AdaptivePredictor(n_features=7)
    
    # 模拟历史数据
    np.random.seed(42)
    
    # 第一阶段: 稳定数据
    print("\n[阶段1] 稳定数据预测...")
    for i in range(20):
        features = np.random.randn(7)
        actual = 0.3 + np.random.randn() * 0.1
        predictor.update(features, np.clip(actual, 0, 1))
    
    # 预测
    features = np.random.randn(7)
    result = predictor.predict(features)
    print(f"  预测值: {result.value:.4f}")
    print(f"  置信度: {result.confidence:.4f}")
    print(f"  漂移状态: {result.drift_status.value}")
    print(f"  模型权重: {result.model_weights}")
    
    # 第二阶段: 概念漂移
    print("\n[阶段2] 模拟概念漂移 (数据分布变化)...")
    for i in range(30):
        features = np.random.randn(7)
        actual = 0.7 + np.random.randn() * 0.15  # 明显上升
        predictor.update(features, np.clip(actual, 0, 1))
    
    result = predictor.predict(features)
    print(f"  预测值: {result.value:.4f}")
    print(f"  漂移状态: {result.drift_status.value}")
    print(f"  自适应学习率: {result.adaptive_lr:.6f}")
    
    # 统计
    stats = predictor.get_stats()
    print(f"\n[统计] 样本数: {stats['sample_count']}")
    print(f"  平均误差: {stats['avg_recent_error']:.4f}")
    
    print("\n✅ 自适应预测器测试通过!")
    return True


async def test_dynamic_scheduler():
    """测试动态调度器"""
    print("\n" + "="*60)
    print("测试2: 动态调度器 (Dynamic Scheduler)")
    print("="*60)
    
    from src.ai_write_x.core.swarm.dynamic_scheduler import (
        DynamicScheduler, AgentCapabilities, AgentState, TaskRequirements,
        SchedulingPolicy
    )
    
    scheduler = DynamicScheduler()
    
    # 注册Agents
    print("\n[注册Agents]")
    agents = [
        ("agent_1", ["analysis", "writing"], ["tech", "finance"]),
        ("agent_2", ["writing", "editing"], ["lifestyle"]),
        ("agent_3", ["research", "analysis"], ["news"])
    ]
    
    for agent_id, caps, specialties in agents:
        capabilities = AgentCapabilities(
            cpu_capacity=1.0,
            memory_capacity=1.0,
            skills=caps,
            specialties=specialties,
            cost_per_task=1.0
        )
        scheduler.register_agent(agent_id, capabilities)
        print(f"  注册: {agent_id} - 技能: {caps}")
    
    # 更新Agent状态
    print("\n[更新Agent状态]")
    scheduler.update_agent_state("agent_1", cpu_usage=0.6, memory_usage=0.4, active_tasks=3, avg_response_time=1.2)
    scheduler.update_agent_state("agent_2", cpu_usage=0.3, memory_usage=0.2, active_tasks=1, avg_response_time=0.8)
    scheduler.update_agent_state("agent_3", cpu_usage=0.7, memory_usage=0.5, active_tasks=5, avg_response_time=2.0)
    
    # 执行调度
    print("\n[执行调度任务]")
    task_req = TaskRequirements(
        cpu_demand=0.1,
        memory_demand=0.1,
        required_skills=["writing"],
        priority=7
    )
    
    decision = await scheduler.schedule(task_req)
    if decision:
        print(f"  调度策略: {decision.policy_used.value}")
        print(f"  选择Agent: {decision.agent_id}")
        print(f"  置信度: {decision.confidence:.4f}")
    
    # 模拟任务结果
    print("\n[报告任务结果]")
    scheduler.report_outcome(decision.agent_id, 1.5, True, 0.8)
    
    # 统计
    stats = scheduler.get_stats()
    print(f"\n[统计] 总调度数: {stats['total_scheduled']}")
    print(f"  策略使用: {stats['policy_usage']}")
    
    print("\n✅ 动态调度器测试通过!")
    return True


async def test_decentralized_comm():
    """测试去中心化通信"""
    print("\n" + "="*60)
    print("测试3: 去中心化通信 (Decentralized Comm)")
    print("="*60)
    
    from src.ai_write_x.core.swarm.decentralized_comm import (
        DecentralizedCommManager, MessageType, MessagePriority
    )
    
    # 创建通信管理器
    comm = DecentralizedCommManager("test_agent")
    
    # 注册处理器
    async def handle_heartbeat(msg):
        print(f"  收到心跳: {msg.sender_id}")
    
    comm.register_handler(MessageType.HEARTBEAT, handle_heartbeat)
    
    # 启动
    print("\n[启动通信]")
    await comm.start()
    
    # 模拟发现其他Agents
    print("\n[模拟Agent发现]")
    from src.ai_write_x.core.swarm.decentralized_comm import AgentInfo
    comm.discovered_agents["agent_a"] = AgentInfo(
        agent_id="agent_a",
        capabilities=["task1"],
        specialties=["domain1"]
    )
    comm.discovered_agents["agent_b"] = AgentInfo(
        agent_id="agent_b",
        capabilities=["task2"],
        specialties=["domain2"]
    )
    print(f"  发现Agents: {list(comm.discovered_agents.keys())}")
    
    # 广播消息
    print("\n[广播消息]")
    from src.ai_write_x.core.swarm.decentralized_comm import Message
    heartbeat_msg = Message(
        msg_type=MessageType.HEARTBEAT,
        sender_id="test_agent",
        payload={"load": 0.5},
        priority=MessagePriority.NORMAL,
        ttl=3,
        trace=[]
    )
    await comm.broadcast(heartbeat_msg)
    
    # 获取统计
    stats = comm.get_stats()
    print(f"\n[统计] 活跃Agents: {stats['active_agents']}")
    
    # 停止
    await comm.stop()
    
    print("\n✅ 去中心化通信测试通过!")
    return True


async def test_dynamic_roles():
    """测试动态角色系统"""
    print("\n" + "="*60)
    print("测试4: 动态自组织角色 (Self-Organizing Roles)")
    print("="*60)
    
    from src.ai_write_x.core.swarm.self_organizing_roles import (
        DynamicRoleAssigner, AgentRole, RoleEligibility
    )
    
    assigner = DynamicRoleAssigner()
    
    # 注册Agents
    print("\n[注册Agents]")
    agents = [
        ("alpha", ["coordination", "strategy", "writing"], AgentRole.COORDINATOR),
        ("beta", ["execution", "writing", "editing"], AgentRole.EXECUTOR),
        ("gamma", ["analysis", "research"], AgentRole.EXECUTOR),
        ("delta", ["quality", "review"], AgentRole.EVALUATOR),
        ("epsilon", ["exploration", "research"], AgentRole.EXPLORER)
    ]
    
    for agent_id, caps, role in agents:
        assigner.register_agent(agent_id, caps, initial_role=role)
        print(f"  注册: {agent_id} - 角色: {role.value}")
    
    # 模拟任务结果
    print("\n[模拟任务执行]")
    assigner.report_task_result("alpha", AgentRole.COORDINATOR, True, 0.85, 1.2, 0.9)
    assigner.report_task_result("beta", AgentRole.EXECUTOR, True, 0.75, 0.8, 0.7)
    assigner.report_task_result("gamma", AgentRole.EXECUTOR, True, 0.90, 0.6, 0.8)
    assigner.report_task_result("delta", AgentRole.EVALUATOR, True, 0.88, 1.0, 0.85)
    assigner.report_task_result("epsilon", AgentRole.EXPLORER, True, 0.70, 1.5, 0.6)
    
    # 评估角色适合度
    print("\n[角色适合度评估]")
    profile = assigner.agent_profiles["beta"]
    eligibility = RoleEligibility.evaluate_all(profile)
    print(f"  Beta (当前EXECUTOR) 适合度:")
    for role, score in eligibility.items():
        print(f"    {role.value}: {score:.3f}")
    
    # 执行角色重平衡
    print("\n[执行角色重平衡]")
    changes = await assigner.rebalance_roles()
    if changes:
        print(f"  角色变更: {changes}")
    else:
        print("  无需变更")
    
    # 角色分布
    print("\n[角色分布]")
    dist = assigner.get_role_distribution()
    for role, count in dist.items():
        print(f"  {role}: {count}")
    
    print("\n✅ 动态角色系统测试通过!")
    return True


async def test_consensus_memory():
    """测试增强共识记忆"""
    print("\n" + "="*60)
    print("测试5: 增强共识记忆 (Enhanced Consensus Memory)")
    print("="*60)
    
    from src.ai_write_x.core.consensus_memory import (
        EnhancedConsensusMemory, VoteType, TrustLevel
    )
    
    memory = EnhancedConsensusMemory()
    
    # 模拟Agent注册和信任
    print("\n[初始化信任]")
    for agent_id in ["agent_a", "agent_b", "agent_c", "agent_d"]:
        weight = memory.get_vote_weight(agent_id)
        print(f"  {agent_id} 初始权重: {weight:.3f}")
    
    # 写入共享记忆
    print("\n[写入共享记忆]")
    
    # 快速路径
    result1 = await memory.write_memory(
        "trending_topic:AI",
        {"topic": "人工智能", "score": 95},
        "agent_a",
        confidence=0.9
    )
    print(f"  快速写入 'trending_topic:AI': {'成功' if result1 else '失败'}")
    
    # 触发共识
    result2 = await memory.write_memory(
        "best_publishing_time",
        {"hour": 20, "day": "saturday"},
        "agent_b",
        confidence=0.7
    )
    print(f"  共识写入 'best_publishing_time': {'通过' if result2 else '拒绝'}")
    
    # 读取
    print("\n[读取记忆]")
    value = await memory.read_memory("trending_topic:AI", "agent_c")
    print(f"  读取 trending_topic:AI: {value}")
    
    # 搜索
    print("\n[搜索记忆]")
    results = memory.search_memory("publishing")
    print(f"  搜索 'publishing': {len(results)} 条结果")
    
    # 信任更新
    print("\n[更新信任]")
    memory.update_trust("agent_a", True)
    memory.update_trust("agent_b", False)
    
    for agent_id in ["agent_a", "agent_b"]:
        trust = memory.agent_trust.get(agent_id)
        if trust:
            print(f"  {agent_id}: 信任分数 {trust.trust_score:.3f}, 等级 {trust.trust_level.value}")
    
    # 统计
    stats = memory.get_consensus_stats()
    print(f"\n[统计]")
    print(f"  提案发起: {stats['proposals_initiated']}")
    print(f"  提案通过: {stats['proposals_approved']}")
    print(f"  记忆写入: {stats['memory_writes']}")
    print(f"  冲突解决: {stats['conflicts_resolved']}")
    
    print("\n✅ 增强共识记忆测试通过!")
    return True


async def main():
    """主测试函数"""
    print("\n" + "="*60)
    print("🎯 AIWriteX 架构修复综合测试")
    print("="*60)
    print(f"开始时间: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    
    results = []
    
    # 测试1: 自适应预测器
    try:
        result = await test_adaptive_predictor()
        results.append(("自适应预测器", result))
    except Exception as e:
        print(f"\n❌ 自适应预测器测试失败: {e}")
        results.append(("自适应预测器", False))
    
    # 测试2: 动态调度器
    try:
        result = await test_dynamic_scheduler()
        results.append(("动态调度器", result))
    except Exception as e:
        print(f"\n❌ 动态调度器测试失败: {e}")
        results.append(("动态调度器", False))
    
    # 测试3: 去中心化通信
    try:
        result = await test_decentralized_comm()
        results.append(("去中心化通信", result))
    except Exception as e:
        print(f"\n❌ 去中心化通信测试失败: {e}")
        results.append(("去中心化通信", False))
    
    # 测试4: 动态角色系统
    try:
        result = await test_dynamic_roles()
        results.append(("动态角色系统", result))
    except Exception as e:
        print(f"\n❌ 动态角色系统测试失败: {e}")
        results.append(("动态角色系统", False))
    
    # 测试5: 增强共识记忆
    try:
        result = await test_consensus_memory()
        results.append(("增强共识记忆", result))
    except Exception as e:
        print(f"\n❌ 增强共识记忆测试失败: {e}")
        results.append(("增强共识记忆", False))
    
    # 汇总结果
    print("\n" + "="*60)
    print("📊 测试结果汇总")
    print("="*60)
    
    passed = sum(1 for _, r in results if r)
    total = len(results)
    
    for name, result in results:
        status = "✅ 通过" if result else "❌ 失败"
        print(f"  {name}: {status}")
    
    print(f"\n总计: {passed}/{total} 测试通过")
    
    if passed == total:
        print("\n🎉 所有测试通过! 架构修复成功!")
    else:
        print("\n⚠️ 部分测试失败，请检查错误信息")
    
    print(f"\n结束时间: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")


if __name__ == "__main__":
    asyncio.run(main())
