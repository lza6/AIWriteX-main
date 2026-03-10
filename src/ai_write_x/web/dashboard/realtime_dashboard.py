"""
AIWriteX V18.1 - Realtime Dashboard Module
实时数据可视化面板 - 创作过程实时监控

功能:
1. 实时数据流展示: WebSocket推送实时更新
2. 多维度指标监控: CPU、内存、API调用、内容生成进度
3. 创作过程可视化: 文章生成各阶段进度追踪
4. 效果对比面板: A/B测试结果实时展示
5. 智能告警系统: 异常指标自动检测和通知
"""

import asyncio
import json
import time
from typing import Dict, List, Optional, Any, Callable
from dataclasses import dataclass, field, asdict
from datetime import datetime, timedelta
from enum import Enum, auto
from collections import deque, defaultdict
import numpy as np
from uuid import UUID, uuid4


class WidgetType(Enum):
    """仪表板组件类型"""
    LINE_CHART = "line_chart"           # 折线图 - 趋势展示
    BAR_CHART = "bar_chart"             # 柱状图 - 对比展示
    PIE_CHART = "pie_chart"             # 饼图 - 占比展示
    GAUGE = "gauge"                     # 仪表盘 - 单一指标
    HEATMAP = "heatmap"                 # 热力图 - 密度分布
    PROGRESS = "progress"               # 进度条 - 任务进度
    LOG_VIEWER = "log_viewer"           # 日志查看器
    METRIC_CARD = "metric_card"         # 指标卡片
    COMPARISON = "comparison"           # 对比视图


class AlertLevel(Enum):
    """告警级别"""
    INFO = "info"
    WARNING = "warning"
    ERROR = "error"
    CRITICAL = "critical"


@dataclass
class MetricPoint:
    """指标数据点"""
    timestamp: datetime
    value: float
    metadata: Dict[str, Any] = field(default_factory=dict)


@dataclass
class DashboardWidget:
    """仪表板组件配置"""
    id: str
    title: str
    type: WidgetType
    data_source: str                    # 数据源标识
    refresh_interval: int = 5           # 刷新间隔(秒)
    config: Dict[str, Any] = field(default_factory=dict)
    position: Dict[str, int] = field(default_factory=lambda: {"x": 0, "y": 0, "w": 6, "h": 4})
    created_at: datetime = field(default_factory=datetime.now)


@dataclass
class AlertRule:
    """告警规则"""
    id: str
    name: str
    metric: str                         # 监控指标
    condition: str                      # 条件: >, <, ==, >=, <=
    threshold: float                    # 阈值
    level: AlertLevel
    message: str
    enabled: bool = True
    cooldown: int = 300                 # 冷却时间(秒)
    last_triggered: Optional[datetime] = None


@dataclass
class AlertEvent:
    """告警事件"""
    id: str
    rule_id: str
    level: AlertLevel
    message: str
    metric_value: float
    timestamp: datetime = field(default_factory=datetime.now)
    acknowledged: bool = False


class RealtimeDashboard:
    """
    实时数据可视化面板
    
    核心功能:
    - 实时数据流处理
    - 多维度指标监控
    - 创作过程可视化
    - 智能告警系统
    """
    
    _instance = None
    
    def __new__(cls):
        if cls._instance is None:
            cls._instance = super().__new__(cls)
            cls._instance._initialized = False
        return cls._instance
    
    def __init__(self):
        if self._initialized:
            return
            
        self._initialized = True
        self.widgets: Dict[str, DashboardWidget] = {}
        self.metrics_history: Dict[str, deque] = defaultdict(lambda: deque(maxlen=1000))
        self.alert_rules: Dict[str, AlertRule] = {}
        self.active_alerts: List[AlertEvent] = []
        self.subscribers: List[Callable] = []
        self._running = False
        self._update_task = None
        
        # 默认指标定义
        self._default_metrics = {
            "cpu_usage": {"label": "CPU使用率", "unit": "%", "max": 100},
            "memory_usage": {"label": "内存使用", "unit": "MB", "max": 4096},
            "api_calls": {"label": "API调用次数", "unit": "次/分", "max": 1000},
            "content_generated": {"label": "内容生成数", "unit": "篇/时", "max": 100},
            "active_agents": {"label": "活跃智能体", "unit": "个", "max": 50},
            "avg_response_time": {"label": "平均响应时间", "unit": "ms", "max": 5000},
            "success_rate": {"label": "成功率", "unit": "%", "max": 100},
        }
        
        # 默认告警规则
        self._init_default_rules()
        
    def _init_default_rules(self):
        """初始化默认告警规则"""
        default_rules = [
            AlertRule(
                id="rule_cpu_high",
                name="CPU使用率过高",
                metric="cpu_usage",
                condition=">",
                threshold=80.0,
                level=AlertLevel.WARNING,
                message="CPU使用率超过80%，可能影响系统性能"
            ),
            AlertRule(
                id="rule_memory_high",
                name="内存使用过高",
                metric="memory_usage",
                condition=">",
                threshold=3072.0,
                level=AlertLevel.WARNING,
                message="内存使用超过3GB，建议清理缓存"
            ),
            AlertRule(
                id="rule_api_error",
                name="API错误率过高",
                metric="success_rate",
                condition="<",
                threshold=95.0,
                level=AlertLevel.ERROR,
                message="API成功率低于95%，请检查外部服务"
            ),
            AlertRule(
                id="rule_response_slow",
                name="响应时间过长",
                metric="avg_response_time",
                condition=">",
                threshold=3000.0,
                level=AlertLevel.WARNING,
                message="平均响应时间超过3秒"
            ),
        ]
        
        for rule in default_rules:
            self.alert_rules[rule.id] = rule
    
    async def start(self):
        """启动仪表板"""
        if self._running:
            return
            
        self._running = True
        self._update_task = asyncio.create_task(self._update_loop())
        
        # 创建默认组件
        self._create_default_widgets()
        
    def _create_default_widgets(self):
        """创建默认仪表板组件"""
        default_widgets = [
            DashboardWidget(
                id="widget_cpu",
                title="CPU使用率",
                type=WidgetType.GAUGE,
                data_source="cpu_usage",
                position={"x": 0, "y": 0, "w": 3, "h": 3}
            ),
            DashboardWidget(
                id="widget_memory",
                title="内存使用",
                type=WidgetType.GAUGE,
                data_source="memory_usage",
                position={"x": 3, "y": 0, "w": 3, "h": 3}
            ),
            DashboardWidget(
                id="widget_api_trend",
                title="API调用趋势",
                type=WidgetType.LINE_CHART,
                data_source="api_calls",
                position={"x": 6, "y": 0, "w": 6, "h": 4}
            ),
            DashboardWidget(
                id="widget_content_progress",
                title="内容生成进度",
                type=WidgetType.PROGRESS,
                data_source="content_generated",
                position={"x": 0, "y": 3, "w": 6, "h": 2}
            ),
            DashboardWidget(
                id="widget_agent_status",
                title="智能体状态",
                type=WidgetType.PIE_CHART,
                data_source="active_agents",
                position={"x": 6, "y": 4, "w": 3, "h": 3}
            ),
            DashboardWidget(
                id="widget_success_rate",
                title="成功率",
                type=WidgetType.METRIC_CARD,
                data_source="success_rate",
                position={"x": 9, "y": 4, "w": 3, "h": 2}
            ),
        ]
        
        for widget in default_widgets:
            self.widgets[widget.id] = widget
    
    async def stop(self):
        """停止仪表板"""
        self._running = False
        if self._update_task:
            self._update_task.cancel()
            try:
                await self._update_task
            except asyncio.CancelledError:
                pass
    
    async def _update_loop(self):
        """数据更新循环"""
        while self._running:
            try:
                # 收集系统指标
                await self._collect_metrics()
                
                # 检查告警规则
                await self._check_alerts()
                
                # 通知订阅者
                await self._notify_subscribers()
                
                await asyncio.sleep(5)  # 每5秒更新一次
            except Exception as e:
                await asyncio.sleep(5)
    
    async def _collect_metrics(self):
        """收集系统指标"""
        import psutil
        
        # CPU使用率
        cpu_percent = psutil.cpu_percent(interval=1)
        self.record_metric("cpu_usage", cpu_percent)
        
        # 内存使用
        memory = psutil.virtual_memory()
        memory_mb = memory.used / 1024 / 1024
        self.record_metric("memory_usage", memory_mb)
        
        # 其他指标由外部模块推送
    
    def record_metric(self, metric_name: str, value: float, metadata: Dict = None):
        """
        记录指标数据
        
        Args:
            metric_name: 指标名称
            value: 指标值
            metadata: 额外元数据
        """
        point = MetricPoint(
            timestamp=datetime.now(),
            value=value,
            metadata=metadata or {}
        )
        self.metrics_history[metric_name].append(point)
        
    def get_metric_history(
        self,
        metric_name: str,
        duration: timedelta = timedelta(hours=1)
    ) -> List[MetricPoint]:
        """
        获取指标历史数据
        
        Args:
            metric_name: 指标名称
            duration: 时间范围
            
        Returns:
            指标数据点列表
        """
        if metric_name not in self.metrics_history:
            return []
            
        cutoff_time = datetime.now() - duration
        return [
            point for point in self.metrics_history[metric_name]
            if point.timestamp > cutoff_time
        ]
    
    def get_current_value(self, metric_name: str) -> Optional[float]:
        """获取指标当前值"""
        if metric_name not in self.metrics_history:
            return None
            
        history = self.metrics_history[metric_name]
        if not history:
            return None
            
        return history[-1].value
    
    async def _check_alerts(self):
        """检查告警规则"""
        for rule in self.alert_rules.values():
            if not rule.enabled:
                continue
                
            # 检查冷却时间
            if rule.last_triggered:
                cooldown_end = rule.last_triggered + timedelta(seconds=rule.cooldown)
                if datetime.now() < cooldown_end:
                    continue
            
            # 获取当前值
            current_value = self.get_current_value(rule.metric)
            if current_value is None:
                continue
            
            # 检查条件
            triggered = False
            if rule.condition == ">" and current_value > rule.threshold:
                triggered = True
            elif rule.condition == "<" and current_value < rule.threshold:
                triggered = True
            elif rule.condition == ">=" and current_value >= rule.threshold:
                triggered = True
            elif rule.condition == "<=" and current_value <= rule.threshold:
                triggered = True
            elif rule.condition == "==" and current_value == rule.threshold:
                triggered = True
            
            if triggered:
                await self._trigger_alert(rule, current_value)
    
    async def _trigger_alert(self, rule: AlertRule, value: float):
        """触发告警"""
        rule.last_triggered = datetime.now()
        
        alert = AlertEvent(
            id=str(uuid4()),
            rule_id=rule.id,
            level=rule.level,
            message=rule.message,
            metric_value=value
        )
        
        self.active_alerts.append(alert)
        
        # 限制告警数量
        if len(self.active_alerts) > 100:
            self.active_alerts = self.active_alerts[-100:]
    
    async def _notify_subscribers(self):
        """通知订阅者"""
        if not self.subscribers:
            return
            
        data = self._prepare_dashboard_data()
        
        for callback in self.subscribers:
            try:
                if asyncio.iscoroutinefunction(callback):
                    asyncio.create_task(callback(data))
                else:
                    callback(data)
            except Exception:
                pass
    
    def _prepare_dashboard_data(self) -> Dict:
        """准备仪表板数据"""
        return {
            "timestamp": datetime.now().isoformat(),
            "widgets": {
                widget_id: {
                    "title": widget.title,
                    "type": widget.type.value,
                    "current_value": self.get_current_value(widget.data_source),
                    "history": [
                        {
                            "timestamp": point.timestamp.isoformat(),
                            "value": point.value
                        }
                        for point in list(self.metrics_history.get(widget.data_source, []))[-100:]
                    ]
                }
                for widget_id, widget in self.widgets.items()
            },
            "alerts": [
                {
                    "id": alert.id,
                    "level": alert.level.value,
                    "message": alert.message,
                    "metric_value": alert.metric_value,
                    "timestamp": alert.timestamp.isoformat(),
                    "acknowledged": alert.acknowledged
                }
                for alert in self.active_alerts[-10:]  # 最近10条
            ],
            "system_status": self._get_system_status()
        }
    
    def _get_system_status(self) -> Dict:
        """获取系统状态"""
        cpu = self.get_current_value("cpu_usage") or 0
        memory = self.get_current_value("memory_usage") or 0
        success_rate = self.get_current_value("success_rate") or 100
        
        # 计算综合健康度
        health_score = 100
        if cpu > 80:
            health_score -= 20
        if memory > 3072:
            health_score -= 20
        if success_rate < 95:
            health_score -= 30
            
        status = "healthy"
        if health_score < 50:
            status = "critical"
        elif health_score < 75:
            status = "warning"
        
        return {
            "health_score": health_score,
            "status": status,
            "active_widgets": len(self.widgets),
            "active_alerts": len([a for a in self.active_alerts if not a.acknowledged]),
            "metrics_count": len(self.metrics_history)
        }
    
    def subscribe(self, callback: Callable):
        """订阅数据更新"""
        self.subscribers.append(callback)
    
    def unsubscribe(self, callback: Callable):
        """取消订阅"""
        if callback in self.subscribers:
            self.subscribers.remove(callback)
    
    def add_widget(self, widget: DashboardWidget) -> str:
        """添加组件"""
        self.widgets[widget.id] = widget
        return widget.id
    
    def remove_widget(self, widget_id: str):
        """移除组件"""
        if widget_id in self.widgets:
            del self.widgets[widget_id]
    
    def add_alert_rule(self, rule: AlertRule) -> str:
        """添加告警规则"""
        self.alert_rules[rule.id] = rule
        return rule.id
    
    def acknowledge_alert(self, alert_id: str):
        """确认告警"""
        for alert in self.active_alerts:
            if alert.id == alert_id:
                alert.acknowledged = True
                break
    
    def get_dashboard_config(self) -> Dict:
        """获取仪表板配置"""
        return {
            "widgets": [
                {
                    "id": w.id,
                    "title": w.title,
                    "type": w.type.value,
                    "position": w.position,
                    "config": w.config
                }
                for w in self.widgets.values()
            ],
            "alert_rules": [
                {
                    "id": r.id,
                    "name": r.name,
                    "metric": r.metric,
                    "condition": r.condition,
                    "threshold": r.threshold,
                    "level": r.level.value,
                    "enabled": r.enabled
                }
                for r in self.alert_rules.values()
            ],
            "metrics": self._default_metrics
        }


# 全局仪表板实例
dashboard = RealtimeDashboard()


async def get_dashboard() -> RealtimeDashboard:
    """获取仪表板实例"""
    if not dashboard._running:
        await dashboard.start()
    return dashboard
