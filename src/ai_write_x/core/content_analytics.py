# -*- coding: UTF-8 -*-
"""
V16.0 - Content Analytics (内容效果分析追踪)

追踪和分析内容发布后的表现：
1. 多维度效果指标 (阅读量、点赞、分享、转化率)
2. 时间序列分析 (生命周期曲线)
3. 归因分析 (什么因素导致了成功)
4. 用户行为路径追踪
5. 自动报告生成
"""

import json
from datetime import datetime, timedelta
from typing import Dict, List, Optional, Any, Tuple
from dataclasses import dataclass, field
from collections import defaultdict
import threading

import numpy as np
from scipy import stats

from src.ai_write_x.utils import log
from src.ai_write_x.database.db_manager import db_manager


@dataclass
class ContentMetrics:
    """内容指标"""
    content_id: str
    content_title: str
    
    # 基础指标
    impressions: int = 0  # 曝光
    views: int = 0  # 阅读
    likes: int = 0  # 点赞
    shares: int = 0  # 分享
    comments: int = 0  # 评论
    clicks: int = 0  # 点击
    
    # 深度指标
    avg_read_time: float = 0.0  # 平均阅读时长 (秒)
    bounce_rate: float = 0.0  # 跳出率
    scroll_depth: float = 0.0  # 平均滚动深度 (0-1)
    
    # 转化指标
    conversions: int = 0  # 转化次数
    conversion_value: float = 0.0  # 转化价值
    
    # 时间
    publish_time: datetime = field(default_factory=datetime.now)
    last_updated: datetime = field(default_factory=datetime.now)
    
    @property
    def ctr(self) -> float:
        """点击率"""
        return self.clicks / max(self.impressions, 1)
    
    @property
    def engagement_rate(self) -> float:
        """参与率"""
        engagements = self.likes + self.shares + self.comments
        return engagements / max(self.views, 1)
    
    @property
    def conversion_rate(self) -> float:
        """转化率"""
        return self.conversions / max(self.views, 1)
    
    @property
    def virality_score(self) -> float:
        """传播分数 (分享/阅读比)"""
        return min(self.shares / max(self.views, 1) * 100, 100)
    
    @property
    def quality_score(self) -> float:
        """综合质量分数 (0-100)"""
        # 加权计算
        view_weight = 0.2
        engagement_weight = 0.3
        time_weight = 0.2
        depth_weight = 0.15
        virality_weight = 0.15
        
        # 归一化
        view_score = min(self.views / 1000, 1.0) * 100
        engagement_score = self.engagement_rate * 100
        time_score = min(self.avg_read_time / 300, 1.0) * 100  # 5分钟为满分
        depth_score = self.scroll_depth * 100
        virality_score = self.virality_score
        
        return (
            view_score * view_weight +
            engagement_score * engagement_weight +
            time_score * time_weight +
            depth_score * depth_weight +
            virality_score * virality_weight
        )


@dataclass
class TimeSeriesPoint:
    """时间序列数据点"""
    timestamp: datetime
    metric_name: str
    value: float


@dataclass
class ContentLifecycle:
    """内容生命周期分析"""
    content_id: str
    
    # 阶段划分
    burst_phase_end: Optional[datetime] = None  # 爆发期结束
    steady_phase_end: Optional[datetime] = None  # 稳定期结束
    decline_phase_start: Optional[datetime] = None  # 衰退期开始
    
    # 关键指标
    peak_views_per_hour: float = 0.0
    total_lifecycle_days: float = 0.0
    
    # 预测
    predicted_remaining_value: float = 0.0


class AttributionAnalyzer:
    """归因分析器 - 分析成功因素"""
    
    def __init__(self):
        self.factor_correlations: Dict[str, float] = {}
    
    def analyze_success_factors(
        self,
        content_list: List[ContentMetrics],
        min_success_threshold: float = 70.0
    ) -> Dict[str, Any]:
        """
        分析成功内容的共同因素
        
        Args:
            content_list: 内容列表
            min_success_threshold: 成功阈值 (质量分数)
        
        Returns:
            归因分析报告
        """
        # 分离成功和失败内容
        successful = [c for c in content_list if c.quality_score >= min_success_threshold]
        unsuccessful = [c for c in content_list if c.quality_score < min_success_threshold]
        
        if not successful or not unsuccessful:
            return {"error": "样本不足"}
        
        # 分析因素 (简化版 - 实际应包含更多因素)
        factors = {
            "avg_engagement_rate": {
                "successful": np.mean([c.engagement_rate for c in successful]),
                "unsuccessful": np.mean([c.engagement_rate for c in unsuccessful])
            },
            "avg_read_time": {
                "successful": np.mean([c.avg_read_time for c in successful]),
                "unsuccessful": np.mean([c.avg_read_time for c in unsuccessful])
            },
            "avg_scroll_depth": {
                "successful": np.mean([c.scroll_depth for c in successful]),
                "unsuccessful": np.mean([c.scroll_depth for c in unsuccessful])
            }
        }
        
        # 计算影响程度
        insights = []
        for factor, values in factors.items():
            diff = values["successful"] - values["unsuccessful"]
            if abs(diff) > 0.1:  # 显著差异
                direction = "正向" if diff > 0 else "负向"
                insights.append({
                    "factor": factor,
                    "impact": direction,
                    "difference": round(diff, 3),
                    "significance": "高" if abs(diff) > 0.2 else "中"
                })
        
        # 排序影响程度
        insights.sort(key=lambda x: abs(x["difference"]), reverse=True)
        
        return {
            "success_count": len(successful),
            "unsuccess_count": len(unsuccessful),
            "success_rate": len(successful) / len(content_list),
            "key_factors": insights[:5],  # Top 5 因素
            "factor_comparison": factors
        }


class ContentAnalytics:
    """
    V16.0 内容效果分析追踪系统
    
    功能：
    1. 实时指标追踪
    2. 生命周期分析
    3. 归因分析
    4. 自动报告生成
    5. 异常检测
    """
    
    _instance = None
    _lock = threading.Lock()
    
    def __new__(cls):
        with cls._lock:
            if cls._instance is None:
                cls._instance = super(ContentAnalytics, cls).__new__(cls)
                cls._instance._initialized = False
        return cls._instance
    
    def __init__(self):
        if self._initialized:
            return
        
        self._initialized = True
        self.metrics_cache: Dict[str, ContentMetrics] = {}
        self.time_series_data: Dict[str, List[TimeSeriesPoint]] = defaultdict(list)
        self.attribution_analyzer = AttributionAnalyzer()
        
        log.print_log("[V16.0] 📊 Content Analytics (内容效果分析) 已初始化", "success")
    
    def track_content(
        self,
        content_id: str,
        content_title: str,
        publish_time: Optional[datetime] = None
    ) -> ContentMetrics:
        """开始追踪新内容"""
        metrics = ContentMetrics(
            content_id=content_id,
            content_title=content_title,
            publish_time=publish_time or datetime.now()
        )
        self.metrics_cache[content_id] = metrics
        return metrics
    
    def update_metric(
        self,
        content_id: str,
        metric_name: str,
        value: float,
        accumulate: bool = True
    ):
        """更新指标"""
        if content_id not in self.metrics_cache:
            return
        
        metrics = self.metrics_cache[content_id]
        
        # 更新指标
        if hasattr(metrics, metric_name):
            current = getattr(metrics, metric_name)
            if accumulate:
                setattr(metrics, metric_name, current + value)
            else:
                setattr(metrics, metric_name, value)
        
        # 更新时间
        metrics.last_updated = datetime.now()
        
        # 记录时间序列
        self.time_series_data[content_id].append(TimeSeriesPoint(
            timestamp=datetime.now(),
            metric_name=metric_name,
            value=value if not accumulate else getattr(metrics, metric_name)
        ))
    
    def batch_update_metrics(self, content_id: str, updates: Dict[str, float]):
        """批量更新指标"""
        for metric_name, value in updates.items():
            self.update_metric(content_id, metric_name, value)
    
    def get_metrics(self, content_id: str) -> Optional[ContentMetrics]:
        """获取内容指标"""
        return self.metrics_cache.get(content_id)
    
    def get_top_performing(
        self,
        metric: str = "quality_score",
        n: int = 10,
        time_range: Optional[tuple] = None
    ) -> List[ContentMetrics]:
        """获取表现最佳的内容"""
        contents = list(self.metrics_cache.values())
        
        # 时间过滤
        if time_range:
            start, end = time_range
            contents = [
                c for c in contents 
                if start <= c.publish_time <= end
            ]
        
        # 排序
        contents.sort(key=lambda x: getattr(x, metric, 0), reverse=True)
        
        return contents[:n]
    
    def analyze_lifecycle(self, content_id: str) -> ContentLifecycle:
        """分析内容生命周期"""
        if content_id not in self.time_series_data:
            return ContentLifecycle(content_id=content_id)
        
        data = self.time_series_data[content_id]
        
        # 按时间排序
        views_data = [p for p in data if p.metric_name == "views"]
        views_data.sort(key=lambda x: x.timestamp)
        
        if not views_data:
            return ContentLifecycle(content_id=content_id)
        
        # 计算每小时阅读数
        hourly_views = defaultdict(float)
        for point in views_data:
            hour_key = point.timestamp.replace(minute=0, second=0, microsecond=0)
            hourly_views[hour_key] += point.value
        
        if not hourly_views:
            return ContentLifecycle(content_id=content_id)
        
        # 找到峰值
        peak_hour = max(hourly_views.keys(), key=lambda h: hourly_views[h])
        peak_value = hourly_views[peak_hour]
        
        # 确定阶段 (简化算法)
        sorted_hours = sorted(hourly_views.keys())
        lifecycle = ContentLifecycle(
            content_id=content_id,
            peak_views_per_hour=peak_value,
            total_lifecycle_days=(sorted_hours[-1] - sorted_hours[0]).total_seconds() / 86400
        )
        
        # 找到爆发期结束 (阅读数下降到峰值的 50%)
        for hour in sorted_hours:
            if hourly_views[hour] < peak_value * 0.5:
                lifecycle.burst_phase_end = hour
                break
        
        return lifecycle
    
    def detect_anomalies(self, content_id: str) -> List[Dict]:
        """检测异常表现"""
        if content_id not in self.time_series_data:
            return []
        
        data = self.time_series_data[content_id]
        anomalies = []
        
        # 按指标分组
        metric_groups = defaultdict(list)
        for point in data:
            metric_groups[point.metric_name].append(point)
        
        # 对每个指标进行异常检测 (Z-score)
        for metric_name, points in metric_groups.items():
            if len(points) < 10:
                continue
            
            values = [p.value for p in points]
            mean = np.mean(values)
            std = np.std(values)
            
            if std == 0:
                continue
            
            for point in points:
                z_score = abs(point.value - mean) / std
                if z_score > 2.5:  # 异常阈值
                    anomalies.append({
                        "timestamp": point.timestamp.isoformat(),
                        "metric": metric_name,
                        "value": point.value,
                        "z_score": round(z_score, 2),
                        "type": "spike" if point.value > mean else "drop"
                    })
        
        return anomalies
    
    def generate_report(
        self,
        time_range: Optional[tuple] = None,
        include_attribution: bool = True
    ) -> Dict[str, Any]:
        """生成分析报告"""
        report = {
            "generated_at": datetime.now().isoformat(),
            "period": {
                "start": time_range[0].isoformat() if time_range else None,
                "end": time_range[1].isoformat() if time_range else None
            }
        }
        
        # 获取范围内的内容
        contents = list(self.metrics_cache.values())
        if time_range:
            start, end = time_range
            contents = [c for c in contents if start <= c.publish_time <= end]
        
        if not contents:
            report["summary"] = "该时间段内无内容数据"
            return report
        
        # 汇总统计
        report["summary"] = {
            "total_contents": len(contents),
            "total_views": sum(c.views for c in contents),
            "total_engagements": sum(c.likes + c.shares + c.comments for c in contents),
            "avg_quality_score": round(np.mean([c.quality_score for c in contents]), 2),
            "avg_engagement_rate": round(np.mean([c.engagement_rate for c in contents]), 4),
        }
        
        # Top 表现
        report["top_performers"] = [
            {
                "content_id": c.content_id,
                "title": c.content_title[:50],
                "quality_score": round(c.quality_score, 2),
                "views": c.views,
                "engagement_rate": round(c.engagement_rate, 4)
            }
            for c in self.get_top_performing(n=5, time_range=time_range)
        ]
        
        # 归因分析
        if include_attribution and len(contents) >= 10:
            report["attribution"] = self.attribution_analyzer.analyze_success_factors(contents)
        
        # 趋势分析
        if len(contents) >= 2:
            publish_times = [c.publish_time for c in contents]
            quality_scores = [c.quality_score for c in contents]
            
            # 简单线性趋势
            if len(set(publish_times)) > 1:
                time_numeric = [(t - min(publish_times)).total_seconds() for t in publish_times]
                slope, intercept, r_value, p_value, std_err = stats.linregress(time_numeric, quality_scores)
                
                report["quality_trend"] = {
                    "slope": round(slope, 6),
                    "r_squared": round(r_value ** 2, 4),
                    "trend": "improving" if slope > 0 else "declining" if slope < 0 else "stable"
                }
        
        return report
    
    def export_data(self, format: str = "json") -> str:
        """导出分析数据"""
        data = {
            "metrics": {
                cid: {
                    "content_id": m.content_id,
                    "title": m.content_title,
                    "views": m.views,
                    "engagement_rate": m.engagement_rate,
                    "quality_score": m.quality_score,
                    "publish_time": m.publish_time.isoformat()
                }
                for cid, m in self.metrics_cache.items()
            },
            "exported_at": datetime.now().isoformat()
        }
        
        if format == "json":
            return json.dumps(data, indent=2, ensure_ascii=False)
        
        return str(data)


# 全局实例
_content_analytics = None


def get_content_analytics() -> ContentAnalytics:
    """获取内容分析系统全局实例"""
    global _content_analytics
    if _content_analytics is None:
        _content_analytics = ContentAnalytics()
    return _content_analytics
