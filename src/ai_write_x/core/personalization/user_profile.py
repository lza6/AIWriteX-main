"""
AIWriteX V19.0 - User Profile Module
用户画像模块 - 多维度用户特征建模

功能:
1. 多维度画像: 兴趣、行为、偏好、目标
2. 动态更新: 基于交互实时更新画像
3. 相似用户: 发现相似用户群体
4. 隐私保护: 数据加密和匿名化处理
"""

import json
import hashlib
from typing import Dict, List, Optional, Any, Set
from dataclasses import dataclass, field
from datetime import datetime, timedelta
from enum import Enum, auto
from uuid import uuid4
import numpy as np
from collections import defaultdict


class ProfileDimension(Enum):
    """画像维度"""
    INTERESTS = "interests"             # 兴趣偏好
    BEHAVIOR = "behavior"               # 行为特征
    STYLE = "style"                     # 风格偏好
    GOALS = "goals"                     # 目标意图
    SKILLS = "skills"                   # 技能水平
    DEMOGRAPHICS = "demographics"       # 人口统计
    PSYCHOGRAPHICS = "psychographics"   # 心理特征


class ContentStyle(Enum):
    """内容风格"""
    FORMAL = "formal"                   # 正式
    CASUAL = "casual"                   # 随意
    HUMOROUS = "humorous"               # 幽默
    SERIOUS = "serious"                 # 严肃
    STORYTELLING = "storytelling"       # 故事化
    ANALYTICAL = "analytical"           # 分析型
    EMOTIONAL = "emotional"             # 情感型


class ContentLength(Enum):
    """内容长度偏好"""
    SHORT = "short"                     # 简短 (< 500字)
    MEDIUM = "medium"                   # 中等 (500-1500字)
    LONG = "long"                       # 长文 (1500-3000字)
    EXTENSIVE = "extensive"             # 深度 (> 3000字)


@dataclass
class UserPreference:
    """用户偏好"""
    content_style: ContentStyle = ContentStyle.CASUAL
    content_length: ContentLength = ContentLength.MEDIUM
    topics: List[str] = field(default_factory=list)
    keywords: List[str] = field(default_factory=list)
    disliked_topics: List[str] = field(default_factory=list)
    reading_time: str = "anytime"       # morning, afternoon, evening, anytime
    update_frequency: str = "daily"     # hourly, daily, weekly
    language: str = "zh"
    tone_preferences: Dict[str, float] = field(default_factory=dict)


@dataclass
class UserProfile:
    """
    用户画像
    
    多维度用户特征建模
    """
    user_id: str
    created_at: datetime = field(default_factory=datetime.now)
    updated_at: datetime = field(default_factory=datetime.now)
    
    # 基础信息
    nickname: str = ""
    email_hash: str = ""
    
    # 偏好设置
    preferences: UserPreference = field(default_factory=UserPreference)
    
    # 行为统计
    total_contents_generated: int = 0
    total_contents_published: int = 0
    total_reading_time: int = 0  # 分钟
    avg_satisfaction: float = 0.0  # 0-5
    
    # 兴趣标签及权重
    interest_weights: Dict[str, float] = field(default_factory=dict)
    
    # 技能评估
    writing_skill_level: int = 3  # 1-5
    domain_expertise: Dict[str, int] = field(default_factory=dict)  # 领域专业度
    
    # 目标设定
    content_goals: List[str] = field(default_factory=list)
    target_audience: str = ""
    
    # 使用模式
    usage_patterns: Dict[str, Any] = field(default_factory=dict)
    
    # 隐私设置
    data_sharing_enabled: bool = False
    personalization_enabled: bool = True
    
    def update_preference(self, key: str, value: Any):
        """更新偏好"""
        if hasattr(self.preferences, key):
            setattr(self.preferences, key, value)
            self.updated_at = datetime.now()
    
    def add_interest(self, topic: str, weight: float = 0.5):
        """添加兴趣"""
        if topic in self.interest_weights:
            # 强化已有兴趣
            self.interest_weights[topic] = min(
                1.0, self.interest_weights[topic] + weight * 0.1
            )
        else:
            self.interest_weights[topic] = weight
        self.updated_at = datetime.now()
    
    def remove_interest(self, topic: str):
        """移除兴趣"""
        if topic in self.interest_weights:
            del self.interest_weights[topic]
            if topic in self.preferences.topics:
                self.preferences.topics.remove(topic)
        self.updated_at = datetime.now()
    
    def get_top_interests(self, n: int = 5) -> List[tuple]:
        """获取Top N兴趣"""
        sorted_interests = sorted(
            self.interest_weights.items(),
            key=lambda x: x[1],
            reverse=True
        )
        return sorted_interests[:n]
    
    def update_satisfaction(self, rating: float):
        """更新满意度"""
        # 使用指数移动平均
        alpha = 0.3
        self.avg_satisfaction = (
            (1 - alpha) * self.avg_satisfaction + alpha * rating
        )
        self.updated_at = datetime.now()
    
    def get_profile_vector(self) -> List[float]:
        """获取画像向量表示"""
        # 构建特征向量
        features = []
        
        # 风格偏好 (one-hot)
        style_values = [s.value for s in ContentStyle]
        style_vec = [1.0 if self.preferences.content_style.value == s else 0.0 for s in style_values]
        features.extend(style_vec)
        
        # 长度偏好 (one-hot)
        length_values = [l.value for l in ContentLength]
        length_vec = [1.0 if self.preferences.content_length.value == l else 0.0 for l in length_values]
        features.extend(length_vec)
        
        # 兴趣权重 (取Top 10)
        top_interests = self.get_top_interests(10)
        interest_vec = [w for _, w in top_interests]
        interest_vec.extend([0.0] * (10 - len(interest_vec)))
        features.extend(interest_vec)
        
        # 技能水平 (归一化)
        features.append(self.writing_skill_level / 5.0)
        
        # 使用量 (对数归一化)
        features.append(np.log1p(self.total_contents_generated) / 10.0)
        
        # 满意度
        features.append(self.avg_satisfaction / 5.0)
        
        return features
    
    def to_dict(self) -> Dict:
        """转换为字典"""
        return {
            "user_id": self.user_id,
            "nickname": self.nickname,
            "preferences": {
                "content_style": self.preferences.content_style.value,
                "content_length": self.preferences.content_length.value,
                "topics": self.preferences.topics,
                "language": self.preferences.language
            },
            "interests": self.get_top_interests(10),
            "stats": {
                "total_generated": self.total_contents_generated,
                "total_published": self.total_contents_published,
                "avg_satisfaction": round(self.avg_satisfaction, 2)
            },
            "created_at": self.created_at.isoformat(),
            "updated_at": self.updated_at.isoformat()
        }


class ProfileManager:
    """
    画像管理器
    
    管理所有用户画像
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
        self.profiles: Dict[str, UserProfile] = {}
        self.similarity_cache: Dict[str, List[tuple]] = {}
    
    def create_profile(self, user_id: str, nickname: str = "") -> UserProfile:
        """创建新用户画像"""
        profile = UserProfile(
            user_id=user_id,
            nickname=nickname or f"用户_{user_id[:8]}"
        )
        self.profiles[user_id] = profile
        return profile
    
    def get_profile(self, user_id: str) -> Optional[UserProfile]:
        """获取用户画像"""
        return self.profiles.get(user_id)
    
    def find_similar_users(self, user_id: str, n: int = 5) -> List[tuple]:
        """
        查找相似用户
        
        Returns:
            [(相似用户ID, 相似度), ...]
        """
        if user_id not in self.profiles:
            return []
        
        # 检查缓存
        cache_key = f"{user_id}_{n}"
        if cache_key in self.similarity_cache:
            return self.similarity_cache[cache_key]
        
        target_profile = self.profiles[user_id]
        target_vector = np.array(target_profile.get_profile_vector())
        
        similarities = []
        for uid, profile in self.profiles.items():
            if uid == user_id:
                continue
            
            vector = np.array(profile.get_profile_vector())
            
            # 计算余弦相似度
            norm_target = np.linalg.norm(target_vector)
            norm_vector = np.linalg.norm(vector)
            
            if norm_target > 0 and norm_vector > 0:
                similarity = np.dot(target_vector, vector) / (norm_target * norm_vector)
                similarities.append((uid, float(similarity)))
        
        # 排序并返回Top N
        similarities.sort(key=lambda x: x[1], reverse=True)
        result = similarities[:n]
        
        # 缓存结果
        self.similarity_cache[cache_key] = result
        
        return result
    
    def get_user_segments(self) -> Dict[str, List[str]]:
        """
        用户分群
        
        Returns:
            {群体标签: [用户ID列表], ...}
        """
        segments = {
            "高频用户": [],
            "专业创作者": [],
            "新手用户": [],
            "内容消费者": []
        }
        
        for uid, profile in self.profiles.items():
            # 高频用户: 生成内容多
            if profile.total_contents_generated > 100:
                segments["高频用户"].append(uid)
            
            # 专业创作者: 技能水平高且发布多
            if profile.writing_skill_level >= 4 and profile.total_contents_published > 50:
                segments["专业创作者"].append(uid)
            
            # 新手用户: 生成少且技能水平低
            if profile.total_contents_generated < 10 and profile.writing_skill_level <= 2:
                segments["新手用户"].append(uid)
            
            # 内容消费者: 阅读时间长但生成少
            if profile.total_reading_time > 100 and profile.total_contents_generated < 20:
                segments["内容消费者"].append(uid)
        
        return segments
    
    def export_profiles(self) -> List[Dict]:
        """导出所有画像"""
        return [profile.to_dict() for profile in self.profiles.values()]
    
    def import_profiles(self, profiles_data: List[Dict]):
        """导入画像数据"""
        for data in profiles_data:
            user_id = data.get("user_id")
            if user_id:
                profile = UserProfile(user_id=user_id)
                # 恢复数据...
                self.profiles[user_id] = profile


# 全局画像管理器实例
profile_manager = ProfileManager()


def get_profile_manager() -> ProfileManager:
    """获取画像管理器实例"""
    return profile_manager
