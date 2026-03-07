# -*- coding: UTF-8 -*-
"""
V16.0 - Autonomous Scheduler (自治调度系统)

基于预测引擎和历史效果数据，自动决定：
1. 何时生成内容 (最优发布时间预测)
2. 生成什么内容 (话题选择优化)
3. 使用什么策略 (模板、风格选择)

使用强化学习持续优化调度策略。
"""

import json
import random
import asyncio
import numpy as np
from datetime import datetime, timedelta
from typing import Dict, List, Optional, Tuple, Any
from dataclasses import dataclass, field
from enum import Enum
import threading
from collections import defaultdict

from src.ai_write_x.utils import log
from src.ai_write_x.database.db_manager import db_manager
from src.ai_write_x.config.config import Config
from src.ai_write_x.core.predictive_engine import get_predictive_engine, TrendPrediction


class ContentStrategy(Enum):
    """内容策略类型"""
    TREND_FOLLOWING = "trend_following"  # 趋势跟随
    CONTRARIAN = "contrarian"  # 反向观点
    EVERGREEN = "evergreen"  # 常青内容
    TIMELY = "timely"  # 时效性内容
    DEEP_DIVE = "deep_dive"  # 深度分析


@dataclass
class SchedulingDecision:
    """调度决策"""
    topic: str
    scheduled_time: datetime
    strategy: ContentStrategy
    confidence: float
    expected_score: float
    reasoning: str
    metadata: Dict[str, Any] = field(default_factory=dict)


@dataclass
class TimeSlot:
    """时间槽"""
    hour: int
    day_of_week: int
    avg_engagement: float
    competition_level: float  # 竞争程度
    optimal_categories: List[str]


class EngagementPredictor:
    """参与度预测器 - 预测特定时间发布的效果"""
    
    def __init__(self):
        # 24小时 x 7天的参与度矩阵
        self.hourly_pattern = self._init_hourly_pattern()
        self.category_preferences = defaultdict(lambda: defaultdict(float))
        
    def _init_hourly_pattern(self) -> Dict[int, Dict[int, float]]:
        """初始化小时模式 (基于一般社交媒体数据)"""
        pattern = {}
        for day in range(7):  # 0=Monday
            pattern[day] = {}
            for hour in range(24):
                # 工作日 vs 周末模式
                if day < 5:  # 工作日
                    if 7 <= hour <= 9:  # 早高峰
                        base = 0.8
                    elif 12 <= hour <= 14:  # 午休
                        base = 0.9
                    elif 18 <= hour <= 22:  # 晚高峰
                        base = 1.0
                    elif 0 <= hour <= 6:  # 深夜
                        base = 0.2
                    else:
                        base = 0.5
                else:  # 周末
                    if 9 <= hour <= 11:  # 上午
                        base = 0.7
                    elif 14 <= hour <= 17:  # 下午
                        base = 0.8
                    elif 20 <= hour <= 23:  # 晚上
                        base = 0.9
                    else:
                        base = 0.4
                
                pattern[day][hour] = base
        return pattern
    
    def predict_engagement(
        self, 
        publish_time: datetime, 
        category: str,
        historical_avg: float = 50.0
    ) -> float:
        """预测参与度"""
        day = publish_time.weekday()
        hour = publish_time.hour
        
        # 基础时间模式
        base_score = self.hourly_pattern.get(day, {}).get(hour, 0.5)
        
        # 分类偏好
        category_boost = self.category_preferences[category].get(hour, 1.0)
        
        # 综合预测
        predicted = historical_avg * base_score * category_boost
        return min(predicted, 100.0)
    
    def update_pattern(self, publish_time: datetime, actual_engagement: float, category: str):
        """根据实际结果更新模式 (在线学习)"""
        day = publish_time.weekday()
        hour = publish_time.hour
        
        # 简单的指数移动平均更新
        alpha = 0.1  # 学习率
        current = self.hourly_pattern[day][hour]
        self.hourly_pattern[day][hour] = current * (1 - alpha) + (actual_engagement / 100) * alpha


class ReinforcementScheduler:
    """强化学习调度器 - 持续优化调度策略"""
    
    def __init__(self, learning_rate: float = 0.1, epsilon: float = 0.2):
        self.lr = learning_rate
        self.epsilon = epsilon  # 探索率
        
        # 策略价值表: (state, action) -> value
        self.q_table: Dict[Tuple, Dict[str, float]] = defaultdict(lambda: defaultdict(float))
        
        # 状态历史
        self.state_history: List[Tuple] = []
        self.action_history: List[str] = []
        
    def get_state(self, context: Dict) -> Tuple:
        """将上下文转换为状态"""
        # 简化状态表示
        hour_bucket = context.get("hour", 0) // 4  # 6个时段
        trend_score_bucket = int(context.get("trend_score", 50) // 20)  # 5档
        category = context.get("category", "general")
        
        return (hour_bucket, trend_score_bucket, category)
    
    def select_action(self, state: Tuple, available_actions: List[str]) -> str:
        """选择动作 (epsilon-greedy)"""
        if not available_actions:
            return "default"
        
        # 探索
        if random.random() < self.epsilon:
            return random.choice(available_actions)
        
        # 利用
        q_values = self.q_table[state]
        if not q_values:
            return random.choice(available_actions)
        
        # 选择 Q 值最高的动作
        best_action = max(available_actions, key=lambda a: q_values.get(a, 0))
        return best_action
    
    def update(self, state: Tuple, action: str, reward: float, next_state: Tuple):
        """更新 Q 值"""
        # Q-learning 更新规则
        current_q = self.q_table[state][action]
        
        # 下一状态的最大 Q 值
        next_q_values = self.q_table[next_state]
        max_next_q = max(next_q_values.values()) if next_q_values else 0
        
        # 更新
        new_q = current_q + self.lr * (reward + 0.9 * max_next_q - current_q)
        self.q_table[state][action] = new_q


class AutonomousScheduler:
    """
    V16.0 自治调度系统
    
    功能：
    1. 基于预测趋势自动安排内容生成
    2. 优化发布时间以最大化参与度
    3. 使用强化学习持续改进调度策略
    4. 自适应调整生成频率和主题
    """
    
    _instance = None
    _lock = threading.Lock()
    
    def __new__(cls):
        with cls._lock:
            if cls._instance is None:
                cls._instance = super(AutonomousScheduler, cls).__new__(cls)
                cls._instance._initialized = False
        return cls._instance
    
    def __init__(self):
        if self._initialized:
            return
            
        self._initialized = True
        self.engagement_predictor = EngagementPredictor()
        self.rl_scheduler = ReinforcementScheduler()
        self.predictive_engine = get_predictive_engine()
        
        # 调度队列
        self.scheduled_tasks: List[SchedulingDecision] = []
        self.max_queue_size = 10
        
        # 运行状态
        self.is_running = False
        self.scheduler_thread = None
        
        log.print_log("[V16.0] 🎯 Autonomous Scheduler (自治调度系统) 已初始化", "success")
    
    def start(self):
        """启动自治调度"""
        if self.is_running:
            return
        
        self.is_running = True
        self.scheduler_thread = threading.Thread(target=self._scheduling_loop, daemon=True)
        self.scheduler_thread.start()
        log.print_log("[V16.0] ▶️ 自治调度系统已启动", "success")
    
    def stop(self):
        """停止自治调度"""
        self.is_running = False
        log.print_log("[V16.0] ⏹️ 自治调度系统已停止", "info")
    
    def _scheduling_loop(self):
        """调度主循环"""
        import time
        
        while self.is_running:
            try:
                # 每小时检查一次
                if datetime.now().minute == 0:
                    asyncio.run(self._make_scheduling_decisions())
                
                # 检查并执行到期的调度任务
                self._execute_due_tasks()
                
            except Exception as e:
                log.print_log(f"[V16.0] 调度循环异常: {e}", "error")
            
            time.sleep(60)  # 每分钟检查一次
    
    async def _make_scheduling_decisions(self):
        """制定调度决策"""
        try:
            # 1. 获取预测趋势
            predictions = await self.predictive_engine.predict_trends(
                horizon_days=3,
                top_n=20
            )
            
            if not predictions:
                return
            
            # 2. 为每个预测制定调度决策
            new_decisions = []
            for pred in predictions:
                decision = self._create_scheduling_decision(pred)
                if decision:
                    new_decisions.append(decision)
            
            # 3. 排序并选择最优决策
            new_decisions.sort(key=lambda x: x.expected_score * x.confidence, reverse=True)
            
            # 4. 更新调度队列
            for decision in new_decisions[:self.max_queue_size]:
                if not any(d.topic == decision.topic for d in self.scheduled_tasks):
                    self.scheduled_tasks.append(decision)
                    log.print_log(
                        f"[V16.0] 📅 新增调度任务: {decision.topic[:30]}... "
                        f"时间: {decision.scheduled_time.strftime('%m-%d %H:%M')} "
                        f"策略: {decision.strategy.value}",
                        "info"
                    )
            
            # 限制队列大小
            self.scheduled_tasks = self.scheduled_tasks[:self.max_queue_size]
            
        except Exception as e:
            log.print_log(f"[V16.0] 制定调度决策失败: {e}", "error")
    
    def _create_scheduling_decision(self, prediction: TrendPrediction) -> Optional[SchedulingDecision]:
        """为预测创建调度决策"""
        try:
            # 1. 确定最优发布时间
            optimal_time = self._find_optimal_publish_time(prediction)
            
            # 2. 选择内容策略
            strategy = self._select_content_strategy(prediction)
            
            # 3. 计算预期得分
            expected_score = self.engagement_predictor.predict_engagement(
                optimal_time,
                prediction.category,
                prediction.predicted_score
            )
            
            # 4. 生成决策理由
            reasoning = self._generate_reasoning(prediction, optimal_time, strategy)
            
            return SchedulingDecision(
                topic=prediction.topic,
                scheduled_time=optimal_time,
                strategy=strategy,
                confidence=prediction.confidence,
                expected_score=expected_score,
                reasoning=reasoning,
                metadata={
                    "predicted_score": prediction.predicted_score,
                    "keywords": prediction.keywords,
                    "data_sources": prediction.data_sources
                }
            )
            
        except Exception as e:
            log.print_log(f"[V16.0] 创建调度决策失败: {e}", "warning")
            return None
    
    def _find_optimal_publish_time(self, prediction: TrendPrediction) -> datetime:
        """找到最优发布时间"""
        now = datetime.now()
        base_time = max(now, prediction.predicted_peak_time - timedelta(hours=2))
        
        best_time = base_time
        best_score = 0
        
        # 在未来 48 小时内搜索最优时段
        for offset_hours in range(48):
            candidate_time = base_time + timedelta(hours=offset_hours)
            
            # 预测参与度
            score = self.engagement_predictor.predict_engagement(
                candidate_time,
                prediction.category,
                prediction.predicted_score
            )
            
            if score > best_score:
                best_score = score
                best_time = candidate_time
        
        return best_time
    
    def _select_content_strategy(self, prediction: TrendPrediction) -> ContentStrategy:
        """选择内容策略"""
        # 基于预测特征选择策略
        if prediction.predicted_score > 80:
            return ContentStrategy.TIMELY  # 高热度 -> 时效性内容
        elif prediction.confidence > 0.8:
            return ContentStrategy.DEEP_DIVE  # 高置信度 -> 深度分析
        elif "争议" in prediction.topic or "问题" in prediction.topic:
            return ContentStrategy.CONTRARIAN  # 争议话题 -> 反向观点
        else:
            return ContentStrategy.TREND_FOLLOWING  # 默认 -> 趋势跟随
    
    def _generate_reasoning(
        self, 
        prediction: TrendPrediction, 
        optimal_time: datetime,
        strategy: ContentStrategy
    ) -> str:
        """生成决策理由"""
        reasons = [
            f"预测热度: {prediction.predicted_score:.1f}",
            f"置信度: {prediction.confidence:.1%}",
            f"最优发布时间: {optimal_time.strftime('%m-%d %H:%M')}",
            f"策略: {strategy.value}",
            f"数据来源: {', '.join(prediction.data_sources[:2])}"
        ]
        return "; ".join(reasons)
    
    def _execute_due_tasks(self):
        """执行到期的调度任务"""
        now = datetime.now()
        due_tasks = [t for t in self.scheduled_tasks if t.scheduled_time <= now]
        
        for task in due_tasks:
            try:
                self._trigger_content_generation(task)
                self.scheduled_tasks.remove(task)
            except Exception as e:
                log.print_log(f"[V16.0] 执行调度任务失败: {e}", "error")
    
    def _trigger_content_generation(self, decision: SchedulingDecision):
        """触发内容生成"""
        log.print_log(
            f"[V16.0] 🚀 触发自治生成: {decision.topic[:40]}... "
            f"策略: {decision.strategy.value}",
            "success"
        )
        
        # 这里应该调用实际的内容生成流程
        # 简化处理：记录到数据库，等待调度器执行
        try:
            db_manager.add_scheduled_task(
                topic=decision.topic,
                platform="autonomous",
                scheduled_time=decision.scheduled_time,
                metadata={
                    "strategy": decision.strategy.value,
                    "expected_score": decision.expected_score,
                    "confidence": decision.confidence,
                    "reasoning": decision.reasoning
                }
            )
        except Exception as e:
            log.print_log(f"[V16.0] 添加任务到数据库失败: {e}", "warning")
    
    def get_scheduled_tasks(self) -> List[Dict]:
        """获取已调度的任务"""
        return [
            {
                "topic": d.topic,
                "scheduled_time": d.scheduled_time.isoformat(),
                "strategy": d.strategy.value,
                "confidence": d.confidence,
                "expected_score": d.expected_score,
                "reasoning": d.reasoning
            }
            for d in self.scheduled_tasks
        ]
    
    def feedback(self, topic: str, actual_engagement: float, publish_time: datetime):
        """接收反馈以改进策略"""
        # 更新参与度预测器
        self.engagement_predictor.update_pattern(publish_time, actual_engagement, "general")
        
        # 找到对应的调度决策
        for decision in self.scheduled_tasks:
            if decision.topic == topic:
                # 计算奖励 (实际 vs 预期)
                reward = actual_engagement - decision.expected_score
                
                # 更新强化学习器
                state = self.rl_scheduler.get_state({
                    "hour": publish_time.hour,
                    "trend_score": decision.expected_score,
                    "category": "general"
                })
                next_state = state  # 简化
                
                self.rl_scheduler.update(state, decision.strategy.value, reward, next_state)
                
                log.print_log(
                    f"[V16.0] 📊 调度反馈: {topic[:30]}... "
                    f"预期: {decision.expected_score:.1f} "
                    f"实际: {actual_engagement:.1f} "
                    f"奖励: {reward:+.1f}",
                    "info"
                )
                break


# 全局实例
_autonomous_scheduler = None


def get_autonomous_scheduler() -> AutonomousScheduler:
    """获取自治调度器全局实例"""
    global _autonomous_scheduler
    if _autonomous_scheduler is None:
        _autonomous_scheduler = AutonomousScheduler()
    return _autonomous_scheduler
