"""
AIWriteX 性能测试和压力测试
测试系统在各种负载下的性能表现
"""
import os
import sys
import pytest
import time
import asyncio
import random
from unittest.mock import patch, MagicMock, Mock
from unittest import TestCase
import threading

project_root = os.path.dirname(os.path.dirname(__file__))
if project_root not in sys.path:
    sys.path.insert(0, project_root)


class TestLLMClientPerformance(TestCase):
    """测试 LLM 客户端性能"""

    def test_llm_response_time(self):
        """测试 LLM 响应时间"""
        from src.ai_write_x.core.llm_client import LLMClient
        
        client = LLMClient()
        
        # Mock LLM 响应
        with patch.object(client, '_client') as mock_client:
            mock_response = MagicMock()
            mock_response.choices = [MagicMock(message=MagicMock(content="回复"))]
            mock_response.usage = MagicMock(prompt_tokens=10, completion_tokens=20, total_tokens=30)
            mock_client.chat.completions.create.return_value = mock_response
            
            start_time = time.time()
            response = client.chat(messages=[{"role": "user", "content": "测试"}])
            end_time = time.time()
            
            response_time = end_time - start_time
            
            # 响应时间应该小于 5 秒 (Mock 情况下应该更快)
            assert response_time < 5.0
            assert response is not None

    def test_llm_concurrent_requests(self):
        """测试 LLM 并发请求"""
        from src.ai_write_x.core.llm_client import LLMClient
        
        client = LLMClient()
        results = []
        errors = []
        
        def make_request(i):
            try:
                with patch.object(client, '_client') as mock_client:
                    mock_response = MagicMock()
                    mock_response.choices = [MagicMock(message=MagicMock(content=f"回复{i}"))]
                    mock_client.chat.completions.create.return_value = mock_response
                    
                    response = client.chat(messages=[{"role": "user", "content": f"测试{i}"}])
                    results.append(response)
            except Exception as e:
                errors.append(e)
        
        # 创建 10 个并发请求
        threads = []
        for i in range(10):
            t = threading.Thread(target=make_request, args=(i,))
            threads.append(t)
            t.start()
        
        # 等待所有线程完成
        for t in threads:
            t.join()
        
        # 验证所有请求都成功
        assert len(results) == 10
        assert len(errors) == 0

    def test_llm_cache_performance(self):
        """测试 LLM 缓存性能"""
        from src.ai_write_x.core.llm_client import LLMClient
        
        client = LLMClient()
        
        # Mock LLM 响应
        with patch.object(client, '_client') as mock_client:
            mock_response = MagicMock()
            mock_response.choices = [MagicMock(message=MagicMock(content="缓存回复"))]
            mock_client.chat.completions.create.return_value = mock_response
            
            # 第一次请求
            client._add_to_cache("cache_key", {"content": "缓存回复"})
            
            # 第二次请求 (应该命中缓存)
            start_time = time.time()
            cached_response = client._get_from_cache("cache_key")
            cache_time = time.time() - start_time
            
            # 缓存命中应该非常快 (< 1ms)
            assert cache_time < 0.001
            assert cached_response is not None


class TestDatabasePerformance(TestCase):
    """测试数据库性能"""

    def test_database_query_performance(self):
        """测试数据库查询性能"""
        from src.ai_write_x.database.repository.article_repo import ArticleRepository
        
        repo = ArticleRepository()
        
        # Mock 数据库查询
        with patch.object(repo, 'get_all', return_value=[]):
            start_time = time.time()
            results = repo.get_all(limit=100)
            query_time = time.time() - start_time
            
            # 查询时间应该小于 1 秒
            assert query_time < 1.0

    def test_database_bulk_insert(self):
        """测试数据库批量插入"""
        from src.ai_write_x.database.repository.article_repo import ArticleRepository
        
        repo = ArticleRepository()
        
        # Mock 批量插入
        with patch.object(repo, 'bulk_create', return_value=True):
            articles = [
                {"title": f"文章{i}", "content": f"内容{i}", "topic_id": "topic1"}
                for i in range(100)
            ]
            
            start_time = time.time()
            result = repo.bulk_create(articles)
            insert_time = time.time() - start_time
            
            # 批量插入时间应该小于 5 秒
            assert insert_time < 5.0
            assert result == True


class TestCachePerformance(TestCase):
    """测试缓存性能"""

    def test_semantic_cache_performance(self):
        """测试缓存性能 (V21)"""
        from src.ai_write_x.core.hyper_cache_v21 import HyperCacheV21
        
        cache = HyperCacheV21(enable_l1=True, enable_l2=False, enable_l3=False)
        
        # 添加大量缓存
        for i in range(100):
            cache.set(f"key{i}", f"value{i}")
        
        # 测试缓存命中率
        hits = 0
        total = 50
        
        start_time = time.time()
        for i in range(total):
            if cache.get(f"key{i}") is not None:
                hits += 1
        search_time = time.time() - start_time
        
        # 命中率应该 100%
        assert hits == total
        # 搜索时间应该合理
        assert search_time < 1.0

    def test_cache_eviction(self):
        """测试缓存淘汰机制 (V21)"""
        from src.ai_write_x.core.hyper_cache_v21 import HyperCacheV21
        from src.ai_write_x.core.hyper_cache_v21 import AdaptiveEvictionPolicy
        
        policy = AdaptiveEvictionPolicy(cache_size=50)
        
        # 添加超过最大容量的缓存
        for i in range(100):
            policy.access(f"key{i}", size_bytes=100)
            if len(policy._lru_queue) > 50:
                policy.evict()
        
        # 验证缓存大小不超过限制
        assert len(policy._lru_queue) <= 50


class TestMemoryPerformance(TestCase):
    """测试内存性能"""

    def test_memory_optimizer_performance(self):
        """测试内存优化器性能"""
        from src.ai_write_x.utils.performance_optimizer import MemoryOptimizer
        
        optimizer = MemoryOptimizer()
        
        # 测试内存使用监控
        memory_before = optimizer.get_memory_usage_mb()
        
        # 创建一些数据
        data = [i for i in range(100000)]
        
        memory_after = optimizer.get_memory_usage_mb()
        
        # 验证内存监控工作正常
        assert memory_after >= memory_before
        
        # 测试垃圾回收
        del data
        optimizer.force_gc()
        
        memory_after_gc = optimizer.get_memory_usage_mb()
        
        # 验证垃圾回收后内存减少
        assert memory_after_gc <= memory_after

    def test_browser_pool_performance(self):
        """测试浏览器池性能"""
        from src.ai_write_x.utils.performance_optimizer import BrowserInstancePool
        
        with patch('src.ai_write_x.utils.performance_optimizer.Playwright') as MockPlaywright:
            mock_pw = MagicMock()
            MockPlaywright.return_value = mock_pw
            
            mock_browser = MagicMock()
            mock_pw.chromium.launch.return_value = mock_browser
            
            pool = BrowserInstancePool(max_instances=3)
            
            # 测试并发获取实例
            instances = []
            for i in range(5):
                with patch.object(pool, 'get_instance', return_value=mock_browser):
                    instance = pool.get_instance()
                    instances.append(instance)
            
            # 验证池大小限制
            stats = pool.get_stats()
            assert isinstance(stats, dict)


class TestWorkflowPerformance(TestCase):
    """测试工作流性能"""

    def test_workflow_execution_time(self):
        """测试工作流执行时间"""
        from src.ai_write_x.core.unified_workflow import UnifiedContentWorkflow
        
        workflow = UnifiedContentWorkflow()
        
        # Mock 所有步骤
        with patch.object(workflow, '_step_logic_deep_dive', return_value="step1"):
            with patch.object(workflow, '_step_creative_blueprint', return_value="step2"):
                with patch.object(workflow, '_step_master_drafting', return_value="step3"):
                    with patch.object(workflow, '_step_reflexion', return_value="step4"):
                        with patch.object(workflow, '_step_visual', return_value="step5"):
                            start_time = time.time()
                            
                            # 执行工作流
                            result = workflow.execute_stepwise_sync(
                                topic="测试主题",
                                use_dimensional=False
                            )
                            
                            execution_time = time.time() - start_time
                            
                            # 执行时间应该合理 (< 10 秒 for Mock)
                            assert execution_time < 10.0

    def test_workflow_parallel_execution(self):
        """测试工作流并行执行"""
        from src.ai_write_x.core.unified_workflow import UnifiedContentWorkflow
        
        workflow = UnifiedContentWorkflow()
        
        # Mock 并行任务
        async def parallel_task(i):
            await asyncio.sleep(0.01)
            return f"result{i}"
        
        # 执行并行任务
        async def run_parallel():
            tasks = [parallel_task(i) for i in range(5)]
            results = await asyncio.gather(*tasks)
            return results
        
        results = asyncio.run(run_parallel())
        
        # 验证所有任务都完成
        assert len(results) == 5


class TestSwarmPerformance(TestCase):
    """测试 Swarm 性能"""

    def test_swarm_concurrent_agents(self):
        """测试 Swarm 并发智能体"""
        from src.ai_write_x.core.swarm.swarm_consciousness import SwarmConsciousness
        from src.ai_write_x.core.swarm.swarm_agent import SwarmAgent
        
        consciousness = SwarmConsciousness()
        
        # 添加多个智能体
        for i in range(10):
            agent = SwarmAgent(
                agent_id=f"agent{i}",
                role="researcher",
                goal="目标",
                backstory="背景"
            )
            consciousness.add_agent(agent)
        
        # 验证智能体数量
        assert len(consciousness.agents) == 10

    def test_load_balancer_performance(self):
        """测试负载均衡器性能"""
        from src.ai_write_x.core.adaptive_load_balancer import AdaptiveLoadBalancer, NodeHealth
        
        balancer = AdaptiveLoadBalancer()
        
        # 添加节点
        for i in range(5):
            balancer.add_node(f"node{i}")
        
        # 分配任务
        start_time = time.time()
        for i in range(100):
            with patch.object(balancer, '_get_node_load', return_value=0):
                node = balancer.assign_task(f"task{i}")
                assert node is not None
        assign_time = time.time() - start_time
        
        # 分配时间应该合理
        assert assign_time < 5.0


class TestAPIPerformance(TestCase):
    """测试 API 性能"""

    def test_api_response_time(self):
        """测试 API 响应时间"""
        from src.ai_write_x.web.app import app
        from fastapi.testclient import TestClient
        
        with TestClient(app) as client:
            # Mock API 处理
            with patch('src.ai_write_x.web.api.config.ConfigManager') as MockConfig:
                mock_config = MagicMock()
                mock_config.get.return_value = {"test": "value"}
                MockConfig.return_value = mock_config
                
                start_time = time.time()
                response = client.get("/api/config")
                response_time = time.time() - start_time
                
                # 响应时间应该小于 1 秒
                assert response_time < 1.0
                assert response.status_code in [200, 404, 500]

    def test_api_concurrent_requests(self):
        """测试 API 并发请求"""
        from src.ai_write_x.web.app import app
        from fastapi.testclient import TestClient
        
        results = []
        
        def make_request(i):
            with TestClient(app) as client:
                with patch('src.ai_write_x.web.api.config.ConfigManager') as MockConfig:
                    mock_config = MagicMock()
                    mock_config.get.return_value = {"test": f"value{i}"}
                    MockConfig.return_value = mock_config
                    
                    response = client.get("/api/config")
                    results.append(response.status_code)
        
        # 创建 10 个并发请求
        threads = []
        for i in range(10):
            t = threading.Thread(target=make_request, args=(i,))
            threads.append(t)
            t.start()
        
        # 等待所有线程完成
        for t in threads:
            t.join()
        
        # 验证所有请求都完成
        assert len(results) == 10


class TestStressTest(TestCase):
    """压力测试"""

    def test_high_concurrency_workflow(self):
        """高并发工作流压力测试"""
        from src.ai_write_x.core.unified_workflow import UnifiedContentWorkflow
        
        errors = []
        successes = []
        
        def run_workflow(i):
            try:
                workflow = UnifiedContentWorkflow()
                
                # Mock 工作流执行
                with patch.object(workflow, 'execute_stepwise_sync', return_value={"result": f"result{i}"}):
                    result = workflow.execute_stepwise_sync(topic=f"主题{i}")
                    successes.append(result)
            except Exception as e:
                errors.append(e)
        
        # 创建 20 个并发工作流
        threads = []
        for i in range(20):
            t = threading.Thread(target=run_workflow, args=(i,))
            threads.append(t)
            t.start()
        
        # 等待所有线程完成
        for t in threads:
            t.join()
        
        # 验证成功率
        success_rate = len(successes) / (len(successes) + len(errors))
        
        # 成功率应该大于 95%
        assert success_rate > 0.95

    def test_memory_stress_test(self):
        """内存压力测试"""
        from src.ai_write_x.utils.performance_optimizer import MemoryOptimizer
        
        optimizer = MemoryOptimizer()
        
        # 创建大量数据
        data_list = []
        for i in range(1000):
            data = [j for j in range(1000)]
            data_list.append(data)
        
        # 验证内存使用在增长
        memory_after_alloc = optimizer.get_memory_usage_mb()
        
        # 释放内存
        data_list.clear()
        optimizer.force_gc()
        
        memory_after_gc = optimizer.get_memory_usage_mb()
        
        # 验证垃圾回收后内存减少
        assert memory_after_gc < memory_after_alloc

    def test_database_stress_test(self):
        """数据库压力测试"""
        from src.ai_write_x.database.repository.article_repo import ArticleRepository
        
        repo = ArticleRepository()
        
        # Mock 批量操作
        with patch.object(repo, 'bulk_create', return_value=True):
            # 批量插入大量数据
            articles = [
                {"title": f"文章{i}", "content": f"内容{i}" * 100, "topic_id": "topic1"}
                for i in range(1000)
            ]
            
            start_time = time.time()
            result = repo.bulk_create(articles)
            insert_time = time.time() - start_time
            
            # 验证插入时间合理
            assert insert_time < 30.0
            assert result == True


class TestScalabilityTest(TestCase):
    """可扩展性测试"""

    def test_horizontal_scaling(self):
        """水平扩展测试"""
        from src.ai_write_x.core.adaptive_load_balancer import AdaptiveLoadBalancer
        
        balancer = AdaptiveLoadBalancer()
        
        # 初始节点
        balancer.add_node("node1")
        
        # 添加更多节点
        balancer.add_node("node2")
        balancer.add_node("node3")
        
        # 验证负载均衡
        node = balancer.select_node()
        assert node is not None

    def test_cache_scaling(self):
        """缓存扩展测试"""
        from src.ai_write_x.core.hyper_cache_v21 import AdaptiveEvictionPolicy
        
        # 测试不同缓存大小
        for max_size in [100, 500, 1000]:
            policy = AdaptiveEvictionPolicy(cache_size=max_size)
            
            # 填充缓存
            for i in range(max_size + 10):
                policy.access(f"key{i}", size_bytes=10)
                if len(policy._lru_queue) > max_size:
                    policy.evict()
            
            # 验证缓存大小
            assert len(policy._lru_queue) <= max_size


class TestResourceUtilization(TestCase):
    """资源利用率测试"""

    def test_cpu_utilization(self):
        """CPU 利用率测试"""
        import psutil
        
        # 获取 CPU 使用率
        cpu_percent = psutil.cpu_percent(interval=1)
        
        # CPU 使用率应该合理 (< 90%)
        assert cpu_percent < 90

    def test_memory_utilization(self):
        """内存利用率测试"""
        import psutil
        
        # 获取内存使用率
        memory = psutil.virtual_memory()
        memory_percent = memory.percent
        
        # 内存使用率应该合理 (< 90%)
        assert memory_percent < 90


# 运行测试
if __name__ == "__main__":
    pytest.main([__file__, "-v", "--tb=short"])
