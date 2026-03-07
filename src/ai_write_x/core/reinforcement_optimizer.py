# -*- coding: UTF-8 -*-
"""
V16.0 - Reinforcement Optimizer (强化学习优化器)

基于内容发布效果的反馈，持续优化：
1. 话题选择策略
2. 生成参数 (温度、模型选择)
3. 模板选择
4. 发布时间

使用多臂老虎机 (MAB) 和上下文老虎机 (LinUCB) 算法。
"""

import json
import random
import numpy as np
from datetime import datetime, timedelta
from typing import Dict, List, Optional, Tuple, Any
from dataclasses import dataclass
from collections import defaultdict
import threading

from src.ai_write_x.utils import log
from src.ai_write_x.database.db_manager import db_manager


@dataclass
class Arm:
    """多臂老虎机的臂 (可选策略)"""
    id: str
    name: str
    config: Dict[str, Any]
    
    # 统计
    pulls: int = 0  # 拉动次数
    rewards: float = 0.0  # 总奖励
    
    @property
    def average_reward(self) -> float:
        return self.rewards / max(self.pulls, 1)


class EpsilonGreedyMAB:
    """Epsilon-Greedy 多臂老虎机"""
    
    def __init__(self, epsilon: float = 0.1):
        self.epsilon = epsilon  # 探索概率
        self.arms: Dict[str, Arm] = {}
        
    def add_arm(self, arm: Arm):
        """添加臂"""
        self.arms[arm.id] = arm
    
    def select_arm(self) -> Arm:
        """选择臂 (探索或利用)"""
        if not self.arms:
            raise ValueError("No arms available")
        
        # 探索
        if random.random() < self.epsilon:
            return random.choice(list(self.arms.values()))
        
        # 利用 - 选择平均奖励最高的
        return max(self.arms.values(), key=lambda a: a.average_reward)
    
    def update(self, arm_id: str, reward: float):
        """更新臂的统计"""
        if arm_id in self.arms:
            self.arms[arm_id].pulls += 1
            self.arms[arm_id].rewards += reward


class LinUCB:
    """线性上下文老虎机 (LinUCB)"""
    
    def __init__(self, n_features: int, alpha: float = 1.0):
        self.n_features = n_features
        self.alpha = alpha  # 探索参数
        
        # 每个臂的参数
        self.A: Dict[str, np.ndarray] = {}  # 特征协方差矩阵
        self.b: Dict[str, np.ndarray] = {}  # 奖励向量
        
    def initialize_arm(self, arm_id: str):
        """初始化臂"""
        self.A[arm_id] = np.eye(self.n_features)
        self.b[arm_id] = np.zeros(self.n_features)
    
    def select_arm(self, context: np.ndarray, available_arms: List[str]) -> str:
        """
        基于上下文选择臂
        
        Args:
            context: 特征向量 (n_features,)
            available_arms: 可用臂的 ID 列表
        
        Returns:
            选择的臂 ID
        """
        best_arm = None
        best_ucb = -float('inf')
        
        for arm_id in available_arms:
            if arm_id not in self.A:
                self.initialize_arm(arm_id)
            
            # 计算 theta (最小二乘估计)
            A_inv = np.linalg.inv(self.A[arm_id])
            theta = A_inv @ self.b[arm_id]
            
            # 期望奖励
            expected_reward = theta @ context
            
            # 置信区间
            uncertainty = self.alpha * np.sqrt(context @ A_inv @ context)
            
            # UCB
            ucb = expected_reward + uncertainty
            
            if ucb > best_ucb:
                best_ucb = ucb
                best_arm = arm_id
        
        return best_arm
    
    def update(self, arm_id: str, context: np.ndarray, reward: float):
        """更新臂的参数"""
        if arm_id not in self.A:
            self.initialize_arm(arm_id)
        
        self.A[arm_id] += np.outer(context, context)
        self.b[arm_id] += reward * context


class ThompsonSampling:
    """汤普森采样 (贝叶斯方法)"""
    
    def __init__(self):
        # 每个臂的先验 (Beta 分布)
        self.alpha: Dict[str, float] = defaultdict(lambda: 1.0)
        self.beta: Dict[str, float] = defaultdict(lambda: 1.0)
    
    def select_arm(self, arm_ids: List[str]) -> str:
        """选择臂 - 从后验采样"""
        best_arm = None
        best_sample = -1
        
        for arm_id in arm_ids:
            # 从 Beta 分布采样
            sample = random.betavariate(self.alpha[arm_id], self.beta[arm_id])
            if sample > best_sample:
                best_sample = sample
                best_arm = arm_id
        
        return best_arm
    
    def update(self, arm_id: str, reward: float):
        """更新后验"""
        # reward 应该在 [0, 1] 之间
        normalized_reward = max(0, min(1, reward / 100))
        
        self.alpha[arm_id] += normalized_reward
        self.beta[arm_id] += (1 - normalized_reward)


class ReinforcementOptimizer:
    """
    V16.0 强化学习优化器
    
    功能：
    1. 话题选择优化 (MAB)
    2. 模型选择优化 (LinUCB)
    3. 模板选择优化 (Thompson Sampling)
    4. 生成参数优化 (贝叶斯优化)
    """
    
    _instance = None
    _lock = threading.Lock()
    
    def __new__(cls):
        with cls._lock:
            if cls._instance is None:
                cls._instance = super(ReinforcementOptimizer, cls).__new__(cls)
                cls._instance._initialized = False
        return cls._instance
    
    def __init__(self):
        if self._initialized:
            return
        
        self._initialized = True
        
        # 不同优化目标使用不同算法
        self.topic_mab = EpsilonGreedyMAB(epsilon=0.15)  # 话题选择
        self.model_linucb = LinUCB(n_features=10, alpha=1.0)  # 模型选择
        self.template_ts = ThompsonSampling()  # 模板选择
        
        # 性能历史
        self.performance_history: List[Dict] = []
        
        # 策略状态
        self.strategy_state = {
            "topic_weights": defaultdict(float),
            "model_weights": defaultdict(float),
            "template_weights": defaultdict(float),
            "hour_performance": defaultdict(list)
        }
        
        log.print_log("[V16.0] 🎓 Reinforcement Optimizer (强化学习优化器) 已初始化", "success")
    
    def initialize_strategies(self):
        """初始化策略臂"""
        # 初始化话题策略
        topic_strategies = [
            ("trend_following", "趋势跟随", {"strategy": "follow"}),
            ("contrarian", "反向观点", {"strategy": "contrarian"}),
            ("evergreen", "常青内容", {"strategy": "evergreen"}),
            ("deep_dive", "深度分析", {"strategy": "deep"}),
        ]
        
        for arm_id, name, config in topic_strategies:
            self.topic_mab.add_arm(Arm(id=arm_id, name=name, config=config))
        
        log.print_log(f"[V16.0] ✅ 已初始化 {len(topic_strategies)} 个话题策略", "info")
    
    def select_topic_strategy(self) -> Tuple[str, Dict]:
        """选择话题策略"""
        if not self.topic_mab.arms:
            self.initialize_strategies()
        
        arm = self.topic_mab.select_arm()
        return arm.id, arm.config
    
    def select_model(
        self, 
        context: Dict[str, Any],
        available_models: List[str]
    ) -> str:
        """
        基于上下文选择模型
        
        Args:
            context: 上下文特征
                - content_complexity: 内容复杂度 (0-10)
                - urgency: 紧急程度 (0-10)
                - quality_requirement: 质量要求 (0-10)
            available_models: 可用模型列表
        """
        # 构建特征向量
        features = np.array([
            context.get("content_complexity", 5) / 10,
            context.get("urgency", 5) / 10,
            context.get("quality_requirement", 5) / 10,
            context.get("budget_constraint", 5) / 10,
            random.random(),  # 随机特征增加多样性
        ])
        
        # 填充到 10 维
        features = np.pad(features, (0, 10 - len(features)), mode='constant')
        
        return self.model_linucb.select_arm(features, available_models)
    
    def select_template(
        self,
        available_templates: List[str]
    ) -> str:
        """选择模板"""
        if not available_templates:
            return "default"
        
        return self.template_ts.select_arm(available_templates)
    
    def record_outcome(
        self,
        decision_type: str,  # "topic", "model", "template"
        choice: str,
        context: Dict[str, Any],
        outcome: float  # 结果分数 (0-100)
    ):
        """
        记录决策结果
        
        Args:
            decision_type: 决策类型
            choice: 选择的策略/模型/模板
            context: 上下文
            outcome: 结果 (参与度、转化率等)
        """
        try:
            # 计算奖励 (归一化到 [-1, 1])
            reward = (outcome - 50) / 50
            
            # 更新对应的算法
            if decision_type == "topic":
                self.topic_mab.update(choice, reward)
                
            elif decision_type == "model":
                features = np.array([
                    context.get("content_complexity", 5) / 10,
                    context.get("urgency", 5) / 10,
                    context.get("quality_requirement", 5) / 10,
                    context.get("budget_constraint", 5) / 10,
                    random.random(),
                ])
                features = np.pad(features, (0, 10 - len(features)), mode='constant')
                self.model_linucb.update(choice, features, reward)
                
            elif decision_type == "template":
                self.template_ts.update(choice, outcome)
            
            # 记录历史
            self.performance_history.append({
                "timestamp": datetime.now().isoformat(),
                "type": decision_type,
                "choice": choice,
                "outcome": outcome,
                "reward": reward
            })
            
            # 限制历史大小
            if len(self.performance_history) > 10000:
                self.performance_history = self.performance_history[-5000:]
            
        except Exception as e:
            log.print_log(f"[V16.0] 记录结果失败: {e}", "warning")
    
    def get_strategy_performance(self, decision_type: Optional[str] = None) -> Dict:
        """获取策略性能报告"""
        report = {}
        
        if decision_type is None or decision_type == "topic":
            report["topic_strategies"] = {
                arm_id: {
                    "name": arm.name,
                    "pulls": arm.pulls,
                    "avg_reward": round(arm.average_reward, 3)
                }
                for arm_id, arm in self.topic_mab.arms.items()
            }
        
        if decision_type is None or decision_type == "model":
            # LinUCB 不直接存储历史，需要从 performance_history 计算
            model_stats = defaultdict(lambda: {"count": 0, "total_outcome": 0})
            for record in self.performance_history:
                if record["type"] == "model":
                    choice = record["choice"]
                    model_stats[choice]["count"] += 1
                    model_stats[choice]["total_outcome"] += record["outcome"]
            
            report["model_performance"] = {
                model: {
                    "uses": stats["count"],
                    "avg_outcome": round(stats["total_outcome"] / max(stats["count"], 1), 2)
                }
                for model, stats in model_stats.items()
            }
        
        if decision_type is None or decision_type == "template":
            report["template_performance"] = {
                template: {
                    "alpha": self.template_ts.alpha[template],
                    "beta": self.template_ts.beta[template],
                    "expected_conversion": round(
                        self.template_ts.alpha[template] / 
                        (self.template_ts.alpha[template] + self.template_ts.beta[template]), 
                        3
                    )
                }
                for template in set([r["choice"] for r in self.performance_history if r["type"] == "template"])
            }
        
        return report
    
    def recommend_optimal_hour(self, category: str = "general") -> int:
        """推荐最优发布时间 (0-23)"""
        # 从历史数据中学习最优时间
        hour_performance = defaultdict(list)
        
        for record in self.performance_history:
            if record["type"] == "timing":
                hour = record.get("hour", 12)
                hour_performance[hour].append(record["outcome"])
        
        if not hour_performance:
            # 默认返回晚高峰
            return 20
        
        # 计算每个小时的平均表现
        best_hour = max(
            hour_performance.keys(),
            key=lambda h: np.mean(hour_performance[h])
        )
        
        return best_hour
    
    def export_policy(self) -> Dict:
        """导出学习到的策略"""
        return {
            "topic_strategy": {
                arm_id: {
                    "name": arm.name,
                    "pulls": arm.pulls,
                    "total_reward": arm.rewards
                }
                for arm_id, arm in self.topic_mab.arms.items()
            },
            "performance_history_count": len(self.performance_history),
            "last_updated": datetime.now().isoformat()
        }
    
    def import_policy(self, policy: Dict):
        """导入策略"""
        try:
            for arm_id, data in policy.get("topic_strategy", {}).items():
                if arm_id in self.topic_mab.arms:
                    self.topic_mab.arms[arm_id].pulls = data.get("pulls", 0)
                    self.topic_mab.arms[arm_id].rewards = data.get("total_reward", 0)
            
            log.print_log("[V16.0] ✅ 策略已导入", "success")
        except Exception as e:
            log.print_log(f"[V16.0] 导入策略失败: {e}", "error")


# 全局实例
_reinforcement_optimizer = None


def get_reinforcement_optimizer() -> ReinforcementOptimizer:
    """获取强化学习优化器全局实例"""
    global _reinforcement_optimizer
    if _reinforcement_optimizer is None:
        _reinforcement_optimizer = ReinforcementOptimizer()
    return _reinforcement_optimizer
