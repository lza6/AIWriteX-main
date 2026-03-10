"""
AIWriteX V19.0 - Personalization System
深度个性化系统 - 用户行为学习、个性化推荐、自适应风格

功能:
1. 用户画像: 多维度用户特征建模
2. 行为学习: 从用户交互中学习偏好
3. 个性化推荐: 基于协同过滤和内容匹配
4. 自适应风格: 根据用户偏好调整生成风格
"""

from .user_profile import UserProfile, UserPreference, ProfileDimension
from .behavior_tracker import BehaviorTracker, BehaviorEvent
from .recommendation_engine import RecommendationEngine, RecommendationType

__all__ = [
    'UserProfile',
    'UserPreference',
    'ProfileDimension',
    'BehaviorTracker',
    'BehaviorEvent',
    'RecommendationEngine',
    'RecommendationType'
]
