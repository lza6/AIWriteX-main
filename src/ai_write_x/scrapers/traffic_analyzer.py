#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
流量分析系统 V18 - 智能爆款预测
分析全网新闻热度，预测可能爆火的内容
"""
import json
import math
import re
from datetime import datetime, timedelta
from typing import List, Dict, Tuple, Optional
from collections import defaultdict
from dataclasses import dataclass

from logger_utils import logger


@dataclass
class TrafficScore:
    """流量分数"""
    total_score: float
    authority_score: float  # 权威度
    trending_score: float   # 趋势分
    freshness_score: float  # 新鲜度
    viral_score: float      # 传播潜力
    engagement_score: float # 互动潜力


class TrafficAnalyzer:
    """
    流量分析系统
    评估新闻内容的流量潜力
    """
    
    def __init__(self):
        # 权威媒体权重
        self.authority_weights = {
            # 国际权威
            "BBC": 10, "纽约时报": 10, "Reuters": 10, "AP": 10,
            "华尔街日报": 10, "Financial Times": 10, "Bloomberg": 10,
            "The Guardian": 9, "CNN": 9, "Washington Post": 9,
            "Reuters": 10, "AP": 10, "NPR": 9, "Economist": 10,
            
            # 科技权威
            "TechCrunch": 8, "The Verge": 8, "Wired": 8,
            "Ars Technica": 8, "MIT Tech Review": 9, "Nature": 10,
            "Science": 10, "OpenAI": 10, "DeepMind": 10, "Anthropic": 10,
            
            # 国内权威
            "新华社": 9, "人民日报": 9, "澎湃新闻": 8, "财经": 8,
            "36氪": 7, "机器之心": 8, "极客公园": 7,
            
            # 社交媒体
            "知乎": 6, "微博": 6, "抖音": 7, "B站": 6,
            "GitHub": 7, "Hacker News": 8, "Reddit": 6,
        }
        
        # 热点关键词权重
        self.viral_keywords = {
            # 科技热点
            "AI": 3.0, "人工智能": 3.0, "ChatGPT": 3.0, "GPT": 3.0,
            "大模型": 2.5, "LLM": 2.5, "OpenAI": 2.5, "Claude": 2.5,
            "机器学习": 2.0, "深度学习": 2.0, "神经网络": 2.0,
            "自动驾驶": 2.0, "机器人": 2.0, "人形机器人": 2.5,
            "芯片": 2.0, "半导体": 2.0, "光刻机": 2.5, "英伟达": 2.5,
            "苹果": 2.0, "iPhone": 2.0, "华为": 2.5, "小米": 1.5,
            "特斯拉": 2.0, "马斯克": 2.5, "SpaceX": 2.5,
            
            # 财经热点
            "比特币": 2.5, "加密货币": 2.5, "区块链": 2.0,
            "股市": 2.0, "A股": 2.0, "港股": 2.0, "美股": 2.0,
            "暴涨": 2.0, "暴跌": 2.5, "崩盘": 3.0, "涨停": 2.0,
            "降息": 2.0, "加息": 2.0, "美联储": 2.0, "央行": 1.8,
            "通胀": 2.0, " recession": 2.5, "经济危机": 3.0,
            
            # 社会热点
            "疫情": 2.0, "病毒": 2.0, "疫苗": 1.8,
            "战争": 3.0, "冲突": 2.5, "制裁": 2.0,
            "特朗普": 2.0, "拜登": 1.8, "美国大选": 2.5,
            "俄罗斯": 2.0, "乌克兰": 2.0, "中国": 1.5,
            
            # 爆款词
            "震惊": 1.5, "重磅": 1.5, "突发": 2.0, "独家": 1.5,
            "揭秘": 1.5, "曝光": 1.5, "真相": 1.5,
            "Breaking": 2.0, "Exclusive": 1.5, "Urgent": 2.0,
            "Alert": 1.8, "Just In": 1.8, "Live": 1.5,
            
            # 情感词
            "裁员": 2.0, "失业": 2.0, "倒闭": 2.5, "破产": 2.5,
            "突破": 1.8, "创纪录": 1.8, "里程碑": 1.8,
        }
        
        # 标题爆款模式
        self.viral_patterns = [
            r"^(震惊|重磅|突发|独家|揭秘|曝光)",
            r"(暴涨|暴跌|崩盘|涨停|跌停)",
            r"(首次|突破|创纪录|里程碑)",
            r"(最.*的|史上|全球|全国)",
            r"(AI|人工智能|ChatGPT).*重磅",
            r"(马斯克|特斯拉|OpenAI).*新",
        ]
    
    def analyze(self, title: str, source: str = "", content: str = "") -> TrafficScore:
        """
        分析内容的流量潜力
        
        Returns:
            TrafficScore: 各项流量分数
        """
        # 1. 权威度分数
        authority_score = self._calculate_authority(source)
        
        # 2. 趋势分数
        trending_score = self._calculate_trending(title, content)
        
        # 3. 新鲜度分数
        freshness_score = self._calculate_freshness(title, content)
        
        # 4. 传播潜力
        viral_score = self._calculate_viral_potential(title, content)
        
        # 5. 互动潜力
        engagement_score = self._calculate_engagement(title, content)
        
        # 计算总分
        total_score = (
            authority_score * 0.25 +
            trending_score * 0.25 +
            freshness_score * 0.15 +
            viral_score * 0.20 +
            engagement_score * 0.15
        )
        
        return TrafficScore(
            total_score=total_score,
            authority_score=authority_score,
            trending_score=trending_score,
            freshness_score=freshness_score,
            viral_score=viral_score,
            engagement_score=engagement_score
        )
    
    def _calculate_authority(self, source: str) -> float:
        """计算权威度分数 (0-100)"""
        base_score = 50  # 基础分
        
        # 根据来源加权
        for key, weight in self.authority_weights.items():
            if key.lower() in source.lower():
                base_score = max(base_score, weight * 10)
        
        return min(100, base_score)
    
    def _calculate_trending(self, title: str, content: str) -> float:
        """计算趋势分数 (0-100)"""
        text = f"{title} {content}".lower()
        score = 30  # 基础分
        
        # 热点关键词加分
        for keyword, weight in self.viral_keywords.items():
            if keyword.lower() in text:
                score += weight * 10
        
        return min(100, score)
    
    def _calculate_freshness(self, title: str, content: str) -> float:
        """计算新鲜度分数 (0-100)"""
        text = f"{title} {content}".lower()
        score = 50  # 基础分
        
        # 时间相关词
        fresh_keywords = [
            "刚刚", "最新", "今日", "今天", "实时", "live",
            "now", "latest", "breaking", "just", "today",
            "突发", "快讯", "即时"
        ]
        
        for kw in fresh_keywords:
            if kw.lower() in text:
                score += 10
        
        return min(100, score)
    
    def _calculate_viral_potential(self, title: str, content: str) -> float:
        """计算传播潜力 (0-100)"""
        score = 30  # 基础分
        
        # 检查爆款模式
        for pattern in self.viral_patterns:
            if re.search(pattern, title, re.IGNORECASE):
                score += 20
        
        # 数字吸引度
        if re.search(r'\d+', title):
            score += 5
        
        # 标点符号情感
        if '！' in title or '!' in title:
            score += 5
        if '？' in title or '?' in title:
            score += 3
        
        # 标题长度适中 (15-30字最佳)
        title_len = len(title)
        if 15 <= title_len <= 30:
            score += 10
        elif title_len < 10:
            score -= 5
        elif title_len > 50:
            score -= 10
        
        return min(100, max(0, score))
    
    def _calculate_engagement(self, title: str, content: str) -> float:
        """计算互动潜力 (0-100)"""
        score = 40  # 基础分
        
        # 争议性话题
        controversial = [
            "争议", " debate", " argue", " criticize",
            " vs ", "对比", "PK", "较量",
            "为什么", "怎么办", "如何", "真相",
        ]
        
        for word in controversial:
            if word.lower() in title.lower():
                score += 10
        
        # 情感词
        emotional = [
            "震惊", "愤怒", "感动", "泪目", "心疼",
            "amazing", "shocking", "outrage", "touching"
        ]
        
        for word in emotional:
            if word.lower() in title.lower():
                score += 8
        
        return min(100, score)
    
    def rank_content(self, items: List[Dict]) -> List[Dict]:
        """
        对内容列表进行流量潜力排序
        
        Args:
            items: 新闻列表，每项包含title, source, content等
            
        Returns:
            排序后的列表，每项增加traffic_score字段
        """
        ranked = []
        
        for item in items:
            title = item.get("title", "")
            source = item.get("source", "")
            content = item.get("content", "") or item.get("summary", "")
            
            score = self.analyze(title, source, content)
            
            ranked.append({
                **item,
                "traffic_score": {
                    "total": round(score.total_score, 2),
                    "authority": round(score.authority_score, 2),
                    "trending": round(score.trending_score, 2),
                    "freshness": round(score.freshness_score, 2),
                    "viral": round(score.viral_score, 2),
                    "engagement": round(score.engagement_score, 2),
                },
                "predicted_views": self._estimate_views(score.total_score)
            })
        
        # 按总分排序
        ranked.sort(key=lambda x: x["traffic_score"]["total"], reverse=True)
        
        return ranked
    
    def _estimate_views(self, score: float) -> str:
        """预估阅读量"""
        if score >= 90:
            return "100万+"
        elif score >= 80:
            return "50万+"
        elif score >= 70:
            return "20万+"
        elif score >= 60:
            return "10万+"
        elif score >= 50:
            return "5万+"
        else:
            return "1万+"
    
    def get_viral_candidates(self, items: List[Dict], top_n: int = 10) -> List[Dict]:
        """获取可能爆火的候选内容"""
        ranked = self.rank_content(items)
        
        # 过滤高潜力内容
        candidates = [
            item for item in ranked
            if item["traffic_score"]["total"] >= 60
        ]
        
        return candidates[:top_n]
    
    def get_category_analysis(self, items: List[Dict]) -> Dict:
        """分类分析"""
        categories = defaultdict(list)
        
        for item in items:
            cat = item.get("category", "其他")
            categories[cat].append(item)
        
        analysis = {}
        for cat, cat_items in categories.items():
            scores = [item.get("traffic_score", {}).get("total", 0) for item in cat_items]
            analysis[cat] = {
                "count": len(cat_items),
                "avg_score": sum(scores) / len(scores) if scores else 0,
                "max_score": max(scores) if scores else 0,
                "top_item": cat_items[0] if cat_items else None
            }
        
        return analysis


# 全局分析器
_analyzer: Optional[TrafficAnalyzer] = None


def get_traffic_analyzer() -> TrafficAnalyzer:
    """获取全局分析器"""
    global _analyzer
    if _analyzer is None:
        _analyzer = TrafficAnalyzer()
    return _analyzer


if __name__ == "__main__":
    # 测试
    analyzer = get_traffic_analyzer()
    
    test_items = [
        {"title": "ChatGPT-5突然发布，性能暴涨300%，震惊AI界", "source": "机器之心", "category": "AI"},
        {"title": "苹果股价暴跌20%，市值蒸发万亿", "source": "财经网", "category": "财经"},
        {"title": "某明星离婚", "source": "微博", "category": "娱乐"},
        {"title": "Python 4.0发布", "source": "GitHub", "category": "技术"},
    ]
    
    ranked = analyzer.rank_content(test_items)
    
    print("流量潜力分析:")
    for item in ranked:
        print(f"\n{item['title']}")
        print(f"  总分: {item['traffic_score']['total']}")
        print(f"  预估阅读: {item['predicted_views']}")
