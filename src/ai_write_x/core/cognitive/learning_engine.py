"""
AIWriteX V19.0 - Learning Engine Module
学习引擎 - 持续学习和进化系统

功能:
1. 经验学习: 从每次交互中提取经验
2. 模式识别: 识别用户偏好和行为模式
3. 策略优化: 基于反馈优化生成策略
4. 知识迁移: 跨领域知识转移
"""

import json
from typing import Dict, List, Optional, Any, Callable
from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum, auto
from uuid import uuid4
import numpy as np
from collections import defaultdict, deque


class LearningMode(Enum):
    """学习模式"""
    SUPERVISED = "supervised"       # 监督学习: 基于反馈
    REINFORCEMENT = "reinforcement" # 强化学习: 基于奖励
    UNSUPERVISED = "unsupervised"   # 无监督学习: 模式发现
    FEW_SHOT = "few_shot"          # 少样本学习
    TRANSFER = "transfer"          # 迁移学习


class ExperienceType(Enum):
    """经验类型"""
    SUCCESS = "success"             # 成功经验
    FAILURE = "failure"             # 失败经验
    FEEDBACK = "feedback"           # 反馈经验
    OBSERVATION = "observation"     # 观察经验


@dataclass
class Experience:
    """经验条目"""
    id: str
    experience_type: ExperienceType
    context: Dict[str, Any]         # 上下文信息
    action: str                     # 采取的行动
    outcome: str                    # 结果
    reward: float                   # 奖励值 (-1 to 1)
    timestamp: datetime
    metadata: Dict[str, Any] = field(default_factory=dict)
    
    def to_dict(self) -> Dict:
        return {
            "id": self.id,
            "type": self.experience_type.value,
            "action": self.action,
            "outcome": self.outcome,
            "reward": self.reward,
            "timestamp": self.timestamp.isoformat()
        }


@dataclass
class Strategy:
    """策略"""
    id: str
    name: str
    description: str
    parameters: Dict[str, Any]
    success_rate: float = 0.0
    usage_count: int = 0
    created_at: datetime = field(default_factory=datetime.now)
    last_used: Optional[datetime] = None


class LearningEngine:
    """
    学习引擎
    
    实现持续学习和自我改进
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
        self.experiences: List[Experience] = []
        self.strategies: Dict[str, Strategy] = {}
        self.patterns: Dict[str, Any] = defaultdict(list)
        self.learning_rate = 0.1
        self.exploration_rate = 0.2
        
        # 初始化默认策略
        self._init_default_strategies()
    
    def _init_default_strategies(self):
        """初始化默认策略"""
        default_strategies = [
            Strategy(
                id="strategy_detailed",
                name="详细内容策略",
                description="生成详细、全面的内容",
                parameters={"length": "long", "depth": "detailed"}
            ),
            Strategy(
                id="strategy_concise",
                name="简洁内容策略",
                description="生成简洁、直击要点内容",
                parameters={"length": "short", "depth": "concise"}
            ),
            Strategy(
                id="strategy_storytelling",
                name="故事化策略",
                description="使用故事化叙述方式",
                parameters={"style": "story", "emotional": True}
            ),
            Strategy(
                id="strategy_data_driven",
                name="数据驱动策略",
                description="使用数据和事实支撑观点",
                parameters={"style": "analytical", "data_focused": True}
            )
        ]
        
        for strategy in default_strategies:
            self.strategies[strategy.id] = strategy
    
    def add_experience(
        self,
        experience_type: ExperienceType,
        context: Dict,
        action: str,
        outcome: str,
        reward: float,
        metadata: Dict = None
    ) -> Experience:
        """添加经验"""
        experience = Experience(
            id=str(uuid4()),
            experience_type=experience_type,
            context=context,
            action=action,
            outcome=outcome,
            reward=reward,
            timestamp=datetime.now(),
            metadata=metadata or {}
        )
        
        self.experiences.append(experience)
        
        # 更新策略
        self._update_strategies(experience)
        
        # 限制经验数量
        if len(self.experiences) > 1000:
            self.experiences = self.experiences[-1000:]
        
        return experience
    
    def _update_strategies(self, experience: Experience):
        """基于经验更新策略"""
        # 识别相关策略
        strategy_id = experience.context.get("strategy_id")
        if strategy_id and strategy_id in self.strategies:
            strategy = self.strategies[strategy_id]
            
            # 更新成功率
            strategy.usage_count += 1
            strategy.last_used = datetime.now()
            
            # 使用指数移动平均更新成功率
            alpha = self.learning_rate
            strategy.success_rate = (
                (1 - alpha) * strategy.success_rate +
                alpha * (1 if experience.reward > 0 else 0)
            )
    
    def learn_from_feedback(
        self,
        content_id: str,
        feedback: Dict[str, Any]
    ):
        """从反馈中学习"""
        # 解析反馈
        rating = feedback.get("rating", 3)  # 1-5评分
        comments = feedback.get("comments", "")
        
        # 转换为奖励值 (-1 to 1)
        reward = (rating - 3) / 2
        
        # 创建经验
        self.add_experience(
            experience_type=ExperienceType.FEEDBACK,
            context={"content_id": content_id, "feedback": feedback},
            action="content_generation",
            outcome=f"user_rating_{rating}",
            reward=reward,
            metadata={"comments": comments}
        )
        
        # 提取模式
        self._extract_patterns(feedback)
    
    def _extract_patterns(self, feedback: Dict):
        """从反馈中提取模式"""
        # 分析用户偏好
        preferences = feedback.get("preferences", {})
        
        for key, value in preferences.items():
            if value:
                self.patterns[f"pref_{key}"].append(value)
    
    def select_strategy(
        self,
        context: Dict[str, Any],
        explore: bool = True
    ) -> Strategy:
        """
        选择最优策略
        
        Args:
            context: 上下文信息
            explore: 是否允许探索
            
        Returns:
            选择的策略
        """
        # 探索 vs 利用
        if explore and np.random.random() < self.exploration_rate:
            # 随机选择策略进行探索
            return np.random.choice(list(self.strategies.values()))
        
        # 根据成功率选择策略
        valid_strategies = [
            s for s in self.strategies.values()
            if s.usage_count > 0 or s.success_rate > 0
        ]
        
        if not valid_strategies:
            return list(self.strategies.values())[0]
        
        # 根据成功率加权选择
        weights = [s.success_rate + 0.1 for s in valid_strategies]
        total = sum(weights)
        probabilities = [w / total for w in weights]
        
        return np.random.choice(valid_strategies, p=probabilities)
    
    def get_user_preferences(self) -> Dict[str, Any]:
        """获取学习到的用户偏好"""
        preferences = {}
        
        # 分析成功经验中的共同特征
        success_experiences = [
            e for e in self.experiences
            if e.experience_type == ExperienceType.SUCCESS or e.reward > 0.5
        ]
        
        if success_experiences:
            # 统计成功策略
            strategy_success = defaultdict(int)
            for exp in success_experiences:
                strategy_id = exp.context.get("strategy_id")
                if strategy_id:
                    strategy_success[strategy_id] += 1
            
            # 找出最成功的策略
            if strategy_success:
                best_strategy = max(strategy_success.items(), key=lambda x: x[1])
                preferences["preferred_strategy"] = best_strategy[0]
        
        # 添加模式偏好
        for pattern_key, values in self.patterns.items():
            if values:
                # 统计最常见的值
                value_counts = defaultdict(int)
                for v in values:
                    value_counts[v] += 1
                most_common = max(value_counts.items(), key=lambda x: x[1])
                preferences[pattern_key] = most_common[0]
        
        return preferences
    
    def adapt_parameters(self, base_parameters: Dict) -> Dict:
        """基于学习调整参数"""
        preferences = self.get_user_preferences()
        
        adapted = base_parameters.copy()
        
        # 根据学习到的偏好调整参数
        if "pref_length" in preferences:
            adapted["length"] = preferences["pref_length"]
        
        if "pref_style" in preferences:
            adapted["style"] = preferences["pref_style"]
        
        if "pref_tone" in preferences:
            adapted["tone"] = preferences["pref_tone"]
        
        return adapted
    
    def get_learning_stats(self) -> Dict:
        """获取学习统计"""
        if not self.experiences:
            return {
                "total_experiences": 0,
                "avg_reward": 0,
                "best_strategy": None
            }
        
        # 计算平均奖励
        avg_reward = np.mean([e.reward for e in self.experiences])
        
        # 找出最佳策略
        best_strategy = max(
            self.strategies.values(),
            key=lambda s: s.success_rate
        ) if self.strategies else None
        
        # 经验类型分布
        type_distribution = defaultdict(int)
        for exp in self.experiences:
            type_distribution[exp.experience_type.value] += 1
        
        return {
            "total_experiences": len(self.experiences),
            "avg_reward": avg_reward,
            "best_strategy": best_strategy.name if best_strategy else None,
            "strategy_count": len(self.strategies),
            "experience_types": dict(type_distribution),
            "learning_rate": self.learning_rate,
            "exploration_rate": self.exploration_rate
        }
    
    def export_knowledge(self) -> Dict:
        """导出学习到的知识"""
        return {
            "strategies": {
                sid: {
                    "name": s.name,
                    "success_rate": s.success_rate,
                    "usage_count": s.usage_count
                }
                for sid, s in self.strategies.items()
            },
            "preferences": self.get_user_preferences(),
            "patterns": dict(self.patterns),
            "stats": self.get_learning_stats()
        }
    
    def reset_learning(self):
        """重置学习状态"""
        self.experiences = []
        self.patterns = defaultdict(list)
        self._init_default_strategies()


# 全局学习引擎实例
learning_engine = LearningEngine()


def get_learning_engine() -> LearningEngine:
    """获取学习引擎实例"""
    return learning_engine
