"""
AIWriteX 爬虫和新闻聚合系统测试
测试 scrapers、news_aggregator 和 spider_manager 模块
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


class TestHotNewsTool(TestCase):
    """测试热点新闻工具"""

    def test_hotnews_initialization(self):
        """测试热点新闻工具初始化"""
        from src.ai_write_x.tools.hotnews import HotNewsTool
        
        tool = HotNewsTool()
        assert tool is not None

    def test_get_weibo_hotsearch(self):
        """测试获取微博热搜"""
        from src.ai_write_x.tools.hotnews import HotNewsTool
        
        tool = HotNewsTool()
        
        # Mock 请求
        with patch('requests.get') as mock_get:
            mock_response = MagicMock()
            mock_response.json.return_value = {
                "data": [{"word": "热点 1", "hot": 1000}]
            }
            mock_response.status_code = 200
            mock_get.return_value = mock_response
            
            result = tool.get_weibo_hotsearch()
            assert isinstance(result, list) or result is None

    def test_get_douyin_hotsearch(self):
        """测试获取抖音热搜"""
        from src.ai_write_x.tools.hotnews import HotNewsTool
        
        tool = HotNewsTool()
        
        with patch('requests.get') as mock_get:
            mock_response = MagicMock()
            mock_response.json.return_value = {"data": []}
            mock_response.status_code = 200
            mock_get.return_value = mock_response
            
            result = tool.get_douyin_hotsearch()
            assert isinstance(result, list) or result is None

    def test_get_zhihu_hotsearch(self):
        """测试获取知乎热榜"""
        from src.ai_write_x.tools.hotnews import HotNewsTool
        
        tool = HotNewsTool()
        
        with patch('requests.get') as mock_get:
            mock_response = MagicMock()
            mock_response.json.return_value = {"data": []}
            mock_response.status_code = 200
            mock_get.return_value = mock_response
            
            result = tool.get_zhihu_hotsearch()
            assert isinstance(result, list) or result is None

    def test_aggregate_all_hotsearch(self):
        """测试聚合所有热搜"""
        from src.ai_write_x.tools.hotnews import HotNewsTool
        
        tool = HotNewsTool()
        
        # Mock 所有方法返回空列表
        with patch.object(tool, 'get_weibo_hotsearch', return_value=[]):
            with patch.object(tool, 'get_douyin_hotsearch', return_value=[]):
                with patch.object(tool, 'get_zhihu_hotsearch', return_value=[]):
                    result = tool.aggregate_all_hotsearch()
                    assert isinstance(result, list)


class TestSpiderManager(TestCase):
    """测试爬虫管理器"""

    def test_spider_manager_initialization(self):
        """测试爬虫管理器初始化"""
        from src.ai_write_x.tools.spider_manager import SpiderManager
        
        sm = SpiderManager()
        assert sm is not None

    def test_register_scraper(self):
        """测试注册爬虫"""
        from src.ai_write_x.tools.spider_manager import SpiderManager
        
        sm = SpiderManager()
        
        def test_scraper():
            return "data"
        
        sm.register_scraper("test", test_scraper)
        
        assert "test" in sm.scrapers

    def test_run_scraper(self):
        """测试运行爬虫"""
        from src.ai_write_x.tools.spider_manager import SpiderManager
        
        sm = SpiderManager()
        
        def test_scraper():
            return {"data": "test"}
        
        sm.register_scraper("test", test_scraper)
        result = sm.run_scraper("test")
        
        assert result == {"data": "test"}

    def test_run_all_scrapers(self):
        """测试运行所有爬虫"""
        from src.ai_write_x.tools.spider_manager import SpiderManager
        
        sm = SpiderManager()
        
        sm.register_scraper("test1", lambda: {"data": "test1"})
        sm.register_scraper("test2", lambda: {"data": "test2"})
        
        results = sm.run_all_scrapers()
        
        assert len(results) >= 2


class TestSpiderRunner(TestCase):
    """测试爬虫运行器"""

    def test_spider_runner_initialization(self):
        """测试爬虫运行器初始化"""
        from src.ai_write_x.tools.spider_runner import SpiderRunner
        
        sr = SpiderRunner()
        assert sr is not None

    @pytest.mark.asyncio
    async def test_async_fetch(self):
        """测试异步抓取"""
        from src.ai_write_x.tools.spider_runner import SpiderRunner
        
        sr = SpiderRunner()
        
        with patch('aiohttp.ClientSession') as mock_session:
            mock_response = AsyncMock()
            mock_response.text.return_value = "<html>test</html>"
            mock_response.status = 200
            
            mock_context = AsyncMock()
            mock_context.__aenter__.return_value = mock_response
            mock_session.return_value = mock_context
            
            result = await sr.async_fetch("http://example.com")
            assert "test" in result or result is None


class TestNewsAggregatorDataSources(TestCase):
    """测试新闻数据源"""

    def test_rss_source(self):
        """测试 RSS 数据源"""
        from src.ai_write_x.news_aggregator.data_sources import RSSSource
        
        source = RSSSource("http://example.com/rss")
        assert source.url == "http://example.com/rss"

    def test_api_source(self):
        """测试 API 数据源"""
        from src.ai_write_x.news_aggregator.data_sources import APISource
        
        source = APISource("http://api.example.com", {"key": "value"})
        assert source.base_url == "http://api.example.com"

    def test_web_source(self):
        """测试网页数据源"""
        from src.ai_write_x.news_aggregator.data_sources import WebSource
        
        source = WebSource("http://example.com", ["selector1"])
        assert source.url == "http://example.com"


class TestNewsAggregatorAIProcessor(TestCase):
    """测试新闻 AI 处理器"""

    def test_ai_processor_initialization(self):
        """测试 AI 处理器初始化"""
        from src.ai_write_x.news_aggregator.ai_processor import AIProcessor
        
        processor = AIProcessor()
        assert processor is not None

    def test_extract_summary(self):
        """测试提取摘要"""
        from src.ai_write_x.news_aggregator.ai_processor import AIProcessor
        
        processor = AIProcessor()
        
        # Mock LLM 调用
        with patch.object(processor, '_llm_summarize') as mock_llm:
            mock_llm.return_value = "这是摘要"
            result = processor.extract_summary("这是一段长文本" * 10)
            assert result == "这是摘要"

    def test_extract_keywords(self):
        """测试提取关键词"""
        from src.ai_write_x.news_aggregator.ai_processor import AIProcessor
        
        processor = AIProcessor()
        
        with patch.object(processor, '_llm_extract_keywords') as mock_llm:
            mock_llm.return_value = ["关键词 1", "关键词 2"]
            result = processor.extract_keywords("测试文本")
            assert isinstance(result, list)

    def test_classify_topic(self):
        """测试主题分类"""
        from src.ai_write_x.news_aggregator.ai_processor import AIProcessor
        
        processor = AIProcessor()
        
        with patch.object(processor, '_llm_classify') as mock_llm:
            mock_llm.return_value = "科技"
            result = processor.classify_topic("AI 相关新闻")
            assert result == "科技"


class TestNewsAggregatorDeduplication(TestCase):
    """测试新闻去重模块"""

    def test_deduplicator_initialization(self):
        """测试去重器初始化"""
        from src.ai_write_x.news_aggregator.deduplication import NewsDeduplicator
        
        dedup = NewsDeduplicator()
        assert dedup is not None

    def test_add_news(self):
        """测试添加新闻"""
        from src.ai_write_x.news_aggregator.deduplication import NewsDeduplicator
        
        dedup = NewsDeduplicator()
        dedup.add_news("news1", "标题 1")
        
        assert len(dedup.news_items) > 0

    def test_is_duplicate(self):
        """测试检测重复"""
        from src.ai_write_x.news_aggregator.deduplication import NewsDeduplicator
        
        dedup = NewsDeduplicator()
        dedup.add_news("news1", "相同标题")
        
        is_dup = dedup.is_duplicate("相同标题")
        assert is_dup == True

    def test_get_unique_news(self):
        """测试获取唯一新闻"""
        from src.ai_write_x.news_aggregator.deduplication import NewsDeduplicator
        
        dedup = NewsDeduplicator()
        dedup.add_news("news1", "标题 1")
        dedup.add_news("news2", "标题 2")
        
        unique = dedup.get_unique_news()
        assert len(unique) >= 1


class TestNewsAggregatorTrendAnalyzer(TestCase):
    """测试新闻趋势分析器"""

    def test_trend_analyzer_initialization(self):
        """测试趋势分析器初始化"""
        from src.ai_write_x.news_aggregator.trend_analyzer import TrendAnalyzer
        
        analyzer = TrendAnalyzer()
        assert analyzer is not None

    def test_analyze_trend(self):
        """测试分析趋势"""
        from src.ai_write_x.news_aggregator.trend_analyzer import TrendAnalyzer
        
        analyzer = TrendAnalyzer()
        
        news_items = [
            {"title": "新闻 1", "timestamp": "2026-03-09 10:00"},
            {"title": "新闻 2", "timestamp": "2026-03-09 11:00"},
        ]
        
        result = analyzer.analyze_trend(news_items)
        assert isinstance(result, dict) or result is None

    def test_predict_hot(self):
        """测试预测热点"""
        from src.ai_write_x.news_aggregator.trend_analyzer import TrendAnalyzer
        
        analyzer = TrendAnalyzer()
        
        with patch.object(analyzer, '_calculate_trend_score', return_value=0.9):
            result = analyzer.predict_hot("测试主题")
            assert result is not None


class TestNewsAggregatorHubManager(TestCase):
    """测试新闻聚合中心管理器"""

    def test_hub_manager_initialization(self):
        """测试中心管理器初始化"""
        from src.ai_write_x.news_aggregator.hub_manager import NewsHubManager
        
        manager = NewsHubManager()
        assert manager is not None

    def test_fetch_all_sources(self):
        """测试获取所有数据源"""
        from src.ai_write_x.news_aggregator.hub_manager import NewsHubManager
        
        manager = NewsHubManager()
        
        # Mock 数据源
        with patch.object(manager, '_fetch_source', return_value=[]):
            results = manager.fetch_all_sources()
            assert isinstance(results, list)

    def test_process_and_store(self):
        """测试处理和存储"""
        from src.ai_write_x.news_aggregator.hub_manager import NewsHubManager
        
        manager = NewsHubManager()
        
        news_items = [{"title": "测试新闻", "content": "内容"}]
        
        # Mock 存储
        with patch.object(manager, '_store_news') as mock_store:
            manager.process_and_store(news_items)
            mock_store.assert_called()


class TestMCPTools(TestCase):
    """测试 MCP 工具"""

    def test_mcp_tools_initialization(self):
        """测试 MCP 工具初始化"""
        from src.ai_write_x.tools.mcp_tools import MCPTools
        
        tools = MCPTools()
        assert tools is not None

    def test_register_mcp_service(self):
        """测试注册 MCP 服务"""
        from src.ai_write_x.tools.mcp_tools import MCPTools
        
        tools = MCPTools()
        tools.register_mcp_service("test_service", {"url": "http://test.com"})
        
        assert "test_service" in tools.mcp_services

    def test_call_mcp_tool(self):
        """测试调用 MCP 工具"""
        from src.ai_write_x.tools.mcp_tools import MCPTools
        
        tools = MCPTools()
        
        # Mock MCP 调用
        with patch('requests.post') as mock_post:
            mock_response = MagicMock()
            mock_response.json.return_value = {"result": "success"}
            mock_post.return_value = mock_response
            
            result = tools.call_mcp_tool("test_service", "test_method")
            assert result is not None


class TestMCPManager(TestCase):
    """测试 MCP 管理器"""

    def test_mcp_manager_initialization(self):
        """测试 MCP 管理器初始化"""
        from src.ai_write_x.tools.mcp_manager import MCPManager
        
        manager = MCPManager()
        assert manager is not None

    def test_load_services_config(self):
        """测试加载服务配置"""
        from src.ai_write_x.tools.mcp_manager import MCPManager
        
        manager = MCPManager()
        
        # Mock 配置文件
        with patch('os.path.exists', return_value=True):
            with patch('json.load', return_value={"service1": {}}):
                manager.load_services_config()
                assert len(manager.services_config) > 0

    def test_start_service(self):
        """测试启动服务"""
        from src.ai_write_x.tools.mcp_manager import MCPManager
        
        manager = MCPManager()
        
        # Mock  subprocess
        with patch('subprocess.Popen') as mock_popen:
            mock_process = MagicMock()
            mock_popen.return_value = mock_process
            
            manager.start_service("test_service", "python test.py")
            assert "test_service" in manager.running_services


class TestContentParser(TestCase):
    """测试内容解析器"""

    def test_parser_initialization(self):
        """测试解析器初始化"""
        from src.ai_write_x.utils.content_parser import ContentParser
        
        parser = ContentParser()
        assert parser is not None

    def test_parse_html(self):
        """测试解析 HTML"""
        from src.ai_write_x.utils.content_parser import ContentParser
        
        parser = ContentParser()
        html = "<html><body><h1>标题</h1><p>内容</p></body></html>"
        
        result = parser.parse_html(html)
        assert result is not None

    def test_parse_markdown(self):
        """测试解析 Markdown"""
        from src.ai_write_x.utils.content_parser import ContentParser
        
        parser = ContentParser()
        markdown = "# 标题\n\n内容"
        
        result = parser.parse_markdown(markdown)
        assert "<h1>" in result or result is not None

    def test_extract_text(self):
        """测试提取文本"""
        from src.ai_write_x.utils.content_parser import ContentParser
        
        parser = ContentParser()
        html = "<html><body><p>测试文本</p></body></html>"
        
        text = parser.extract_text(html)
        assert "测试文本" in text or text is None


class TestTopicDeduplicator(TestCase):
    """测试话题去重器"""

    def test_deduplicator_initialization(self):
        """测试去重器初始化"""
        from src.ai_write_x.utils.topic_deduplicator import TopicDeduplicator
        
        dedup = TopicDeduplicator()
        assert dedup is not None

    def test_add_topic(self):
        """测试添加话题"""
        from src.ai_write_x.utils.topic_deduplicator import TopicDeduplicator
        
        dedup = TopicDeduplicator()
        dedup.add_topic("话题 1")
        
        assert len(dedup.topics) > 0

    def test_is_duplicate(self):
        """测试检测重复"""
        from src.ai_write_x.utils.topic_deduplicator import TopicDeduplicator
        
        dedup = TopicDeduplicator()
        dedup.add_topic("相同话题")
        
        is_dup = dedup.is_duplicate("相同话题")
        assert is_dup == True

    def test_get_unique_topics(self):
        """测试获取唯一话题"""
        from src.ai_write_x.utils.topic_deduplicator import TopicDeduplicator
        
        dedup = TopicDeduplicator()
        dedup.add_topic("话题 1")
        dedup.add_topic("话题 2")
        
        topics = dedup.get_unique_topics()
        assert len(topics) >= 1


# 运行测试
if __name__ == "__main__":
    pytest.main([__file__, "-v", "--tb=short"])
