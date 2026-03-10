# -*- coding: UTF-8 -*-
"""
Adaptive Model Router V2 - 自适应模型路由器

功能:
- 任务复杂度 4 层分类 (简单→专家)
- 成本 - 质量帕累托优化
- 实时性能反馈路由
- 自动降级链 (Premium → Fast)

版本：V2.0.0
作者：AIWriteX Team
创建日期：2026-03-09
"""

import time
from typing import Dict, Any, List, Optional, Callable
from dataclasses import dataclass
from enum import Enum
import json


class TaskComplexity(Enum):
    """任务复杂度等级"""
    SIMPLE = 1          # 简单任务：事实查询、简单计算
    INTERMEDIATE = 2    # 中等任务：分析总结、创意写作
    ADVANCED = 3        # 高级任务：复杂推理、专业领域
    EXPERT = 4          # 专家任务：创造性解决方案、跨领域整合


@dataclass
class ModelConfig:
    """模型配置"""
    name: str
    provider: str
    cost_per_1k_tokens: float
    max_tokens: int
    latency_p50_ms: float
    latency_p95_ms: float
    quality_score: float  # 1-10 分
    context_window: int
    is_available: bool = True


@dataclass
class RoutingDecision:
    """路由决策"""
    model_name: str
    reason: str
    estimated_cost: float
    estimated_latency_ms: float
    complexity: TaskComplexity
    fallback_chain: List[str]


class AdaptiveModelRouter:
    """
    自适应模型路由器 V2

    特性:
    - 基于任务内容自动分析复杂度
    - 多目标优化（成本、延迟、质量）
    - 实时性能监控与动态调整
    - 智能降级策略
    """

    def __init__(self, optimization_mode: str = 'balanced'):
        """
        初始化路由器

        Args:
            optimization_mode: 优化模式
                - 'cost': 成本优先
                - 'speed': 速度优先
                - 'quality': 质量优先
                - 'balanced': 平衡模式
        """
        self.optimization_mode = optimization_mode

        # 模型配置池
        self.model_pool: Dict[str, ModelConfig] = {}

        # 性能历史记录
        self.performance_history: List[Dict[str, Any]] = []

        # 成本预算（美元/月）
        self.monthly_budget = 100.0
        self.current_month_cost = 0.0

        # 注册默认模型
        self._register_default_models()

        # 复杂度判断关键词
        self.complexity_keywords = {
            TaskComplexity.SIMPLE: [
                '是什么', '定义', '解释', '计算', '翻译', '拼写', '语法'
            ],
            TaskComplexity.INTERMEDIATE: [
                '分析', '总结', '概括', '比较', '优缺点', '为什么', '如何'
            ],
            TaskComplexity.ADVANCED: [
                '推理', '证明', '设计', '优化', '策略', '方案', '预测'
            ],
            TaskComplexity.EXPERT: [
                '创新', '创造', '突破性', '跨领域', '系统性', '架构', '范式'
            ]
        }

    def register_model(self, config: ModelConfig):
        """注册模型"""
        self.model_pool[config.name] = config

    def route(
        self,
        prompt: str,
        context: Optional[Dict[str, Any]] = None,
        budget_constraint: Optional[float] = None
    ) -> RoutingDecision:
        """
        路由决策

        Args:
            prompt: 用户输入
            context: 上下文信息
            budget_constraint: 预算约束

        Returns:
            路由决策
        """
        # 1. 分析任务复杂度
        complexity = self._analyze_complexity(prompt)

        # 2. 获取可用模型
        available_models = [
            m for m in self.model_pool.values()
            if m.is_available
        ]

        # 3. 根据优化模式评分
        scored_models = self._score_models(
            available_models,
            complexity,
            budget_constraint
        )

        # 4. 选择最优模型
        best_model = max(scored_models, key=lambda x: x['total_score'])

        # 5. 生成降级链
        fallback_chain = self._generate_fallback_chain(
            best_model['model'],
            complexity
        )

        # 6. 估算成本和延迟
        estimated_tokens = self._estimate_tokens(prompt)
        estimated_cost = (estimated_tokens / 1000) * \
            best_model['model'].cost_per_1k_tokens
        estimated_latency = self._estimate_latency(
            best_model['model'], complexity)

        decision = RoutingDecision(
            model_name=best_model['model'].name,
            reason=best_model['reason'],
            estimated_cost=estimated_cost,
            estimated_latency_ms=estimated_latency,
            complexity=complexity,
            fallback_chain=fallback_chain
        )

        # 7. 记录决策
        self._log_decision(decision, prompt)

        return decision

    def update_performance(
        self,
        model_name: str,
        actual_latency_ms: float,
        actual_tokens: int,
        success: bool = True
    ):
        """更新性能历史"""
        self.performance_history.append({
            'timestamp': time.time(),
            'model_name': model_name,
            'latency_ms': actual_latency_ms,
            'tokens': actual_tokens,
            'success': success
        })

        # 保留最近 1000 条记录
        if len(self.performance_history) > 1000:
            self.performance_history = self.performance_history[-1000:]

        # 更新模型可用性
        if not success:
            if model_name in self.model_pool:
                # 连续失败 3 次标记为不可用
                recent_failures = sum(
                    1 for record in self.performance_history[-10:]
                    if record['model_name'] == model_name and not record['success']
                )
                if recent_failures >= 3:
                    self.model_pool[model_name].is_available = False

    def _register_default_models(self):
        """注册默认模型"""
        default_models = [
            ModelConfig(
                name="gpt-4-turbo",
                provider="OpenAI",
                cost_per_1k_tokens=0.01,
                max_tokens=128000,
                latency_p50_ms=1500,
                latency_p95_ms=3000,
                quality_score=9.5,
                context_window=128000
            ),
            ModelConfig(
                name="claude-3-opus",
                provider="Anthropic",
                cost_per_1k_tokens=0.015,
                max_tokens=200000,
                latency_p50_ms=2000,
                latency_p95_ms=4000,
                quality_score=9.8,
                context_window=200000
            ),
            ModelConfig(
                name="deepseek-chat",
                provider="DeepSeek",
                cost_per_1k_tokens=0.001,
                max_tokens=128000,
                latency_p50_ms=800,
                latency_p95_ms=1500,
                quality_score=8.5,
                context_window=128000
            ),
            ModelConfig(
                name="qwen-plus",
                provider="Alibaba",
                cost_per_1k_tokens=0.002,
                max_tokens=32000,
                latency_p50_ms=600,
                latency_p95_ms=1200,
                quality_score=8.0,
                context_window=32000
            ),
            ModelConfig(
                name="fast-model",
                provider="Generic",
                cost_per_1k_tokens=0.0001,
                max_tokens=8000,
                latency_p50_ms=200,
                latency_p95_ms=500,
                quality_score=6.0,
                context_window=8000
            )
        ]

        for model in default_models:
            self.register_model(model)

    def _analyze_complexity(self, prompt: str) -> TaskComplexity:
        """分析任务复杂度"""
        prompt_lower = prompt.lower()

        # 关键词匹配
        scores = {level: 0 for level in TaskComplexity}

        for level, keywords in self.complexity_keywords.items():
            for keyword in keywords:
                if keyword.lower() in prompt_lower:
                    scores[level] += 1

        # 考虑长度因素
        word_count = len(prompt.split())
        if word_count > 500:
            scores[TaskComplexity.ADVANCED] += 1
        if word_count > 1000:
            scores[TaskComplexity.EXPERT] += 1

        # 返回最高分等级
        return max(scores, key=scores.get)

    def _score_models(
        self,
        models: List[ModelConfig],
        complexity: TaskComplexity,
        budget_constraint: Optional[float] = None
    ) -> List[Dict[str, Any]]:
        """对模型进行评分"""
        scored = []

        for model in models:
            scores = {}
            reasons = []

            # 成本评分 (0-1)
            max_cost = max(m.cost_per_1k_tokens for m in models)
            cost_score = 1 - (model.cost_per_1k_tokens /
                              max_cost) if max_cost > 0 else 0
            scores['cost'] = cost_score

            # 速度评分 (0-1)
            max_latency = max(m.latency_p50_ms for m in models)
            speed_score = 1 - (model.latency_p50_ms /
                               max_latency) if max_latency > 0 else 0
            scores['speed'] = speed_score

            # 质量评分 (0-1)
            quality_score = model.quality_score / 10.0
            scores['quality'] = quality_score

            # 根据优化模式加权
            if self.optimization_mode == 'cost':
                weights = {'cost': 0.7, 'speed': 0.2, 'quality': 0.1}
            elif self.optimization_mode == 'speed':
                weights = {'cost': 0.2, 'speed': 0.7, 'quality': 0.1}
            elif self.optimization_mode == 'quality':
                weights = {'cost': 0.1, 'speed': 0.2, 'quality': 0.7}
            else:  # balanced
                weights = {'cost': 0.33, 'speed': 0.33, 'quality': 0.34}

            # 根据复杂度调整权重
            if complexity == TaskComplexity.SIMPLE:
                weights['cost'] += 0.2
                weights['quality'] -= 0.2
            elif complexity == TaskComplexity.EXPERT:
                weights['quality'] += 0.3
                weights['cost'] -= 0.15
                weights['speed'] -= 0.15

            # 计算总分
            total_score = sum(scores[k] * v for k, v in weights.items())

            # 预算约束检查
            if budget_constraint:
                estimated_cost = (1000 / 1000) * \
                    model.cost_per_1k_tokens  # 假设 1k tokens
                if estimated_cost > budget_constraint:
                    total_score *= 0.5  # 惩罚
                    reasons.append(f"超出预算约束")

            reasons.append(
                f"{self.optimization_mode}模式，复杂度{complexity.name}，"
                f"成本:{model.cost_per_1k_tokens:.4f}, 质量:{model.quality_score}"
            )

            scored.append({
                'model': model,
                'total_score': total_score,
                'scores': scores,
                'reason': '; '.join(reasons)
            })

        return scored

    def _generate_fallback_chain(
        self,
        selected_model: ModelConfig,
        complexity: TaskComplexity
    ) -> List[str]:
        """生成降级链"""
        fallback = []

        # 按质量排序
        sorted_models = sorted(
            [m for m in self.model_pool.values() if m.is_available],
            key=lambda m: m.quality_score,
            reverse=True
        )

        # 从当前模型开始，依次降级
        current_idx = next(
            (i for i, m in enumerate(sorted_models)
             if m.name == selected_model.name),
            0
        )

        # 添加所有其他可用模型作为降级选项
        for model in sorted_models[current_idx + 1:]:
            # 只要不是当前选中的模型都可以加入降级链
            if model.name != selected_model.name:
                fallback.append(model.name)

        # 如果降级链为空，至少添加一个最便宜的模型
        if not fallback:
            cheapest = min(
                [m for m in self.model_pool.values() if m.is_available and m.name !=
                 selected_model.name],
                key=lambda m: m.cost_per_1k_tokens,
                default=None
            )
            if cheapest:
                fallback.append(cheapest.name)

        return fallback[:3]  # 最多 3 个降级选项

    def _estimate_tokens(self, prompt: str) -> int:
        """估算 token 数"""
        # 简单估算：每 4 个字符约 1 个 token
        char_count = len(prompt)
        estimated_tokens = char_count // 4

        # 加上响应预估（假设响应是输入的 1-3 倍）
        response_multiplier = 2
        return int(estimated_tokens * response_multiplier)

    def _estimate_latency(
        self,
        model: ModelConfig,
        complexity: TaskComplexity
    ) -> float:
        """估算延迟"""
        base_latency = model.latency_p50_ms

        # 复杂度影响
        complexity_multiplier = {
            TaskComplexity.SIMPLE: 0.8,
            TaskComplexity.INTERMEDIATE: 1.0,
            TaskComplexity.ADVANCED: 1.3,
            TaskComplexity.EXPERT: 1.6
        }

        return base_latency * complexity_multiplier[complexity]

    def _log_decision(self, decision: RoutingDecision, prompt: str):
        """记录路由决策"""
        # 这里可以集成到日志系统
        pass

    def get_stats(self) -> Dict[str, Any]:
        """获取统计信息"""
        total_requests = len(self.performance_history)
        success_rate = sum(
            1 for r in self.performance_history if r['success']
        ) / total_requests if total_requests > 0 else 0

        avg_latency = sum(
            r['latency_ms'] for r in self.performance_history
        ) / total_requests if total_requests > 0 else 0

        return {
            'total_requests': total_requests,
            'success_rate': f"{success_rate:.2%}",
            'avg_latency_ms': avg_latency,
            'available_models': len([m for m in self.model_pool.values() if m.is_available]),
            'optimization_mode': self.optimization_mode
        }


# 示例用法
if __name__ == "__main__":
    router = AdaptiveModelRouter(optimization_mode='balanced')

    # 测试不同任务
    prompts = [
        "Python 是什么？",  # 简单
        "分析一下 Python 的优缺点",  # 中等
        "设计一个高并发的 Python 系统架构",  # 高级
        "创造一个全新的编程范式"  # 专家
    ]

    for prompt in prompts:
        decision = router.route(prompt)
        print(f"\n任务：{prompt}")
        print(f"推荐模型：{decision.model_name}")
        print(f"原因：{decision.reason}")
        print(f"预估成本：${decision.estimated_cost:.4f}")
        print(f"预估延迟：{decision.estimated_latency_ms:.0f}ms")
        print(f"降级链：{' -> '.join(decision.fallback_chain)}")

    # 打印统计
    stats = router.get_stats()
    print(f"\n路由统计：{stats}")
