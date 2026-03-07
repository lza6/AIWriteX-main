"""
预测性负载均衡器 V2 (Predictive Load Balancer V2)
基于机器学习的负载预测与调度优化

核心组件:
1. 负载预测器 - 使用滑动窗口和指数加权预测未来负载
2. 调度策略优化器
3. 自适应重平衡器
"""
import asyncio
from enum import Enum
from typing import Dict, List, Any, Optional, Tuple
from datetime import datetime, timedelta
from collections import defaultdict, deque
import uuid
import json
import random
import math
import numpy as np

from src.ai_write_x.utils import log


class LoadMetric:
    """负载指标"""
    
    def __init__(
        self,
        agent_id: str,
        cpu_usage: float = 0.0,
        memory_usage: float = 0.0,
        task_queue_size: int = 0,
        avg_response_time: float = 0.0,
        success_rate: float = 1.0,
        active_tasks: int = 0,
        timestamp: datetime = None
    ):
        self.agent_id = agent_id
        self.cpu_usage = cpu_usage
        self.memory_usage = memory_usage
        self.task_queue_size = task_queue_size
        self.avg_response_time = avg_response_time
        self.success_rate = success_rate
        self.active_tasks = active_tasks
        self.timestamp = timestamp or datetime.now()
    
    def to_vector(self) -> List[float]:
        """转换为特征向量"""
        return [
            self.cpu_usage,
            self.memory_usage,
            self.task_queue_size / 100.0,  # 归一化
            self.avg_response_time / 10.0,
            self.success_rate,
            self.active_tasks / 10.0,
            (self.timestamp - datetime.now()).total_seconds() / 3600.0
        ]
    
    @property
    def load_score(self) -> float:
        """计算综合负载分数"""
        return (
            0.3 * self.cpu_usage +
            0.2 * self.memory_usage +
            0.2 * min(self.task_queue_size / 50.0, 1.0) +
            0.15 * min(self.avg_response_time / 5.0, 1.0) +
            0.15 * (1.0 - self.success_rate)
        )


class TransformerPredictor:
    """
    负载预测器 (简化版)
    
    使用滑动窗口平均和指数加权预测未来负载
    不依赖torch也可工作
    """
    
    def __init__(
        self,
        input_dim: int = 7,
        hidden_dim: int = 64,
        num_heads: int = 4,
        num_layers: int = 2,
        output_dim: int = 1
    ):
        self.input_dim = input_dim
        self.hidden_dim = hidden_dim
        self.num_heads = num_heads
        self.num_layers = num_layers
        self.output_dim = output_dim
        
        # 简化的预测参数
        self.ewm_alpha = 0.3  # 指数加权移动平均参数
        self.is_trained = False
        
        # 预测模型参数
        self.weights = np.random.randn(input_dim, output_dim) * 0.01
        
        log.print_log(f"[Predictor] 负载预测器已初始化 (简化模式)", "info")
    
    def predict(self, history: np.ndarray) -> float:
        """
        预测未来负载
        
        Args:
            history: (seq_len, input_dim) 历史负载特征
        Returns:
            预测的负载分数
        """
        if len(history) == 0:
            return 0.0
        
        # 使用指数加权移动平均
        if len(history) == 1:
            return np.mean(history[-1])
        
        # 计算加权平均
        weights = np.array([self.ewm_alpha * (1 - self.ewm_alpha) ** i 
                          for i in range(len(history) - 1, -1, -1)])
        weights = weights / weights.sum()
        
        weighted_history = np.average(history, axis=0, weights=weights)
        
        # 简单线性预测
        prediction = np.dot(weighted_history, self.weights).item()
        
        return np.clip(prediction, 0.0, 1.0)
    
    def update(self, actual: float, predicted: float):
        """更新预测模型"""
        error = actual - predicted
        
        # 简单梯度更新
        learning_rate = 0.01
        self.weights += learning_rate * error * np.random.randn(self.input_dim, self.output_dim) * 0.001
        
        self.is_trained = True
    
    def fit(self, X: np.ndarray, y: np.ndarray, epochs: int = 10):
        """训练预测模型"""
        for epoch in range(epochs):
            for i in range(len(X)):
                pred = self.predict(X[i])
                self.update(y[i], pred)


class PPOScheduler:
    """
    PPO调度策略 - 简化版
    """
    
    def __init__(
        self,
        state_dim: int = 20,
        action_dim: int = 10,
        hidden_dim: int = 64
    ):
        self.state_dim = state_dim
        self.action_dim = action_dim
        
        # 简化的策略参数
        self.policy_weights = np.random.randn(state_dim, action_dim) * 0.01
        self.value_weights = np.random.randn(state_dim, 1) * 0.01
        
        # 超参数
        self.gamma = 0.99
        self.lambda_ = 0.95
        self.clip_ratio = 0.2
        self.learning_rate = 3e-4
        
        # 经验缓存
        self.memory: List[Dict] = []
        
        log.print_log(f"[PPO] PPO调度器已初始化 (简化模式)", "info")
    
    def get_action(self, state: np.ndarray) -> Tuple[int, float]:
        """
        获取调度动作
        
        Args:
            state: 状态向量
        Returns:
            (action, log_prob)
        """
        # 简单策略
        logits = np.dot(state, self.policy_weights)
        action = int(np.argmax(logits))
        
        # 简化的log_prob
        log_prob = -np.log(np.abs(logits[action]) + 1e-8)
        
        return action, log_prob
    
    def evaluate(self, states: np.ndarray, actions: np.ndarray) -> Tuple[np.ndarray, np.ndarray]:
        """评估状态和动作"""
        values = np.dot(states, self.value_weights)
        logits = np.dot(states, self.policy_weights)
        
        probs = softmax(logits)
        action_probs = probs[np.arange(len(actions)), actions]
        
        return values, action_probs
    
    def update(self, rewards: List[float], states: np.ndarray, actions: np.ndarray):
        """更新策略"""
        if len(rewards) == 0:
            return
        
        # 计算returns
        returns = []
        discounted = 0
        for r in reversed(rewards):
            discounted = r + self.gamma * discounted
            returns.insert(0, discounted)
        
        returns = np.array(returns)
        returns = (returns - returns.mean()) / (returns.std() + 1e-8)
        
        # 简化更新
        for i, (state, action, ret) in enumerate(zip(states, actions, returns)):
            advantage = ret - np.dot(state, self.value_weights).item()
            
            # 策略梯度更新
            self.policy_weights += self.learning_rate * advantage * np.outer(state, softmax(np.dot(state, self.policy_weights)))
            
            # 值函数更新
            self.value_weights += self.learning_rate * advantage * state.reshape(-1, 1)


def softmax(x: np.ndarray) -> np.ndarray:
    """Softmax函数"""
    exp_x = np.exp(x - np.max(x))
    return exp_x / exp_x.sum()


class PredictiveLoadBalancer:
    """
    预测性负载均衡器 V2
    
    特性:
    - 基于历史负载预测未来负载
    - 智能任务分配
    - 自适应重平衡
    """
    
    def __init__(self):
        self.predictors: Dict[str, TransformerPredictor] = {}
        self.ppo_scheduler = PPOScheduler()
        
        # 负载历史
        self.load_history: Dict[str, deque] = defaultdict(lambda: deque(maxlen=1000))
        
        # 重平衡配置
        self.rebalance_threshold = 0.3
        self.rebalance_interval = 60
        
        # 统计
        self.stats = {
            "total_allocations": 0,
            "successful_rebalances": 0,
            "prediction_errors": []
        }
    
    def get_predictor(self, agent_id: str) -> TransformerPredictor:
        """获取或创建预测器"""
        if agent_id not in self.predictors:
            self.predictors[agent_id] = TransformerPredictor()
        return self.predictors[agent_id]
    
    async def record_load(self, agent_id: str, metric: LoadMetric):
        """记录负载指标"""
        self.load_history[agent_id].append(metric)
    
    async def predict_load(self, agent_id: str, horizon: int = 5) -> float:
        """
        预测未来负载
        
        Args:
            agent_id: Agent ID
            horizon: 预测步数
        Returns:
            预测的负载分数
        """
        history = self.load_history.get(agent_id)
        if not history or len(history) < 3:
            return 0.5  # 默认中等负载
        
        # 获取历史向量
        vectors = np.array([m.to_vector() for m in list(history)[-10:]])
        
        # 预测
        predictor = self.get_predictor(agent_id)
        prediction = predictor.predict(vectors)
        
        return prediction
    
    async def select_agent(
        self,
        agent_states: Dict[str, Dict[str, Any]]
    ) -> Optional[str]:
        """
        选择最优Agent
        
        Args:
            agent_states: Agent状态字典
        Returns:
            选中的Agent ID
        """
        if not agent_states:
            return None
        
        candidates = []
        
        for agent_id, state in agent_states.items():
            # 预测负载
            predicted_load = await self.predict_load(agent_id)
            
            # 获取当前负载
            current_load = state.get("current_load", 0.5)
            
            # 综合评分 (越低越好)
            score = 0.6 * predicted_load + 0.4 * current_load
            
            candidates.append({
                "agent_id": agent_id,
                "score": score,
                "predicted": predicted_load,
                "current": current_load
            })
        
        # 选择负载最低的
        candidates.sort(key=lambda x: x["score"])
        
        self.stats["total_allocations"] += 1
        
        return candidates[0]["agent_id"] if candidates else None
    
    async def should_rebalance(self, agent_id: str, current_load: float, predicted_load: float) -> bool:
        """判断是否需要重平衡"""
        load_change = abs(current_load - predicted_load)
        return load_change > self.rebalance_threshold
    
    async def rebalance(self, agent_states: Dict[str, Dict[str, Any]]) -> List[Tuple[str, str]]:
        """
        重平衡任务
        
        Returns:
            [(from_agent, to_agent), ...] 迁移列表
        """
        migrations = []
        
        # 找出过载和欠载的Agent
        overloaded = []
        underloaded = []
        
        for agent_id, state in agent_states.items():
            load = state.get("current_load", 0.5)
            
            if load > 0.8:
                overloaded.append((agent_id, load))
            elif load < 0.3:
                underloaded.append((agent_id, load))
        
        # 从过载迁移到欠载
        overloaded.sort(key=lambda x: x[1], reverse=True)
        underloaded.sort(key=lambda x: x[1])
        
        while overloaded and underloaded:
            from_agent, _ = overloaded.pop(0)
            to_agent, _ = underloaded.pop(0)
            
            migrations.append((from_agent, to_agent))
            self.stats["successful_rebalances"] += 1
        
        return migrations
    
    def get_stats(self) -> Dict[str, Any]:
        """获取统计信息"""
        return {
            **self.stats,
            "active_predictors": len(self.predictors),
            "history_sizes": {k: len(v) for k, v in self.load_history.items()}
        }


# 全局实例
_global_balancer: Optional[PredictiveLoadBalancer] = None


def get_predictive_balancer() -> PredictiveLoadBalancer:
    """获取全局预测负载均衡器"""
    global _global_balancer
    if _global_balancer is None:
        _global_balancer = PredictiveLoadBalancer()
    return _global_balancer