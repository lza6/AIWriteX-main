"""
AIWriteX V19.0 - Recommendation Engine
推荐引擎 - 个性化内容推荐系统

功能:
1. 内容推荐: 基于用户画像的内容推荐
2. 模板推荐: 适合用户风格的模板
3. 话题推荐: 用户可能感兴趣的话题
4. 时机推荐: 最佳发布时机
"""

import json
import random
from typing import Dict, List, Optional, Any, Tuple
from dataclasses import dataclass
from datetime import datetime, timedelta
from enum import Enum, auto
from collections import defaultdict
import numpy as np


class RecommendationType(Enum):
    """推荐类型"""
    CONTENT_TOPIC = "content_topic"     # 内容话题
    TEMPLATE = "template"               # 模板
    PUBLISH_TIME = "publish_time"       # 发布时间
    STYLE = "style"                     # 风格
    KEYWORD = "keyword"                 # 关键词
    REFERENCE = "reference"             # 参考资料


@dataclass
class Recommendation:
    """推荐项"""
    id: str
    type: RecommendationType
    item: Any                           # 推荐内容
    score: float                       # 推荐分数 0-1
    reason: str                        # 推荐理由
    confidence: float                  # 置信度
    timestamp: datetime


class RecommendationEngine:
    """
    推荐引擎
    
    提供个性化推荐服务
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
        self.user_interactions: Dict[str, List[Dict]] = defaultdict(list)
        self.content_features: Dict[str, Dict] = {}
        self.template_scores: Dict[str, Dict[str, float]] = defaultdict(dict)
        self.topic_trends: Dict[str, float] = {}
        
        # 最佳发布时间（按小时）
        self.optimal_hours = {
            "morning": [7, 8, 9],           # 早高峰
            "lunch": [12, 13],              # 午休
            "evening": [18, 19, 20, 21],    # 晚高峰
            "night": [22, 23]               # 睡前
        }
    
    def recommend_topics(
        self,
        user_id: str,
        user_interests: List[str],
        n: int = 5
    ) -> List[Recommendation]:
        """推荐内容话题"""
        # 基于用户兴趣生成话题
        recommendations = []
        
        # 热门话题
        hot_topics = [
            "人工智能发展趋势",
            "数字化转型案例",
            "职场效率提升",
            "健康生活方式",
            "投资理财技巧",
            "教育创新方法",
            "科技产品评测",
            "心理健康管理"
        ]
        
        # 根据兴趣过滤和排序
        for topic in hot_topics:
            score = self._calculate_topic_score(topic, user_interests)
            if score > 0.3:
                recommendations.append(Recommendation(
                    id=f"topic_{hash(topic)}",
                    type=RecommendationType.CONTENT_TOPIC,
                    item=topic,
                    score=score,
                    reason=f"与您的兴趣 '{random.choice(user_interests)}' 相关" if user_interests else "热门话题",
                    confidence=score,
                    timestamp=datetime.now()
                ))
        
        # 按分数排序
        recommendations.sort(key=lambda x: x.score, reverse=True)
        return recommendations[:n]
    
    def _calculate_topic_score(self, topic: str, interests: List[str]) -> float:
        """计算话题匹配分数"""
        if not interests:
            return 0.5
        
        # 简单的关键词匹配
        topic_words = set(topic.lower().split())
        max_score = 0.0
        
        for interest in interests:
            interest_words = set(interest.lower().split())
            if topic_words & interest_words:
                score = len(topic_words & interest_words) / len(topic_words | interest_words)
                max_score = max(max_score, score)
        
        return max_score
    
    def recommend_templates(
        self,
        user_id: str,
        content_type: str,
        user_style: str,
        n: int = 3
    ) -> List[Recommendation]:
        """推荐模板"""
        # 模板库
        templates = [
            {"id": "t1", "name": "简洁商务", "style": "formal", "category": "business"},
            {"id": "t2", "name": "活泼创意", "style": "casual", "category": "creative"},
            {"id": "t3", "name": "数据驱动", "style": "analytical", "category": "data"},
            {"id": "t4", "name": "故事叙述", "style": "storytelling", "category": "narrative"},
            {"id": "t5", "name": "极简主义", "style": "minimal", "category": "minimal"}
        ]
        
        recommendations = []
        
        for template in templates:
            # 计算匹配分数
            style_match = 1.0 if template["style"] == user_style else 0.3
            category_match = 0.7 if template["category"] == content_type else 0.4
            
            # 用户历史偏好
            history_score = self.template_scores.get(user_id, {}).get(template["id"], 0.5)
            
            score = (style_match * 0.4 + category_match * 0.3 + history_score * 0.3)
            
            recommendations.append(Recommendation(
                id=template["id"],
                type=RecommendationType.TEMPLATE,
                item=template,
                score=score,
                reason=f"符合您的{user_style}风格偏好" if style_match > 0.5 else "多样化推荐",
                confidence=score,
                timestamp=datetime.now()
            ))
        
        recommendations.sort(key=lambda x: x.score, reverse=True)
        return recommendations[:n]
    
    def recommend_publish_time(
        self,
        user_id: str,
        target_audience: str = "general"
    ) -> Recommendation:
        """推荐最佳发布时间"""
        current_hour = datetime.now().hour
        
        # 根据不同受众推荐
        if target_audience == "business":
            recommended_slots = self.optimal_hours["morning"] + self.optimal_hours["lunch"]
        elif target_audience == "young":
            recommended_slots = self.optimal_hours["evening"] + self.optimal_hours["night"]
        else:
            recommended_slots = self.optimal_hours["evening"]
        
        # 选择下一个即将到来的时间段
        next_slot = None
        for slot in sorted(recommended_slots):
            if slot > current_hour:
                next_slot = slot
                break
        
        if next_slot is None:
            next_slot = recommended_slots[0]  # 明天第一个时间段
        
        recommended_time = datetime.now().replace(hour=next_slot, minute=0, second=0)
        if next_slot < current_hour:
            recommended_time += timedelta(days=1)
        
        return Recommendation(
            id=f"time_{user_id}_{next_slot}",
            type=RecommendationType.PUBLISH_TIME,
            item=recommended_time,
            score=0.85,
            reason=f"{target_audience}受众在{next_slot}:00时段最活跃",
            confidence=0.85,
            timestamp=datetime.now()
        )
    
    def recommend_keywords(
        self,
        user_id: str,
        topic: str,
        n: int = 5
    ) -> List[Recommendation]:
        """推荐关键词"""
        # 基于话题的关键词库
        keyword_library = {
            "人工智能": ["AI", "机器学习", "深度学习", "神经网络", "自然语言处理"],
            "职场": ["效率", "时间管理", "职业发展", "沟通技巧", "领导力"],
            "健康": ["运动", "饮食", "睡眠", "心理健康", "生活习惯"],
            "投资": ["理财", "股票", "基金", "风险管理", "资产配置"],
            "教育": ["学习方法", "在线教育", "技能培训", "知识管理", "终身学习"]
        }
        
        # 找到最匹配的话题
        best_match = None
        best_score = 0.0
        
        for lib_topic, keywords in keyword_library.items():
            score = self._calculate_topic_score(topic, [lib_topic])
            if score > best_score:
                best_score = score
                best_match = keywords
        
        if not best_match:
            best_match = ["创新", "趋势", "分析", "案例", "实践"]
        
        recommendations = [
            Recommendation(
                id=f"kw_{i}",
                type=RecommendationType.KEYWORD,
                item=kw,
                score=0.7 + (0.3 * (len(best_match) - i) / len(best_match)),
                reason=f"与'{topic}'话题高度相关",
                confidence=0.8,
                timestamp=datetime.now()
            )
            for i, kw in enumerate(best_match[:n])
        ]
        
        return recommendations
    
    def recommend_style_adaptation(
        self,
        user_id: str,
        content_goal: str
    ) -> Recommendation:
        """推荐风格适配"""
        style_mapping = {
            "专业": "formal",
            "轻松": "casual",
            "幽默": "humorous",
            "严肃": "serious",
            "故事": "storytelling",
            "分析": "analytical"
        }
        
        # 根据内容目标推荐风格
        if "教育" in content_goal or "专业" in content_goal:
            recommended_style = "formal"
            reason = "教育/专业内容适合正式风格"
        elif "娱乐" in content_goal or "轻松" in content_goal:
            recommended_style = "casual"
            reason = "娱乐内容适合轻松风格"
        elif "深度" in content_goal or "分析" in content_goal:
            recommended_style = "analytical"
            reason = "深度分析适合分析型风格"
        else:
            recommended_style = "storytelling"
            reason = "故事叙述更具吸引力"
        
        return Recommendation(
            id=f"style_{user_id}_{recommended_style}",
            type=RecommendationType.STYLE,
            item=recommended_style,
            score=0.8,
            reason=reason,
            confidence=0.8,
            timestamp=datetime.now()
        )
    
    def record_feedback(
        self,
        user_id: str,
        recommendation_id: str,
        accepted: bool,
        rating: Optional[float] = None
    ):
        """记录推荐反馈"""
        self.user_interactions[user_id].append({
            "recommendation_id": recommendation_id,
            "accepted": accepted,
            "rating": rating,
            "timestamp": datetime.now()
        })
        
        # 更新模板评分（如果是模板推荐）
        if "template" in recommendation_id:
            template_id = recommendation_id.split("_")[-1]
            current_score = self.template_scores[user_id].get(template_id, 0.5)
            
            # 使用指数移动平均更新
            feedback_score = 1.0 if accepted else 0.0
            if rating:
                feedback_score = rating / 5.0
            
            new_score = 0.7 * current_score + 0.3 * feedback_score
            self.template_scores[user_id][template_id] = new_score
    
    def get_recommendation_stats(self, user_id: str) -> Dict:
        """获取推荐统计"""
        interactions = self.user_interactions.get(user_id, [])
        
        if not interactions:
            return {
                "total_interactions": 0,
                "acceptance_rate": 0.0,
                "avg_rating": 0.0
            }
        
        accepted = sum(1 for i in interactions if i["accepted"])
        ratings = [i["rating"] for i in interactions if i["rating"]]
        
        return {
            "total_interactions": len(interactions),
            "acceptance_rate": accepted / len(interactions),
            "avg_rating": sum(ratings) / len(ratings) if ratings else 0.0
        }


# 全局推荐引擎实例
recommendation_engine = RecommendationEngine()


def get_recommendation_engine() -> RecommendationEngine:
    """获取推荐引擎实例"""
    return recommendation_engine
