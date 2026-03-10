"""
AIWriteX V19.0 - Reasoning Chain Module
类人推理链 - 模拟人类思维过程的链式推理

功能:
1. 多步推理: 将复杂问题分解为多个推理步骤
2. 推理类型: 演绎、归纳、类比、因果等多种推理模式
3. 推理验证: 每一步的可验证性和一致性检查
4. 推理可视化: 展示完整推理路径
"""

import json
from typing import Dict, List, Optional, Any, Callable
from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum, auto
from uuid import uuid4
import numpy as np


class ReasoningType(Enum):
    """推理类型"""
    DEDUCTIVE = "deductive"         # 演绎推理: 一般到特殊
    INDUCTIVE = "inductive"         # 归纳推理: 特殊到一般
    ANALOGICAL = "analogical"       # 类比推理: 相似性推理
    CAUSAL = "causal"               # 因果推理: 因果关系
    ABDUCTIVE = "abductive"         # 溯因推理: 最佳解释
    COUNTERFACTUAL = "counterfactual"  # 反事实推理: 假设分析
    MORAL = "moral"                 # 道德推理: 价值判断


class ConfidenceLevel(Enum):
    """置信级别"""
    CERTAIN = 1.0
    HIGH = 0.8
    MODERATE = 0.6
    LOW = 0.4
    UNCERTAIN = 0.2


@dataclass
class ReasoningStep:
    """推理步骤"""
    id: str
    step_number: int
    description: str
    reasoning_type: ReasoningType
    premises: List[str]              # 前提条件
    conclusion: str                  # 结论
    confidence: float               # 置信度 0-1
    evidence: List[str]             # 支持证据
    assumptions: List[str]          # 假设条件
    counter_arguments: List[str]    # 反方论点
    timestamp: datetime = field(default_factory=datetime.now)
    metadata: Dict[str, Any] = field(default_factory=dict)
    
    def to_dict(self) -> Dict:
        return {
            "id": self.id,
            "step_number": self.step_number,
            "description": self.description,
            "reasoning_type": self.reasoning_type.value,
            "premises": self.premises,
            "conclusion": self.conclusion,
            "confidence": self.confidence,
            "evidence": self.evidence,
            "assumptions": self.assumptions,
            "counter_arguments": self.counter_arguments,
            "timestamp": self.timestamp.isoformat(),
            "metadata": self.metadata
        }


@dataclass
class ReasoningChain:
    """
    推理链
    
    模拟人类的多步推理过程，支持多种推理类型的组合
    """
    id: str = field(default_factory=lambda: str(uuid4()))
    topic: str = ""
    goal: str = ""
    steps: List[ReasoningStep] = field(default_factory=list)
    final_conclusion: str = ""
    overall_confidence: float = 0.0
    created_at: datetime = field(default_factory=datetime.now)
    completed_at: Optional[datetime] = None
    
    def add_step(
        self,
        description: str,
        reasoning_type: ReasoningType,
        premises: List[str],
        conclusion: str,
        confidence: float = 0.8,
        evidence: List[str] = None,
        assumptions: List[str] = None,
        counter_arguments: List[str] = None,
        metadata: Dict = None
    ) -> ReasoningStep:
        """添加推理步骤"""
        step = ReasoningStep(
            id=str(uuid4()),
            step_number=len(self.steps) + 1,
            description=description,
            reasoning_type=reasoning_type,
            premises=premises,
            conclusion=conclusion,
            confidence=confidence,
            evidence=evidence or [],
            assumptions=assumptions or [],
            counter_arguments=counter_arguments or [],
            metadata=metadata or {}
        )
        self.steps.append(step)
        self._update_overall_confidence()
        return step
    
    def _update_overall_confidence(self):
        """更新整体置信度"""
        if not self.steps:
            self.overall_confidence = 0.0
            return
        
        # 计算各步骤置信度的加权平均
        confidences = [step.confidence for step in self.steps]
        # 使用几何平均，强调 weakest link
        self.overall_confidence = np.prod(confidences) ** (1 / len(confidences))
    
    def validate_chain(self) -> Dict[str, Any]:
        """验证推理链的合理性"""
        issues = []
        warnings = []
        
        # 检查步骤间的逻辑连贯性
        for i in range(1, len(self.steps)):
            prev_step = self.steps[i - 1]
            curr_step = self.steps[i]
            
            # 检查当前步骤的前提是否包含前一步的结论
            if prev_step.conclusion not in curr_step.premises:
                warnings.append(
                    f"步骤{curr_step.step_number}的前提未明确引用步骤{prev_step.step_number}的结论"
                )
        
        # 检查置信度
        low_confidence_steps = [s for s in self.steps if s.confidence < 0.5]
        if low_confidence_steps:
            issues.append(
                f"有{len(low_confidence_steps)}个步骤置信度低于0.5"
            )
        
        # 检查是否有反方论点未处理
        unaddressed_counters = [
            s for s in self.steps 
            if s.counter_arguments and len(s.counter_arguments) > len(s.evidence)
        ]
        if unaddressed_counters:
            warnings.append(
                f"有{len(unaddressed_counters)}个步骤存在未充分回应的反方论点"
            )
        
        return {
            "valid": len(issues) == 0,
            "issues": issues,
            "warnings": warnings,
            "step_count": len(self.steps),
            "overall_confidence": self.overall_confidence
        }
    
    def get_reasoning_path(self) -> List[Dict]:
        """获取推理路径"""
        return [step.to_dict() for step in self.steps]
    
    def explain(self) -> str:
        """生成推理过程的解释"""
        lines = [
            f"# 推理链: {self.topic}",
            f"**目标**: {self.goal}",
            f"**整体置信度**: {self.overall_confidence:.1%}",
            "",
            "## 推理过程",
            ""
        ]
        
        for step in self.steps:
            lines.append(f"### 步骤 {step.step_number}: {step.description}")
            lines.append(f"**推理类型**: {step.reasoning_type.value}")
            lines.append("")
            lines.append("**前提**:")
            for premise in step.premises:
                lines.append(f"- {premise}")
            lines.append("")
            lines.append(f"**结论**: {step.conclusion}")
            lines.append(f"**置信度**: {step.confidence:.1%}")
            
            if step.evidence:
                lines.append("")
                lines.append("**证据**:")
                for evidence in step.evidence:
                    lines.append(f"- {evidence}")
            
            if step.counter_arguments:
                lines.append("")
                lines.append("**反方论点**:")
                for counter in step.counter_arguments:
                    lines.append(f"- {counter}")
            
            lines.append("")
        
        lines.append("## 最终结论")
        lines.append(self.final_conclusion)
        
        return "\n".join(lines)
    
    def to_dict(self) -> Dict:
        return {
            "id": self.id,
            "topic": self.topic,
            "goal": self.goal,
            "steps": [step.to_dict() for step in self.steps],
            "final_conclusion": self.final_conclusion,
            "overall_confidence": self.overall_confidence,
            "created_at": self.created_at.isoformat(),
            "completed_at": self.completed_at.isoformat() if self.completed_at else None
        }


class ReasoningEngine:
    """
    推理引擎
    
    提供多种推理模式的应用
    """
    
    def __init__(self):
        self.reasoning_chains: List[ReasoningChain] = []
        self._reasoning_patterns: Dict[ReasoningType, Callable] = {
            ReasoningType.DEDUCTIVE: self._apply_deductive_reasoning,
            ReasoningType.INDUCTIVE: self._apply_inductive_reasoning,
            ReasoningType.ANALOGICAL: self._apply_analogical_reasoning,
            ReasoningType.CAUSAL: self._apply_causal_reasoning,
            ReasoningType.ABDUCTIVE: self._apply_abductive_reasoning,
        }
    
    def create_chain(self, topic: str, goal: str) -> ReasoningChain:
        """创建新的推理链"""
        chain = ReasoningChain(topic=topic, goal=goal)
        self.reasoning_chains.append(chain)
        return chain
    
    def apply_reasoning(
        self,
        chain: ReasoningChain,
        reasoning_type: ReasoningType,
        context: Dict[str, Any]
    ) -> Optional[ReasoningStep]:
        """应用特定推理模式"""
        if reasoning_type in self._reasoning_patterns:
            return self._reasoning_patterns[reasoning_type](chain, context)
        return None
    
    def _apply_deductive_reasoning(
        self,
        chain: ReasoningChain,
        context: Dict
    ) -> ReasoningStep:
        """应用演绎推理"""
        general_rule = context.get("general_rule", "")
        specific_case = context.get("specific_case", "")
        conclusion = context.get("conclusion", "")
        
        return chain.add_step(
            description="演绎推理: 从一般规则推导特定结论",
            reasoning_type=ReasoningType.DEDUCTIVE,
            premises=[f"一般规则: {general_rule}", f"特定情况: {specific_case}"],
            conclusion=conclusion,
            confidence=context.get("confidence", 0.9),
            evidence=["逻辑有效性保证"]
        )
    
    def _apply_inductive_reasoning(
        self,
        chain: ReasoningChain,
        context: Dict
    ) -> ReasoningStep:
        """应用归纳推理"""
        observations = context.get("observations", [])
        pattern = context.get("pattern", "")
        conclusion = context.get("conclusion", "")
        
        return chain.add_step(
            description="归纳推理: 从观察中总结一般规律",
            reasoning_type=ReasoningType.INDUCTIVE,
            premises=[f"观察{i+1}: {obs}" for i, obs in enumerate(observations)],
            conclusion=conclusion,
            confidence=context.get("confidence", 0.7),
            evidence=[f"发现的模式: {pattern}"],
            assumptions=["观察样本具有代表性"]
        )
    
    def _apply_analogical_reasoning(
        self,
        chain: ReasoningChain,
        context: Dict
    ) -> ReasoningStep:
        """应用类比推理"""
        source_domain = context.get("source_domain", "")
        target_domain = context.get("target_domain", "")
        similarities = context.get("similarities", [])
        conclusion = context.get("conclusion", "")
        
        return chain.add_step(
            description="类比推理: 基于相似性进行推理",
            reasoning_type=ReasoningType.ANALOGICAL,
            premises=[
                f"源领域: {source_domain}",
                f"目标领域: {target_domain}",
                f"相似点: {', '.join(similarities)}"
            ],
            conclusion=conclusion,
            confidence=context.get("confidence", 0.6),
            evidence=[f"相似性分析: {len(similarities)}个共同点"],
            counter_arguments=["类比的不完全性可能导致错误结论"]
        )
    
    def _apply_causal_reasoning(
        self,
        chain: ReasoningChain,
        context: Dict
    ) -> ReasoningStep:
        """应用因果推理"""
        cause = context.get("cause", "")
        effect = context.get("effect", "")
        mechanism = context.get("mechanism", "")
        
        return chain.add_step(
            description="因果推理: 分析因果关系",
            reasoning_type=ReasoningType.CAUSAL,
            premises=[f"原因: {cause}", f"作用机制: {mechanism}"],
            conclusion=f"结果: {effect}",
            confidence=context.get("confidence", 0.75),
            evidence=["因果机制解释", "相关性数据支持"],
            assumptions=["不存在其他混杂因素"]
        )
    
    def _apply_abductive_reasoning(
        self,
        chain: ReasoningChain,
        context: Dict
    ) -> ReasoningStep:
        """应用溯因推理"""
        observation = context.get("observation", "")
        possible_explanations = context.get("possible_explanations", [])
        best_explanation = context.get("best_explanation", "")
        
        return chain.add_step(
            description="溯因推理: 寻找最佳解释",
            reasoning_type=ReasoningType.ABDUCTIVE,
            premises=[f"观察: {observation}"] + [f"可能解释: {exp}" for exp in possible_explanations],
            conclusion=f"最佳解释: {best_explanation}",
            confidence=context.get("confidence", 0.6),
            evidence=["解释的简洁性", "与现有知识的一致性"],
            counter_arguments=["可能存在未考虑到的解释"]
        )
    
    def get_chain_by_id(self, chain_id: str) -> Optional[ReasoningChain]:
        """通过ID获取推理链"""
        for chain in self.reasoning_chains:
            if chain.id == chain_id:
                return chain
        return None
    
    def get_chains_by_topic(self, topic: str) -> List[ReasoningChain]:
        """通过主题获取推理链"""
        return [chain for chain in self.reasoning_chains if topic in chain.topic]


# 全局推理引擎实例
reasoning_engine = ReasoningEngine()


def get_reasoning_engine() -> ReasoningEngine:
    """获取推理引擎实例"""
    return reasoning_engine
