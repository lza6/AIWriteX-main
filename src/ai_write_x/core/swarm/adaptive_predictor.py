"""
自适应预测器 V3 (Adaptive Predictor V3)

解决痛点:
1. 预测器过于简化 → 实现多模型集成 + 在线学习
2. 缺乏在线学习 → 增量学习 + 自适应权重调整
3. 无法适应环境变化 → 概念漂移检测 + 模型自适应

核心特性:
- 集成多个预测模型 (EWMA, ARIMA-like, 自适应线性回归)
- 在线增量学习，无需重新训练
- 概念漂移检测，自动调整模型权重
- 自适应学习率，根据预测误差动态调整
"""
import asyncio
from typing import Dict, List, Any, Optional, Tuple, Deque
from datetime import datetime, timedelta
from collections import deque, defaultdict
from dataclasses import dataclass, field
import numpy as np
from enum import Enum
import json

from src.ai_write_x.utils import log


class DriftStatus(Enum):
    """概念漂移状态"""
    STABLE = "stable"           # 稳定状态
    WARNING = "warning"         # 警告状态
    DRIFTING = "drifting"       # 正在漂移
    ADAPTING = "adapting"       # 自适应中


@dataclass
class PredictionResult:
    """预测结果"""
    value: float
    confidence: float          # 置信度 0-1
    model_weights: Dict[str, float]  # 各模型权重
    drift_status: DriftStatus
    adaptive_lr: float         # 当前学习率
    feature_importance: Dict[str, float]


@dataclass
class OnlineLearningState:
    """在线学习状态"""
    sample_count: int = 0
    error_history: deque = field(default_factory=lambda: deque(maxlen=100))
    recent_errors: deque = field(default_factory=lambda: deque(maxlen=20))
    learning_rate: float = 0.01
    model_weights: Dict[str, float] = field(default_factory=dict)
    drift_detector: Any = None


class ConceptDriftDetector:
    """
    概念漂移检测器 (ADWIN-like算法简化版)
    检测数据分布的变化，触发模型自适应
    """
    
    def __init__(self, delta: float = 0.002):
        self.delta = delta  # 置信度参数
        self.window_size = 30  # 滑动窗口大小
        self.error_rates: deque = deque(maxlen=self.window_size * 2)
        self.change_detected = False
        
    def add_element(self, error: float):
        """添加新的预测误差"""
        self.error_rates.append(error)
        self.change_detected = False
        
        if len(self.error_rates) >= self.window_size:
            self._check_drift()
    
    def _check_drift(self):
        """检测漂移"""
        n = len(self.error_rates)
        if n < self.window_size:
            return
        
        # 将窗口分成两半，比较均值差异
        mid = n // 2
        window1 = list(self.error_rates)[:mid]
        window2 = list(self.error_rates)[mid:]
        
        mean1 = np.mean(window1)
        mean2 = np.mean(window2)
        std1 = np.std(window1) + 1e-8
        std2 = np.std(window2) + 1e-8
        
        # 计算差异统计量
        m = 1.0 / (1.0 / len(window1) + 1.0 / len(window2))
        epsilon = np.sqrt(2.0 / m * np.log(2.0 / self.delta))
        
        if abs(mean1 - mean2) > epsilon:
            self.change_detected = True
            log.print_log(f"[DriftDetector] 概念漂移检测: |{mean1:.4f} - {mean2:.4f}| > {epsilon:.4f}", "warning")
    
    def get_status(self) -> DriftStatus:
        """获取当前漂移状态"""
        if self.change_detected:
            return DriftStatus.DRIFTING
        
        if len(self.error_rates) < self.window_size:
            return DriftStatus.STABLE
        
        # 计算误差趋势
        recent = list(self.error_rates)[-10:]
        if len(recent) >= 10:
            trend = np.polyfit(range(10), recent, 1)[0]
            if trend > 0.01:
                return DriftStatus.WARNING
        
        return DriftStatus.STABLE
    
    def reset(self):
        """重置检测器"""
        self.error_rates.clear()
        self.change_detected = False


class EWMAModel:
    """指数加权移动平均模型 (基线模型)"""
    
    def __init__(self, alpha: float = 0.3):
        self.alpha = alpha
        self.ewm_value: Optional[float] = None
        
    def update(self, value: float):
        """更新模型"""
        if self.ewm_value is None:
            self.ewm_value = value
        else:
            self.ewm_value = self.alpha * value + (1 - self.alpha) * self.ewm_value
    
    def predict(self, steps: int = 1) -> float:
        """预测"""
        return self.ewm_value if self.ewm_value is not None else 0.5


class AdaptiveLinearRegression:
    """
    自适应线性回归模型
    使用增量梯度下降更新权重
    """
    
    def __init__(self, n_features: int, lr: float = 0.01):
        self.n_features = n_features
        self.weights = np.random.randn(n_features) * 0.1
        self.bias = 0.0
        self.lr = lr
        self.momentum = np.zeros(n_features)
        self.beta = 0.9  # 动量系数
        
    def predict(self, features: np.ndarray) -> float:
        """预测"""
        return np.clip(np.dot(features, self.weights) + self.bias, 0.0, 1.0)
    
    def update(self, features: np.ndarray, actual: float, adaptive_lr: Optional[float] = None):
        """增量更新"""
        lr = adaptive_lr if adaptive_lr is not None else self.lr
        
        pred = self.predict(features)
        error = actual - pred
        
        # 梯度计算
        grad_w = -2 * error * features
        grad_b = -2 * error
        
        # 动量更新
        self.momentum = self.beta * self.momentum + (1 - self.beta) * grad_w
        
        # 参数更新
        self.weights -= lr * self.momentum
        self.bias -= lr * grad_b
        
        return abs(error)


class TrendSeasonalityModel:
    """
    趋势-季节性模型 (简化版Holt-Winters)
    捕捉长期趋势和周期性模式
    """
    
    def __init__(self, alpha: float = 0.3, beta: float = 0.1, gamma: float = 0.1, season_period: int = 24):
        self.alpha = alpha  # 水平平滑系数
        self.beta = beta    # 趋势平滑系数
        self.gamma = gamma  # 季节性平滑系数
        self.season_period = season_period
        
        self.level: Optional[float] = None
        self.trend: Optional[float] = None
        self.seasonals: deque = deque(maxlen=season_period)
        
    def update(self, value: float):
        """更新模型"""
        if self.level is None:
            self.level = value
            self.trend = 0.0
            self.seasonals.append(0.0)
            return
        
        # 获取季节性分量
        season_idx = len(self.seasonals) % self.season_period
        seasonal = self.seasonals[season_idx] if season_idx < len(self.seasonals) else 0.0
        
        # 更新水平
        last_level = self.level
        self.level = self.alpha * (value - seasonal) + (1 - self.alpha) * (self.level + self.trend)
        
        # 更新趋势
        self.trend = self.beta * (self.level - last_level) + (1 - self.beta) * self.trend
        
        # 更新季节性
        new_seasonal = self.gamma * (value - self.level) + (1 - self.gamma) * seasonal
        self.seasonals.append(new_seasonal)
    
    def predict(self, steps: int = 1) -> float:
        """预测"""
        if self.level is None:
            return 0.5
        
        season_idx = (len(self.seasonals) + steps - 1) % self.season_period
        seasonal = self.seasonals[season_idx] if season_idx < len(self.seasonals) else 0.0
        
        return np.clip(self.level + steps * self.trend + seasonal, 0.0, 1.0)


class AdaptivePredictor:
    """
    自适应预测器 V3
    
    集成多个模型，实现在线学习和自适应
    """
    
    MODEL_NAMES = ["ewma", "adaptive_lr", "trend_seasonal"]
    
    def __init__(
        self,
        n_features: int = 7,
        initial_lr: float = 0.01,
        adaptivity_factor: float = 0.5
    ):
        self.n_features = n_features
        self.initial_lr = initial_lr
        self.adaptivity_factor = adaptivity_factor
        
        # 初始化多个模型
        self.models = {
            "ewma": EWMAModel(alpha=0.3),
            "adaptive_lr": AdaptiveLinearRegression(n_features, lr=initial_lr),
            "trend_seasonal": TrendSeasonalityModel(alpha=0.3, beta=0.1, season_period=24)
        }
        
        # 模型权重 (动态调整)
        self.model_weights = {name: 1.0 / len(self.MODEL_NAMES) for name in self.MODEL_NAMES}
        
        # 在线学习状态
        self.learning_state = OnlineLearningState(
            learning_rate=initial_lr,
            model_weights=self.model_weights.copy()
        )
        
        # 概念漂移检测器
        self.drift_detectors = {
            name: ConceptDriftDetector() for name in self.MODEL_NAMES
        }
        
        # 历史数据
        self.feature_history: deque = deque(maxlen=100)
        self.target_history: deque = deque(maxlen=100)
        
        # 特征重要性
        self.feature_importance = {f"f{i}": 1.0 / n_features for i in range(n_features)}
        
        log.print_log(f"[AdaptivePredictor] 自适应预测器 V3 已初始化 (模型: {self.MODEL_NAMES})", "success")
    
    def predict(self, features: Optional[np.ndarray] = None, history: Optional[Deque] = None) -> PredictionResult:
        """
        进行预测
        
        Args:
            features: 当前特征向量
            history: 历史数据队列
        Returns:
            PredictionResult 包含预测值和元数据
        """
        predictions = {}
        
        # 1. EWMA 预测
        predictions["ewma"] = self.models["ewma"].predict()
        
        # 2. 自适应线性回归预测
        if features is not None:
            predictions["adaptive_lr"] = self.models["adaptive_lr"].predict(features)
        else:
            predictions["adaptive_lr"] = predictions["ewma"]
        
        # 3. 趋势-季节性预测
        predictions["trend_seasonal"] = self.models["trend_seasonal"].predict()
        
        # 加权集成预测
        weighted_pred = sum(
            self.model_weights[name] * pred 
            for name, pred in predictions.items()
        )
        
        # 计算置信度 (基于模型一致性)
        pred_std = np.std(list(predictions.values()))
        confidence = np.exp(-pred_std * 5)  # 标准差越小，置信度越高
        
        # 检查漂移状态
        drift_status = self._get_overall_drift_status()
        
        # 计算自适应学习率
        adaptive_lr = self._compute_adaptive_lr()
        
        return PredictionResult(
            value=np.clip(weighted_pred, 0.0, 1.0),
            confidence=confidence,
            model_weights=self.model_weights.copy(),
            drift_status=drift_status,
            adaptive_lr=adaptive_lr,
            feature_importance=self.feature_importance.copy()
        )
    
    def update(self, features: np.ndarray, actual: float):
        """
        在线更新所有模型
        
        Args:
            features: 特征向量
            actual: 实际值
        """
        self.feature_history.append(features)
        self.target_history.append(actual)
        self.learning_state.sample_count += 1
        
        # 1. 更新 EWMA
        self.models["ewma"].update(actual)
        ewma_pred = self.models["ewma"].predict()
        ewma_error = abs(actual - ewma_pred)
        self.drift_detectors["ewma"].add_element(ewma_error)
        
        # 2. 更新自适应线性回归
        adaptive_lr = self._compute_adaptive_lr()
        lr_error = self.models["adaptive_lr"].update(features, actual, adaptive_lr)
        self.drift_detectors["adaptive_lr"].add_element(lr_error)
        
        # 3. 更新趋势-季节性模型
        self.models["trend_seasonal"].update(actual)
        ts_pred = self.models["trend_seasonal"].predict()
        ts_error = abs(actual - ts_pred)
        self.drift_detectors["trend_seasonal"].add_element(ts_error)
        
        # 4. 更新学习状态
        self.learning_state.error_history.append(ewma_error)
        self.learning_state.recent_errors.append(ewma_error)
        
        # 5. 动态调整模型权重 (基于最近表现)
        self._update_model_weights()
        
        # 6. 更新特征重要性
        self._update_feature_importance(features, actual)
        
        # 7. 检查概念漂移并自适应
        self._adapt_to_drift()
    
    def _compute_adaptive_lr(self) -> float:
        """计算自适应学习率"""
        if len(self.learning_state.recent_errors) < 10:
            return self.initial_lr
        
        # 基于误差趋势调整学习率
        recent_mean = np.mean(list(self.learning_state.recent_errors)[-10:])
        
        if len(self.learning_state.error_history) >= 20:
            older_mean = np.mean(list(self.learning_state.error_history)[-20:-10])
            
            # 误差增加，增大学习率
            if recent_mean > older_mean * 1.1:
                return min(self.initial_lr * 2.0, 0.1)
            # 误差减少，减小学习率
            elif recent_mean < older_mean * 0.9:
                return max(self.initial_lr * 0.5, 0.001)
        
        return self.initial_lr
    
    def _update_model_weights(self):
        """动态调整模型权重 (基于最近预测误差)"""
        if len(self.target_history) < 20:
            return
        
        # 计算各模型最近误差
        errors = {}
        recent_targets = list(self.target_history)[-20:]
        
        for name in self.MODEL_NAMES:
            if name == "ewma":
                preds = [self.models["ewma"].predict()] * len(recent_targets)
            elif name == "trend_seasonal":
                preds = [self.models["trend_seasonal"].predict()] * len(recent_targets)
            else:
                continue
            
            mse = np.mean([(p - t) ** 2 for p, t in zip(preds, recent_targets)])
            errors[name] = mse
        
        # 根据误差计算权重 (误差越小，权重越大)
        if errors:
            total_inv_error = sum(1.0 / (e + 1e-6) for e in errors.values())
            for name, error in errors.items():
                self.model_weights[name] = (1.0 / (error + 1e-6)) / total_inv_error
        
        self.learning_state.model_weights = self.model_weights.copy()
    
    def _update_feature_importance(self, features: np.ndarray, actual: float):
        """更新特征重要性 (基于梯度)"""
        if not hasattr(self.models["adaptive_lr"], 'weights'):
            return
        
        weights = np.abs(self.models["adaptive_lr"].weights)
        total = np.sum(weights) + 1e-8
        
        for i in range(min(len(weights), self.n_features)):
            self.feature_importance[f"f{i}"] = weights[i] / total
    
    def _get_overall_drift_status(self) -> DriftStatus:
        """获取整体漂移状态"""
        statuses = [d.get_status() for d in self.drift_detectors.values()]
        
        if DriftStatus.DRIFTING in statuses:
            return DriftStatus.DRIFTING
        elif DriftStatus.ADAPTING in statuses:
            return DriftStatus.ADAPTING
        elif DriftStatus.WARNING in statuses:
            return DriftStatus.WARNING
        return DriftStatus.STABLE
    
    def _adapt_to_drift(self):
        """根据漂移状态进行自适应调整"""
        drift_status = self._get_overall_drift_status()
        
        if drift_status == DriftStatus.DRIFTING:
            log.print_log("[AdaptivePredictor] 检测到概念漂移，触发自适应调整", "warning")
            
            # 1. 重置漂移检测器
            for detector in self.drift_detectors.values():
                detector.reset()
            
            # 2. 临时增大学习率
            self.learning_state.learning_rate = min(self.initial_lr * 3.0, 0.1)
            
            # 3. 给所有模型更多权重，减少依赖单一模型
            for name in self.model_weights:
                self.model_weights[name] = 1.0 / len(self.MODEL_NAMES)
            
        elif drift_status == DriftStatus.WARNING:
            # 轻微增加学习率
            self.learning_state.learning_rate = min(self.initial_lr * 1.5, 0.05)
    
    def get_stats(self) -> Dict[str, Any]:
        """获取预测器统计信息"""
        return {
            "sample_count": self.learning_state.sample_count,
            "current_lr": self._compute_adaptive_lr(),
            "model_weights": self.model_weights.copy(),
            "drift_status": self._get_overall_drift_status().value,
            "feature_importance": self.feature_importance.copy(),
            "avg_recent_error": np.mean(self.learning_state.recent_errors) if self.learning_state.recent_errors else 0.0
        }


# 全局预测器实例
_global_predictors: Dict[str, AdaptivePredictor] = {}


def get_adaptive_predictor(agent_id: str, n_features: int = 7) -> AdaptivePredictor:
    """获取或创建自适应预测器"""
    global _global_predictors
    if agent_id not in _global_predictors:
        _global_predictors[agent_id] = AdaptivePredictor(n_features=n_features)
    return _global_predictors[agent_id]


async def predict_with_online_learning(
    agent_id: str,
    features: np.ndarray,
    actual_value: Optional[float] = None
) -> PredictionResult:
    """
    使用在线学习进行预测
    
    Args:
        agent_id: Agent ID
        features: 特征向量
        actual_value: 实际值 (用于在线更新)
    Returns:
        PredictionResult
    """
    predictor = get_adaptive_predictor(agent_id, len(features))
    
    # 进行预测
    result = predictor.predict(features=features)
    
    # 如果有实际值，更新模型
    if actual_value is not None:
        predictor.update(features, actual_value)
    
    return result
