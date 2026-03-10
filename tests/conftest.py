"""
Pytest配置文件
提供全局fixture和配置
"""
import os
import sys
import pytest
import asyncio
from unittest.mock import MagicMock, patch

# 添加项目根目录到路径
project_root = os.path.dirname(os.path.dirname(__file__))
if project_root not in sys.path:
    sys.path.insert(0, project_root)


@pytest.fixture(scope="session")
def event_loop():
    """创建事件循环"""
    loop = asyncio.get_event_loop_policy().new_event_loop()
    yield loop
    loop.close()


@pytest.fixture(scope="function")
def mock_browser_context():
    """模拟浏览器上下文"""
    context = MagicMock()
    page = MagicMock()
    context.new_page.return_value = page
    context.cookies.return_value = [{"name": "test", "value": "value"}]
    context.pages = []
    return context


@pytest.fixture(scope="function")
def mock_playwright():
    """模拟Playwright"""
    playwright = MagicMock()
    browser = MagicMock()
    context = MagicMock()
    
    browser.new_context.return_value = context
    playwright.chromium.launch.return_value = browser
    
    return playwright, browser, context


@pytest.fixture(scope="function")
def temp_dir(tmp_path):
    """临时目录"""
    return tmp_path


@pytest.fixture(scope="function")
def mock_memory_optimizer():
    """模拟内存优化器"""
    with patch('src.ai_write_x.utils.performance_optimizer.memory_optimizer') as mock:
        mock.get_memory_usage_mb.return_value = 100.0
        mock.get_system_memory.return_value = {
            "total_mb": 16000,
            "available_mb": 8000,
            "percent": 50.0,
            "used_mb": 8000
        }
        yield mock


@pytest.fixture(scope="function")
def mock_browser_pool():
    """模拟浏览器池"""
    with patch('src.ai_write_x.utils.performance_optimizer.browser_pool') as mock:
        mock.get_stats.return_value = {
            "pool_size": 2,
            "in_use": 1,
            "max_instances": 3
        }
        yield mock


@pytest.fixture(scope="session")
def test_config():
    """测试配置"""
    return {
        "test_platforms": ["xiaohongshu", "douyin", "zhihu"],
        "test_timeout": 30,
        "mock_publish": True
    }
