# -*- coding: UTF-8 -*-
"""
V17.0 - Intelligent Dashboard (智能可视化面板)

提供实时数据可视化、智能洞察和交互式分析：
1. 实时指标监控
2. 智能异常检测
3. 自然语言查询
4. 预测性可视化
5. 自定义仪表盘
"""

import json
import asyncio
from datetime import datetime, timedelta
from typing import Dict, List, Optional, Union, Any, Callable
from dataclasses import dataclass, field
from enum import Enum
import threading
from collections import deque, defaultdict

from ..utils import log


class ChartType(Enum):
    """图表类型"""
    LINE = "line"
    BAR = "bar"
    PIE = "pie"
    AREA = "area"
    GAUGE = "gauge"
    TABLE = "table"
    HEATMAP = "heatmap"
    SCATTER = "scatter"


class AlertLevel(Enum):
    """告警级别"""
    INFO = "info"
    WARNING = "warning"
    CRITICAL = "critical"


@dataclass
class Metric:
    """指标数据点"""
    name: str
    value: Union[int, float]
    timestamp: datetime
    labels: Dict[str, str] = field(default_factory=dict)
    unit: str = ""


@dataclass
class TimeSeries:
    """时间序列"""
    name: str
    data: deque = field(default_factory=lambda: deque(maxlen=1000))
    unit: str = ""
    
    def add(self, value: Union[int, float], timestamp: Optional[datetime] = None):
        """添加数据点"""
        self.data.append({
            "timestamp": timestamp or datetime.now(),
            "value": value
        })
    
    def get_latest(self, n: int = 100) -> List[Dict]:
        """获取最新n个数据点"""
        return list(self.data)[-n:]
    
    def get_stats(self) -> Dict[str, float]:
        """获取统计信息"""
        values = [d["value"] for d in self.data]
        if not values:
            return {}
        return {
            "count": len(values),
            "min": min(values),
            "max": max(values),
            "mean": sum(values) / len(values),
            "latest": values[-1]
        }


@dataclass
class Alert:
    """告警"""
    id: str
    metric_name: str
    level: AlertLevel
    message: str
    timestamp: datetime
    value: float
    threshold: float
    acknowledged: bool = False


@dataclass
class Widget:
    """仪表盘组件"""
    id: str
    name: str
    chart_type: ChartType
    data_source: str  # 数据源名称
    config: Dict[str, Any] = field(default_factory=dict)
    position: Dict[str, int] = field(default_factory=lambda: {"x": 0, "y": 0, "w": 4, "h": 3})


class AnomalyDetector:
    """异常检测器"""
    
    def __init__(self, window_size: int = 20, threshold: float = 3.0):
        self.window_size = window_size
        self.threshold = threshold
        self.history: Dict[str, deque] = defaultdict(lambda: deque(maxlen=window_size))
    
    def detect(self, metric_name: str, value: float) -> Optional[Alert]:
        """检测异常"""
        history = self.history[metric_name]
        
        if len(history) < self.window_size // 2:
            history.append(value)
            return None
        
        # 使用Z-Score检测异常
        mean = sum(history) / len(history)
        std = (sum((x - mean) ** 2 for x in history) / len(history)) ** 0.5
        
        if std == 0:
            history.append(value)
            return None
        
        z_score = abs(value - mean) / std
        
        history.append(value)
        
        if z_score > self.threshold:
            level = AlertLevel.CRITICAL if z_score > self.threshold * 1.5 else AlertLevel.WARNING
            return Alert(
                id=f"alert_{metric_name}_{datetime.now().timestamp()}",
                metric_name=metric_name,
                level=level,
                message=f"{metric_name} 异常值检测: {value:.2f} (Z-Score: {z_score:.2f})",
                timestamp=datetime.now(),
                value=value,
                threshold=mean + self.threshold * std
            )
        
        return None


class IntelligentDashboard:
    """
    V17.0 智能可视化面板
    
    提供实时数据监控、智能洞察和交互式分析能力。
    """
    
    _instance = None
    _lock = threading.Lock()
    
    def __new__(cls):
        with cls._lock:
            if cls._instance is None:
                cls._instance = super(IntelligentDashboard, cls).__new__(cls)
                cls._instance._initialized = False
        return cls._instance
    
    def __init__(self):
        if self._initialized:
            return
        
        self._initialized = True
        
        # 时间序列数据
        self.time_series: Dict[str, TimeSeries] = {}
        
        # 异常检测
        self.anomaly_detector = AnomalyDetector()
        
        # 告警
        self.alerts: List[Alert] = []
        self.alert_callbacks: List[Callable] = []
        
        # 仪表盘组件
        self.widgets: Dict[str, Widget] = {}
        
        # 指标收集间隔
        self.collection_interval = 5  # 秒
        self._running = False
        
        log.print_log("[V17.0] 📊 Intelligent Dashboard (智能可视化面板) 已初始化", "success")
    
    def register_metric(self, name: str, unit: str = ""):
        """注册指标"""
        if name not in self.time_series:
            self.time_series[name] = TimeSeries(name=name, unit=unit)
    
    def record_metric(self, name: str, value: Union[int, float], labels: Optional[Dict] = None):
        """记录指标"""
        if name not in self.time_series:
            self.register_metric(name)
        
        self.time_series[name].add(value)
        
        # 异常检测
        alert = self.anomaly_detector.detect(name, value)
        if alert:
            self._add_alert(alert)
    
    def _add_alert(self, alert: Alert):
        """添加告警"""
        self.alerts.append(alert)
        
        # 通知回调
        for callback in self.alert_callbacks:
            try:
                callback(alert)
            except Exception as e:
                log.print_log(f"[V17.0] 告警回调错误: {e}", "error")
        
        log.print_log(f"[V17.0] 🚨 告警: {alert.message}", "warning" if alert.level == AlertLevel.WARNING else "error")
    
    def get_metric(self, name: str) -> Optional[TimeSeries]:
        """获取指标"""
        return self.time_series.get(name)
    
    def query_metrics(
        self,
        pattern: str,
        start_time: Optional[datetime] = None,
        end_time: Optional[datetime] = None
    ) -> Dict[str, List[Dict]]:
        """查询指标"""
        results = {}
        
        for name, series in self.time_series.items():
            if pattern in name or pattern == "*":
                data = series.get_latest()
                
                # 时间过滤
                if start_time or end_time:
                    data = [
                        d for d in data
                        if (not start_time or d["timestamp"] >= start_time)
                        and (not end_time or d["timestamp"] <= end_time)
                    ]
                
                results[name] = data
        
        return results
    
    def create_widget(
        self,
        name: str,
        chart_type: ChartType,
        data_source: str,
        config: Optional[Dict] = None
    ) -> str:
        """创建仪表盘组件"""
        import uuid
        widget_id = str(uuid.uuid4())[:8]
        
        widget = Widget(
            id=widget_id,
            name=name,
            chart_type=chart_type,
            data_source=data_source,
            config=config or {}
        )
        
        self.widgets[widget_id] = widget
        return widget_id
    
    def get_widget_data(self, widget_id: str) -> Optional[Dict]:
        """获取组件数据"""
        widget = self.widgets.get(widget_id)
        if not widget:
            return None
        
        series = self.time_series.get(widget.data_source)
        if not series:
            return None
        
        return {
            "widget": {
                "id": widget.id,
                "name": widget.name,
                "type": widget.chart_type.value,
                "config": widget.config
            },
            "data": series.get_latest(100),
            "stats": series.get_stats()
        }
    
    def get_all_widgets(self) -> List[Dict]:
        """获取所有组件"""
        return [
            {
                "id": w.id,
                "name": w.name,
                "type": w.chart_type.value,
                "position": w.position,
                "data_source": w.data_source
            }
            for w in self.widgets.values()
        ]
    
    def get_alerts(
        self,
        level: Optional[AlertLevel] = None,
        acknowledged: Optional[bool] = None
    ) -> List[Alert]:
        """获取告警"""
        alerts = self.alerts
        
        if level:
            alerts = [a for a in alerts if a.level == level]
        
        if acknowledged is not None:
            alerts = [a for a in alerts if a.acknowledged == acknowledged]
        
        return sorted(alerts, key=lambda x: x.timestamp, reverse=True)
    
    def acknowledge_alert(self, alert_id: str) -> bool:
        """确认告警"""
        for alert in self.alerts:
            if alert.id == alert_id:
                alert.acknowledged = True
                return True
        return False
    
    def on_alert(self, callback: Callable):
        """注册告警回调"""
        self.alert_callbacks.append(callback)
    
    def natural_language_query(self, query: str) -> Dict[str, Any]:
        """自然语言查询"""
        # 简化实现 - 实际应该使用NLP
        query_lower = query.lower()
        
        response = {
            "query": query,
            "interpretation": "",
            "data": {}
        }
        
        if "平均" in query or "average" in query_lower or "mean" in query_lower:
            response["interpretation"] = "查询平均值"
            for name, series in self.time_series.items():
                stats = series.get_stats()
                if stats:
                    response["data"][name] = {"mean": stats.get("mean", 0)}
        
        elif "最新" in query or "latest" in query_lower or "current" in query_lower:
            response["interpretation"] = "查询最新值"
            for name, series in self.time_series.items():
                stats = series.get_stats()
                if stats:
                    response["data"][name] = {"latest": stats.get("latest", 0)}
        
        elif "告警" in query or "alert" in query_lower:
            response["interpretation"] = "查询告警"
            response["data"]["alerts"] = len(self.get_alerts(acknowledged=False))
        
        else:
            response["interpretation"] = "查询所有指标"
            for name, series in self.time_series.items():
                response["data"][name] = series.get_stats()
        
        return response
    
    def get_summary(self) -> Dict[str, Any]:
        """获取仪表盘摘要"""
        return {
            "total_metrics": len(self.time_series),
            "total_widgets": len(self.widgets),
            "active_alerts": len(self.get_alerts(acknowledged=False)),
            "metrics_summary": {
                name: series.get_stats()
                for name, series in self.time_series.items()
            }
        }


# 全局实例
_intelligent_dashboard = None


def get_intelligent_dashboard() -> IntelligentDashboard:
    """获取智能仪表盘全局实例"""
    global _intelligent_dashboard
    if _intelligent_dashboard is None:
        _intelligent_dashboard = IntelligentDashboard()
    return _intelligent_dashboard
