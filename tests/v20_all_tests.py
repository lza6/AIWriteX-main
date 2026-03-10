# -*- coding: UTF-8 -*-
"""
V20 完整功能验证测试

运行所有测试以确保 V20 功能 100% 可运行
"""

import sys
import time
import asyncio
from pathlib import Path

# 添加项目路径
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))


def test_imports():
    """测试 1: 导入所有模块"""
    print("\n" + "="*60)
    print("测试 1: 模块导入")
    print("="*60)

    try:
        from src.ai_write_x.core.batch_processor_v2 import BatchProcessorV2
        print("✅ batch_processor_v2 导入成功")

        from src.ai_write_x.core.semantic_cache_v2 import SemanticCacheV2
        print("✅ semantic_cache_v2 导入成功")

        from src.ai_write_x.core.adaptive_model_router import AdaptiveModelRouter
        print("✅ adaptive_model_router 导入成功")

        from src.ai_write_x.web.middleware.performance_v2 import (
            ResponseCacheV2,
            gzip_middleware
        )
        print("✅ performance_v2 导入成功")

        from src.ai_write_x.web.middleware.rate_limit_v2 import (
            RateLimiter,
            CircuitBreaker
        )
        print("✅ rate_limit_v2 导入成功")

        return True
    except Exception as e:
        print(f"❌ 导入失败：{e}")
        return False


def test_batch_processor():
    """测试 2: 批处理器功能"""
    print("\n" + "="*60)
    print("测试 2: 批处理器")
    print("="*60)

    try:
        from src.ai_write_x.core.batch_processor_v2 import BatchProcessorV2

        async def mock_llm(requests):
            await asyncio.sleep(0.01)
            return [{'result': 'ok'} for _ in requests]

        processor = BatchProcessorV2(
            batch_function=mock_llm,
            min_batch_size=2,
            max_batch_size=10,
            window_ms=50
        )

        async def run_test():
            await processor.start()

            # 发送请求
            tasks = [processor.add_request(
                {'query': f'q{i}'}) for i in range(5)]
            results = await asyncio.gather(*tasks)

            assert len(results) == 5
            print(f"✅ 处理了 {len(results)} 个请求")

            stats = processor.get_stats()
            print(
                f"✅ 统计信息：{stats['total_requests']} 请求，{stats['batches_processed']} 批次")

            await processor.stop()

        asyncio.run(run_test())
        return True
    except Exception as e:
        print(f"❌ 批处理器测试失败：{e}")
        import traceback
        traceback.print_exc()
        return False


def test_semantic_cache():
    """测试 3: 语义缓存功能"""
    print("\n" + "="*60)
    print("测试 3: 语义缓存")
    print("="*60)

    try:
        from src.ai_write_x.core.semantic_cache_v2 import SemanticCacheV2

        cache = SemanticCacheV2(
            db_path="data/test_cache_verify.db"
        )

        # 清空旧数据
        cache.clear()

        # 写入缓存
        query = "Python 学习技巧"
        response = "多写代码，多看文档"

        # V2 API 使用消息列表格式
        messages = [{"role": "user", "content": query}]
        cache.set(messages, response)
        print(f"✅ 写入缓存：{query}")

        # 读取缓存
        result = cache.get(messages)
        assert result is not None
        assert isinstance(result, str)
        print(f"✅ 缓存命中：{result}")

        # 统计信息
        stats = cache.get_stats()
        print(f"✅ 统计：{stats['hits']}次命中，{stats['misses']}次未命中")

        return True
    except Exception as e:
        print(f"❌ 语义缓存测试失败：{e}")
        import traceback
        traceback.print_exc()
        return False


def test_model_router():
    """测试 4: 模型路由器功能"""
    print("\n" + "="*60)
    print("测试 4: 模型路由器")
    print("="*60)

    try:
        from src.ai_write_x.core.adaptive_model_router import AdaptiveModelRouter

        router = AdaptiveModelRouter(optimization_mode='balanced')

        # 测试简单任务
        decision1 = router.route("1+1=?")
        print(f"✅ 简单任务路由：{decision1.model_name}")

        # 测试复杂任务
        decision2 = router.route("设计量子 AI 架构")
        print(f"✅ 复杂任务路由：{decision2.model_name}")

        # 验证降级链
        assert len(decision2.fallback_chain) > 0
        print(f"✅ 降级链：{len(decision2.fallback_chain)}个备选")

        return True
    except Exception as e:
        print(f"❌ 模型路由器测试失败：{e}")
        import traceback
        traceback.print_exc()
        return False


def test_rate_limiter():
    """测试 5: 限流器功能"""
    print("\n" + "="*60)
    print("测试 5: 限流器")
    print("="*60)

    try:
        from src.ai_write_x.web.middleware.rate_limit_v2 import RateLimiter, RateLimitConfig

        limiter = RateLimiter(RateLimitConfig(
            requests_per_second=5,
            burst_size=10
        ))

        # 模拟请求
        ip = "192.168.1.100"
        allowed_count = 0
        blocked_count = 0

        for i in range(15):
            allowed, info = limiter.allow_request(ip, "/api/test")
            if allowed:
                allowed_count += 1
            else:
                blocked_count += 1

        print(f"✅ 允许：{allowed_count}，拒绝：{blocked_count}")
        assert allowed_count > 0 and blocked_count > 0

        return True
    except Exception as e:
        print(f"❌ 限流器测试失败：{e}")
        import traceback
        traceback.print_exc()
        return False


def test_circuit_breaker():
    """测试 6: 熔断器功能"""
    print("\n" + "="*60)
    print("测试 6: 熔断器")
    print("="*60)

    try:
        from src.ai_write_x.web.middleware.rate_limit_v2 import (
            CircuitBreaker,
            CircuitBreakerConfig,
            CircuitState
        )

        cb = CircuitBreaker(CircuitBreakerConfig(
            failure_threshold=3,
            success_threshold=2,
            timeout_seconds=1
        ))

        # 初始状态
        assert cb.get_state() == CircuitState.CLOSED
        print(f"✅ 初始状态：CLOSED")

        # 模拟失败
        def failing_func():
            raise Exception("失败")

        for i in range(3):
            try:
                cb.call(failing_func)
            except:
                pass

        # 应该变为 OPEN
        assert cb.get_state() == CircuitState.OPEN
        print(f"✅ 失败后状态：OPEN")

        # 等待超时
        time.sleep(1.1)

        # 应该变为 HALF_OPEN
        assert cb.get_state() == CircuitState.HALF_OPEN
        print(f"✅ 超时后状态：HALF_OPEN")

        # 成功调用
        def success_func():
            return "成功"

        cb.call(success_func)
        cb.call(success_func)

        # 恢复为 CLOSED
        assert cb.get_state() == CircuitState.CLOSED
        print(f"✅ 恢复后状态：CLOSED")

        return True
    except Exception as e:
        print(f"❌ 熔断器测试失败：{e}")
        import traceback
        traceback.print_exc()
        return False


def main():
    """主函数"""
    print("\n" + "🚀"*30)
    print("🚀 AIWriteX V20 完整功能验证")
    print("🚀"*30)

    tests = [
        ("模块导入", test_imports),
        ("批处理器", test_batch_processor),
        ("语义缓存", test_semantic_cache),
        ("模型路由器", test_model_router),
        ("限流器", test_rate_limiter),
        ("熔断器", test_circuit_breaker),
    ]

    results = []
    for name, test_func in tests:
        result = test_func()
        results.append((name, result))

    # 生成报告
    print("\n" + "="*60)
    print("📊 测试报告")
    print("="*60)

    passed = sum(1 for _, r in results if r)
    total = len(results)

    for name, result in results:
        status = "✅" if result else "❌"
        print(f"{status} {name}")

    print(f"\n总计：{passed}/{total} 通过 ({passed/total*100:.1f}%)")

    if passed == total:
        print("\n🎉 所有测试通过！V20 功能已 100% 落地！")
        return True
    else:
        print(f"\n⚠️ 有 {total - passed} 个测试失败")
        return False


if __name__ == "__main__":
    success = main()
    sys.exit(0 if success else 1)
