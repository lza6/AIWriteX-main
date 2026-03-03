# -*- coding: utf-8 -*-
"""
超级新闻聚合系统 - NewsHub
整合 Horizon + TrendRadar + NewsNow 优点

核心功能：
- 多源数据采集（50+ 数据源）
- AI 智能处理（评分、摘要、情感分析）
- 实时去重和聚类
- 趋势分析和预测
- 多渠道智能通知
"""

from .hub_manager import NewsHubManager
from .data_sources import DataSourceRegistry, DataSourceCategory, DataSource
from .ai_processor import AIContentProcessor
from .deduplication import SemanticDeduplicator
from .trend_analyzer import TrendAnalyzer

__all__ = [
    'NewsHubManager',
    'DataSourceRegistry',
    'DataSourceCategory',
    'DataSource',
    'AIContentProcessor',
    'SemanticDeduplicator',
    'TrendAnalyzer',
]

__version__ = '1.0.0'
