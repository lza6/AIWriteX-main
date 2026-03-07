# -*- coding: UTF-8 -*-
"""
V16.0 - Experiment Engine (A/B 测试框架)

自动化内容实验平台，支持：
1. 多变量测试 (标题、配图、发布时间)
2. 自动流量分配
3. 统计显著性检验
4. 获胜策略自动推广
"""

import json
import hashlib
import random
from datetime import datetime, timedelta
from typing import Dict, List, Optional, Any, Tuple
from dataclasses import dataclass, field
from enum import Enum
import threading
from collections import defaultdict

import numpy as np
from scipy import stats

from src.ai_write_x.utils import log
from src.ai_write_x.database.db_manager import db_manager


class ExperimentStatus(Enum):
    """实验状态"""
    DRAFT = "draft"
    RUNNING = "running"
    PAUSED = "paused"
    COMPLETED = "completed"
    CANCELLED = "cancelled"


class ExperimentType(Enum):
    """实验类型"""
    HEADLINE = "headline"  # 标题测试
    TEMPLATE = "template"  # 模板测试
    TIMING = "timing"  # 发布时间测试
    IMAGE = "image"  # 配图测试
    STYLE = "style"  # 写作风格测试
    MULTIVARIATE = "multivariate"  # 多变量测试


@dataclass
class Variant:
    """实验变体"""
    id: str
    name: str
    config: Dict[str, Any]
    traffic_percentage: float  # 0-1
    
    # 指标
    impressions: int = 0
    clicks: int = 0
    engagements: int = 0
    conversions: int = 0
    
    @property
    def ctr(self) -> float:
        """点击率"""
        return self.clicks / max(self.impressions, 1)
    
    @property
    def engagement_rate(self) -> float:
        """参与率"""
        return self.engagements / max(self.impressions, 1)


@dataclass
class Experiment:
    """实验定义"""
    id: str
    name: str
    type: ExperimentType
    status: ExperimentStatus
    hypothesis: str
    
    # 变体
    control_variant: Variant
    treatment_variants: List[Variant]
    
    # 配置
    target_metric: str  # "ctr", "engagement", "conversion"
    min_sample_size: int = 1000
    confidence_level: float = 0.95
    
    # 时间
    created_at: datetime = field(default_factory=datetime.now)
    started_at: Optional[datetime] = None
    ended_at: Optional[datetime] = None
    
    # 结果
    winner_variant_id: Optional[str] = None
    is_statistically_significant: bool = False
    uplift_percentage: float = 0.0


class StatisticalAnalyzer:
    """统计分析器"""
    
    @staticmethod
    def calculate_sample_size(
        baseline_rate: float,
        min_detectable_effect: float,
        alpha: float = 0.05,
        power: float = 0.8
    ) -> int:
        """
        计算所需样本量
        
        Args:
            baseline_rate: 基线转化率
            min_detectable_effect: 最小可检测效应 (相对变化)
            alpha: 显著性水平
            power: 统计功效
        """
        # 简化计算 (实际应使用更精确的公式)
        z_alpha = stats.norm.ppf(1 - alpha / 2)
        z_beta = stats.norm.ppf(power)
        
        p1 = baseline_rate
        p2 = baseline_rate * (1 + min_detectable_effect)
        
        p_pooled = (p1 + p2) / 2
        
        n = (
            (z_alpha * np.sqrt(2 * p_pooled * (1 - p_pooled)) +
             z_beta * np.sqrt(p1 * (1 - p1) + p2 * (1 - p2))) ** 2
        ) / (p1 - p2) ** 2
        
        return int(np.ceil(n))
    
    @staticmethod
    def two_proportion_z_test(
        successes_a: int, trials_a: int,
        successes_b: int, trials_b: int
    ) -> Tuple[float, float]:
        """
        双比例 Z 检验
        
        Returns:
            (z_statistic, p_value)
        """
        if trials_a == 0 or trials_b == 0:
            return 0.0, 1.0
        
        p1 = successes_a / trials_a
        p2 = successes_b / trials_b
        
        p_pooled = (successes_a + successes_b) / (trials_a + trials_b)
        
        se = np.sqrt(p_pooled * (1 - p_pooled) * (1 / trials_a + 1 / trials_b))
        
        if se == 0:
            return 0.0, 1.0
        
        z = (p1 - p2) / se
        p_value = 2 * (1 - stats.norm.cdf(abs(z)))
        
        return z, p_value
    
    @staticmethod
    def calculate_confidence_interval(
        successes: int, trials: int, confidence: float = 0.95
    ) -> Tuple[float, float]:
        """计算置信区间"""
        if trials == 0:
            return 0.0, 0.0
        
        p = successes / trials
        z = stats.norm.ppf((1 + confidence) / 2)
        se = np.sqrt(p * (1 - p) / trials)
        
        margin = z * se
        return max(0, p - margin), min(1, p + margin)


class TrafficRouter:
    """流量分配路由器"""
    
    def __init__(self):
        self.user_assignments: Dict[str, str] = {}  # user_id -> variant_id
        
    def assign_variant(self, user_id: str, experiment: Experiment) -> Variant:
        """为用户分配变体"""
        # 检查是否已有分配
        if user_id in self.user_assignments:
            assigned_id = self.user_assignments[user_id]
            # 验证变体是否仍在实验中
            all_variants = [experiment.control_variant] + experiment.treatment_variants
            for v in all_variants:
                if v.id == assigned_id:
                    return v
        
        # 新分配 - 基于流量比例
        all_variants = [experiment.control_variant] + experiment.treatment_variants
        weights = [v.traffic_percentage for v in all_variants]
        
        selected = random.choices(all_variants, weights=weights, k=1)[0]
        self.user_assignments[user_id] = selected.id
        
        return selected
    
    def get_variant_for_user(self, user_id: str, experiment: Experiment) -> Optional[Variant]:
        """获取用户已分配的变体"""
        if user_id not in self.user_assignments:
            return None
        
        variant_id = self.user_assignments[user_id]
        all_variants = [experiment.control_variant] + experiment.treatment_variants
        
        for v in all_variants:
            if v.id == variant_id:
                return v
        return None


class ExperimentEngine:
    """
    V16.0 A/B 测试引擎
    
    功能：
    1. 创建和管理实验
    2. 自动流量分配
    3. 实时统计分析
    4. 自动决策获胜变体
    """
    
    _instance = None
    _lock = threading.Lock()
    
    def __new__(cls):
        with cls._lock:
            if cls._instance is None:
                cls._instance = super(ExperimentEngine, cls).__new__(cls)
                cls._instance._initialized = False
        return cls._instance
    
    def __init__(self):
        if self._initialized:
            return
        
        self._initialized = True
        self.experiments: Dict[str, Experiment] = {}
        self.analyzer = StatisticalAnalyzer()
        self.router = TrafficRouter()
        
        log.print_log("[V16.0] 🧪 Experiment Engine (A/B 测试框架) 已初始化", "success")
    
    def create_experiment(
        self,
        name: str,
        experiment_type: ExperimentType,
        hypothesis: str,
        control_config: Dict[str, Any],
        treatment_configs: List[Dict[str, Any]],
        target_metric: str = "engagement",
        traffic_split: Optional[List[float]] = None
    ) -> str:
        """
        创建新实验
        
        Returns:
            experiment_id
        """
        try:
            # 生成实验 ID
            exp_id = hashlib.md5(f"{name}{datetime.now()}".encode()).hexdigest()[:12]
            
            # 默认平均分配流量
            if traffic_split is None:
                n_variants = len(treatment_configs) + 1
                traffic_split = [1.0 / n_variants] * n_variants
            
            # 创建控制组
            control = Variant(
                id=f"{exp_id}_control",
                name="Control",
                config=control_config,
                traffic_percentage=traffic_split[0]
            )
            
            # 创建实验组
            treatments = []
            for i, config in enumerate(treatment_configs):
                treatments.append(Variant(
                    id=f"{exp_id}_treatment_{i}",
                    name=f"Treatment {i+1}",
                    config=config,
                    traffic_percentage=traffic_split[i + 1]
                ))
            
            # 创建实验
            experiment = Experiment(
                id=exp_id,
                name=name,
                type=experiment_type,
                status=ExperimentStatus.DRAFT,
                hypothesis=hypothesis,
                control_variant=control,
                treatment_variants=treatments,
                target_metric=target_metric
            )
            
            self.experiments[exp_id] = experiment
            
            log.print_log(
                f"[V16.0] 📝 实验已创建: {name} ({exp_id}) "
                f"类型: {experiment_type.value} "
                f"变体数: {len(treatments) + 1}",
                "success"
            )
            
            return exp_id
            
        except Exception as e:
            log.print_log(f"[V16.0] 创建实验失败: {e}", "error")
            raise
    
    def start_experiment(self, experiment_id: str) -> bool:
        """启动实验"""
        if experiment_id not in self.experiments:
            log.print_log(f"[V16.0] 实验不存在: {experiment_id}", "error")
            return False
        
        exp = self.experiments[experiment_id]
        exp.status = ExperimentStatus.RUNNING
        exp.started_at = datetime.now()
        
        log.print_log(f"[V16.0] ▶️ 实验已启动: {exp.name}", "success")
        return True
    
    def get_variant_for_content(
        self, 
        experiment_id: str, 
        content_id: str
    ) -> Optional[Variant]:
        """为内容获取实验变体"""
        if experiment_id not in self.experiments:
            return None
        
        exp = self.experiments[experiment_id]
        if exp.status != ExperimentStatus.RUNNING:
            return exp.control_variant
        
        return self.router.assign_variant(content_id, exp)
    
    def record_event(
        self,
        experiment_id: str,
        variant_id: str,
        event_type: str  # "impression", "click", "engagement", "conversion"
    ):
        """记录实验事件"""
        if experiment_id not in self.experiments:
            return
        
        exp = self.experiments[experiment_id]
        
        # 找到对应变体
        all_variants = [exp.control_variant] + exp.treatment_variants
        for variant in all_variants:
            if variant.id == variant_id:
                if event_type == "impression":
                    variant.impressions += 1
                elif event_type == "click":
                    variant.clicks += 1
                elif event_type == "engagement":
                    variant.engagements += 1
                elif event_type == "conversion":
                    variant.conversions += 1
                break
    
    def analyze_experiment(self, experiment_id: str) -> Dict[str, Any]:
        """分析实验结果"""
        if experiment_id not in self.experiments:
            return {"error": "实验不存在"}
        
        exp = self.experiments[experiment_id]
        control = exp.control_variant
        
        results = {
            "experiment_id": experiment_id,
            "name": exp.name,
            "status": exp.status.value,
            "control": self._variant_stats(control),
            "treatments": []
        }
        
        # 分析每个实验组
        for treatment in exp.treatment_variants:
            # 计算统计显著性
            if exp.target_metric == "ctr":
                z_stat, p_value = self.analyzer.two_proportion_z_test(
                    control.clicks, control.impressions,
                    treatment.clicks, treatment.impressions
                )
            elif exp.target_metric == "engagement":
                z_stat, p_value = self.analyzer.two_proportion_z_test(
                    control.engagements, control.impressions,
                    treatment.engagements, treatment.impressions
                )
            else:
                z_stat, p_value = 0.0, 1.0
            
            # 计算提升
            if exp.target_metric == "ctr":
                control_rate = control.ctr
                treatment_rate = treatment.ctr
            elif exp.target_metric == "engagement":
                control_rate = control.engagement_rate
                treatment_rate = treatment.engagement_rate
            else:
                control_rate = 0
                treatment_rate = 0
            
            uplift = ((treatment_rate - control_rate) / max(control_rate, 0.0001)) * 100
            
            is_significant = p_value < (1 - exp.confidence_level)
            
            results["treatments"].append({
                "variant_id": treatment.id,
                "name": treatment.name,
                "stats": self._variant_stats(treatment),
                "z_statistic": round(z_stat, 3),
                "p_value": round(p_value, 4),
                "is_significant": is_significant,
                "uplift_percentage": round(uplift, 2)
            })
        
        return results
    
    def _variant_stats(self, variant: Variant) -> Dict:
        """获取变体统计"""
        return {
            "impressions": variant.impressions,
            "clicks": variant.clicks,
            "engagements": variant.engagements,
            "conversions": variant.conversions,
            "ctr": round(variant.ctr, 4),
            "engagement_rate": round(variant.engagement_rate, 4)
        }
    
    def conclude_experiment(self, experiment_id: str) -> Optional[str]:
        """
        结束实验并确定获胜变体
        
        Returns:
            winner_variant_id or None
        """
        if experiment_id not in self.experiments:
            return None
        
        exp = self.experiments[experiment_id]
        exp.status = ExperimentStatus.COMPLETED
        exp.ended_at = datetime.now()
        
        # 分析结果
        results = self.analyze_experiment(experiment_id)
        
        best_variant = exp.control_variant
        best_score = self._get_metric_score(exp.control_variant, exp.target_metric)
        is_significant = False
        
        for treatment_result in results.get("treatments", []):
            if treatment_result["is_significant"]:
                is_significant = True
                treatment_id = treatment_result["variant_id"]
                
                # 找到变体对象
                for t in exp.treatment_variants:
                    if t.id == treatment_id:
                        score = self._get_metric_score(t, exp.target_metric)
                        if score > best_score:
                            best_score = score
                            best_variant = t
        
        exp.winner_variant_id = best_variant.id
        exp.is_statistically_significant = is_significant
        
        if best_variant != exp.control_variant and is_significant:
            uplift = ((best_score - self._get_metric_score(exp.control_variant, exp.target_metric)) 
                     / max(self._get_metric_score(exp.control_variant, exp.target_metric), 0.0001)) * 100
            exp.uplift_percentage = uplift
            
            log.print_log(
                f"[V16.0] 🏆 实验结论: {exp.name} "
                f"获胜变体: {best_variant.name} "
                f"提升: {uplift:.1f}% "
                f"显著性: {is_significant}",
                "success"
            )
        else:
            log.print_log(
                f"[V16.0] 📊 实验结论: {exp.name} 无显著差异",
                "info"
            )
        
        return best_variant.id
    
    def _get_metric_score(self, variant: Variant, metric: str) -> float:
        """获取指定指标分数"""
        if metric == "ctr":
            return variant.ctr
        elif metric == "engagement":
            return variant.engagement_rate
        elif metric == "conversion":
            return variant.conversions / max(variant.impressions, 1)
        return 0.0
    
    def list_experiments(self, status: Optional[ExperimentStatus] = None) -> List[Dict]:
        """列出所有实验"""
        results = []
        for exp in self.experiments.values():
            if status is None or exp.status == status:
                results.append({
                    "id": exp.id,
                    "name": exp.name,
                    "type": exp.type.value,
                    "status": exp.status.value,
                    "variants_count": len(exp.treatment_variants) + 1,
                    "started_at": exp.started_at.isoformat() if exp.started_at else None,
                    "winner": exp.winner_variant_id
                })
        return results


# 全局实例
_experiment_engine = None


def get_experiment_engine() -> ExperimentEngine:
    """获取实验引擎全局实例"""
    global _experiment_engine
    if _experiment_engine is None:
        _experiment_engine = ExperimentEngine()
    return _experiment_engine
