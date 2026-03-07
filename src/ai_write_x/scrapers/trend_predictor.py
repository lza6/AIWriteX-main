#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
热点趋势预测系统 V17
基于历史数据和实时抓取，预测即将爆火的话题

核心算法:
1. 话题热度增长趋势分析
2. 多平台传播速度评估
3. 关键词共现网络分析
4. 时间序列预测
"""
import asyncio
import json
import math
from datetime import datetime, timedelta
from typing import List, Dict, Tuple, Optional
from dataclasses import dataclass, field
from collections import defaultdict
import re

from logger_utils import logger


@dataclass
class TrendingTopic:
    """热点话题"""
    keyword: str
    current_score: float
    growth_rate: float  # 增长率
    platforms: List[str]  # 出现的平台
    mention_count: int  # 提及次数
    velocity: float  # 传播速度
    predicted_peak: datetime  # 预测峰值时间
    confidence: float  # 预测置信度
    related_topics: List[str]  # 相关话题
    sentiment: float  # 情感倾向 (-1到1)


class TrendPredictor:
    """
    热点趋势预测系统 V17
    """
    
    def __init__(self, history_window: int = 24):
        """
        Args:
            history_window: 历史数据时间窗口（小时）
        """
        self.history_window = history_window
        self.topic_history: Dict[str, List[Tuple[datetime, float]]] = defaultdict(list)
        self.keyword_graph: Dict[str, set] = defaultdict(set)
        self.last_analysis: Optional[datetime] = None
        
        # 热点词库
        self.burst_keywords = {
            "突发", "重磅", "震惊", "爆炸", "独家", "揭秘",
            "Breaking", "Exclusive", "Urgent", "Alert",
            "AI", "人工智能", "ChatGPT", "大模型", "LLM",
            "暴涨", "暴跌", "崩盘", "涨停", "比特币", "加密货币",
            "战争", "冲突", "制裁", "贸易战",
        }
    
    def record_topic(self, keyword: str, score: float, timestamp: Optional[datetime] = None):
        """记录话题出现"""
        if timestamp is None:
            timestamp = datetime.now()
        
        # 清理过期数据
        cutoff = timestamp - timedelta(hours=self.history_window)
        self.topic_history[keyword] = [
            (ts, sc) for ts, sc in self.topic_history[keyword]
            if ts > cutoff
        ]
        
        # 添加新记录
        self.topic_history[keyword].append((timestamp, score))
    
    def analyze_trends(self, current_topics: List[Dict]) -> List[TrendingTopic]:
        """
        分析热点趋势
        
        Args:
            current_topics: 当前抓取的话题列表
            
        Returns:
            预测的热点话题列表
        """
        # 记录当前话题
        for topic in current_topics:
            keyword = topic.get("title", "") or topic.get("keyword", "")
            score = topic.get("hot_score", 0) or topic.get("score", 50)
            self.record_topic(keyword, score)
        
        trending = []
        
        for keyword, history in self.topic_history.items():
            if len(history) < 2:
                continue
            
            # 计算增长率
            growth_rate = self._calculate_growth_rate(history)
            
            # 计算传播速度
            velocity = self._calculate_velocity(history)
            
            # 预测峰值
            predicted_peak = self._predict_peak(history)
            
            # 计算置信度
            confidence = self._calculate_confidence(history, growth_rate)
            
            # 获取相关话题
            related = self._get_related_topics(keyword)
            
            # 情感分析
            sentiment = self._analyze_sentiment(keyword)
            
            # 获取当前分数
            current_score = history[-1][1] if history else 0
            
            # 判断是否为热点候选
            hot_score = self._calculate_hot_score(
                current_score, growth_rate, velocity, confidence
            )
            
            if hot_score > 50:  # 阈值
                trending.append(TrendingTopic(
                    keyword=keyword,
                    current_score=current_score,
                    growth_rate=growth_rate,
                    platforms=topic.get("platforms", ["unknown"]),
                    mention_count=len(history),
                    velocity=velocity,
                    predicted_peak=predicted_peak,
                    confidence=confidence,
                    related_topics=related,
                    sentiment=sentiment
                ))
        
        # 按热度排序
        trending.sort(key=lambda x: x.current_score * (1 + x.growth_rate), reverse=True)
        
        self.last_analysis = datetime.now()
        
        return trending[:20]  # 返回前20个热点
    
    def _calculate_growth_rate(self, history: List[Tuple[datetime, float]]) -> float:
        """计算增长率"""
        if len(history) < 2:
            return 0.0
        
        # 使用指数加权
        recent_scores = [sc for _, sc in history[-5:]]  # 最近5次
        if len(recent_scores) < 2:
            return 0.0
        
        # 计算平均增长率
        growth_rates = []
        for i in range(1, len(recent_scores)):
            if recent_scores[i-1] > 0:
                rate = (recent_scores[i] - recent_scores[i-1]) / recent_scores[i-1]
                growth_rates.append(rate)
        
        if not growth_rates:
            return 0.0
        
        # 加权平均，越近权重越高
        weights = [0.1, 0.15, 0.2, 0.25, 0.3][-len(growth_rates):]
        weighted_avg = sum(r * w for r, w in zip(growth_rates, weights)) / sum(weights)
        
        return weighted_avg
    
    def _calculate_velocity(self, history: List[Tuple[datetime, float]]) -> float:
        """计算传播速度（每小时提及次数）"""
        if len(history) < 2:
            return 0.0
        
        time_span = (history[-1][0] - history[0][0]).total_seconds() / 3600
        if time_span < 0.1:
            return len(history) * 10  # 短时间内高频出现
        
        return len(history) / time_span
    
    def _predict_peak(self, history: List[Tuple[datetime, float]]) -> datetime:
        """预测峰值时间"""
        if len(history) < 3:
            return datetime.now() + timedelta(hours=1)
        
        # 简单线性预测
        times = [(ts - history[0][0]).total_seconds() / 3600 for ts, _ in history]
        scores = [sc for _, sc in history]
        
        # 计算增长趋势
        n = len(times)
        sum_x = sum(times)
        sum_y = sum(scores)
        sum_xy = sum(x * y for x, y in zip(times, scores))
        sum_x2 = sum(x * x for x in times)
        
        if n * sum_x2 - sum_x * sum_x == 0:
            return datetime.now() + timedelta(hours=2)
        
        slope = (n * sum_xy - sum_x * sum_y) / (n * sum_x2 - sum_x * sum_x)
        
        # 预测达到峰值的时间（假设热度翻倍时达到峰值）
        if slope > 0:
            current_score = scores[-1]
            target_score = current_score * 2
            hours_to_peak = (target_score - current_score) / slope
            return datetime.now() + timedelta(hours=max(1, min(hours_to_peak, 48)))
        
        return datetime.now() + timedelta(hours=2)
    
    def _calculate_confidence(
        self,
        history: List[Tuple[datetime, float]],
        growth_rate: float
    ) -> float:
        """计算预测置信度"""
        confidence = 0.5  # 基础置信度
        
        # 数据点越多，置信度越高
        confidence += min(0.2, len(history) * 0.02)
        
        # 增长越稳定，置信度越高
        if len(history) >= 3:
            scores = [sc for _, sc in history]
            variance = sum((s - sum(scores)/len(scores))**2 for s in scores) / len(scores)
            stability = 1 / (1 + math.sqrt(variance) / 100)
            confidence += stability * 0.2
        
        # 增长率适中时置信度最高
        if 0.1 <= growth_rate <= 1.0:
            confidence += 0.1
        
        return min(1.0, confidence)
    
    def _get_related_topics(self, keyword: str, max_related: int = 5) -> List[str]:
        """获取相关话题"""
        related = self.keyword_graph.get(keyword, set())
        return list(related)[:max_related]
    
    def _analyze_sentiment(self, text: str) -> float:
        """简单情感分析"""
        positive_words = {
            "好", "优秀", "成功", "增长", "突破", "创新", "利好",
            "good", "great", "excellent", "success", "growth", "breakthrough"
        }
        negative_words = {
            "差", "失败", "下跌", "崩溃", "危机", "裁员", "亏损",
            "bad", "fail", "crash", "crisis", "loss", "decline"
        }
        
        text_lower = text.lower()
        pos_count = sum(1 for w in positive_words if w in text_lower)
        neg_count = sum(1 for w in negative_words if w in text_lower)
        
        total = pos_count + neg_count
        if total == 0:
            return 0.0
        
        return (pos_count - neg_count) / total
    
    def _calculate_hot_score(
        self,
        current_score: float,
        growth_rate: float,
        velocity: float,
        confidence: float
    ) -> float:
        """计算热点分数"""
        # 基础分数
        base = current_score
        
        # 增长加成
        growth_bonus = growth_rate * 100 if growth_rate > 0 else 0
        
        # 速度加成
        velocity_bonus = velocity * 10
        
        # 置信度加权
        total = (base + growth_bonus + velocity_bonus) * confidence
        
        return total
    
    def extract_keywords(self, text: str) -> List[str]:
        """提取关键词"""
        # 简单的关键词提取
        # 实际项目中可以使用jieba、spaCy等NLP库
        
        # 移除标点
        text = re.sub(r'[^\w\s]', ' ', text)
        
        # 分词（简化版）
        words = text.split()
        
        # 过滤停用词
        stopwords = {"的", "了", "在", "是", "我", "有", "和", "就", "不", "人", "the", "is", "a", "to", "of", "and"}
        keywords = [w for w in words if len(w) > 1 and w.lower() not in stopwords]
        
        # 统计词频
        word_freq = defaultdict(int)
        for word in keywords:
            word_freq[word] += 1
        
        # 返回高频词
        sorted_words = sorted(word_freq.items(), key=lambda x: x[1], reverse=True)
        return [word for word, _ in sorted_words[:10]]
    
    def build_keyword_graph(self, texts: List[str]):
        """构建关键词共现图"""
        for text in texts:
            keywords = self.extract_keywords(text)
            
            # 建立共现关系
            for i, kw1 in enumerate(keywords):
                for kw2 in keywords[i+1:]:
                    self.keyword_graph[kw1].add(kw2)
                    self.keyword_graph[kw2].add(kw1)
    
    def get_burst_keywords(self) -> List[str]:
        """获取突发关键词"""
        results = []
        
        for keyword, history in self.topic_history.items():
            if len(history) < 2:
                continue
            
            growth_rate = self._calculate_growth_rate(history)
            velocity = self._calculate_velocity(history)
            
            # 突发条件：快速增长 + 高传播速度
            if growth_rate > 0.5 and velocity > 5:
                results.append({
                    "keyword": keyword,
                    "growth_rate": growth_rate,
                    "velocity": velocity,
                    "mentions": len(history)
                })
        
        # 按综合分数排序
        results.sort(
            key=lambda x: x["growth_rate"] * x["velocity"],
            reverse=True
        )
        
        return results[:10]
    
    def get_report(self) -> Dict:
        """获取趋势预测报告"""
        return {
            "last_analysis": self.last_analysis.isoformat() if self.last_analysis else None,
            "tracked_topics": len(self.topic_history),
            "history_window_hours": self.history_window,
            "top_burst_keywords": self.get_burst_keywords()
        }


# 全局预测器实例
_predictor: Optional[TrendPredictor] = None


def get_trend_predictor() -> TrendPredictor:
    """获取全局预测器实例"""
    global _predictor
    if _predictor is None:
        _predictor = TrendPredictor()
    return _predictor


if __name__ == "__main__":
    # 测试
    predictor = get_trend_predictor()
    
    # 模拟一些数据
    test_topics = [
        {"title": "AI breakthrough in medical diagnosis", "hot_score": 80, "platforms": ["twitter", "reddit"]},
        {"title": "Bitcoin price surge", "hot_score": 95, "platforms": ["twitter", "news"]},
        {"title": "New iPhone announced", "hot_score": 70, "platforms": ["news", "tech"]},
    ]
    
    # 分析趋势
    trends = predictor.analyze_trends(test_topics)
    
    print("热点趋势预测:")
    for trend in trends:
        print(f"\n{trend.keyword}")
        print(f"  当前热度: {trend.current_score:.0f}")
        print(f"  增长率: {trend.growth_rate:.2%}")
        print(f"  传播速度: {trend.velocity:.1f}/h")
        print(f"  预测峰值: {trend.predicted_peak}")
        print(f"  置信度: {trend.confidence:.1%}")
