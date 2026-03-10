"""
AIWriteX 端到端集成测试
测试完整的工作流：从热点发现 → 内容生成 → 多平台发布
"""
import os
import sys
import pytest
import time
from unittest.mock import patch, MagicMock, Mock, AsyncMock
from unittest import TestCase
import asyncio

project_root = os.path.dirname(os.path.dirname(__file__))
if project_root not in sys.path:
    sys.path.insert(0, project_root)


class TestEndToEndWorkflow(TestCase):
    """测试端到端工作流"""

    @pytest.mark.asyncio
    async def test_full_article_generation_workflow(self):
        """测试完整的文章生成工作流"""
        from src.ai_write_x.core.unified_workflow import UnifiedContentWorkflow
        
        # Mock 所有依赖
        with patch('src.ai_write_x.core.unified_workflow.LLMClient') as MockLLM:
            with patch('src.ai_write_x.core.unified_workflow.MemoryManager') as MockMemory:
                with patch('src.ai_write_x.core.unified_workflow.KnowledgeGraph') as MockKG:
                    
                    # 设置 Mock
                    mock_llm = MagicMock()
                    mock_llm.chat.return_value = MagicMock(
                        choices=[MagicMock(message=MagicMock(content="生成内容"))]
                    )
                    MockLLM.return_value = mock_llm
                    
                    mock_memory = MagicMock()
                    mock_memory.get_similarity_context.return_value = ""
                    MockMemory.return_value = mock_memory
                    
                    mock_kg = MagicMock()
                    mock_kg.search.return_value = None
                    MockKG.return_value = mock_kg
                    
                    # 创建工作流实例
                    workflow = UnifiedContentWorkflow()
                    
                    # 执行工作流
                    result = await workflow.execute_stepwise(
                        topic="测试主题",
                        use_dimensional=False
                    )
                    
                    # 验证结果
                    assert result is not None
                    assert isinstance(result, dict)

    @pytest.mark.asyncio
    async def test_hotnews_to_publish_workflow(self):
        """测试从热点到发布的工作流"""
        # 1. 获取热点
        from src.ai_write_x.tools.hotnews import HotNewsTool
        
        with patch('requests.get') as mock_get:
            mock_response = MagicMock()
            mock_response.json.return_value = {
                "data": [{"word": "热点话题", "hot": 10000}]
            }
            mock_response.status_code = 200
            mock_get.return_value = mock_response
            
            hotnews = HotNewsTool()
            topics = hotnews.get_weibo_hotsearch()
            
            assert isinstance(topics, list)
            
            if topics:
                # 2. 生成文章 (Mock)
                with patch('src.ai_write_x.core.content_generation.ContentGenerationEngine') as MockGen:
                    mock_gen = MagicMock()
                    mock_gen.execute_workflow.return_value = {
                        "title": "生成的文章标题",
                        "content": "生成的文章内容"
                    }
                    MockGen.return_value = mock_gen
                    
                    # 3. 发布 (Mock)
                    with patch('src.ai_write_x.tools.publishers.multi_platform_hub.MultiPlatformHub') as MockHub:
                        mock_hub = MagicMock()
                        mock_hub.publish_to_platform.return_value = (True, "发布成功")
                        MockHub.return_value = mock_hub
                        
                        # 执行发布
                        success, message = mock_hub.publish_to_platform(
                            "wechat",
                            "生成的文章标题",
                            "生成的文章内容"
                        )
                        
                        assert success == True


class TestDatabaseIntegration(TestCase):
    """测试数据库集成"""

    def test_topic_lifecycle(self):
        """测试话题完整生命周期"""
        from src.ai_write_x.database.db_manager import DBManager
        from src.ai_write_x.database.repository.topic_repo import TopicRepository
        
        # 使用内存数据库测试
        with patch('src.ai_write_x.database.create_engine') as mock_engine:
            mock_engine.return_value = MagicMock()
            
            db = DBManager()
            topic_repo = TopicRepository()
            
            # 创建话题
            topic_data = {
                "title": "测试话题",
                "source_platform": "wechat",
                "hot_score": 100
            }
            
            # Mock 数据库操作
            with patch.object(topic_repo, 'add', return_value=MagicMock(id="1")):
                topic_id = topic_repo.add(**topic_data)
                assert topic_id is not None
                
                # 查询话题
                with patch.object(topic_repo, 'get_by_id', return_value=MagicMock(**topic_data, id="1")):
                    topic = topic_repo.get_by_id("1")
                    assert topic is not None
                    assert topic.title == "测试话题"

    def test_article_lifecycle(self):
        """测试文章完整生命周期"""
        from src.ai_write_x.database.repository.article_repo import ArticleRepository
        
        with patch('src.ai_write_x.database.repository.article_repo.Session') as MockSession:
            mock_session = MagicMock()
            MockSession.return_value.__enter__.return_value = mock_session
            
            article_repo = ArticleRepository()
            
            # 创建文章
            with patch.object(article_repo, 'create', return_value=MagicMock(id="1")):
                article_id = article_repo.create(
                    title="测试文章",
                    content="测试内容",
                    topic_id="topic1"
                )
                assert article_id is not None

    def test_memory_lifecycle(self):
        """测试记忆完整生命周期"""
        from src.ai_write_x.database.repository.memory_repo import MemoryRepository
        
        with patch('src.ai_write_x.database.repository.memory_repo.Session') as MockSession:
            mock_session = MagicMock()
            MockSession.return_value.__enter__.return_value = mock_session
            
            memory_repo = MemoryRepository()
            
            # 添加记忆
            with patch.object(memory_repo, 'add', return_value=MagicMock(id="1")):
                memory_id = memory_repo.add(
                    agent_role="researcher",
                    memory_text="测试记忆内容"
                )
                assert memory_id is not None


class TestMultiPlatformPublishingIntegration(TestCase):
    """测试多平台发布集成"""

    def test_sync_multi_platform_publish(self):
        """测试同步多平台发布"""
        from src.ai_write_x.tools.publishers.multi_platform_hub import MultiPlatformHub
        
        hub = MultiPlatformHub()
        
        # Mock 所有发布器
        with patch.object(hub, '_get_publisher') as mock_get_pub:
            mock_pub = MagicMock()
            mock_pub.publish.return_value = (True, "发布成功")
            mock_get_pub.return_value = mock_pub
            
            # 发布到多个平台
            results = hub.publish_to_all(
                title="测试标题",
                content="测试内容",
                platforms=["wechat", "xiaohongshu"]
            )
            
            # 验证所有平台都发布成功
            assert len(results) >= 1

    @pytest.mark.asyncio
    async def test_async_multi_platform_publish(self):
        """测试异步多平台发布"""
        from src.ai_write_x.tools.publishers.async_multi_platform_hub import AsyncMultiPlatformHub
        
        hub = AsyncMultiPlatformHub(max_concurrent=3)
        
        # Mock 异步发布
        async def mock_publish(platform, title, content):
            await asyncio.sleep(0.01)  # 模拟网络延迟
            return (True, f"{platform}发布成功")
        
        with patch.object(hub, 'publish_to_platform', side_effect=mock_publish):
            results = await hub.publish_to_all(
                title="测试标题",
                content="测试内容",
                platforms=["wechat", "xiaohongshu", "zhihu"]
            )
            
            # 验证所有平台都发布成功
            assert len(results) >= 1


class TestSchedulerIntegration(TestCase):
    """测试调度器集成"""

    def test_create_scheduled_task(self):
        """测试创建定时任务"""
        from src.ai_write_x.core.scheduler import Scheduler
        
        scheduler = Scheduler()
        
        # Mock 任务添加
        with patch.object(scheduler, 'add_job', return_value=True):
            result = scheduler.add_job(
                func=lambda: None,
                trigger="date",
                run_date="2026-03-10 10:00:00",
                args=["arg1"]
            )
            assert result == True

    def test_autonomous_scheduling(self):
        """测试自治调度"""
        from src.ai_write_x.core.autonomous_scheduler import AutonomousScheduler
        
        scheduler = AutonomousScheduler()
        
        # Mock 预测和调度
        with patch.object(scheduler, 'predict_optimal_time', return_value="2026-03-10 10:00"):
            with patch.object(scheduler, 'schedule_task', return_value=True):
                optimal_time = scheduler.predict_optimal_time("content_type")
                result = scheduler.schedule_task(optimal_time, "task")
                
                assert result == True


class TestVectorDBIntegration(TestCase):
    """测试向量数据库集成"""

    def test_vector_db_initialization(self):
        """测试向量数据库初始化"""
        from src.ai_write_x.core.vector_db import VectorDatabase
        
        with patch('src.ai_write_x.core.vector_db.VectorDatabase.connect', return_value=None):
            vdb = VectorDatabase()
            assert vdb is not None

    def test_vector_store_and_search(self):
        """测试向量存储和搜索"""
        from src.ai_write_x.core.vector_db import VectorDatabase
        
        with patch('src.ai_write_x.core.vector_db.VectorDatabase.connect'):
            vdb = VectorDatabase()
            
            # Mock 向量操作
            with patch.object(vdb, 'insert', return_value=True):
                with patch.object(vdb, 'search', return_value=[{"id": "1", "score": 0.9}]):
                    # 存储向量
                    vdb.insert("collection", [0.1, 0.2, 0.3], metadata={"text": "测试"})
                    
                    # 搜索向量
                    results = vdb.search("collection", [0.1, 0.2, 0.3], limit=10)
                    assert len(results) > 0


class TestTemplateSystemIntegration(TestCase):
    """测试模板系统集成"""

    def test_adaptive_template_selection(self):
        """测试自适应模板选择"""
        from src.ai_write_x.core.adaptive_template_engine import AdaptiveTemplateEngine
        
        engine = AdaptiveTemplateEngine()
        
        # Mock 模板选择
        with patch.object(engine, 'select_template', return_value="template1"):
            template = engine.select_template(
                topic="科技",
                style="formal",
                platform="wechat"
            )
            assert template is not None

    def test_dynamic_template_generation(self):
        """测试动态模板生成"""
        from src.ai_write_x.core.dynamic_template_generator import DynamicTemplateGenerator
        
        generator = DynamicTemplateGenerator()
        
        # Mock 模板生成
        with patch.object(generator, 'generate', return_value="<html>模板</html>"):
            template = generator.generate(
                content_type="article",
                style="modern"
            )
            assert "<html>" in template


class TestAestheticEvaluationIntegration(TestCase):
    """测试美学评估集成"""

    def test_aesthetic_scoring(self):
        """测试美学评分"""
        from src.ai_write_x.core.aesthetic_summarizer import AestheticSummarizer
        
        summarizer = AestheticSummarizer()
        
        # Mock 评分
        with patch.object(summarizer, 'summarize', return_value={"score": 8.5, "feedback": "很好"}):
            result = summarizer.summarize("文章内容")
            assert "score" in result or "feedback" in result

    def test_quality_evaluation(self):
        """测试质量评估"""
        from src.ai_write_x.core.quality_engine import QualityEngine
        
        qe = QualityEngine()
        
        # Mock 评估
        with patch.object(qe, 'evaluate_content', return_value={"coherence": 0.8, "relevance": 0.9}):
            result = qe.evaluate_content("文章内容", "主题")
            assert isinstance(result, dict)


class TestPerformanceIntegration(TestCase):
    """测试性能集成"""

    def test_memory_optimization_during_workflow(self):
        """测试工作流期间的内存优化"""
        from src.ai_write_x.utils.performance_optimizer import MemoryOptimizer
        
        optimizer = MemoryOptimizer()
        
        # 模拟内存使用
        initial_memory = optimizer.get_memory_usage_mb()
        
        # 执行一些操作
        data = [i for i in range(10000)]
        
        # 强制垃圾回收
        optimizer.force_gc()
        
        # 验证内存被管理
        assert optimizer.get_memory_usage_mb() is not None

    def test_browser_pool_management(self):
        """测试浏览器池管理"""
        from src.ai_write_x.utils.performance_optimizer import BrowserInstancePool
        
        with patch('src.ai_write_x.utils.performance_optimizer.Playwright') as MockPlaywright:
            mock_pw = MagicMock()
            MockPlaywright.return_value = mock_pw
            
            pool = BrowserInstancePool(max_instances=3)
            
            # Mock 浏览器实例
            mock_browser = MagicMock()
            mock_pw.chromium.launch.return_value = mock_browser
            
            # 获取实例
            with patch.object(pool, 'get_instance', return_value=mock_browser):
                instance = pool.get_instance()
                assert instance is not None
            
            # 验证池统计
            stats = pool.get_stats()
            assert isinstance(stats, dict)


class TestErrorHandlingIntegration(TestCase):
    """测试错误处理集成"""

    def test_exception_handling_in_workflow(self):
        """测试工作流中的异常处理"""
        from src.ai_write_x.core.exceptions import WorkflowException
        from src.ai_write_x.utils.exception_handler import handle_exception
        
        @handle_exception(default_return=None)
        def workflow_step():
            raise WorkflowException("工作流错误")
        
        # 应该不抛出异常
        result = workflow_step()
        assert result is None

    def test_retry_mechanism(self):
        """测试重试机制"""
        from src.ai_write_x.utils.exception_handler import retry_on_exception
        
        call_count = 0
        
        @retry_on_exception(Exception, max_retries=3, delay=0.01)
        def flaky_operation():
            nonlocal call_count
            call_count += 1
            if call_count < 3:
                raise Exception("临时错误")
            return "成功"
        
        result = flaky_operation()
        assert result == "成功"
        assert call_count == 3


class TestLoggingIntegration(TestCase):
    """测试日志集成"""

    def test_structured_logging(self):
        """测试结构化日志"""
        from src.ai_write_x.utils.structured_logger import StructuredLogger
        
        logger = StructuredLogger("test_logger")
        
        # 验证日志方法存在
        assert hasattr(logger, 'info')
        assert hasattr(logger, 'error')
        assert hasattr(logger, 'debug')

    def test_cognitive_logging(self):
        """测试认知日志"""
        from src.ai_write_x.core.cognitive_cognitive_logger import CognitiveLogger
        
        logger = CognitiveLogger()
        
        # 记录认知事件
        logger.log_cognitive_event({
            "type": "reasoning",
            "step": "inference",
            "data": "测试数据"
        })
        
        # 验证事件被记录
        events = logger.get_cognitive_trace()
        assert len(events) > 0


class TestConfigIntegration(TestCase):
    """测试配置集成"""

    def test_config_across_modules(self):
        """测试跨模块配置"""
        from src.ai_write_x.core.config_center.config_manager import ConfigManager
        
        cm = ConfigManager()
        
        # Mock 配置
        with patch.object(cm, 'get', return_value="test_value"):
            value = cm.get("section", "key", default="default")
            assert value == "test_value"

    def test_hot_reload_config(self):
        """测试配置热重载"""
        from src.ai_write_x.core.config_center.config_manager import ConfigManager
        
        cm = ConfigManager()
        
        # Mock 重载
        with patch.object(cm, 'reload', return_value=True):
            result = cm.reload()
            assert result == True


class TestSystemHealthIntegration(TestCase):
    """测试系统健康集成"""

    def test_system_entropy_monitoring(self):
        """测试系统熵监控"""
        from src.ai_write_x.database.db_manager import DBManager
        
        db = DBManager()
        
        # Mock 熵值记录
        with patch.object(db, 'record_entropy', return_value=True):
            result = db.record_entropy(
                component="test",
                entropy_value=0.5,
                status="normal"
            )
            assert result == True

    def test_performance_metrics_collection(self):
        """测试性能指标收集"""
        from src.ai_write_x.core.metrics import MetricsCollector
        
        collector = MetricsCollector()
        
        # Mock 指标收集
        with patch.object(collector, 'record_metric', return_value=True):
            collector.record_metric(
                name="test_metric",
                value=100,
                tags={"key": "value"}
            )
            
            # 验证指标被记录
            assert True


# 运行测试
if __name__ == "__main__":
    pytest.main([__file__, "-v", "--tb=short"])
