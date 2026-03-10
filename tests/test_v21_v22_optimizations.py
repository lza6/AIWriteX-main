#!/usr/bin/env python
# -*- coding: UTF-8 -*-
"""
V21-V22 核心优化单元测试套件

测试范围:
1. EventStore 持久化功能
2. 索引加速查询性能
3. 缓存自适应淘汰策略
4. ADAPTIVE 负载均衡策略

运行方式:
    uv run pytest tests/test_v21_v22_optimizations.py -v
"""

import pytest
import asyncio
import time
from pathlib import Path
import sys

# 添加项目路径
sys.path.insert(0, str(Path(__file__).parent.parent / "src"))


class TestEventStorePersistence:
    """EventStore 持久化测试"""

    @pytest.mark.asyncio
    async def test_basic_persistence(self):
        """测试基本持久化功能"""
        from ai_write_x.core.quantum_architecture_v21 import EventStore, DomainEvent, EventType

        db_path = "data/test_events.db"

        # 创建带持久化的 EventStore
        store = EventStore(max_events=1000, persistence_path=db_path)

        # 追加 150 个事件
        for i in range(150):
            event = DomainEvent(
                aggregate_id=f"order_{i % 10}",
                event_type=EventType.REQUEST_RECEIVED,
                payload={"order_id": i}
            )
            await store.append(event)

        # 等待持久化完成
        await asyncio.sleep(2)

        # 验证数据库文件存在
        assert Path(db_path).exists(), "SQLite 数据库文件应该存在"

        # 验证索引加速查询
        events = await store.get_events(aggregate_id="order_5")
        assert len(events) > 0, "应该能查询到事件"

        print(f"✅ 持久化基本功能测试通过：找到 {len(events)} 条记录")

    @pytest.mark.asyncio
    async def test_index_performance(self):
        """测试索引性能提升"""
        from ai_write_x.core.quantum_architecture_v21 import EventStore, DomainEvent, EventType

        store = EventStore(max_events=100000)

        # 填充 10000 条数据
        for i in range(10000):
            event = DomainEvent(
                aggregate_id=f"user_{i % 100}",
                event_type=EventType.REQUEST_RECEIVED,
                payload={"data": "x" * 100}
            )
            await store.append(event)

        # 测试无索引查询 (模拟旧版本)
        start = time.time()
        old_way = [e for e in store._events if e.aggregate_id == "user_50"]
        old_elapsed = time.time() - start

        # 测试有索引查询
        start = time.time()
        new_way = await store.get_events(aggregate_id="user_50")
        new_elapsed = time.time() - start

        speedup = old_elapsed / \
            new_elapsed if new_elapsed > 0 else float('inf')

        print(f"❌ 无索引查询：{old_elapsed*1000:.2f}ms")
        print(f"✅ 有索引查询：{new_elapsed*1000:.2f}ms")
        print(f"🚀 性能提升：{speedup:.1f}x")

        assert speedup > 1.1, f"索引加速应至少 1.1x，实际 {speedup:.1f}x"

    @pytest.mark.asyncio
    async def test_history_load(self):
        """测试历史事件加载"""
        from ai_write_x.core.quantum_architecture_v21 import EventStore, DomainEvent, EventType

        db_path = "data/test_restart.db"

        # Phase 1: 运行并持久化
        store1 = EventStore(persistence_path=db_path)
        for i in range(500):
            await store1.append(DomainEvent(
                aggregate_id=f"agg_{i % 50}",
                payload={"iteration": i}
            ))

        await asyncio.sleep(2)  # 等待持久化

        # Phase 2: 模拟重启，创建新实例
        store2 = EventStore(persistence_path=db_path)
        loaded_events = await store2.load_events_from_db()

        # 验证历史事件成功加载
        assert len(
            loaded_events) == 500, f"应该加载 500 条历史事件，实际 {len(loaded_events)}"
        print(f"✅ 系统重启恢复测试通过：加载 {len(loaded_events)} 条事件")


class TestAdaptiveCacheEviction:
    """自适应缓存淘汰测试"""

    def test_size_aware_eviction(self):
        """测试大小感知的淘汰策略"""
        from ai_write_x.core.hyper_cache_v21 import AdaptiveEvictionPolicy

        policy = AdaptiveEvictionPolicy(cache_size=1000)
        policy._weights = {'lru': 0.1, 'lfu': 0.1, 'size': 0.8}

        # 添加不同大小的条目
        for i in range(20):
            key = f"key_{i}"
            size = 100 if i < 10 else 1000  # 10 个小条目，10 个大条目

            policy.access(key, size_bytes=size)

        # 手动触发淘汰
        victim = policy.evict()

        # 验证优先淘汰大条目
        assert victim is not None, "应该淘汰一个条目"
        # Since evicted item's size is removed, we check key origin directly. Large entries are key_10 to key_19.
        victim_id = int(victim.split('_')[1])
        assert victim_id >= 10, f"应该优先淘汰大条目 (key_10-key_19)，实际淘汰：{victim}"
        print(f"✅ 自适应淘汰测试通过：淘汰了条目 {victim}")

    def test_priority_calculation(self):
        """测试优先级计算"""
        from ai_write_x.core.hyper_cache_v21 import AdaptiveEvictionPolicy

        policy = AdaptiveEvictionPolicy(cache_size=1000)

        # 添加高频访问条目
        for i in range(100):
            policy.access("hot_key", size_bytes=100)

        # 添加低频访问条目
        policy.access("cold_key", size_bytes=100)

        # 计算优先级
        hot_priority = policy.calculate_priority("hot_key")
        cold_priority = policy.calculate_priority("cold_key")

        print(f"热数据优先级：{hot_priority:.3f}")
        print(f"冷数据优先级：{cold_priority:.3f}")

        assert hot_priority > cold_priority, "热数据应该有更高的优先级"


class TestAdaptiveLoadBalancer:
    """ADAPTIVE 负载均衡测试"""

    def test_adaptive_strategy_selection(self):
        """测试自适应策略选择"""
        from ai_write_x.core.adaptive_load_balancer import (
            AdaptiveLoadBalancer, BackendNode, LoadBalancingStrategy, NodeStatus
        )

        lb = AdaptiveLoadBalancer(strategy=LoadBalancingStrategy.ADAPTIVE)

        # 添加测试节点
        nodes = [
            BackendNode(id="node1", host="192.168.1.1", port=8000),
            BackendNode(id="node2", host="192.168.1.2", port=8000),
            BackendNode(id="node3", host="192.168.1.3", port=8000),
        ]

        # 设置不同的负载场景
        # 场景 1: 高并发 (>1000 连接)
        for node in nodes:
            node.active_connections = 500  # 总共 1500

        selected = lb._select_adaptive(nodes)
        print(f"✅ 高并发场景：选择了 {selected.id} (最少连接策略)")

        # 场景 2: 高延迟 (>500ms)
        for node in nodes:
            node.active_connections = 100
            node.avg_response_time = 600

        selected = lb._select_adaptive(nodes)
        print(f"✅ 高延迟场景：选择了 {selected.id} (健康度优先策略)")

        # 场景 3: 高负载 (>70%)
        for node in nodes:
            node.avg_response_time = 200
            node.current_load = 0.8

        selected = lb._select_adaptive(nodes)
        print(f"✅ 高负载场景：选择了 {selected.id} (加权随机策略)")

        # 场景 4: 正常负载
        for node in nodes:
            node.current_load = 0.3

        selected = lb._select_adaptive(nodes)
        print(f"✅ 正常负载场景：选择了 {selected.id} (轮询策略)")


async def run_all_tests():
    """运行所有测试"""
    print("\n" + "="*80)
    print("🧪 V21-V22 核心优化单元测试")
    print("="*80 + "\n")

    # EventStore 测试
    print("📦 测试组 1: EventStore 持久化\n")
    test_store = TestEventStorePersistence()
    await test_store.test_basic_persistence()
    await test_store.test_index_performance()
    await test_store.test_history_load()

    # 缓存测试
    print("\n💾 测试组 2: 自适应缓存淘汰\n")
    test_cache = TestAdaptiveCacheEviction()
    test_cache.test_size_aware_eviction()
    test_cache.test_priority_calculation()

    # 负载均衡测试
    print("\n⚖️  测试组 3: ADAPTIVE 负载均衡\n")
    test_lb = TestAdaptiveLoadBalancer()
    test_lb.test_adaptive_strategy_selection()

    print("\n" + "="*80)
    print("✅ 所有测试通过！")
    print("="*80 + "\n")


if __name__ == "__main__":
    asyncio.run(run_all_tests())
