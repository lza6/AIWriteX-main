"""
AIWriteX 发布器Mock测试
使用Mock测试发布器功能，无需真实浏览器
"""
import os
import sys
import pytest
from unittest.mock import patch, MagicMock, mock_open, PropertyMock

project_root = os.path.dirname(os.path.dirname(__file__))
if project_root not in sys.path:
    sys.path.insert(0, project_root)


class TestBasePublisher:
    """测试基础发布器"""
    
    def test_publisher_initialization(self):
        """测试发布器初始化"""
        from src.ai_write_x.tools.publishers.base_publisher import PlaywrightPublisher
        
        class TestPublisher(PlaywrightPublisher):
            def publish(self, title, content, images=None, **kwargs):
                return True, "test"
        
        publisher = TestPublisher("test_platform", headless=True)
        assert publisher.platform_name == "test_platform"
        assert publisher.headless == True
        
    def test_cookie_file_path(self):
        """测试Cookie文件路径"""
        from src.ai_write_x.tools.publishers.base_publisher import PlaywrightPublisher
        
        class TestPublisher(PlaywrightPublisher):
            def publish(self, title, content, images=None, **kwargs):
                return True, "test"
        
        publisher = TestPublisher("test_platform")
        assert "test_platform_cookies.json" in publisher.cookie_file
        
    def test_load_cookies(self):
        """测试加载Cookie"""
        from src.ai_write_x.tools.publishers.base_publisher import PlaywrightPublisher
        
        class TestPublisher(PlaywrightPublisher):
            def publish(self, title, content, images=None, **kwargs):
                return True, "test"
        
        publisher = TestPublisher("test_platform")
        
        mock_context = MagicMock()
        test_cookies = [{"name": "test", "value": "value"}]
        
        with patch('os.path.exists', return_value=True):
            with patch('builtins.open', mock_open(read_data='[{"name": "test", "value": "value"}]')):
                with patch('json.load', return_value=test_cookies):
                    publisher._load_cookies(mock_context)
                    mock_context.add_cookies.assert_called_once()


class TestXiaohongshuPublisher:
    """测试小红书发布器"""
    
    def test_xiaohongshu_initialization(self):
        """测试小红书发布器初始化"""
        from src.ai_write_x.tools.publishers.xiaohongshu_publisher import XiaohongshuPublisher
        
        publisher = XiaohongshuPublisher(headless=True)
        assert publisher.platform_name == "xiaohongshu"
        
    def test_xiaohongshu_urls(self):
        """测试小红书URL配置"""
        from src.ai_write_x.tools.publishers.xiaohongshu_publisher import XiaohongshuPublisher
        
        publisher = XiaohongshuPublisher()
        assert "xiaohongshu.com" in publisher.login_url
        
    @patch('src.ai_write_x.tools.publishers.xiaohongshu_publisher.sync_playwright')
    def test_xiaohongshu_publish_mock(self, mock_playwright):
        """Mock测试小红书发布"""
        from src.ai_write_x.tools.publishers.xiaohongshu_publisher import XiaohongshuPublisher
        
        # 设置Mock
        mock_p = MagicMock()
        mock_browser = MagicMock()
        mock_context = MagicMock()
        mock_page = MagicMock()
        
        mock_playwright.return_value.__enter__ = MagicMock(return_value=mock_p)
        mock_playwright.return_value.__exit__ = MagicMock(return_value=False)
        mock_p.chromium.launch.return_value = mock_browser
        mock_browser.new_context.return_value = mock_context
        mock_context.new_page.return_value = mock_page
        mock_context.cookies.return_value = []
        
        publisher = XiaohongshuPublisher(headless=True)
        
        with patch('os.path.exists', return_value=False):
            success, message = publisher.publish(
                title="测试标题",
                content="测试内容",
                images=[],
                commit=False
            )
            
            assert isinstance(success, bool)
            assert isinstance(message, str)


class TestDouyinPublisher:
    """测试抖音发布器"""
    
    def test_douyin_initialization(self):
        """测试抖音发布器初始化"""
        from src.ai_write_x.tools.publishers.douyin_publisher import DouyinPublisher
        
        publisher = DouyinPublisher(headless=True)
        assert publisher.platform_name == "douyin"
        
    def test_douyin_urls(self):
        """测试抖音URL配置"""
        from src.ai_write_x.tools.publishers.douyin_publisher import DouyinPublisher
        
        publisher = DouyinPublisher()
        assert "douyin.com" in publisher.login_url
        assert "douyin.com" in publisher.video_publish_url
        
    def test_publish_video_params(self):
        """测试视频发布参数"""
        from src.ai_write_x.tools.publishers.douyin_publisher import DouyinPublisher
        
        publisher = DouyinPublisher()
        
        # 测试无效视频路径
        success, message = publisher.publish_video(
            video_path="/nonexistent/video.mp4",
            title="测试"
        )
        assert success == False
        assert "不存在" in message


class TestZhihuPublisher:
    """测试知乎发布器"""
    
    def test_zhihu_initialization(self):
        """测试知乎发布器初始化"""
        from src.ai_write_x.tools.publishers.zhihu_publisher import ZhihuPublisher
        
        publisher = ZhihuPublisher(headless=True)
        assert publisher.platform_name == "zhihu"
        
    def test_zhihu_urls(self):
        """测试知乎URL配置"""
        from src.ai_write_x.tools.publishers.zhihu_publisher import ZhihuPublisher
        
        publisher = ZhihuPublisher()
        assert "zhihu.com" in publisher.login_url


class TestToutiaoPublisher:
    """测试今日头条发布器"""
    
    def test_toutiao_initialization(self):
        """测试今日头条发布器初始化"""
        from src.ai_write_x.tools.publishers.toutiao_publisher import ToutiaoPublisher
        
        publisher = ToutiaoPublisher(headless=True)
        assert publisher.platform_name == "toutiao"
        
    def test_toutiao_urls(self):
        """测试今日头条URL配置"""
        from src.ai_write_x.tools.publishers.toutiao_publisher import ToutiaoPublisher
        
        publisher = ToutiaoPublisher()
        assert "toutiao.com" in publisher.login_url


class TestBaijiahaoPublisher:
    """测试百家号发布器"""
    
    def test_baijiahao_initialization(self):
        """测试百家号发布器初始化"""
        from src.ai_write_x.tools.publishers.baijiahao_publisher import BaijiahaoPublisher
        
        publisher = BaijiahaoPublisher(headless=True)
        assert publisher.platform_name == "baijiahao"
        
    def test_baijiahao_urls(self):
        """测试百家号URL配置"""
        from src.ai_write_x.tools.publishers.baijiahao_publisher import BaijiahaoPublisher
        
        publisher = BaijiahaoPublisher()
        assert "baijiahao.baidu.com" in publisher.login_url


class TestMultiPlatformHub:
    """测试多平台发布中心"""
    
    def test_hub_singleton(self):
        """测试Hub单例模式"""
        from src.ai_write_x.tools.publishers.multi_platform_hub import MultiPlatformHub
        
        hub1 = MultiPlatformHub()
        hub2 = MultiPlatformHub()
        assert hub1 is hub2
        
    def test_hub_initialization(self):
        """测试Hub初始化"""
        from src.ai_write_x.tools.publishers.multi_platform_hub import MultiPlatformHub
        
        hub = MultiPlatformHub()
        assert len(hub.configs) > 0
        
    def test_create_publish_task(self):
        """测试创建发布任务"""
        from src.ai_write_x.tools.publishers.multi_platform_hub import (
            MultiPlatformHub, PlatformType
        )
        
        hub = MultiPlatformHub()
        task = hub.create_publish_task(
            title="测试标题",
            content="测试内容",
            images=[],
            platforms=[PlatformType.ZHIHU]
        )
        
        assert task.title == "测试标题"
        assert len(task.platforms) == 1
        assert task.status == "pending"
        
    def test_get_platform_status(self):
        """测试获取平台状态"""
        from src.ai_write_x.tools.publishers.multi_platform_hub import MultiPlatformHub
        
        hub = MultiPlatformHub()
        status = hub.get_platform_status()
        
        assert isinstance(status, dict)
        assert len(status) > 0
        
    def test_enable_disable_platform(self):
        """测试启用/禁用平台"""
        from src.ai_write_x.tools.publishers.multi_platform_hub import (
            MultiPlatformHub, PlatformType
        )
        
        hub = MultiPlatformHub()
        
        # 禁用平台
        hub.disable_platform(PlatformType.ZHIHU)
        assert hub.configs[PlatformType.ZHIHU].enabled == False
        
        # 启用平台
        hub.enable_platform(PlatformType.ZHIHU)
        assert hub.configs[PlatformType.ZHIHU].enabled == True
        
    def test_get_publish_stats(self):
        """测试获取发布统计"""
        from src.ai_write_x.tools.publishers.multi_platform_hub import MultiPlatformHub
        
        hub = MultiPlatformHub()
        stats = hub.get_publish_stats()
        
        assert "total_tasks" in stats
        assert "performance" in stats
        assert "memory" in stats["performance"]


class TestAsyncMultiPlatformHub:
    """测试异步多平台发布中心"""
    
    @pytest.mark.asyncio
    async def test_async_hub_initialization(self):
        """测试异步Hub初始化"""
        from src.ai_write_x.tools.publishers.async_multi_platform_hub import AsyncMultiPlatformHub
        
        hub = AsyncMultiPlatformHub(max_concurrent=3)
        assert hub.max_concurrent == 3
        assert len(hub.configs) > 0
        
    @pytest.mark.asyncio
    async def test_async_create_task(self):
        """测试异步创建任务"""
        from src.ai_write_x.tools.publishers.async_multi_platform_hub import (
            AsyncMultiPlatformHub, PlatformType
        )
        
        hub = AsyncMultiPlatformHub()
        task = hub.create_publish_task(
            title="测试",
            content="内容",
            platforms=[PlatformType.ZHIHU, PlatformType.XIAOHONGSHU]
        )
        
        assert task.id is not None
        assert len(task.platforms) == 2
        
    def test_async_hub_stats(self):
        """测试异步Hub统计"""
        from src.ai_write_x.tools.publishers.async_multi_platform_hub import AsyncMultiPlatformHub
        
        hub = AsyncMultiPlatformHub()
        stats = hub.get_stats()
        
        assert "total_tasks" in stats
        assert "browser_pool_stats" in stats


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
