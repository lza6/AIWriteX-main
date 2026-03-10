"""
AIWriteX V18.1 - Visualization Engine
可视化引擎 - 创作过程可视化和效果展示

功能:
1. 多类型图表生成: 折线图、柱状图、饼图、热力图
2. 创作流程可视化: 文章生成各阶段进度展示
3. 实时数据渲染: WebSocket数据流实时更新图表
4. 交互式探索: 支持缩放、筛选、钻取
"""

import json
from typing import Dict, List, Any, Optional, Tuple
from dataclasses import dataclass, field
from datetime import datetime, timedelta
from enum import Enum
import numpy as np
from collections import defaultdict


class ChartType(Enum):
    """图表类型"""
    LINE = "line"                       # 折线图 - 趋势
    BAR = "bar"                         # 柱状图 - 对比
    PIE = "pie"                         # 饼图 - 占比
    SCATTER = "scatter"                 # 散点图 - 分布
    HEATMAP = "heatmap"                 # 热力图 - 密度
    RADAR = "radar"                     # 雷达图 - 多维度
    GAUGE = "gauge"                     # 仪表盘 - 单一指标
    FUNNEL = "funnel"                   # 漏斗图 - 流程
    SANKEY = "sankey"                   # 桑基图 - 流向
    TREEMAP = "treemap"                 # 树图 - 层级


class AnimationType(Enum):
    """动画类型"""
    NONE = "none"
    FADE = "fade"
    SLIDE = "slide"
    SCALE = "scale"
    WAVE = "wave"


@dataclass
class ChartDataset:
    """图表数据集"""
    label: str
    data: List[Any]
    color: str = "#1890ff"
    fill: bool = False
    tension: float = 0.4


@dataclass
class ChartConfig:
    """图表配置"""
    type: ChartType
    title: str
    datasets: List[ChartDataset]
    labels: List[str] = field(default_factory=list)
    x_axis_label: str = ""
    y_axis_label: str = ""
    show_legend: bool = True
    show_grid: bool = True
    animate: AnimationType = AnimationType.FADE
    height: int = 300


class VisualizationEngine:
    """
    可视化引擎
    
    提供多种图表类型的数据生成和配置
    """
    
    # 预设配色方案
    COLOR_SCHEMES = {
        "default": ["#1890ff", "#52c41a", "#faad14", "#f5222d", "#722ed1", "#13c2c2"],
        "warm": ["#ff7a45", "#ffa940", "#ffc53d", "#ffec3d", "#bae637", "#73d13d"],
        "cool": ["#1890ff", "#36cfc9", "#40a9ff", "#69c0ff", "#91d5ff", "#b7eb8f"],
        "monochrome": ["#262626", "#595959", "#8c8c8c", "#bfbfbf", "#d9d9d9", "#f0f0f0"],
    }
    
    def __init__(self):
        self._color_index = 0
        self._current_scheme = "default"
    
    def create_line_chart(
        self,
        title: str,
        data: Dict[str, List[Tuple[datetime, float]]],
        x_label: str = "时间",
        y_label: str = "数值",
        time_range: timedelta = timedelta(hours=1)
    ) -> ChartConfig:
        """
        创建折线图
        
        Args:
            title: 图表标题
            data: {系列名称: [(时间, 值), ...]}
            x_label: X轴标签
            y_label: Y轴标签
            time_range: 时间范围
        """
        colors = self.COLOR_SCHEMES[self._current_scheme]
        datasets = []
        all_labels = set()
        
        for idx, (label, points) in enumerate(data.items()):
            # 过滤时间范围
            cutoff = datetime.now() - time_range
            filtered = [(t, v) for t, v in points if t > cutoff]
            
            # 生成标签和数据
            labels = [t.strftime("%H:%M") for t, _ in filtered]
            values = [v for _, v in filtered]
            
            all_labels.update(labels)
            
            dataset = ChartDataset(
                label=label,
                data=values,
                color=colors[idx % len(colors)],
                fill=idx == 0,
                tension=0.4
            )
            datasets.append(dataset)
        
        return ChartConfig(
            type=ChartType.LINE,
            title=title,
            datasets=datasets,
            labels=sorted(list(all_labels)),
            x_axis_label=x_label,
            y_axis_label=y_label
        )
    
    def create_bar_chart(
        self,
        title: str,
        categories: List[str],
        values: Dict[str, List[float]],
        horizontal: bool = False
    ) -> ChartConfig:
        """
        创建柱状图
        
        Args:
            title: 图表标题
            categories: 分类标签
            values: {系列名称: [值, ...]}
            horizontal: 是否水平显示
        """
        colors = self.COLOR_SCHEMES[self._current_scheme]
        datasets = []
        
        for idx, (label, data) in enumerate(values.items()):
            dataset = ChartDataset(
                label=label,
                data=data,
                color=colors[idx % len(colors)],
                fill=True
            )
            datasets.append(dataset)
        
        chart_type = ChartType.BAR
        if horizontal:
            # 水平柱状图配置
            pass
        
        return ChartConfig(
            type=chart_type,
            title=title,
            datasets=datasets,
            labels=categories
        )
    
    def create_pie_chart(
        self,
        title: str,
        data: Dict[str, float]
    ) -> ChartConfig:
        """
        创建饼图
        
        Args:
            title: 图表标题
            data: {标签: 值}
        """
        colors = self.COLOR_SCHEMES[self._current_scheme]
        
        dataset = ChartDataset(
            label="占比",
            data=list(data.values()),
            color=colors[0]
        )
        
        return ChartConfig(
            type=ChartType.PIE,
            title=title,
            datasets=[dataset],
            labels=list(data.keys())
        )
    
    def create_gauge(
        self,
        title: str,
        value: float,
        min_val: float = 0,
        max_val: float = 100,
        unit: str = "%"
    ) -> ChartConfig:
        """
        创建仪表盘
        
        Args:
            title: 图表标题
            value: 当前值
            min_val: 最小值
            max_val: 最大值
            unit: 单位
        """
        dataset = ChartDataset(
            label=title,
            data=[value],
            color=self._get_gauge_color(value, max_val)
        )
        
        return ChartConfig(
            type=ChartType.GAUGE,
            title=f"{title}: {value}{unit}",
            datasets=[dataset],
            labels=["当前值", "剩余"]
        )
    
    def create_heatmap(
        self,
        title: str,
        data: List[List[float]],
        x_labels: List[str],
        y_labels: List[str]
    ) -> ChartConfig:
        """
        创建热力图
        
        Args:
            title: 图表标题
            data: 二维数据矩阵
            x_labels: X轴标签
            y_labels: Y轴标签
        """
        # 将二维数据转换为一维，并添加坐标信息
        flat_data = []
        for y_idx, row in enumerate(data):
            for x_idx, value in enumerate(row):
                flat_data.append({
                    "x": x_labels[x_idx],
                    "y": y_labels[y_idx],
                    "v": value
                })
        
        dataset = ChartDataset(
            label="热力值",
            data=flat_data,
            color="#1890ff"
        )
        
        return ChartConfig(
            type=ChartType.HEATMAP,
            title=title,
            datasets=[dataset],
            labels=x_labels
        )
    
    def create_radar_chart(
        self,
        title: str,
        indicators: List[str],
        data: Dict[str, List[float]]
    ) -> ChartConfig:
        """
        创建雷达图
        
        Args:
            title: 图表标题
            indicators: 维度指标
            data: {系列名称: [值, ...]}
        """
        colors = self.COLOR_SCHEMES[self._current_scheme]
        datasets = []
        
        for idx, (label, values) in enumerate(data.items()):
            dataset = ChartDataset(
                label=label,
                data=values,
                color=colors[idx % len(colors)],
                fill=True,
                tension=0
            )
            datasets.append(dataset)
        
        return ChartConfig(
            type=ChartType.RADAR,
            title=title,
            datasets=datasets,
            labels=indicators
        )
    
    def create_funnel_chart(
        self,
        title: str,
        stages: List[str],
        values: List[float]
    ) -> ChartConfig:
        """
        创建漏斗图
        
        Args:
            title: 图表标题
            stages: 阶段名称
            values: 各阶段数值
        """
        colors = self.COLOR_SCHEMES[self._current_scheme]
        
        dataset = ChartDataset(
            label="转化",
            data=values,
            color=colors[0]
        )
        
        return ChartConfig(
            type=ChartType.FUNNEL,
            title=title,
            datasets=[dataset],
            labels=stages
        )
    
    def create_content_creation_flow(
        self,
        stages: Dict[str, Dict]
    ) -> Dict:
        """
        创建内容生成流程可视化
        
        Args:
            stages: {
                "阶段名称": {
                    "status": "pending|processing|completed|failed",
                    "progress": 0-100,
                    "details": {...}
                }
            }
        """
        status_colors = {
            "pending": "#d9d9d9",
            "processing": "#1890ff",
            "completed": "#52c41a",
            "failed": "#f5222d"
        }
        
        flow_data = []
        for stage_name, stage_info in stages.items():
            flow_data.append({
                "name": stage_name,
                "status": stage_info["status"],
                "progress": stage_info.get("progress", 0),
                "color": status_colors.get(stage_info["status"], "#d9d9d9"),
                "details": stage_info.get("details", {})
            })
        
        return {
            "type": "creation_flow",
            "title": "内容生成流程",
            "stages": flow_data,
            "total_progress": sum(s["progress"] for s in flow_data) / len(flow_data) if flow_data else 0
        }
    
    def render_chart(self, config: ChartConfig) -> Dict:
        """
        渲染图表为前端可用格式
        
        Args:
            config: 图表配置
            
        Returns:
            前端图表配置JSON
        """
        return {
            "type": config.type.value,
            "title": config.title,
            "data": {
                "labels": config.labels,
                "datasets": [
                    {
                        "label": ds.label,
                        "data": ds.data,
                        "borderColor": ds.color,
                        "backgroundColor": ds.color + "40" if ds.fill else "transparent",
                        "fill": ds.fill,
                        "tension": ds.tension
                    }
                    for ds in config.datasets
                ]
            },
            "options": {
                "responsive": True,
                "maintainAspectRatio": False,
                "plugins": {
                    "legend": {
                        "display": config.show_legend
                    },
                    "title": {
                        "display": True,
                        "text": config.title
                    }
                },
                "scales": {
                    "x": {
                        "display": True,
                        "title": {
                            "display": bool(config.x_axis_label),
                            "text": config.x_axis_label
                        },
                        "grid": {
                            "display": config.show_grid
                        }
                    },
                    "y": {
                        "display": True,
                        "title": {
                            "display": bool(config.y_axis_label),
                            "text": config.y_axis_label
                        },
                        "grid": {
                            "display": config.show_grid
                        }
                    }
                },
                "animation": {
                    "type": config.animate.value,
                    "duration": 1000
                }
            },
            "height": config.height
        }
    
    def _get_gauge_color(self, value: float, max_val: float) -> str:
        """根据数值获取仪表盘颜色"""
        ratio = value / max_val if max_val > 0 else 0
        
        if ratio < 0.5:
            return "#52c41a"  # 绿色
        elif ratio < 0.75:
            return "#faad14"  # 黄色
        elif ratio < 0.9:
            return "#ff7a45"  # 橙色
        else:
            return "#f5222d"  # 红色
    
    def set_color_scheme(self, scheme: str):
        """设置配色方案"""
        if scheme in self.COLOR_SCHEMES:
            self._current_scheme = scheme
    
    def generate_stats_summary(
        self,
        data: List[float],
        title: str = "统计摘要"
    ) -> Dict:
        """
        生成统计摘要
        
        Args:
            data: 数据列表
            title: 标题
            
        Returns:
            统计信息字典
        """
        if not data:
            return {"title": title, "error": "无数据"}
        
        arr = np.array(data)
        
        return {
            "title": title,
            "count": len(data),
            "sum": float(np.sum(arr)),
            "mean": float(np.mean(arr)),
            "median": float(np.median(arr)),
            "std": float(np.std(arr)),
            "min": float(np.min(arr)),
            "max": float(np.max(arr)),
            "p50": float(np.percentile(arr, 50)),
            "p95": float(np.percentile(arr, 95)),
            "p99": float(np.percentile(arr, 99))
        }


# 全局可视化引擎实例
viz_engine = VisualizationEngine()


def get_viz_engine() -> VisualizationEngine:
    """获取可视化引擎实例"""
    return viz_engine
