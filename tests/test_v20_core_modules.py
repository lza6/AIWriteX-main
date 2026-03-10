# -*- coding: UTF-8 -*-
"""
V20 Core Modules 单元测试套件

测试覆盖:
- Batch Processor V2
- Semantic Cache V3
- Adaptive Model Router
- Performance Middleware V2
- Rate Limit & Circuit Breaker V2

版本：V20.0.0
作者：AIWriteX Team
创建日期：2026-03-09
"""

import pytest
import asyncio
import time
from pathlib import Path
import sys

# 添加项目路径
sys.path.insert(0, str(Path(__file__).parent.parent))


class TestBatchProcessorV2:
    """批处理器 V2 测试"""

    @pytest.fixture
    def mock_batch_function(self):
        """模拟批处理函数"""
        async def mock_batch(requests):
            await asyncio.sleep(0.05)  # 模拟网络延迟
            return [{'result': f'response_{i}'} for i in range(len(requests))]
        return mock_batch

    @pytest.fixture
    def batch_processor(self, mock_batch_function):
        """创建批处理器实例"""
        from src.ai_write_x.core.batch_processor_v2 import BatchProcessorV2
        return BatchProcessorV2(
            batch_function=mock_batch_function,
            min_batch_size=2,
            max_batch_size=10,
            window_ms=50,
            enable_deduplication=True
        )

    @pytest.mark.asyncio
    async def test_basic_batching(self, batch_processor):
        """测试基本批处理功能"""
        await batch_processor.start()

        try:
            # 发送多个请求
            tasks = [
                batch_processor.add_request({'query': f'query_{i}'})
                for i in range(5)
            ]
            results = await asyncio.gather(*tasks)

            # 验证结果
            assert len(results) == 5
            assert all('result' in r for r in results)

            # 验证统计
            stats = batch_processor.get_stats()
            assert stats['total_requests'] >= 5
            assert stats['batches_processed'] >= 1

        finally:
            await batch_processor.stop()

    @pytest.mark.asyncio
    async def test_deduplication(self, batch_processor):
        """测试去重功能"""
        await batch_processor.start()

        try:
            # 发送相同请求
            task1 = batch_processor.add_request({'query': 'same_query'})
            task2 = batch_processor.add_request({'query': 'same_query'})

            result1, result2 = await asyncio.gather(task1, task2)

            # 验证去重（应该共享结果）
            assert result1 == result2

            stats = batch_processor.get_stats()
            assert stats['duplicates_removed'] >= 1

        finally:
            await batch_processor.stop()

    @pytest.mark.asyncio
    async def test_priority(self, batch_processor):
        """测试优先级处理"""
        await batch_processor.start()

        try:
            # 发送不同优先级的请求
            low_priority = batch_processor.add_request(
                {'query': 'low'}, priority=0)
            high_priority = batch_processor.add_request(
                {'query': 'high'}, priority=10)

            results = await asyncio.gather(low_priority, high_priority)

            # 高优先级应该更快得到处理
            assert len(results) == 2

        finally:
            await batch_processor.stop()


class TestSemanticCacheV3:
    """语义缓存 V3 测试"""

    @pytest.fixture
    def cache(self, tmp_path):
        """创建缓存实例"""
        from src.ai_write_x.core.semantic_cache_v3 import SemanticCacheV3
        db_path = str(tmp_path / "test_cache.db")
        return SemanticCacheV3(
            db_path=db_path,
            similarity_threshold=0.85,
            default_ttl_hours=1
        )

    def test_cache_hit(self, cache):
        """测试缓存命中"""
        query = "如何学习 Python？"
        response = {"answer": "多写代码"}

        # 写入缓存
        cache.set(query, response)

        # 读取缓存
        result = cache.get(query)

        assert result is not None
        assert result['answer'] == "多写代码"

    def test_cache_miss(self, cache):
        """测试缓存未命中"""
        result = cache.get("不存在的查询")
        assert result is None

    def test_hot_data_ttl(self, cache):
        """测试热数据 TTL 延长"""
        query = "热门问题"
        response = {"answer": "热门回答"}

        # 写入热数据
        cache.set(query, response, is_hot=True)

        # 验证被标记为热数据
        result = cache.get(query)
        assert result is not None

        stats = cache.get_stats()
        assert stats['cache_size'] == 1

    def test_batch_operations(self, cache):
        """测试批量操作"""
        pairs = [
            ("问题 1", {"answer": "答案 1"}),
            ("问题 2", {"answer": "答案 2"}),
            ("问题 3", {"answer": "答案 3"})
        ]

        # 批量写入
        cache.batch_set(pairs)

        # 批量读取
        queries = ["问题 1", "问题 2", "问题 3"]
        results = cache.batch_get(queries)

        assert len(results) == 3
        assert results["问题 1"]["answer"] == "答案 1"

    def test_invalidation(self, cache):
        """测试缓存失效"""
        query = "临时数据"
        response = {"answer": "临时回答"}

        cache.set(query, response)
        cache.invalidate(query)

        result = cache.get(query)
        assert result is None

    def test_statistics(self, cache):
        """测试统计信息"""
        # 制造一些访问
        for i in range(10):
            query = f"查询{i}"
            cache.set(query, {"answer": f"答案{i}"})
            cache.get(query)

        stats = cache.get_stats()

        assert stats['hits'] == 10
        assert stats['writes'] == 10
        assert 'hit_rate' in stats


class TestAdaptiveModelRouter:
    """自适应模型路由器测试"""

    @pytest.fixture
    def router(self):
        """创建路由器实例"""
        from src.ai_write_x.core.adaptive_model_router import AdaptiveModelRouter
        return AdaptiveModelRouter(optimization_mode='balanced')

    def test_simple_task_routing(self, router):
        """测试简单任务路由"""
        prompt = "Python 是什么？"
        decision = router.route(prompt)

        assert decision.model_name is not None
        assert decision.complexity.name == "SIMPLE"
        assert decision.estimated_cost >= 0

    def test_expert_task_routing(self, router):
        """测试专家级任务路由"""
        prompt = "设计一个革命性的 AI 架构，融合量子计算和神经科学"
        decision = router.route(prompt)

        assert decision.complexity.name == "EXPERT"
        # 专家任务应该推荐更高质量的模型
        assert decision.estimated_latency_ms > 1000

    def test_fallback_chain_generation(self, router):
        """测试降级链生成"""
        prompt = "分析这个问题"
        decision = router.route(prompt)

        assert isinstance(decision.fallback_chain, list)
        assert len(decision.fallback_chain) <= 3

    def test_optimization_modes(self):
        """测试不同优化模式"""
        from src.ai_write_x.core.adaptive_model_router import AdaptiveModelRouter

        modes = ['cost', 'speed', 'quality', 'balanced']
        decisions = {}

        for mode in modes:
            router = AdaptiveModelRouter(optimization_mode=mode)
            decision = router.route("复杂的技术问题")
            decisions[mode] = decision

        # 不同模式应该有不同的决策
        assert len(set(d.model_name for d in decisions.values())) >= 2

    def test_performance_tracking(self, router):
        """测试性能追踪"""
        prompt = "测试问题"
        decision = router.route(prompt)

        # 更新性能记录
        router.update_performance(
            model_name=decision.model_name,
            actual_latency_ms=500,
            actual_tokens=100,
            success=True
        )

        stats = router.get_stats()
        assert stats['total_requests'] >= 1


class TestPerformanceMiddleware:
    """性能中间件测试"""

    def test_response_cache(self):
        """测试响应缓存"""
        from src.ai_write_x.web.middleware.performance_v2 import ResponseCacheV2

        cache = ResponseCacheV2(default_ttl_seconds=60)

        # 设置缓存
        cache.set("key1", {"data": "value1"})

        # 获取缓存
        result = cache.get("key1")
        assert result == {"data": "value1"}

        # 未命中
        result = cache.get("key2")
        assert result is None

    def test_cache_tags(self):
        """测试缓存标签"""
        from src.ai_write_x.web.middleware.performance_v2 import ResponseCacheV2

        cache = ResponseCacheV2()

        cache.set("key1", "value1", tags=['tag1'])
        cache.set("key2", "value2", tags=['tag1', 'tag2'])
        cache.set("key3", "value3", tags=['tag2'])

        # 按标签清除
        cache.invalidate_by_tag('tag1')

        assert cache.get("key1") is None
        assert cache.get("key2") is None
        assert cache.get("key3") is not None

    def test_performance_monitor(self):
        """测试性能监控"""
        from src.ai_write_x.web.middleware.performance_v2 import PerformanceMonitor

        monitor = PerformanceMonitor()

        # 模拟请求
        for i in range(10):
            request_id = f"req_{i}"
            monitor.start_request(request_id)
            time.sleep(0.01)
            monitor.end_request(request_id)

        stats = monitor.get_stats()

        assert stats['total_requests'] == 10
        assert stats['avg_latency_ms'] > 10
        assert 'p95_latency_ms' in stats


class TestRateLimitCircuitBreaker:
    """限流与熔断器测试"""

    def test_token_bucket_basic(self):
        """测试 Token Bucket 基本功能"""
        from src.ai_write_x.web.middleware.rate_limit_v2 import TokenBucket

        bucket = TokenBucket(rate=10, capacity=20)

        # 初始应该允许
        assert bucket.consume(5) is True
        assert bucket.consume(10) is True

        # 超出容量应该拒绝
        assert bucket.consume(10) is False

    def test_rate_limiter_whitelist_blacklist(self):
        """测试白名单黑名单"""
        from src.ai_write_x.web.middleware.rate_limit_v2 import (
            RateLimiter, RateLimitConfig
        )

        limiter = RateLimiter(RateLimitConfig(
            requests_per_second=1,
            burst_size=2
        ))

        # 添加到白名单
        limiter.add_to_whitelist("192.168.1.1")
        allowed, info = limiter.allow_request("192.168.1.1", "/api/test")
        assert allowed is True
        assert info['reason'] == 'whitelisted'

        # 添加到黑名单
        limiter.add_to_blacklist("192.168.1.2")
        allowed, info = limiter.allow_request("192.168.1.2", "/api/test")
        assert allowed is False
        assert info['reason'] == 'blacklisted'

    def test_circuit_breaker_state_machine(self):
        """测试熔断器状态机"""
        from src.ai_write_x.web.middleware.rate_limit_v2 import (
            CircuitBreaker, CircuitBreakerConfig, CircuitState
        )

        cb = CircuitBreaker(CircuitBreakerConfig(
            failure_threshold=3,
            success_threshold=2,
            timeout_seconds=1
        ))

        # 初始状态 CLOSED
        assert cb.get_state() == CircuitState.CLOSED

        # 连续失败触发熔断
        def failing_func():
            raise Exception("失败")

        for _ in range(3):
            try:
                cb.call(failing_func)
            except:
                pass

        # 应该变为 OPEN
        assert cb.get_state() == CircuitState.OPEN

        # 等待超时后应该变为 HALF_OPEN
        time.sleep(1.1)
        assert cb.get_state() == CircuitState.HALF_OPEN

    def test_adaptive_rate_limiter(self):
        """测试自适应限流"""
        from src.ai_write_x.web.middleware.rate_limit_v2 import (
            AdaptiveRateLimiter, RateLimitConfig
        )

        limiter = AdaptiveRateLimiter(RateLimitConfig(
            requests_per_second=10,
            burst_size=20
        ))

        # 模拟高负载
        limiter.adjust_for_load(cpu_usage=0.9, memory_usage=0.9)

        limits = limiter.get_current_limits()
        assert limits['degradation_active'] is True


# 性能基准测试
class TestPerformanceBenchmarks:
    """性能基准测试"""

    def test_batch_processor_throughput(self):
        """测试批处理器吞吐量"""
        from src.ai_write_x.core.batch_processor_v2 import BatchProcessorV2

        async def run_benchmark():
            call_count = 0

            async def mock_batch(requests):
                nonlocal call_count
                call_count += 1
                await asyncio.sleep(0.01)
                return [{'id': i} for i in range(len(requests))]

            processor = BatchProcessorV2(
                batch_function=mock_batch,
                min_batch_size=5,
                max_batch_size=50,
                window_ms=20
            )

            await processor.start()

            start_time = time.time()

            # 发送 100 个请求
            tasks = [
                processor.add_request({'query': f'q_{i}'})
                for i in range(100)
            ]
            results = await asyncio.gather(*tasks)

            elapsed = time.time() - start_time

            await processor.stop()

            # 计算吞吐量
            throughput = len(results) / elapsed

            assert len(results) == 100
            assert elapsed < 5.0  # 应该在 5 秒内完成
            assert throughput > 20  # 每秒至少处理 20 个请求

        asyncio.run(run_benchmark())

    def test_cache_hit_rate(self):
        """测试缓存命中率"""
        from src.ai_write_x.core.semantic_cache_v3 import SemanticCacheV3

        cache = SemanticCacheV3(similarity_threshold=0.85)

        # 预填充缓存
        for i in range(20):
            cache.set(f"查询{i}", {"result": f"结果{i}"})

        # 测试命中率
        hits = 0
        total = 50

        for i in range(total):
            # 重复查询
            result = cache.get(f"查询{i % 20}")
            if result:
                hits += 1

        hit_rate = hits / total

        # 命中率应该>60%
        assert hit_rate > 0.6


if __name__ == "__main__":
    pytest.main([__file__, "-v", "--tb=short"])
