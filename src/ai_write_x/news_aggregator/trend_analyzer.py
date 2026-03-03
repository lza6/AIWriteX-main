# -*- coding: utf-8 -*-
"""
趋势分析器
实现热点趋势识别、预测、时间序列分析
"""

from typing import Dict, List, Any, Optional
from dataclasses import dataclass, field
from datetime import datetime, timedelta
from collections import defaultdict, Counter
import statistics

from src.ai_write_x.utils import log


@dataclass
class TrendItem:
    """趋势项"""
    keyword: str
    count: int = 0
    growth_rate: float = 0.0          # 增长率
    peak_time: Optional[datetime] = None
    sources: List[str] = field(default_factory=list)
    related_keywords: List[str] = field(default_factory=list)
    sentiment_score: float = 0.0
    hot_score: float = 0.0            # 热度分数


@dataclass
class TrendReport:
    """趋势报告"""
    generated_at: datetime = field(default_factory=datetime.now)
    time_window: str = ""             # 时间窗口（如"24h", "7d"）
    top_trends: List[TrendItem] = field(default_factory=list)
    emerging_trends: List[TrendItem] = field(default_factory=list)  # 新兴趋势
    declining_trends: List[TrendItem] = field(default_factory=list)  # 下降趋势
    category_distribution: Dict[str, int] = field(default_factory=dict)
    heatmap_data: Dict[str, Any] = field(default_factory=dict)


class TrendAnalyzer:
    """趋势分析器"""
    
    def __init__(self, history_window_days: int = 7):
        self.history_window_days = history_window_days
        self.history_data = defaultdict(list)  # keyword -> [daily_count]
        self.trend_cache = {}
    
    def analyze_trends(self, contents: List[Dict[str, Any]], 
                      time_window: str = "24h") -> TrendReport:
        """
        分析内容趋势
        
        Args:
            contents: 内容列表
            time_window: 时间窗口
            
        Returns:
            趋势报告
        """
        report = TrendReport(time_window=time_window)
        
        # 提取所有关键词
        all_keywords = []
        keyword_sources = defaultdict(set)
        keyword_timestamps = defaultdict(list)
        
        for content in contents:
            keywords = content.get('keywords', [])
            source = content.get('source', 'unknown')
            timestamp = content.get('published_at', datetime.now())
            
            for kw in keywords:
                all_keywords.append(kw)
                keyword_sources[kw].add(source)
                keyword_timestamps[kw].append(timestamp)
        
        # 统计词频
        keyword_counts = Counter(all_keywords)
        
        # 计算趋势
        trends = []
        for keyword, count in keyword_counts.most_common(50):
            trend = TrendItem(
                keyword=keyword,
                count=count,
                sources=list(keyword_sources[keyword]),
                related_keywords=self._find_related_keywords(keyword, contents)
            )
            
            # 计算增长率
            trend.growth_rate = self._calculate_growth_rate(keyword)
            
            # 计算热度分数
            trend.hot_score = self._calculate_hot_score(trend)
            
            # 找出峰值时间
            if keyword_timestamps[keyword]:
                timestamps = sorted(keyword_timestamps[keyword])
                trend.peak_time = timestamps[len(timestamps) // 2]
            
            trends.append(trend)
            
            # 更新历史数据
            self._update_history(keyword, count)
        
        # 分类趋势
        trends.sort(key=lambda x: x.hot_score, reverse=True)
        
        report.top_trends = trends[:20]
        report.emerging_trends = [t for t in trends if t.growth_rate > 0.5][:10]
        report.declining_trends = [t for t in trends if t.growth_rate < -0.2][:10]
        
        # 分类分布
        report.category_distribution = self._analyze_category_distribution(contents)
        
        # 热力图数据
        report.heatmap_data = self._generate_heatmap_data(contents)
        
        log.print_log(f"[TrendAnalyzer] 趋势分析完成: 发现 {len(trends)} 个趋势")
        
        return report
    
    def _calculate_growth_rate(self, keyword: str) -> float:
        """计算关键词增长率"""
        history = self.history_data.get(keyword, [])
        
        if len(history) < 2:
            return 0.0
        
        # 计算最近两天的增长率
        recent = history[-1] if history else 0
        previous = history[-2] if len(history) > 1 else 1
        
        if previous == 0:
            return 1.0 if recent > 0 else 0.0
        
        return (recent - previous) / previous
    
    def _calculate_hot_score(self, trend: TrendItem) -> float:
        """计算热度分数"""
        # 基础分数（基于出现次数）
        base_score = min(trend.count * 10, 100)
        
        # 增长率加成
        growth_bonus = trend.growth_rate * 20 if trend.growth_rate > 0 else 0
        
        # 多源加成
        source_bonus = len(trend.sources) * 5
        
        # 综合分数
        hot_score = base_score + growth_bonus + source_bonus
        
        return min(hot_score, 100)
    
    def _find_related_keywords(self, keyword: str, 
                               contents: List[Dict[str, Any]], 
                               top_n: int = 5) -> List[str]:
        """查找相关关键词"""
        # 找到包含该关键词的所有内容的其他关键词
        cooccurrence = Counter()
        
        for content in contents:
            keywords = content.get('keywords', [])
            if keyword in keywords:
                for kw in keywords:
                    if kw != keyword:
                        cooccurrence[kw] += 1
        
        return [kw for kw, _ in cooccurrence.most_common(top_n)]
    
    def _update_history(self, keyword: str, count: int):
        """更新历史数据"""
        self.history_data[keyword].append(count)
        
        # 只保留最近N天的数据
        max_history = self.history_window_days
        if len(self.history_data[keyword]) > max_history:
            self.history_data[keyword] = self.history_data[keyword][-max_history:]
    
    def _analyze_category_distribution(self, contents: List[Dict[str, Any]]) -> Dict[str, int]:
        """分析分类分布"""
        categories = [c.get('category', '其他') for c in contents]
        return dict(Counter(categories))
    
    def _generate_heatmap_data(self, contents: List[Dict[str, Any]]) -> Dict[str, Any]:
        """生成热力图数据"""
        hourly_distribution = defaultdict(int)
        source_distribution = defaultdict(int)
        
        for content in contents:
            timestamp = content.get('published_at', datetime.now())
            if isinstance(timestamp, str):
                try:
                    timestamp = datetime.fromisoformat(timestamp.replace('Z', '+00:00'))
                except:
                    continue
            
            hour = timestamp.hour
            hourly_distribution[hour] += 1
            
            source = content.get('source', 'unknown')
            source_distribution[source] += 1
        
        return {
            "hourly": dict(hourly_distribution),
            "by_source": dict(source_distribution),
        }
    
    def predict_trend(self, keyword: str, days_ahead: int = 1) -> Dict[str, Any]:
        """
        预测关键词趋势
        
        Args:
            keyword: 关键词
            days_ahead: 预测未来天数
            
        Returns:
            预测结果
        """
        history = self.history_data.get(keyword, [])
        
        if len(history) < 3:
            return {
                "keyword": keyword,
                "predictable": False,
                "reason": "历史数据不足"
            }
        
        # 简单线性回归预测
        x = list(range(len(history)))
        y = history
        
        n = len(x)
        sum_x = sum(x)
        sum_y = sum(y)
        sum_xy = sum(xi * yi for xi, yi in zip(x, y))
        sum_x2 = sum(xi ** 2 for xi in x)
        
        # 计算斜率和截距
        slope = (n * sum_xy - sum_x * sum_y) / (n * sum_x2 - sum_x ** 2) if (n * sum_x2 - sum_x ** 2) != 0 else 0
        intercept = (sum_y - slope * sum_x) / n
        
        # 预测未来值
        future_x = len(history) + days_ahead - 1
        prediction = slope * future_x + intercept
        
        # 计算置信度（基于历史波动）
        if len(history) > 1:
            variance = statistics.variance(history) if len(history) > 1 else 0
            std_dev = statistics.stdev(history) if len(history) > 1 else 0
            confidence = max(0, 1 - std_dev / max(sum_y / n, 1)) if n > 0 else 0
        else:
            confidence = 0.5
        
        return {
            "keyword": keyword,
            "predictable": True,
            "current_count": history[-1] if history else 0,
            "predicted_count": max(0, int(prediction)),
            "growth_trend": "up" if slope > 0 else "down" if slope < 0 else "stable",
            "confidence": round(confidence, 2),
            "days_ahead": days_ahead
        }
    
    def get_burst_events(self, contents: List[Dict[str, Any]], 
                        threshold: float = 3.0) -> List[Dict[str, Any]]:
        """
        检测突发性事件
        
        Args:
            contents: 内容列表
            threshold: 突发阈值（标准差的倍数）
            
        Returns:
            突发事件列表
        """
        # 按小时统计
        hourly_counts = defaultdict(int)
        
        for content in contents:
            timestamp = content.get('published_at', datetime.now())
            if isinstance(timestamp, str):
                try:
                    timestamp = datetime.fromisoformat(timestamp.replace('Z', '+00:00'))
                except:
                    continue
            
            hour_key = timestamp.strftime("%Y-%m-%d %H")
            hourly_counts[hour_key] += 1
        
        if not hourly_counts:
            return []
        
        # 计算均值和标准差
        counts = list(hourly_counts.values())
        mean_count = statistics.mean(counts)
        std_count = statistics.stdev(counts) if len(counts) > 1 else 0
        
        # 检测异常值
        burst_events = []
        for hour_key, count in hourly_counts.items():
            if std_count > 0:
                z_score = (count - mean_count) / std_count
                if z_score > threshold:
                    burst_events.append({
                        "time": hour_key,
                        "count": count,
                        "z_score": round(z_score, 2),
                        "severity": "high" if z_score > threshold * 2 else "medium"
                    })
        
        return sorted(burst_events, key=lambda x: x['z_score'], reverse=True)


class RealtimeTrendDetector:
    """实时趋势检测器"""
    
    def __init__(self, window_size: int = 100):
        self.window_size = window_size
        self.recent_items = []
        self.trending_keywords = set()
    
    def add_item(self, item: Dict[str, Any]):
        """添加新项目"""
        self.recent_items.append(item)
        
        # 保持窗口大小
        if len(self.recent_items) > self.window_size:
            self.recent_items.pop(0)
        
        # 更新趋势关键词
        self._update_trending_keywords()
    
    def _update_trending_keywords(self):
        """更新趋势关键词"""
        # 统计最近窗口中的关键词
        keyword_counts = Counter()
        
        for item in self.recent_items:
            keywords = item.get('keywords', [])
            for kw in keywords:
                keyword_counts[kw] += 1
        
        # 更新趋势集合
        self.trending_keywords = {
            kw for kw, count in keyword_counts.items()
            if count >= 3  # 至少出现3次才算趋势
        }
    
    def is_trending(self, keyword: str) -> bool:
        """检查关键词是否正在 trending"""
        return keyword in self.trending_keywords
    
    def get_current_trends(self, top_n: int = 10) -> List[str]:
        """获取当前趋势"""
        keyword_counts = Counter()
        
        for item in self.recent_items:
            keywords = item.get('keywords', [])
            for kw in keywords:
                keyword_counts[kw] += 1
        
        return [kw for kw, _ in keyword_counts.most_common(top_n)]
