# -*- coding: UTF-8 -*-
"""
系统指标收集 V15.0 - Metrics Collection

功能特性:
1. 性能指标 (延迟、吞吐量、错误率)
2. 业务指标 (文章生成数、API 调用数)
3. 资源指标 (CPU、内存、磁盘)
4. 告警触发
5. 指标导出 (Prometheus 格式)
"""

import time
import threading
from typing import Any, Dict, List, Optional, Callable
from dataclasses import dataclass, field
from collections import deque
import logging

logger = logging.getLogger(__name__)


@dataclass
class MetricValue:
    """指标值"""
    name: str
    value: float
    timestamp: float
    labels: Dict[str, str] = field(default_factory=dict)


class MetricsCollector:
    """
    指标收集器
    
    单例模式，收集所有系统指标
    """
    
    _instance: Optional['MetricsCollector'] = None
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
        
        # 计数器
        self._counters: Dict[str, int] = {}
        self._counter_lock = threading.Lock()
        
        #  gauges (瞬时值)
        self._gauges: Dict[str, float] = {}
        self._gauge_lock = threading.Lock()
        
        # 历史记录 (用于计算百分位数)
        self._histograms: Dict[str, deque] = {}
        self._histogram_lock = threading.Lock()
        self._max_history = 10000
        
        logger.info("[MetricsCollector] 指标收集器初始化完成")
    
    def increment(self, name: str, value: int = 1, labels: Optional[Dict] = None):
        """增加计数器"""
        key = self._make_key(name, labels)
        with self._counter_lock:
            self._counters[key] = self._counters.get(key, 0) + value
    
    def gauge(self, name: str, value: float, labels: Optional[Dict] = None):
        """设置 gauge 值"""
        key = self._make_key(name, labels)
        with self._gauge_lock:
            self._gauges[key] = value
    
    def histogram(self, name: str, value: float, labels: Optional[Dict] = None):
        """记录直方图值"""
        key = self._make_key(name, labels)
        with self._histogram_lock:
            if key not in self._histograms:
                self._histograms[key] = deque(maxlen=self._max_history)
            self._histograms[key].append(value)
    
    def _make_key(self, name: str, labels: Optional[Dict]) -> str:
        """生成指标键"""
        if not labels:
            return name
        label_str = ",".join(f"{k}={v}" for k, v in sorted(labels.items()))
        return f"{name}{{{label_str}}}"
    
    def get_counter(self, name: str, labels: Optional[Dict] = None) -> int:
        """获取计数器值"""
        key = self._make_key(name, labels)
        with self._counter_lock:
            return self._counters.get(key, 0)
    
    def get_gauge(self, name: str, labels: Optional[Dict] = None) -> float:
        """获取 gauge 值"""
        key = self._make_key(name, labels)
        with self._gauge_lock:
            return self._gauges.get(key, 0.0)
    
    def get_histogram_stats(self, name: str, labels: Optional[Dict] = None) -> Dict[str, float]:
        """获取直方图统计"""
        key = self._make_key(name, labels)
        with self._histogram_lock:
            values = list(self._histograms.get(key, []))
        
        if not values:
            return {"count": 0, "avg": 0, "p50": 0, "p95": 0, "p99": 0}
        
        sorted_values = sorted(values)
        n = len(sorted_values)
        
        return {
            "count": n,
            "avg": sum(values) / n,
            "p50": sorted_values[int(n * 0.5)],
            "p95": sorted_values[int(n * 0.95)] if n >= 20 else sorted_values[-1],
            "p99": sorted_values[int(n * 0.99)] if n >= 100 else sorted_values[-1],
        }
    
    def get_all_metrics(self) -> Dict[str, Any]:
        """获取所有指标"""
        with self._counter_lock:
            counters = dict(self._counters)
        with self._gauge_lock:
            gauges = dict(self._gauges)
        
        histograms = {}
        with self._histogram_lock:
            for key in self._histograms.keys():
                histograms[key] = self.get_histogram_stats(key)
        
        return {
            "counters": counters,
            "gauges": gauges,
            "histograms": histograms,
            "timestamp": time.time(),
        }
    
    def export_prometheus(self) -> str:
        """导出 Prometheus 格式"""
        lines = []
        
        # Counters
        with self._counter_lock:
            for key, value in self._counters.items():
                lines.append(f"# TYPE {key} counter")
                lines.append(f"{key} {value}")
        
        # Gauges
        with self._gauge_lock:
            for key, value in self._gauges.items():
                lines.append(f"# TYPE {key} gauge")
                lines.append(f"{key} {value}")
        
        return "\n".join(lines)


# 便捷函数
def get_metrics_collector() -> MetricsCollector:
    """获取全局指标收集器"""
    return MetricsCollector()


# 预定义指标
METRICS = {
    # 请求相关
    "http_requests_total": "HTTP 请求总数",
    "http_request_duration_ms": "HTTP 请求延迟",
    "http_requests_failed": "HTTP 请求失败数",
    
    # LLM 相关
    "llm_requests_total": "LLM 请求总数",
    "llm_request_duration_ms": "LLM 请求延迟",
    "llm_tokens_input": "输入 token 数",
    "llm_tokens_output": "输出 token 数",
    "llm_cache_hits": "缓存命中数",
    "llm_cost_usd": "LLM 成本 (USD)",
    
    # 业务相关
    "articles_generated": "生成文章数",
    "articles_published": "发布文章数",
    "images_generated": "生成图片数",
    "spider_articles_fetched": "抓取文章数",
    
    # 系统相关
    "system_cpu_usage": "CPU 使用率",
    "system_memory_usage": "内存使用率",
    "active_websocket_connections": "WebSocket 连接数",
}
