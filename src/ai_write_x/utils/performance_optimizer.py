"""
AIWriteX 性能优化模块
包含：浏览器实例池、内存优化、性能监控
"""
import asyncio
import gc
import os
import threading
import time
import weakref
from collections import deque
from concurrent.futures import ThreadPoolExecutor
from contextlib import asynccontextmanager
from dataclasses import dataclass, field
from datetime import datetime
from typing import Dict, List, Optional, Any, Callable
import psutil

from src.ai_write_x.utils import log as lg


@dataclass
class PerformanceMetrics:
    """性能指标数据类"""
    timestamp: datetime = field(default_factory=datetime.now)
    memory_mb: float = 0.0
    cpu_percent: float = 0.0
    browser_instances: int = 0
    active_connections: int = 0
    task_queue_size: int = 0
    avg_response_time_ms: float = 0.0


class MemoryOptimizer:
    """
    内存优化器
    
    特性:
    - 定期垃圾回收
    - 内存使用监控
    - 大对象检测
    """
    
    _instance = None
    _lock = threading.Lock()
    
    def __new__(cls):
        if cls._instance is None:
            with cls._lock:
                if cls._instance is None:
                    cls._instance = super().__new__(cls)
                    cls._instance._initialized = False
        return cls._instance
    
    def __init__(self):
        if self._initialized:
            return
        
        self._initialized = True
        self._gc_threshold = 100  # MB
        self._last_gc_time = time.time()
        self._gc_interval = 300  # 5分钟
        self._running = False
        self._monitor_thread = None
        
    def start_monitoring(self):
        """启动内存监控"""
        if self._running:
            return
        
        self._running = True
        self._monitor_thread = threading.Thread(target=self._monitor_loop, daemon=True)
        self._monitor_thread.start()
        lg.print_log("[MemoryOptimizer] 内存监控已启动", "info")
    
    def stop_monitoring(self):
        """停止内存监控"""
        self._running = False
        if self._monitor_thread:
            self._monitor_thread.join(timeout=5)
        lg.print_log("[MemoryOptimizer] 内存监控已停止", "info")
    
    def _monitor_loop(self):
        """监控循环"""
        while self._running:
            try:
                self.check_and_optimize()
                time.sleep(60)  # 每分钟检查一次
            except Exception as e:
                lg.print_log(f"[MemoryOptimizer] 监控异常: {e}", "error")
    
    def check_and_optimize(self):
        """检查并优化内存"""
        current_time = time.time()
        
        # 检查是否需要GC
        if current_time - self._last_gc_time > self._gc_interval:
            memory_mb = self.get_memory_usage_mb()
            
            if memory_mb > self._gc_threshold:
                lg.print_log(f"[MemoryOptimizer] 内存使用 {memory_mb:.1f}MB，执行垃圾回收...", "info")
                self.force_gc()
                self._last_gc_time = current_time
                
                # 再次检查
                new_memory_mb = self.get_memory_usage_mb()
                freed_mb = memory_mb - new_memory_mb
                if freed_mb > 10:
                    lg.print_log(f"[MemoryOptimizer] 垃圾回收释放 {freed_mb:.1f}MB", "success")
    
    def force_gc(self):
        """强制垃圾回收"""
        gc.collect(0)  # 只收集年轻代，减少停顿
        gc.collect(1)  # 收集中代
        # 避免频繁调用 collect(2) 全量回收
    
    @staticmethod
    def get_memory_usage_mb() -> float:
        """获取当前进程内存使用 (MB)"""
        process = psutil.Process(os.getpid())
        return process.memory_info().rss / 1024 / 1024
    
    @staticmethod
    def get_system_memory() -> Dict[str, float]:
        """获取系统内存信息"""
        mem = psutil.virtual_memory()
        return {
            "total_mb": mem.total / 1024 / 1024,
            "available_mb": mem.available / 1024 / 1024,
            "percent": mem.percent,
            "used_mb": mem.used / 1024 / 1024
        }
    
    def set_gc_threshold(self, threshold_mb: int):
        """设置GC阈值"""
        self._gc_threshold = threshold_mb
        lg.print_log(f"[MemoryOptimizer] GC阈值设置为 {threshold_mb}MB", "info")


class BrowserInstancePool:
    """
    浏览器实例池
    
    特性:
    - 浏览器实例复用
    - 自动健康检查
    - 连接池管理
    - 最大实例数限制
    """
    
    _instance = None
    _lock = threading.Lock()
    
    def __new__(cls):
        if cls._instance is None:
            with cls._lock:
                if cls._instance is None:
                    cls._instance = super().__new__(cls)
                    cls._instance._initialized = False
        return cls._instance
    
    def __init__(self, max_instances: int = 3, headless: bool = True):
        if self._initialized:
            return
        
        self._initialized = True
        self.max_instances = max_instances
        self.headless = headless
        self._pool: deque = deque()
        self._in_use: set = set()
        self._pool_lock = threading.Lock()
        self._playwright = None
        self._browser = None
        self._initialized_browser = False
        
    def _ensure_browser(self):
        """确保浏览器已初始化"""
        if not self._initialized_browser:
            from playwright.sync_api import sync_playwright
            
            self._playwright = sync_playwright().start()
            self._browser = self._playwright.chromium.launch(
                headless=self.headless,
                args=[
                    '--disable-blink-features=AutomationControlled',
                    '--no-sandbox',
                    '--disable-dev-shm-usage',
                    '--disable-gpu',
                    '--disable-web-security',
                    '--disable-features=IsolateOrigins,site-per-process'
                ]
            )
            self._initialized_browser = True
            lg.print_log("[BrowserPool] 浏览器实例池已初始化", "info")
    
    def get_context(self, cookies_file: Optional[str] = None):
        """
        获取浏览器上下文
        
        Args:
            cookies_file: Cookie文件路径
            
        Returns:
            浏览器上下文
        """
        with self._pool_lock:
            self._ensure_browser()
            
            # 尝试从池中获取
            while self._pool:
                context = self._pool.popleft()
                try:
                    # 健康检查
                    page = context.new_page()
                    page.close()
                    self._in_use.add(id(context))
                    
                    # 加载Cookie
                    if cookies_file and os.path.exists(cookies_file):
                        import json
                        with open(cookies_file, 'r', encoding='utf-8') as f:
                            cookies = json.load(f)
                            context.add_cookies(cookies)
                    
                    return context
                except Exception:
                    # 上下文已失效，继续获取下一个
                    continue
            
            # 池为空，创建新上下文
            if len(self._in_use) < self.max_instances:
                context = self._browser.new_context(
                    user_agent="Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
                    viewport={"width": 1920, "height": 1080}
                )
                self._in_use.add(id(context))
                
                # 加载Cookie
                if cookies_file and os.path.exists(cookies_file):
                    import json
                    with open(cookies_file, 'r', encoding='utf-8') as f:
                        cookies = json.load(f)
                        context.add_cookies(cookies)
                
                return context
            else:
                raise RuntimeError(f"浏览器实例池已满 (最大 {self.max_instances} 个)")
    
    def release_context(self, context, cookies_file: Optional[str] = None):
        """
        释放浏览器上下文回池
        
        Args:
            context: 浏览器上下文
            cookies_file: Cookie保存路径
        """
        with self._pool_lock:
            context_id = id(context)
            if context_id in self._in_use:
                self._in_use.remove(context_id)
            
            # 保存Cookie
            if cookies_file:
                try:
                    cookies = context.cookies()
                    import json
                    with open(cookies_file, 'w', encoding='utf-8') as f:
                        json.dump(cookies, f, ensure_ascii=False, indent=4)
                except Exception as e:
                    lg.print_log(f"[BrowserPool] 保存Cookie失败: {e}", "warning")
            
            # 只保留部分上下文在池中
            if len(self._pool) < self.max_instances // 2:
                try:
                    # 清理页面
                    for page in context.pages:
                        page.close()
                    self._pool.append(context)
                except Exception:
                    # 上下文已失效，丢弃
                    pass
            else:
                # 池已满，关闭上下文
                try:
                    context.close()
                except Exception:
                    pass
    
    def close_all(self):
        """关闭所有浏览器实例"""
        with self._pool_lock:
            # 关闭池中的上下文
            while self._pool:
                try:
                    context = self._pool.popleft()
                    context.close()
                except Exception:
                    pass
            
            # 关闭浏览器
            if self._browser:
                try:
                    self._browser.close()
                except Exception:
                    pass
            
            # 停止Playwright
            if self._playwright:
                try:
                    self._playwright.stop()
                except Exception:
                    pass
            
            self._initialized_browser = False
            lg.print_log("[BrowserPool] 浏览器实例池已关闭", "info")
    
    def get_stats(self) -> Dict[str, int]:
        """获取池统计信息"""
        with self._pool_lock:
            return {
                "pool_size": len(self._pool),
                "in_use": len(self._in_use),
                "max_instances": self.max_instances
            }


class PerformanceMonitor:
    """
    性能监控器
    
    特性:
    - 实时性能指标收集
    - 历史数据分析
    - 性能告警
    """
    
    _instance = None
    _lock = threading.Lock()
    
    def __new__(cls):
        if cls._instance is None:
            with cls._lock:
                if cls._instance is None:
                    cls._instance = super().__new__(cls)
                    cls._instance._initialized = False
        return cls._instance
    
    def __init__(self, max_history: int = 1000):
        if self._initialized:
            return
        
        self._initialized = True
        self.max_history = max_history
        self._metrics_history: deque = deque(maxlen=max_history)
        self._running = False
        self._monitor_thread = None
        self._callbacks: List[Callable] = []
        
    def start(self):
        """启动监控"""
        if self._running:
            return
        
        self._running = True
        self._monitor_thread = threading.Thread(target=self._monitor_loop, daemon=True)
        self._monitor_thread.start()
        lg.print_log("[PerformanceMonitor] 性能监控已启动", "info")
    
    def stop(self):
        """停止监控"""
        self._running = False
        if self._monitor_thread:
            self._monitor_thread.join(timeout=5)
        lg.print_log("[PerformanceMonitor] 性能监控已停止", "info")
    
    def _monitor_loop(self):
        """监控循环"""
        while self._running:
            try:
                metrics = self._collect_metrics()
                self._metrics_history.append(metrics)
                
                # 触发回调
                for callback in self._callbacks:
                    try:
                        callback(metrics)
                    except Exception:
                        pass
                
                time.sleep(10)  # 每10秒收集一次
            except Exception as e:
                lg.print_log(f"[PerformanceMonitor] 监控异常: {e}", "error")
    
    def _collect_metrics(self) -> PerformanceMetrics:
        """收集性能指标"""
        process = psutil.Process(os.getpid())
        
        return PerformanceMetrics(
            timestamp=datetime.now(),
            memory_mb=process.memory_info().rss / 1024 / 1024,
            cpu_percent=process.cpu_percent(),
            browser_instances=0,  # 可由外部更新
            active_connections=0,  # 可由外部更新
            task_queue_size=0,  # 可由外部更新
            avg_response_time_ms=0.0  # 可由外部更新
        )
    
    def add_callback(self, callback: Callable):
        """添加监控回调"""
        self._callbacks.append(callback)
    
    def get_latest_metrics(self) -> Optional[PerformanceMetrics]:
        """获取最新指标"""
        if self._metrics_history:
            return self._metrics_history[-1]
        return None
    
    def get_average_metrics(self, last_n: int = 10) -> Dict[str, float]:
        """获取平均指标"""
        if not self._metrics_history:
            return {}
        
        recent = list(self._metrics_history)[-last_n:]
        if not recent:
            return {}
        
        return {
            "avg_memory_mb": sum(m.memory_mb for m in recent) / len(recent),
            "avg_cpu_percent": sum(m.cpu_percent for m in recent) / len(recent),
            "max_memory_mb": max(m.memory_mb for m in recent),
            "max_cpu_percent": max(m.cpu_percent for m in recent)
        }
    
    def get_report(self) -> str:
        """生成性能报告"""
        latest = self.get_latest_metrics()
        avg = self.get_average_metrics()
        
        report = []
        report.append("=" * 50)
        report.append("性能监控报告")
        report.append("=" * 50)
        
        if latest:
            report.append(f"当前内存使用: {latest.memory_mb:.1f} MB")
            report.append(f"当前CPU使用率: {latest.cpu_percent:.1f}%")
        
        if avg:
            report.append(f"平均内存使用: {avg.get('avg_memory_mb', 0):.1f} MB")
            report.append(f"平均CPU使用率: {avg.get('avg_cpu_percent', 0):.1f}%")
            report.append(f"峰值内存使用: {avg.get('max_memory_mb', 0):.1f} MB")
            report.append(f"峰值CPU使用率: {avg.get('max_cpu_percent', 0):.1f}%")
        
        report.append("=" * 50)
        return "\n".join(report)


# 全局实例
memory_optimizer = MemoryOptimizer()
browser_pool = BrowserInstancePool()
performance_monitor = PerformanceMonitor()


def initialize_performance_system():
    """初始化性能优化系统"""
    memory_optimizer.start_monitoring()
    performance_monitor.start()
    lg.print_log("[Performance] 性能优化系统已初始化", "success")


def shutdown_performance_system():
    """关闭性能优化系统"""
    memory_optimizer.stop_monitoring()
    performance_monitor.stop()
    browser_pool.close_all()
    lg.print_log("[Performance] 性能优化系统已关闭", "success")
