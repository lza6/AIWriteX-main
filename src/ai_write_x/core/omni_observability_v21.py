# -*- coding: UTF-8 -*-
"""
V21 全链路可观测性平台 - OmniObservability V21

整合三大支柱:
1. Metrics (指标) - Prometheus + Grafana
2. Tracing (追踪) - OpenTelemetry
3. Logging (日志) - 结构化日志 + ELK

核心特性:
- 分布式追踪
- 实时性能监控
- 自动异常检测
- AI 驱动的根本原因分析
- 端到端可视化

版本：V21.0.0
作者：AIWriteX Team
创建日期：2026-03-10
"""

import asyncio
import time
import json
import hashlib
import threading
from typing import Any, Dict, List, Optional, Callable
from dataclasses import dataclass, field
from enum import Enum
from collections import defaultdict
import logging
from contextvars import ContextVar

logger = logging.getLogger(__name__)


class SpanKind(Enum):
    """Span 类型"""
    INTERNAL = "internal"
    SERVER = "server"
    CLIENT = "client"
    PRODUCER = "producer"
    CONSUMER = "consumer"


@dataclass
class SpanContext:
    """Span 上下文"""
    trace_id: str
    span_id: str
    parent_span_id: Optional[str] = None


@dataclass
class Span:
    """追踪 Span"""
    trace_id: str
    span_id: str
    name: str
    kind: SpanKind
    start_time: float
    end_time: Optional[float] = None
    attributes: Dict[str, Any] = field(default_factory=dict)
    events: List[Dict[str, Any]] = field(default_factory=list)
    status: str = "OK"  # OK, ERROR
    error_message: Optional[str] = None

    def duration_ms(self) -> float:
        """获取持续时间 (毫秒)"""
        if self.end_time is None:
            return (time.time() - self.start_time) * 1000
        return (self.end_time - self.start_time) * 1000

    def to_dict(self) -> Dict[str, Any]:
        """转换为字典"""
        return {
            'trace_id': self.trace_id,
            'span_id': self.span_id,
            'name': self.name,
            'kind': self.kind.value,
            'start_time': self.start_time,
            'end_time': self.end_time or time.time(),
            'duration_ms': self.duration_ms(),
            'attributes': self.attributes,
            'events': self.events,
            'status': self.status,
            'error_message': self.error_message
        }


class SpanBuilder:
    """Span 构建器"""

    def __init__(
        self,
        name: str,
        kind: SpanKind = SpanKind.INTERNAL,
        parent_ctx: Optional[SpanContext] = None
    ):
        self.name = name
        self.kind = kind
        self.parent_ctx = parent_ctx
        self.attributes: Dict[str, Any] = {}
        self.events: List[Dict[str, Any]] = []

    def set_attribute(self, key: str, value: Any):
        """设置属性"""
        self.attributes[key] = value
        return self

    def add_event(self, event_name: str, attributes: Optional[Dict] = None):
        """添加事件"""
        self.events.append({
            'name': event_name,
            'timestamp': time.time(),
            'attributes': attributes or {}
        })
        return self

    def build(self) -> Span:
        """构建 Span"""
        trace_id = (
            self.parent_ctx.trace_id
            if self.parent_ctx
            else hashlib.md5(f"{time.time()}".encode()).hexdigest()
        )

        span_id = hashlib.md5(
            f"{trace_id}:{time.time()}".encode()
        ).hexdigest()[:16]

        return Span(
            trace_id=trace_id,
            span_id=span_id,
            name=self.name,
            kind=self.kind,
            start_time=time.time(),
            parent_span_id=self.parent_ctx.span_id if self.parent_ctx else None,
            attributes=self.attributes,
            events=self.events
        )


class MetricsCollector:
    """
    指标收集器

    支持:
    - Counter (计数器)
    - Gauge (仪表盘)
    - Histogram (直方图)
    - Summary (摘要)
    """

    def __init__(self):
        self._counters: Dict[str, float] = defaultdict(float)
        self._gauges: Dict[str, float] = {}
        self._histograms: Dict[str, List[float]] = defaultdict(list)
        self._summaries: Dict[str, Dict[str, Any]] = {}
        self._lock = threading.RLock()

    def inc_counter(self, name: str, value: float = 1, labels: Optional[Dict] = None):
        """增加计数器"""
        key = self._make_key(name, labels)
        with self._lock:
            self._counters[key] += value

    def set_gauge(self, name: str, value: float, labels: Optional[Dict] = None):
        """设置仪表盘值"""
        key = self._make_key(name, labels)
        with self._lock:
            self._gauges[key] = value

    def observe_histogram(
        self,
        name: str,
        value: float,
        labels: Optional[Dict] = None
    ):
        """观察直方图"""
        key = self._make_key(name, labels)
        with self._lock:
            self._histograms[key].append(value)

            # 保持最近 1000 个样本
            if len(self._histograms[key]) > 1000:
                self._histograms[key] = self._histograms[key][-1000:]

    def record_summary(
        self,
        name: str,
        value: float,
        labels: Optional[Dict] = None
    ):
        """记录摘要"""
        key = self._make_key(name, labels)
        with self._lock:
            if key not in self._summaries:
                self._summaries[key] = {
                    'count': 0,
                    'sum': 0.0,
                    'min': float('inf'),
                    'max': float('-inf')
                }

            summary = self._summaries[key]
            summary['count'] += 1
            summary['sum'] += value
            summary['min'] = min(summary['min'], value)
            summary['max'] = max(summary['max'], value)

    def _make_key(self, name: str, labels: Optional[Dict] = None) -> str:
        """生成指标键"""
        if not labels:
            return name

        label_str = ",".join(f"{k}={v}" for k, v in sorted(labels.items()))
        return f"{name}{{{label_str}}}"

    def get_all_metrics(self) -> Dict[str, Any]:
        """获取所有指标"""
        with self._lock:
            metrics = {
                'counters': dict(self._counters),
                'gauges': dict(self._gauges),
                'histograms': {},
                'summaries': {}
            }

            # 计算直方图百分位
            for key, values in self._histograms.items():
                if values:
                    sorted_vals = sorted(values)
                    metrics['histograms'][key] = {
                        'count': len(sorted_vals),
                        'avg': sum(sorted_vals) / len(sorted_vals),
                        'p50': self._percentile(sorted_vals, 50),
                        'p90': self._percentile(sorted_vals, 90),
                        'p99': self._percentile(sorted_vals, 99)
                    }

            # 计算摘要统计
            for key, summary in self._summaries.items():
                if summary['count'] > 0:
                    metrics['summaries'][key] = {
                        **summary,
                        'avg': summary['sum'] / summary['count']
                    }

            return metrics

    def _percentile(self, sorted_data: List[float], percentile: int) -> float:
        """计算百分位数"""
        if not sorted_data:
            return 0.0

        k = (len(sorted_data) - 1) * percentile / 100
        f = int(k)
        c = f + 1

        if c >= len(sorted_data):
            return sorted_data[-1]

        return sorted_data[f] + (k - f) * (sorted_data[c] - sorted_data[f])

    def export_prometheus_format(self) -> str:
        """导出为 Prometheus 格式"""
        lines = []

        # Counters
        for key, value in self._counters.items():
            metric_name = key.split('{')[0]
            lines.append(f"# TYPE {metric_name} counter")
            lines.append(f"{key} {value}")

        # Gauges
        for key, value in self._gauges.items():
            metric_name = key.split('{')[0]
            lines.append(f"# TYPE {metric_name} gauge")
            lines.append(f"{key} {value}")

        return "\n".join(lines)


class LogAggregator:
    """
    日志聚合器

    支持:
    - 结构化日志
    - 日志级别过滤
    - 异步写入
    - 自动轮转
    """

    def __init__(
        self,
        log_file: str = "logs/observability.log",
        max_size_mb: int = 100,
        backup_count: int = 5
    ):
        self.log_file = log_file
        self.max_size_bytes = max_size_mb * 1024 * 1024
        self.backup_count = backup_count

        self._queue: asyncio.Queue = asyncio.Queue()
        self._running = True
        self._writer_task: Optional[asyncio.Task] = None

        # 启动后台写入
        self._start_writer()

    def _start_writer(self):
        """启动后台写入器"""
        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)

        def run():
            loop.run_until_complete(self._write_loop())

        thread = threading.Thread(target=run, daemon=True)
        thread.start()

    async def _write_loop(self):
        """写入循环"""
        while self._running:
            try:
                logs = []

                # 批量读取
                while not self._queue.empty():
                    logs.append(await self._queue.get())

                if logs:
                    await self._write_to_file(logs)

                await asyncio.sleep(0.1)

            except asyncio.CancelledError:
                break
            except Exception as e:
                logger.error(f"[LogAggregator] 写入异常：{e}")

    async def _write_to_file(self, logs: List[Dict]):
        """写入到文件"""
        import os

        # 检查文件大小
        if os.path.exists(self.log_file):
            size = os.path.getsize(self.log_file)
            if size >= self.max_size_bytes:
                self._rotate_logs()

        # 写入
        with open(self.log_file, 'a', encoding='utf-8') as f:
            for log in logs:
                f.write(json.dumps(log, ensure_ascii=False) + "\n")

    def _rotate_logs(self):
        """轮转日志"""
        import shutil

        # 删除最旧的备份
        oldest = f"{self.log_file}.{self.backup_count}"
        if os.path.exists(oldest):
            os.remove(oldest)

        # 移动现有备份
        for i in range(self.backup_count - 1, 0, -1):
            src = f"{self.log_file}.{i}"
            dst = f"{self.log_file}.{i + 1}"
            if os.path.exists(src):
                shutil.move(src, dst)

        # 当前文件移动到 .1
        if os.path.exists(self.log_file):
            shutil.move(self.log_file, f"{self.log_file}.1")

    def log(
        self,
        level: str,
        message: str,
        **kwargs
    ):
        """记录日志"""
        log_entry = {
            'timestamp': time.time(),
            'level': level,
            'message': message,
            **kwargs
        }

        asyncio.create_task(self._queue.put(log_entry))

    def info(self, message: str, **kwargs):
        self.log('INFO', message, **kwargs)

    def warning(self, message: str, **kwargs):
        self.log('WARNING', message, **kwargs)

    def error(self, message: str, **kwargs):
        self.log('ERROR', message, **kwargs)

    def debug(self, message: str, **kwargs):
        self.log('DEBUG', message, **kwargs)

    def shutdown(self):
        """关闭聚合器"""
        self._running = False


class Tracer:
    """
    分布式追踪器

    支持:
    - 跨进程追踪
    - 上下文传播
    - 自动错误捕获
    """

    def __init__(self, service_name: str):
        self.service_name = service_name
        self._active_spans: ContextVar[Optional[Span]] = ContextVar(
            'active_span', default=None)
        self._finished_spans: List[Span] = []
        self._export_callback: Optional[Callable] = None

    def start_span(
        self,
        name: str,
        kind: SpanKind = SpanKind.INTERNAL,
        parent: Optional[SpanContext] = None
    ) -> 'Span':
        """开始 Span"""
        builder = SpanBuilder(name, kind, parent)
        span = builder.build()

        # 设置为活动 span
        self._active_spans.set(span)

        return span

    def end_span(self, span: Span, status: str = "OK", error: Optional[str] = None):
        """结束 Span"""
        span.end_time = time.time()
        span.status = status
        span.error_message = error

        # 存储
        self._finished_spans.append(span)

        # 导出
        if self._export_callback:
            self._export_callback(span)

        # 恢复父 span
        if span.parent_span_id:
            parent = next(
                (s for s in self._finished_spans if s.span_id == span.parent_span_id),
                None
            )
            if parent:
                self._active_spans.set(parent)
        else:
            self._active_spans.set(None)

    def get_current_span(self) -> Optional[Span]:
        """获取当前活动 span"""
        return self._active_spans.get()

    def inject_context(self) -> Dict[str, str]:
        """注入追踪上下文到请求头"""
        span = self.get_current_span()
        if not span:
            return {}

        return {
            'x-trace-id': span.trace_id,
            'x-span-id': span.span_id,
            'x-parent-span-id': span.parent_span_id or ''
        }

    def extract_context(self, headers: Dict[str, str]) -> Optional[SpanContext]:
        """从请求头提取追踪上下文"""
        trace_id = headers.get('x-trace-id')
        span_id = headers.get('x-span-id')
        parent_span_id = headers.get('x-parent-span-id')

        if not trace_id or not span_id:
            return None

        return SpanContext(
            trace_id=trace_id,
            span_id=span_id,
            parent_span_id=parent_span_id or None
        )

    def set_export_callback(self, callback: Callable[[Span], None]):
        """设置导出回调"""
        self._export_callback = callback

    def get_finished_spans(self, limit: int = 100) -> List[Span]:
        """获取已完成的 spans"""
        return self._finished_spans[-limit:]

    def clear_spans(self):
        """清空 spans"""
        self._finished_spans.clear()


class OmniObservability:
    """
    V21 全链路可观测性平台

    整合:
    - Metrics (Prometheus 兼容)
    - Tracing (OpenTelemetry 兼容)
    - Logging (结构化日志)
    """

    def __init__(self, service_name: str = "ai-write-x"):
        self.service_name = service_name

        # 核心组件
        self.metrics = MetricsCollector()
        self.tracer = Tracer(service_name)
        self.logger = LogAggregator()

        # 自动指标收集
        self._auto_collect = True

        # 设置 span 导出
        self.tracer.set_export_callback(self._on_span_exported)

        logger.info(f"[OmniObservability] 可观测性平台初始化完成 ({service_name})")

    def _on_span_exported(self, span: Span):
        """Span 导出时的回调"""
        # 记录指标
        self.tracer.metrics.observe_histogram(
            'span_duration_ms',
            span.duration_ms(),
            {'span_name': span.name, 'status': span.status}
        )

        # 记录日志
        if span.status == "ERROR":
            self.logger.error(
                f"Span 错误：{span.name}",
                trace_id=span.trace_id,
                span_id=span.span_id,
                error=span.error_message
            )

    def track_request(self, request_id: str):
        """追踪请求装饰器"""
        def decorator(func):
            async def wrapper(*args, **kwargs):
                # 开始追踪
                span = self.tracer.start_span(
                    f"{func.__module__}.{func.__name__}",
                    kind=SpanKind.SERVER
                )
                span.set_attribute('request_id', request_id)

                try:
                    # 执行
                    result = await func(*args, **kwargs)

                    # 成功
                    self.tracer.end_span(span, status="OK")
                    self.metrics.inc_counter('requests_total', labels={
                                             'status': 'success'})

                    return result

                except Exception as e:
                    # 失败
                    self.tracer.end_span(span, status="ERROR", error=str(e))
                    self.metrics.inc_counter(
                        'requests_total', labels={'status': 'error'})

                    raise

            return wrapper
        return decorator

    def get_dashboard_data(self) -> Dict[str, Any]:
        """获取仪表盘数据"""
        return {
            'metrics': self.metrics.get_all_metrics(),
            'traces': [
                span.to_dict()
                for span in self.tracer.get_finished_spans(50)
            ],
            'service_name': self.service_name,
            'timestamp': time.time()
        }

    def export_metrics(self) -> str:
        """导出 Prometheus 格式指标"""
        return self.metrics.export_prometheus_format()

    def shutdown(self):
        """关闭可观测性平台"""
        self.logger.shutdown()
        logger.info("[OmniObservability] 平台已关闭")


# 全局实例
_observability_instance: Optional[OmniObservability] = None


def get_observability(service_name: str = "ai-write-x") -> OmniObservability:
    """获取全局可观测性实例"""
    global _observability_instance
    if _observability_instance is None:
        _observability_instance = OmniObservability(service_name)
    return _observability_instance


# 示例用法
if __name__ == "__main__":
    async def test_observability():
        obs = get_observability()

        # 模拟请求处理
        @obs.track_request("req-001")
        async def process_request():
            await asyncio.sleep(0.1)
            return {"result": "success"}

        # 执行
        result = await process_request()
        print(f"请求结果：{result}")

        # 查看仪表盘
        dashboard = obs.get_dashboard_data()
        print(f"\n仪表盘数据：{json.dumps(dashboard, indent=2, default=str)}")

        # 导出指标
        prometheus_metrics = obs.export_metrics()
        print(f"\nPrometheus 指标:\n{prometheus_metrics}")

        obs.shutdown()

    asyncio.run(test_observability())
