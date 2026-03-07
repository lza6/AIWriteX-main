# -*- coding: UTF-8 -*-
"""
V16.0 - Predictive Engine (趋势预测引擎)

基于历史数据和外部信号预测未来热点趋势，实现 preemptive 内容生成。
使用多种预测模型：时间序列分析、语义趋势聚类、外部信号融合。
"""

import json
import math
import asyncio
import numpy as np
from datetime import datetime, timedelta
from typing import Dict, List, Optional, Tuple, Any
from dataclasses import dataclass, field
from collections import defaultdict
import threading

from src.ai_write_x.utils import log
from src.ai_write_x.database.db_manager import db_manager
from src.ai_write_x.config.config import Config


@dataclass
class TrendPrediction:
    """趋势预测结果"""
    topic: str
    predicted_score: float  # 预测热度分数 0-100
    confidence: float  # 置信度 0-1
    predicted_peak_time: datetime  # 预测峰值时间
    category: str  # 分类
    keywords: List[str] = field(default_factory=list)
    data_sources: List[str] = field(default_factory=list)
    features: Dict[str, float] = field(default_factory=dict)
    
    def to_dict(self) -> Dict:
        return {
            "topic": self.topic,
            "predicted_score": self.predicted_score,
            "confidence": self.confidence,
            "predicted_peak_time": self.predicted_peak_time.isoformat(),
            "category": self.category,
            "keywords": self.keywords,
            "data_sources": self.data_sources,
            "features": self.features
        }


@dataclass
class HistoricalPattern:
    """历史模式"""
    pattern_type: str  # 'daily', 'weekly', 'monthly', 'event'
    time_window: Tuple[datetime, datetime]
    keywords: List[str]
    avg_score: float
    peak_score: float
    recurrence_rate: float  # 重现率


class TimeSeriesForecaster:
    """时间序列预测器 - 使用指数平滑和趋势分解"""
    
    def __init__(self, alpha: float = 0.3, beta: float = 0.1):
        self.alpha = alpha  # 平滑系数
        self.beta = beta    # 趋势系数
        
    def forecast(self, data: List[float], periods: int = 7) -> List[float]:
        """预测未来 periods 个时间点的值"""
        if len(data) < 3:
            return [data[-1] if data else 0.0] * periods
            
        # 初始化
        level = data[0]
        trend = (data[1] - data[0]) if len(data) > 1 else 0
        
        # Holt-Winters 指数平滑
        for value in data[1:]:
            last_level = level
            level = self.alpha * value + (1 - self.alpha) * (level + trend)
            trend = self.beta * (level - last_level) + (1 - self.beta) * trend
        
        # 预测
        forecasts = []
        for i in range(1, periods + 1):
            forecasts.append(level + i * trend)
            
        return forecasts
    
    def detect_anomaly(self, data: List[float], threshold: float = 2.0) -> List[int]:
        """检测异常值 (Z-score 方法)"""
        if len(data) < 3:
            return []
            
        mean = np.mean(data)
        std = np.std(data)
        
        if std == 0:
            return []
            
        anomalies = []
        for i, value in enumerate(data):
            z_score = abs(value - mean) / std
            if z_score > threshold:
                anomalies.append(i)
                
        return anomalies


class SemanticTrendCluster:
    """语义趋势聚类 - 识别相似话题的聚合趋势"""
    
    def __init__(self):
        self.clusters: Dict[str, List[str]] = {}
        self.cluster_scores: Dict[str, float] = {}
        
    def add_topic(self, topic: str, keywords: List[str], score: float):
        """添加话题到聚类"""
        # 查找最匹配的聚类
        best_cluster = None
        best_match_score = 0.0
        
        for cluster_id, cluster_topics in self.clusters.items():
            # 计算关键词重叠度
            cluster_keywords = self._get_cluster_keywords(cluster_id)
            overlap = len(set(keywords) & set(cluster_keywords))
            match_score = overlap / max(len(keywords), len(cluster_keywords), 1)
            
            if match_score > best_match_score and match_score > 0.3:  # 30% 重叠阈值
                best_match_score = match_score
                best_cluster = cluster_id
        
        if best_cluster:
            self.clusters[best_cluster].append(topic)
            self.cluster_scores[best_cluster] = max(self.cluster_scores[best_cluster], score)
        else:
            # 创建新聚类
            new_id = f"cluster_{len(self.clusters)}"
            self.clusters[new_id] = [topic]
            self.cluster_scores[new_id] = score
    
    def _get_cluster_keywords(self, cluster_id: str) -> List[str]:
        """获取聚类的关键词"""
        keywords = set()
        # 简化为取话题中的词汇
        for topic in self.clusters.get(cluster_id, []):
            keywords.update(topic.lower().split())
        return list(keywords)
    
    def get_trending_clusters(self, min_score: float = 50.0) -> List[Tuple[str, float]]:
        """获取热门聚类"""
        trending = [
            (cluster_id, score) 
            for cluster_id, score in self.cluster_scores.items() 
            if score >= min_score
        ]
        return sorted(trending, key=lambda x: x[1], reverse=True)


class PredictiveEngine:
    """
    V16.0 趋势预测引擎
    
    功能：
    1. 多源数据融合分析
    2. 时间序列预测
    3. 语义趋势聚类
    4. 外部信号增强 (搜索趋势、社交媒体热度)
    """
    
    _instance = None
    _lock = threading.Lock()
    
    def __new__(cls):
        with cls._lock:
            if cls._instance is None:
                cls._instance = super(PredictiveEngine, cls).__new__(cls)
                cls._instance._initialized = False
        return cls._instance
    
    def __init__(self):
        if self._initialized:
            return
            
        self._initialized = True
        self.forecaster = TimeSeriesForecaster()
        self.cluster_engine = SemanticTrendCluster()
        self.historical_patterns: List[HistoricalPattern] = []
        self.prediction_cache: Dict[str, TrendPrediction] = {}
        self.cache_ttl = 3600  # 1小时
        
        log.print_log("[V16.0] 🧠 Predictive Engine (趋势预测引擎) 已初始化", "success")
    
    async def predict_trends(
        self, 
        horizon_days: int = 3,
        category: Optional[str] = None,
        top_n: int = 10
    ) -> List[TrendPrediction]:
        """
        预测未来趋势
        
        Args:
            horizon_days: 预测时间窗口 (天)
            category: 特定分类 (None 表示全部分类)
            top_n: 返回前 N 个预测
        
        Returns:
            预测趋势列表
        """
        try:
            # 1. 收集历史数据
            historical_data = await self._collect_historical_data(category)
            
            # 2. 时间序列预测
            time_series_predictions = self._time_series_analysis(historical_data, horizon_days)
            
            # 3. 语义聚类分析
            semantic_predictions = self._semantic_cluster_analysis(historical_data)
            
            # 4. 外部信号增强
            external_signals = await self._fetch_external_signals()
            
            # 5. 融合预测结果
            fused_predictions = self._fuse_predictions(
                time_series_predictions,
                semantic_predictions,
                external_signals
            )
            
            # 6. 排序并返回 Top N
            fused_predictions.sort(key=lambda x: x.predicted_score * x.confidence, reverse=True)
            
            # 缓存结果
            for pred in fused_predictions[:top_n]:
                self.prediction_cache[pred.topic] = pred
            
            log.print_log(
                f"[V16.0] 📈 趋势预测完成: {len(fused_predictions)} 个预测，"
                f"返回 Top {top_n}", 
                "success"
            )
            
            return fused_predictions[:top_n]
            
        except Exception as e:
            log.print_log(f"[V16.0] ❌ 趋势预测失败: {e}", "error")
            return []
    
    async def _collect_historical_data(
        self, 
        category: Optional[str] = None
    ) -> List[Dict]:
        """收集历史话题数据"""
        try:
            # 从数据库获取历史文章数据
            # 这里简化处理，实际应从 topic_memory 和 articles 表聚合
            
            # 模拟历史数据 (实际应从数据库查询)
            historical = []
            
            # 从 NewsHub 缓存获取
            cache_path = "knowledge/newshub_cache.json"
            try:
                import os
                if os.path.exists(cache_path):
                    with open(cache_path, 'r', encoding='utf-8') as f:
                        cache = json.load(f)
                        for item in cache.get("contents", []):
                            historical.append({
                                "topic": item.get("title", ""),
                                "score": item.get("score", 0),
                                "timestamp": datetime.fromisoformat(
                                    item.get("published_at", datetime.now().isoformat())
                                ),
                                "keywords": item.get("keywords", []),
                                "category": item.get("category", "general")
                            })
            except Exception as e:
                log.print_log(f"[V16.0] 读取缓存数据失败: {e}", "warning")
            
            # 从数据库获取文章历史
            try:
                articles = db_manager.get_articles(limit=1000)
                for article in articles:
                    historical.append({
                        "topic": article.get("title", ""),
                        "score": article.get("quality_score", 50),
                        "timestamp": article.get("created_at", datetime.now()),
                        "keywords": article.get("keywords", []),
                        "category": article.get("category", "general")
                    })
            except Exception as e:
                log.print_log(f"[V16.0] 读取文章数据失败: {e}", "warning")
            
            # 过滤分类
            if category:
                historical = [h for h in historical if h.get("category") == category]
            
            return historical
            
        except Exception as e:
            log.print_log(f"[V16.0] 收集历史数据失败: {e}", "error")
            return []
    
    def _time_series_analysis(
        self, 
        data: List[Dict], 
        horizon_days: int
    ) -> Dict[str, List[float]]:
        """时间序列分析"""
        # 按话题分组
        topic_series = defaultdict(list)
        
        for item in data:
            topic = item.get("topic", "")
            if topic:
                topic_series[topic].append(item.get("score", 0))
        
        # 对每个话题进行预测
        predictions = {}
        for topic, scores in topic_series.items():
            if len(scores) >= 3:
                forecast = self.forecaster.forecast(scores, horizon_days)
                predictions[topic] = forecast
        
        return predictions
    
    def _semantic_cluster_analysis(self, data: List[Dict]) -> List[TrendPrediction]:
        """语义聚类分析"""
        # 添加到聚类引擎
        for item in data:
            self.cluster_engine.add_topic(
                item.get("topic", ""),
                item.get("keywords", []),
                item.get("score", 0)
            )
        
        # 获取热门聚类
        trending_clusters = self.cluster_engine.get_trending_clusters(min_score=30.0)
        
        predictions = []
        for cluster_id, score in trending_clusters:
            topics = self.cluster_engine.clusters.get(cluster_id, [])
            if topics:
                predictions.append(TrendPrediction(
                    topic=topics[0],  # 使用聚类代表话题
                    predicted_score=min(score * 1.2, 100),  # 预测热度上浮
                    confidence=0.6,
                    predicted_peak_time=datetime.now() + timedelta(days=1),
                    category="clustered",
                    keywords=topics[:5],
                    data_sources=["semantic_clustering"]
                ))
        
        return predictions
    
    async def _fetch_external_signals(self) -> Dict[str, float]:
        """获取外部信号 (搜索趋势、社交媒体热度)"""
        signals = {}
        
        try:
            # 可以从外部 API 获取实时趋势
            # 例如: Google Trends, Twitter API, 百度指数等
            
            # 这里使用 NewsHub 数据作为信号
            from src.ai_write_x.news_aggregator.hub_manager import aggregate_news
            result = await aggregate_news(min_score=5.0)
            
            for content in result.get("contents", []):
                topic = content.get("title", "")
                score = content.get("score", 0)
                if topic:
                    signals[topic] = score
                    
        except Exception as e:
            log.print_log(f"[V16.0] 获取外部信号失败: {e}", "warning")
        
        return signals
    
    def _fuse_predictions(
        self,
        time_series: Dict[str, List[float]],
        semantic: List[TrendPrediction],
        external: Dict[str, float]
    ) -> List[TrendPrediction]:
        """融合多源预测结果"""
        fused = {}
        
        # 融合时间序列预测
        for topic, forecasts in time_series.items():
            if forecasts:
                avg_forecast = np.mean(forecasts)
                confidence = min(len(forecasts) / 10, 1.0)
                
                fused[topic] = TrendPrediction(
                    topic=topic,
                    predicted_score=float(avg_forecast),
                    confidence=confidence,
                    predicted_peak_time=datetime.now() + timedelta(days=len(forecasts)),
                    category="time_series",
                    data_sources=["historical_analysis"]
                )
        
        # 融合语义聚类预测
        for pred in semantic:
            if pred.topic in fused:
                # 加权融合
                existing = fused[pred.topic]
                fused[pred.topic] = TrendPrediction(
                    topic=pred.topic,
                    predicted_score=(existing.predicted_score + pred.predicted_score) / 2,
                    confidence=max(existing.confidence, pred.confidence),
                    predicted_peak_time=min(existing.predicted_peak_time, pred.predicted_peak_time),
                    category="fused",
                    keywords=list(set(existing.keywords + pred.keywords)),
                    data_sources=existing.data_sources + ["semantic"]
                )
            else:
                fused[pred.topic] = pred
        
        # 融合外部信号
        for topic, score in external.items():
            if topic in fused:
                existing = fused[topic]
                # 外部信号作为增强
                boosted_score = min(existing.predicted_score * 1.1, 100)
                fused[topic] = TrendPrediction(
                    topic=topic,
                    predicted_score=boosted_score,
                    confidence=min(existing.confidence + 0.1, 1.0),
                    predicted_peak_time=existing.predicted_peak_time,
                    category=existing.category,
                    keywords=existing.keywords,
                    data_sources=existing.data_sources + ["external"]
                )
        
        return list(fused.values())
    
    def get_prediction_confidence(self, topic: str) -> float:
        """获取特定话题的预测置信度"""
        if topic in self.prediction_cache:
            return self.prediction_cache[topic].confidence
        return 0.0


# 全局实例
_predictive_engine = None


def get_predictive_engine() -> PredictiveEngine:
    """获取预测引擎全局实例"""
    global _predictive_engine
    if _predictive_engine is None:
        _predictive_engine = PredictiveEngine()
    return _predictive_engine
