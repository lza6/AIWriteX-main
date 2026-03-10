"""
AIWriteX 性能优化模块详细测试
测试MemoryOptimizer、BrowserPool、PerformanceMonitor
"""
import os
import sys
import pytest
import time
import gc
from unittest.mock import patch, MagicMock, Mock

project_root = os.path.dirname(os.path.dirname(__file__))
if project_root not in sys.path:
    sys.path.insert(0, project_root)


class TestMemoryOptimizer:
    """测试内存优化器"""
    
    def test_memory_optimizer_singleton(self):
        """测试内存优化器单例模式"""
        from src.ai_write_x.utils.performance_optimizer import MemoryOptimizer
        
        opt1 = MemoryOptimizer()
        opt2 = MemoryOptimizer()
        assert opt1 is opt2
        
    def test_get_memory_usage(self):
        """测试获取内存使用"""
        from src.ai_write_x.utils.performance_optimizer import memory_optimizer
        
        memory_mb = memory_optimizer.get_memory_usage_mb()
        assert isinstance(memory_mb, float)
        assert memory_mb > 0
        
    def test_get_system_memory(self):
        """测试获取系统内存"""
        from src.ai_write_x.utils.performance_optimizer import memory_optimizer
        
        sys_mem = memory_optimizer.get_system_memory()
        assert "total_mb" in sys_mem
        assert "available_mb" in sys_mem
        assert "percent" in sys_mem
        assert "used_mb" in sys_mem
        
    def test_force_gc(self):
        """测试强制垃圾回收"""
        from src.ai_write_x.utils.performance_optimizer import memory_optimizer
        
        # 不应抛出异常
        memory_optimizer.force_gc()
        
    def test_set_gc_threshold(self):
        """测试设置GC阈值"""
        from src.ai_write_x.utils.performance_optimizer import memory_optimizer
        
        memory_optimizer.set_gc_threshold(200)
        assert memory_optimizer._gc_threshold == 200
        
    def test_check_and_optimize(self):
        """测试检查并优化"""
        from src.ai_write_x.utils.performance_optimizer import memory_optimizer
        
        # 设置较短的间隔以确保执行
        memory_optimizer._last_gc_time = 0
        memory_optimizer._gc_threshold = 1  # 设置很低的阈值
        
        with patch.object(memory_optimizer, 'force_gc') as mock_gc:
            with patch.object(memory_optimizer, 'get_memory_usage_mb', return_value=200):
                memory_optimizer.check_and_optimize()
                mock_gc.assert_called_once()


class TestBrowserInstancePool:
    """测试浏览器实例池"""
    
    def test_browser_pool_singleton(self):
        """测试浏览器池单例模式"""
        from src.ai_write_x.utils.performance_optimizer import BrowserInstancePool
        
        pool1 = BrowserInstancePool()
        pool2 = BrowserInstancePool()
        assert pool1 is pool2
        
    def test_browser_pool_initialization(self):
        """测试浏览器池初始化"""
        from src.ai_write_x.utils.performance_optimizer import browser_pool
        
        assert browser_pool.max_instances == 3
        assert browser_pool.headless == True
        
    def test_get_stats(self):
        """测试获取池统计"""
        from src.ai_write_x.utils.performance_optimizer import browser_pool
        
        stats = browser_pool.get_stats()
        assert "pool_size" in stats
        assert "in_use" in stats
        assert "max_instances" in stats
        
    def test_get_stats_thread_safe(self):
        """测试统计信息线程安全"""
        from src.ai_write_x.utils.performance_optimizer import browser_pool
        import threading
        
        results = []
        
        def get_stats():
            stats = browser_pool.get_stats()
            results.append(stats)
        
        threads = [threading.Thread(target=get_stats) for _ in range(10)]
        for t in threads:
            t.start()
        for t in threads:
            t.join()
        
        assert len(results) == 10


class TestPerformanceMonitor:
    """测试性能监控器"""
    
    def test_performance_monitor_singleton(self):
        """测试性能监控器单例模式"""
        from src.ai_write_x.utils.performance_optimizer import PerformanceMonitor
        
        mon1 = PerformanceMonitor()
        mon2 = PerformanceMonitor()
        assert mon1 is mon2
        
    def test_start_stop(self):
        """测试启动和停止"""
        from src.ai_write_x.utils.performance_optimizer import performance_monitor
        
        performance_monitor.start()
        assert performance_monitor._running == True
        
        performance_monitor.stop()
        assert performance_monitor._running == False
        
    def test_get_latest_metrics(self):
        """测试获取最新指标"""
        from src.ai_write_x.utils.performance_optimizer import performance_monitor
        
        # 先收集一些指标
        performance_monitor.start()
        time.sleep(0.5)
        
        metrics = performance_monitor.get_latest_metrics()
        performance_monitor.stop()
        
        if metrics:
            assert hasattr(metrics, 'memory_mb')
            assert hasattr(metrics, 'cpu_percent')
            
    def test_get_average_metrics(self):
        """测试获取平均指标"""
        from src.ai_write_x.utils.performance_optimizer import performance_monitor
        
        performance_monitor.start()
        time.sleep(0.5)
        
        avg = performance_monitor.get_average_metrics(last_n=5)
        performance_monitor.stop()
        
        if avg:
            assert "avg_memory_mb" in avg or "avg_cpu_percent" in avg
            
    def test_get_report(self):
        """测试生成报告"""
        from src.ai_write_x.utils.performance_optimizer import performance_monitor
        
        report = performance_monitor.get_report()
        assert isinstance(report, str)
        assert "性能监控报告" in report
        
    def test_add_callback(self):
        """测试添加回调"""
        from src.ai_write_x.utils.performance_optimizer import performance_monitor
        
        callback_called = []
        
        def test_callback(metrics):
            callback_called.append(True)
        
        performance_monitor.add_callback(test_callback)
        assert test_callback in performance_monitor._callbacks


class TestPerformanceMetrics:
    """测试性能指标数据类"""
    
    def test_metrics_creation(self):
        """测试指标创建"""
        from src.ai_write_x.utils.performance_optimizer import PerformanceMetrics
        from datetime import datetime
        
        metrics = PerformanceMetrics(
            timestamp=datetime.now(),
            memory_mb=100.5,
            cpu_percent=25.0,
            browser_instances=2,
            active_connections=5,
            task_queue_size=10,
            avg_response_time_ms=150.0
        )
        
        assert metrics.memory_mb == 100.5
        assert metrics.cpu_percent == 25.0
        assert metrics.browser_instances == 2


class TestGlobalInstances:
    """测试全局实例"""
    
    def test_global_memory_optimizer(self):
        """测试全局内存优化器"""
        from src.ai_write_x.utils.performance_optimizer import memory_optimizer
        
        assert memory_optimizer is not None
        assert memory_optimizer._initialized == True
        
    def test_global_browser_pool(self):
        """测试全局浏览器池"""
        from src.ai_write_x.utils.performance_optimizer import browser_pool
        
        assert browser_pool is not None
        assert browser_pool._initialized == True
        
    def test_global_performance_monitor(self):
        """测试全局性能监控器"""
        from src.ai_write_x.utils.performance_optimizer import performance_monitor
        
        assert performance_monitor is not None
        
    def test_initialize_performance_system(self):
        """测试初始化性能系统"""
        from src.ai_write_x.utils.performance_optimizer import (
            initialize_performance_system,
            shutdown_performance_system
        )
        
        with patch('src.ai_write_x.utils.performance_optimizer.memory_optimizer') as mock_mem:
            with patch('src.ai_write_x.utils.performance_optimizer.performance_monitor') as mock_mon:
                initialize_performance_system()
                mock_mem.start_monitoring.assert_called_once()
                mock_mon.start.assert_called_once()
                
    def test_shutdown_performance_system(self):
        """测试关闭性能系统"""
        from src.ai_write_x.utils.performance_optimizer import (
            shutdown_performance_system
        )
        
        with patch('src.ai_write_x.utils.performance_optimizer.memory_optimizer') as mock_mem:
            with patch('src.ai_write_x.utils.performance_optimizer.performance_monitor') as mock_mon:
                with patch('src.ai_write_x.utils.performance_optimizer.browser_pool') as mock_browser:
                    shutdown_performance_system()
                    mock_mem.stop_monitoring.assert_called_once()
                    mock_mon.stop.assert_called_once()
                    mock_browser.close_all.assert_called_once()


class TestAsyncMultiPlatformHub:
    """测试异步多平台中心"""
    
    @pytest.mark.asyncio
    async def test_async_hub_creation(self):
        """测试异步Hub创建"""
        from src.ai_write_x.tools.publishers.async_multi_platform_hub import AsyncMultiPlatformHub
        
        hub = AsyncMultiPlatformHub(max_concurrent=5)
        assert hub.max_concurrent == 5
        
    def test_platform_type_enum(self):
        """测试平台类型枚举"""
        from src.ai_write_x.tools.publishers.async_multi_platform_hub import PlatformType
        
        assert PlatformType.XIAOHONGSHU.value == "xiaohongshu"
        assert PlatformType.DOUYIN.value == "douyin"
        assert PlatformType.ZHIHU.value == "zhihu"
        
    def test_platform_config(self):
        """测试平台配置"""
        from src.ai_write_x.tools.publishers.async_multi_platform_hub import (
            PlatformConfig, PlatformType
        )
        
        config = PlatformConfig(
            platform_type=PlatformType.ZHIHU,
            enabled=True,
            max_retries=5
        )
        
        assert config.platform_type == PlatformType.ZHIHU
        assert config.enabled == True
        assert config.max_retries == 5


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
