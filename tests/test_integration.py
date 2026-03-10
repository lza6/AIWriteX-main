"""
AIWriteX 集成测试套件
测试模块间的协作和端到端功能
"""
import os
import sys
import pytest
import asyncio
from unittest.mock import patch, MagicMock

project_root = os.path.dirname(os.path.dirname(__file__))
if project_root not in sys.path:
    sys.path.insert(0, project_root)


@pytest.mark.integration
class TestEndToEndWorkflow:
    """测试端到端工作流"""
    
    def test_full_publish_workflow(self):
        """测试完整发布工作流"""
        from src.ai_write_x.tools.publishers.multi_platform_hub import (
            MultiPlatformHub, PlatformType
        )
        
        hub = MultiPlatformHub()
        
        # 创建任务
        task = hub.create_publish_task(
            title="集成测试标题",
            content="集成测试内容",
            images=[],
            platforms=[PlatformType.ZHIHU]
        )
        
        assert task is not None
        assert task.title == "集成测试标题"
        assert task.status == "pending"
        
    def test_hub_stats_integration(self):
        """测试Hub统计集成"""
        from src.ai_write_x.tools.publishers.multi_platform_hub import MultiPlatformHub
        from src.ai_write_x.utils.performance_optimizer import memory_optimizer, browser_pool
        
        hub = MultiPlatformHub()
        
        # 获取统计（包含性能指标）
        stats = hub.get_publish_stats()
        
        assert "performance" in stats
        assert "memory" in stats["performance"]
        assert "browser_pool" in stats["performance"]
        
    @pytest.mark.asyncio
    async def test_async_workflow(self):
        """测试异步工作流"""
        from src.ai_write_x.tools.publishers.async_multi_platform_hub import (
            AsyncMultiPlatformHub, PlatformType
        )
        
        hub = AsyncMultiPlatformHub(max_concurrent=2)
        
        # 创建任务
        task = hub.create_publish_task(
            title="异步测试",
            content="内容",
            platforms=[PlatformType.ZHIHU]
        )
        
        assert task is not None
        assert task.id is not None


@pytest.mark.integration
class TestDatabaseIntegration:
    """测试数据库集成"""
    
    def test_repository_chain(self):
        """测试仓库链"""
        from src.ai_write_x.database.repository.article_repo import ArticleRepository
        from src.ai_write_x.database.repository.topic_repo import TopicRepository
        
        with patch('src.ai_write_x.database.repository.article_repo.get_session'):
            article_repo = ArticleRepository()
            assert article_repo is not None
            
        with patch('src.ai_write_x.database.repository.topic_repo.get_session'):
            topic_repo = TopicRepository()
            assert topic_repo is not None
            
    def test_model_serialization(self):
        """测试模型序列化"""
        from src.ai_write_x.database.models import Article, Topic
        
        article = Article(
            id=1,
            title="测试文章",
            content="内容",
            platform="wechat"
        )
        
        data = article.to_dict()
        assert isinstance(data, dict)
        assert data["title"] == "测试文章"
        
        topic = Topic(
            id=1,
            title="测试话题",
            category="tech"
        )
        
        data = topic.to_dict()
        assert isinstance(data, dict)


@pytest.mark.integration
class TestPerformanceIntegration:
    """测试性能模块集成"""
    
    def test_memory_and_browser_integration(self):
        """测试内存和浏览器集成"""
        from src.ai_write_x.utils.performance_optimizer import (
            memory_optimizer,
            browser_pool,
            performance_monitor
        )
        
        # 获取内存状态
        memory_mb = memory_optimizer.get_memory_usage_mb()
        
        # 获取浏览器池状态
        pool_stats = browser_pool.get_stats()
        
        # 获取性能报告
        report = performance_monitor.get_report()
        
        assert memory_mb > 0
        assert "pool_size" in pool_stats
        assert "性能监控报告" in report
        
    def test_performance_system_lifecycle(self):
        """测试性能系统生命周期"""
        from src.ai_write_x.utils.performance_optimizer import (
            initialize_performance_system,
            shutdown_performance_system
        )
        
        with patch('src.ai_write_x.utils.performance_optimizer.memory_optimizer') as mock_mem:
            with patch('src.ai_write_x.utils.performance_optimizer.performance_monitor') as mock_mon:
                # 初始化
                initialize_performance_system()
                mock_mem.start_monitoring.assert_called_once()
                mock_mon.start.assert_called_once()
                
                # 关闭
                shutdown_performance_system()
                mock_mem.stop_monitoring.assert_called_once()
                mock_mon.stop.assert_called_once()


@pytest.mark.integration
class TestPublisherIntegration:
    """测试发布器集成"""
    
    def test_all_publishers_initialization(self):
        """测试所有发布器初始化"""
        from src.ai_write_x.tools.publishers import (
            XiaohongshuPublisher,
            DouyinPublisher,
            ZhihuPublisher,
            ToutiaoPublisher,
            BaijiahaoPublisher
        )
        
        xhs = XiaohongshuPublisher(headless=True)
        assert xhs.platform_name == "xiaohongshu"
        
        dy = DouyinPublisher(headless=True)
        assert dy.platform_name == "douyin"
        
        zh = ZhihuPublisher(headless=True)
        assert zh.platform_name == "zhihu"
        
        tt = ToutiaoPublisher(headless=True)
        assert tt.platform_name == "toutiao"
        
        bjh = BaijiahaoPublisher(headless=True)
        assert bjh.platform_name == "baijiahao"
        
    def test_multi_platform_hub_with_performance(self):
        """测试多平台Hub与性能监控集成"""
        from src.ai_write_x.tools.publishers.multi_platform_hub import MultiPlatformHub
        
        hub = MultiPlatformHub()
        
        # 创建任务
        task = hub.create_publish_task(
            title="性能集成测试",
            content="内容"
        )
        
        # 获取包含性能指标的统计
        stats = hub.get_publish_stats()
        
        assert "total_tasks" in stats
        assert "performance" in stats
        assert "memory" in stats["performance"]
        assert "process_memory_mb" in stats["performance"]["memory"]


@pytest.mark.integration
class TestUtilsIntegration:
    """测试工具模块集成"""
    
    def test_content_parser_and_utils(self):
        """测试内容解析器和工具集成"""
        from src.ai_write_x.utils.content_parser import extract_title, clean_html_tags
        from src.ai_write_x.utils.utils import sanitize_filename
        
        # 解析标题
        content = "# 测试标题\n正文"
        title = extract_title(content)
        
        # 清理HTML
        html = "<p>内容</p>"
        text = clean_html_tags(html)
        
        # 清理文件名
        filename = sanitize_filename("test/file:name.txt")
        
        assert title is not None
        assert "<p>" not in text
        assert "/" not in filename
        
    def test_topic_deduplication_chain(self):
        """测试话题去重链"""
        from src.ai_write_x.utils.topic_deduplicator import (
            calculate_similarity,
            is_duplicate,
            deduplicate_list
        )
        
        topics = ["话题A", "话题B", "话题C"]
        
        # 计算相似度
        sim = calculate_similarity("话题A", "话题B")
        
        # 检查是否重复
        is_dup = is_duplicate("话题A", topics)
        
        # 去重
        unique = deduplicate_list(topics + ["话题A"])
        
        assert 0 <= sim <= 1
        assert isinstance(is_dup, bool)
        assert isinstance(unique, list)


if __name__ == "__main__":
    pytest.main([__file__, "-v", "-m", "integration"])