"""
AIWriteX V18.1 - Comparison Tool
效果对比工具 - A/B测试和内容效果对比

功能:
1. A/B测试结果对比: 多维度指标并排对比
2. 内容版本对比: 不同版本文章的效果分析
3. 时间序列对比: 历史数据趋势对比
4. 智能差异分析: 自动生成差异报告和建议
"""

from typing import Dict, List, Any, Optional, Tuple
from dataclasses import dataclass, field
from datetime import datetime, timedelta
from enum import Enum
import numpy as np
from collections import defaultdict


class ComparisonMode(Enum):
    """对比模式"""
    AB_TEST = "ab_test"                 # A/B测试对比
    VERSION = "version"                 # 版本对比
    TIME_SERIES = "time_series"         # 时间序列对比
    MULTI_DIMENSION = "multi_dimension" # 多维度对比


class MetricType(Enum):
    """指标类型"""
    READ_COUNT = "read_count"           # 阅读量
    LIKE_COUNT = "like_count"           # 点赞数
    SHARE_COUNT = "share_count"         # 分享数
    COMMENT_COUNT = "comment_count"     # 评论数
    CONVERSION_RATE = "conversion_rate" # 转化率
    ENGAGEMENT_RATE = "engagement_rate" # 参与率
    READ_TIME = "read_time"             # 阅读时长
    BOUNCE_RATE = "bounce_rate"         # 跳出率


@dataclass
class ComparisonMetric:
    """对比指标"""
    name: str
    type: MetricType
    value_a: float
    value_b: float
    unit: str = ""
    higher_is_better: bool = True


@dataclass
class ComparisonResult:
    """对比结果"""
    mode: ComparisonMode
    title: str
    variant_a_name: str
    variant_b_name: str
    metrics: List[ComparisonMetric]
    winner: Optional[str] = None
    confidence: float = 0.0
    timestamp: datetime = field(default_factory=datetime.now)
    insights: List[str] = field(default_factory=list)
    recommendations: List[str] = field(default_factory=list)


class ComparisonTool:
    """
    效果对比工具
    
    提供多种对比分析功能，帮助优化内容效果
    """
    
    def __init__(self):
        self._history: List[ComparisonResult] = []
        self._confidence_threshold = 0.95  # 统计显著性阈值
    
    def compare_ab_test(
        self,
        test_name: str,
        variant_a: Dict[str, Any],
        variant_b: Dict[str, Any],
        sample_size_a: int,
        sample_size_b: int,
        metrics_config: Optional[Dict[MetricType, Dict]] = None
    ) -> ComparisonResult:
        """
        A/B测试对比分析
        
        Args:
            test_name: 测试名称
            variant_a: A版本数据
            variant_b: B版本数据
            sample_size_a: A版本样本数
            sample_size_b: B版本样本数
            metrics_config: 指标配置
            
        Returns:
            对比结果
        """
        if metrics_config is None:
            metrics_config = self._default_metrics_config()
        
        metrics = []
        
        for metric_type, config in metrics_config.items():
            value_a = variant_a.get(metric_type.value, 0)
            value_b = variant_b.get(metric_type.value, 0)
            
            metric = ComparisonMetric(
                name=config["name"],
                type=metric_type,
                value_a=float(value_a),
                value_b=float(value_b),
                unit=config.get("unit", ""),
                higher_is_better=config.get("higher_is_better", True)
            )
            metrics.append(metric)
        
        # 计算获胜方
        winner, confidence = self._calculate_winner(metrics, sample_size_a, sample_size_b)
        
        # 生成洞察和建议
        insights = self._generate_insights(metrics, winner)
        recommendations = self._generate_recommendations(metrics, winner)
        
        result = ComparisonResult(
            mode=ComparisonMode.AB_TEST,
            title=test_name,
            variant_a_name=variant_a.get("name", "版本A"),
            variant_b_name=variant_b.get("name", "版本B"),
            metrics=metrics,
            winner=winner,
            confidence=confidence,
            insights=insights,
            recommendations=recommendations
        )
        
        self._history.append(result)
        return result
    
    def compare_versions(
        self,
        content_title: str,
        versions: List[Dict[str, Any]],
        metrics: List[MetricType] = None
    ) -> List[ComparisonResult]:
        """
        多版本对比分析
        
        Args:
            content_title: 内容标题
            versions: 版本数据列表
            metrics: 要对比的指标
            
        Returns:
            对比结果列表
        """
        if len(versions) < 2:
            return []
        
        if metrics is None:
            metrics = [MetricType.READ_COUNT, MetricType.LIKE_COUNT, MetricType.SHARE_COUNT]
        
        results = []
        
        # 对比每个版本与第一个版本
        baseline = versions[0]
        for i in range(1, len(versions)):
            variant = versions[i]
            
            result = self.compare_ab_test(
                test_name=f"{content_title} - 版本对比",
                variant_a=baseline,
                variant_b=variant,
                sample_size_a=baseline.get("sample_size", 100),
                sample_size_b=variant.get("sample_size", 100),
                metrics_config={m: self._get_metric_config(m) for m in metrics}
            )
            
            result.mode = ComparisonMode.VERSION
            results.append(result)
        
        return results
    
    def compare_time_series(
        self,
        metric_name: str,
        current_data: List[Tuple[datetime, float]],
        previous_data: List[Tuple[datetime, float]],
        period_name: str = "同比"
    ) -> Dict[str, Any]:
        """
        时间序列对比
        
        Args:
            metric_name: 指标名称
            current_data: 当前期数据 [(时间, 值), ...]
            previous_data: 对比期数据 [(时间, 值), ...]
            period_name: 对比期名称
            
        Returns:
            对比分析结果
        """
        # 计算统计值
        current_values = [v for _, v in current_data]
        previous_values = [v for _, v in previous_data]
        
        current_stats = self._calculate_stats(current_values)
        previous_stats = self._calculate_stats(previous_values)
        
        # 计算变化率
        change_pct = {}
        for key in ["mean", "sum", "max"]:
            if previous_stats[key] != 0:
                change_pct[key] = (current_stats[key] - previous_stats[key]) / previous_stats[key] * 100
            else:
                change_pct[key] = 0
        
        # 趋势分析
        current_trend = self._calculate_trend(current_values)
        previous_trend = self._calculate_trend(previous_values)
        
        return {
            "metric_name": metric_name,
            "comparison_period": period_name,
            "current_period": {
                "stats": current_stats,
                "trend": current_trend,
                "data_points": len(current_data)
            },
            "previous_period": {
                "stats": previous_stats,
                "trend": previous_trend,
                "data_points": len(previous_data)
            },
            "change_percentage": change_pct,
            "overall_change": change_pct.get("mean", 0),
            "trend_comparison": {
                "current": current_trend,
                "previous": previous_trend,
                "improved": abs(current_trend) < abs(previous_trend) if current_trend * previous_trend > 0 else current_trend > previous_trend
            }
        }
    
    def multi_dimension_compare(
        self,
        title: str,
        items: List[Dict[str, Any]],
        dimensions: List[str]
    ) -> Dict[str, Any]:
        """
        多维度对比分析
        
        Args:
            title: 分析标题
            items: 对比项目列表
            dimensions: 维度列表
            
        Returns:
            多维度对比结果
        """
        # 构建雷达图数据
        radar_data = {}
        for item in items:
            name = item.get("name", "Unknown")
            values = []
            for dim in dimensions:
                values.append(item.get(dim, 0))
            radar_data[name] = values
        
        # 计算各维度排名
        rankings = {}
        for dim in dimensions:
            dim_values = [(item.get("name", "Unknown"), item.get(dim, 0)) for item in items]
            dim_values.sort(key=lambda x: x[1], reverse=True)
            rankings[dim] = dim_values
        
        # 综合评分
        scores = {}
        for item in items:
            name = item.get("name", "Unknown")
            score = sum(item.get(dim, 0) for dim in dimensions) / len(dimensions)
            scores[name] = score
        
        best_item = max(scores.items(), key=lambda x: x[1])
        
        return {
            "title": title,
            "dimensions": dimensions,
            "radar_data": radar_data,
            "rankings": rankings,
            "overall_scores": scores,
            "best_performer": best_item[0],
            "analysis": self._generate_multi_dim_analysis(radar_data, dimensions)
        }
    
    def _default_metrics_config(self) -> Dict[MetricType, Dict]:
        """默认指标配置"""
        return {
            MetricType.READ_COUNT: {"name": "阅读量", "unit": "次", "higher_is_better": True},
            MetricType.LIKE_COUNT: {"name": "点赞数", "unit": "个", "higher_is_better": True},
            MetricType.SHARE_COUNT: {"name": "分享数", "unit": "次", "higher_is_better": True},
            MetricType.COMMENT_COUNT: {"name": "评论数", "unit": "条", "higher_is_better": True},
            MetricType.CONVERSION_RATE: {"name": "转化率", "unit": "%", "higher_is_better": True},
            MetricType.ENGAGEMENT_RATE: {"name": "参与率", "unit": "%", "higher_is_better": True},
            MetricType.READ_TIME: {"name": "平均阅读时长", "unit": "秒", "higher_is_better": True},
            MetricType.BOUNCE_RATE: {"name": "跳出率", "unit": "%", "higher_is_better": False},
        }
    
    def _get_metric_config(self, metric_type: MetricType) -> Dict:
        """获取指标配置"""
        defaults = self._default_metrics_config()
        return defaults.get(metric_type, {"name": metric_type.value, "unit": "", "higher_is_better": True})
    
    def _calculate_winner(
        self,
        metrics: List[ComparisonMetric],
        sample_size_a: int,
        sample_size_b: int
    ) -> Tuple[Optional[str], float]:
        """计算获胜方"""
        score_a = 0
        score_b = 0
        significant_count = 0
        
        for metric in metrics:
            # 简单统计显著性检查
            diff = metric.value_b - metric.value_a
            pooled_std = np.sqrt(
                (metric.value_a * (1 - metric.value_a / 100) / sample_size_a) +
                (metric.value_b * (1 - metric.value_b / 100) / sample_size_b)
            ) if metric.value_a <= 100 and metric.value_b <= 100 else 0.1
            
            if pooled_std > 0:
                z_score = abs(diff) / pooled_std
                is_significant = z_score > 1.96  # 95%置信度
                
                if is_significant:
                    significant_count += 1
                    if metric.higher_is_better:
                        if diff > 0:
                            score_b += 1
                        else:
                            score_a += 1
                    else:
                        if diff > 0:
                            score_a += 1
                        else:
                            score_b += 1
        
        if score_a > score_b:
            return "A", 0.95 if significant_count > 0 else 0.5
        elif score_b > score_a:
            return "B", 0.95 if significant_count > 0 else 0.5
        else:
            return None, 0.5
    
    def _generate_insights(
        self,
        metrics: List[ComparisonMetric],
        winner: Optional[str]
    ) -> List[str]:
        """生成洞察"""
        insights = []
        
        if winner:
            insights.append(f"版本{winner}在整体表现上更优")
        else:
            insights.append("两个版本表现相近，无显著差异")
        
        # 找出差异最大的指标
        max_diff_metric = max(metrics, key=lambda m: abs(m.value_b - m.value_a))
        diff_pct = abs(max_diff_metric.value_b - max_diff_metric.value_a) / max(max_diff_metric.value_a, 0.01) * 100
        
        insights.append(
            f"{max_diff_metric.name}差异最大，达到{diff_pct:.1f}%"
        )
        
        # 分析各指标表现
        better_metrics = [m for m in metrics if (m.value_b > m.value_a) == m.higher_is_better]
        worse_metrics = [m for m in metrics if (m.value_b < m.value_a) == m.higher_is_better]
        
        if better_metrics:
            insights.append(f"版本B在{len(better_metrics)}个指标上表现更好")
        if worse_metrics:
            insights.append(f"版本B在{len(worse_metrics)}个指标上需要改进")
        
        return insights
    
    def _generate_recommendations(
        self,
        metrics: List[ComparisonMetric],
        winner: Optional[str]
    ) -> List[str]:
        """生成建议"""
        recommendations = []
        
        if winner == "B":
            recommendations.append("建议采用版本B的方案")
        elif winner == "A":
            recommendations.append("建议保留版本A，继续优化版本B")
        else:
            recommendations.append("建议增加样本量或延长测试时间以获得更明确的结果")
        
        # 针对表现不佳的指标给出建议
        for metric in metrics:
            diff = metric.value_b - metric.value_a
            if metric.higher_is_better and diff < 0:
                recommendations.append(f"重点关注{metric.name}的优化")
            elif not metric.higher_is_better and diff > 0:
                recommendations.append(f"需要降低{metric.name}")
        
        return recommendations
    
    def _calculate_stats(self, values: List[float]) -> Dict[str, float]:
        """计算统计数据"""
        if not values:
            return {"mean": 0, "median": 0, "std": 0, "min": 0, "max": 0, "sum": 0}
        
        arr = np.array(values)
        return {
            "mean": float(np.mean(arr)),
            "median": float(np.median(arr)),
            "std": float(np.std(arr)),
            "min": float(np.min(arr)),
            "max": float(np.max(arr)),
            "sum": float(np.sum(arr))
        }
    
    def _calculate_trend(self, values: List[float]) -> str:
        """计算趋势"""
        if len(values) < 2:
            return "stable"
        
        # 简单线性回归
        x = np.arange(len(values))
        slope = np.polyfit(x, values, 1)[0]
        
        if slope > 0.01:
            return "upward"
        elif slope < -0.01:
            return "downward"
        else:
            return "stable"
    
    def _generate_multi_dim_analysis(
        self,
        radar_data: Dict[str, List[float]],
        dimensions: List[str]
    ) -> List[str]:
        """生成多维度分析"""
        analysis = []
        
        # 找出每个维度的最佳表现者
        for i, dim in enumerate(dimensions):
            best = max(radar_data.items(), key=lambda x: x[1][i])
            analysis.append(f"{dim}: {best[0]}表现最佳")
        
        return analysis
    
    def get_comparison_history(
        self,
        limit: int = 10
    ) -> List[ComparisonResult]:
        """获取对比历史"""
        return self._history[-limit:]
    
    def export_report(
        self,
        result: ComparisonResult,
        format: str = "json"
    ) -> str:
        """
        导出对比报告
        
        Args:
            result: 对比结果
            format: 导出格式 (json, markdown)
            
        Returns:
            报告内容
        """
        if format == "json":
            import json
            return json.dumps({
                "mode": result.mode.value,
                "title": result.title,
                "variant_a": result.variant_a_name,
                "variant_b": result.variant_b_name,
                "winner": result.winner,
                "confidence": result.confidence,
                "metrics": [
                    {
                        "name": m.name,
                        "type": m.type.value,
                        "value_a": m.value_a,
                        "value_b": m.value_b,
                        "unit": m.unit,
                        "lift": ((m.value_b - m.value_a) / max(m.value_a, 0.01) * 100)
                    }
                    for m in result.metrics
                ],
                "insights": result.insights,
                "recommendations": result.recommendations,
                "timestamp": result.timestamp.isoformat()
            }, ensure_ascii=False, indent=2)
        
        elif format == "markdown":
            lines = [
                f"# {result.title} - 对比报告",
                "",
                f"**对比模式**: {result.mode.value}",
                f"**获胜方**: {result.winner or '无明显差异'}",
                f"**置信度**: {result.confidence * 100:.1f}%",
                f"**生成时间**: {result.timestamp.strftime('%Y-%m-%d %H:%M:%S')}",
                "",
                "## 指标对比",
                "",
                "| 指标 | A版本 | B版本 | 变化 | 变化率 |",
                "|------|-------|-------|------|--------|",
            ]
            
            for m in result.metrics:
                change = m.value_b - m.value_a
                change_pct = (change / max(m.value_a, 0.01)) * 100
                lines.append(
                    f"| {m.name} | {m.value_a}{m.unit} | {m.value_b}{m.unit} | "
                    f"{change:+.2f}{m.unit} | {change_pct:+.1f}% |"
                )
            
            lines.extend([
                "",
                "## 关键洞察",
                "",
            ])
            for insight in result.insights:
                lines.append(f"- {insight}")
            
            lines.extend([
                "",
                "## 优化建议",
                "",
            ])
            for rec in result.recommendations:
                lines.append(f"- {rec}")
            
            return "\n".join(lines)
        
        return ""


# 全局对比工具实例
comparison_tool = ComparisonTool()


def get_comparison_tool() -> ComparisonTool:
    """获取对比工具实例"""
    return comparison_tool
