# -*- coding: UTF-8 -*-
"""
V20 性能基准测试脚本

运行方式:
    python tests/benchmark_v20.py

输出:
    - 批处理器性能测试
    - 语义缓存性能测试  
    - 模型路由器决策速度测试
    - 限流器吞吐量测试
"""

import asyncio
import time
import sys
from pathlib import Path

# 添加项目路径
sys.path.insert(0, str(Path(__file__).parent.parent))


async def benchmark_batch_processor():
    """批处理器性能基准"""
    print("\n" + "="*60)
    print("📊 批处理器 V2 性能基准测试")
    print("="*60)

    from src.ai_write_x.core.batch_processor_v2 import BatchProcessorV2

    call_count = 0

    async def mock_llm_call(requests):
        nonlocal call_count
        call_count += 1
        # 模拟真实 API 调用延迟
        await asyncio.sleep(0.05)
        return [{'result': f'batch_{call_count}_item_{i}'} for i in range(len(requests))]

    processor = BatchProcessorV2(
        batch_function=mock_llm_call,
        min_batch_size=5,
        max_batch_size=50,
        window_ms=50,
        enable_deduplication=True
    )

    await processor.start()

    # 测试不同负载
    test_sizes = [10, 50, 100, 200]

    for size in test_sizes:
        start_time = time.time()

        tasks = [
            processor.add_request({'query': f'query_{i}'}, priority=i % 3)
            for i in range(size)
        ]
        results = await asyncio.gather(*tasks)

        elapsed = time.time() - start_time

        # 计算指标
        throughput = size / elapsed
        avg_latency = (elapsed * 1000) / size

        print(f"\n请求数：{size}")
        print(f"总耗时：{elapsed:.2f}s")
        print(f"吞吐量：{throughput:.1f} req/s")
        print(f"平均延迟：{avg_latency:.1f}ms/req")
        print(f"实际批处理次数：{call_count}")
        print(f"批处理效率：{size/call_count:.1f}x 提升")

    stats = processor.get_stats()
    print(f"\n统计信息:")
    print(f"  总请求数：{stats['total_requests']}")
    print(f"  批处理批次：{stats['batches_processed']}")
    print(f"  去重数量：{stats['duplicates_removed']}")
    print(f"  错误数：{stats['errors']}")

    await processor.stop()


def benchmark_semantic_cache():
    """语义缓存性能基准"""
    print("\n" + "="*60)
    print("💾 语义缓存 V3 性能基准测试")
    print("="*60)

    from src.ai_write_x.core.semantic_cache_v3 import SemanticCacheV3

    cache = SemanticCacheV3(
        db_path="data/benchmark_cache.db",
        similarity_threshold=0.88
    )

    # 清空旧数据
    cache.clear()

    # 预填充缓存
    print("\n预填充缓存...")
    fill_start = time.time()

    for i in range(100):
        cache.set(f"测试查询{i}", {
            "answer": f"答案{i}",
            "data": "x" * 1000  # 1KB 数据
        }, is_hot=(i < 20))

    fill_elapsed = time.time() - fill_start
    print(f"填充 100 条记录耗时：{fill_elapsed:.2f}s")

    # 测试读取性能
    print("\n读取性能测试...")

    test_cases = [
        ("精确匹配", lambda: cache.get("测试查询50")),
        ("热数据读取", lambda: cache.get("测试查询10")),
        ("未命中", lambda: cache.get("不存在的查询")),
    ]

    for name, func in test_cases:
        iterations = 100

        start = time.time()
        for _ in range(iterations):
            func()
        elapsed = time.time() - start

        avg_latency = (elapsed * 1000) / iterations
        qps = iterations / elapsed

        print(f"\n{name}:")
        print(f"  平均延迟：{avg_latency:.2f}ms")
        print(f"  QPS: {qps:.1f}")

    # 批量操作测试
    print("\n批量操作测试...")
    pairs = [(f"批量{i}", {"result": f"结果{i}"}) for i in range(50)]

    start = time.time()
    cache.batch_set(pairs)
    batch_set_time = time.time() - start

    queries = [f"批量{i}" for i in range(50)]
    start = time.time()
    results = cache.batch_get(queries)
    batch_get_time = time.time() - start

    print(f"批量写入 50 条：{batch_set_time*1000:.1f}ms")
    print(f"批量读取 50 条：{batch_get_time*1000:.1f}ms")

    # 统计信息
    stats = cache.get_stats()
    print(f"\n缓存统计:")
    print(f"  命中数：{stats['hits']}")
    print(f"  未命中数：{stats['misses']}")
    print(f"  命中率：{stats['hit_rate']}")
    print(f"  缓存大小：{stats['cache_size']}")


def benchmark_model_router():
    """模型路由器性能基准"""
    print("\n" + "="*60)
    print("🎯 自适应模型路由器性能测试")
    print("="*60)

    from src.ai_write_x.core.adaptive_model_router import AdaptiveModelRouter

    router = AdaptiveModelRouter(optimization_mode='balanced')

    # 测试不同复杂度任务
    test_prompts = [
        ("简单", "1+1 等于几？"),
        ("中等", "解释一下量子力学"),
        ("高级", "设计一个分布式系统架构"),
        ("专家", "创造一个新的数学理论")
    ]

    print("\n路由决策测试:")
    for level, prompt in test_prompts:
        start = time.time()
        decision = router.route(prompt)
        elapsed = time.time() - start

        print(f"\n{level}任务:")
        print(f"  决策耗时：{elapsed*1000:.2f}ms")
        print(f"  推荐模型：{decision.model_name}")
        print(f"  预估成本：${decision.estimated_cost:.4f}")
        print(f"  预估延迟：{decision.estimated_latency_ms:.0f}ms")

    # 压力测试
    print("\n压力测试 (1000 次连续路由):")
    start = time.time()
    for i in range(1000):
        router.route(f"测试问题{i}")
    elapsed = time.time() - start

    print(f"总耗时：{elapsed:.2f}s")
    print(f"平均每次路由：{(elapsed*1000)/1000:.2f}ms")
    print(f"QPS: {1000/elapsed:.1f}")

    stats = router.get_stats()
    print(f"\n路由统计:")
    print(f"  总请求数：{stats['total_requests']}")
    print(f"  成功率：{stats['success_rate']}")
    print(f"  可用模型数：{stats['available_models']}")


def benchmark_rate_limiter():
    """限流器性能基准"""
    print("\n" + "="*60)
    print("🛡️ 限流器与熔断器性能测试")
    print("="*60)

    from src.ai_write_x.web.middleware.rate_limit_v2 import (
        RateLimiter, CircuitBreaker, RateLimitConfig, CircuitBreakerConfig
    )

    limiter = RateLimiter(RateLimitConfig(
        requests_per_second=100,
        burst_size=200,
        per_ip=True
    ))

    # 基础限流测试
    print("\n基础限流测试:")
    allowed_count = 0
    blocked_count = 0

    start = time.time()
    for i in range(500):
        allowed, info = limiter.allow_request(
            f"192.168.1.{i % 256}", "/api/test")
        if allowed:
            allowed_count += 1
        else:
            blocked_count += 1
    elapsed = time.time() - start

    print(f"总请求数：500")
    print(f"允许数：{allowed_count}")
    print(f"拒绝数：{blocked_count}")
    print(f"处理耗时：{elapsed*1000:.1f}ms")
    print(f"平均每个请求：{(elapsed*1000)/500:.2f}ms")

    # 熔断器测试
    print("\n熔断器测试:")
    cb = CircuitBreaker(CircuitBreakerConfig(
        failure_threshold=5,
        success_threshold=3,
        timeout_seconds=2
    ))

    # 模拟成功调用
    success_count = 0
    for i in range(10):
        try:
            result = cb.call(lambda: "success")
            success_count += 1
        except Exception as e:
            pass

    print(f"成功调用数：{success_count}/10")
    print(f"熔断器状态：{cb.get_state().value}")

    stats = cb.get_stats()
    print(f"熔断器统计:")
    print(f"  总调用数：{stats['total_calls']}")
    print(f"  成功数：{stats['successful_calls']}")
    print(f"  失败数：{stats['failed_calls']}")


async def run_all_benchmarks():
    """运行所有基准测试"""
    print("\n" + "🚀"*30)
    print("🚀 AIWriteX V20 性能基准测试套件")
    print("🚀"*30)

    start_time = time.time()

    # 异步测试
    await benchmark_batch_processor()

    # 同步测试
    benchmark_semantic_cache()
    benchmark_model_router()
    benchmark_rate_limiter()

    total_elapsed = time.time() - start_time

    print("\n" + "="*60)
    print("📊 总体测试结果")
    print("="*60)
    print(f"总耗时：{total_elapsed:.2f}s")
    print(f"约 {total_elapsed/60:.1f} 分钟")
    print("\n✅ 所有基准测试完成!")


if __name__ == "__main__":
    asyncio.run(run_all_benchmarks())
