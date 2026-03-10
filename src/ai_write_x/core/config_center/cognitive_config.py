"""
认知配置管理 - 动态调整认知参数
├── 推理深度配置: 控制推理的迭代次数
├── 记忆容量配置: 调整记忆存储限制
├── 注意力配置: 设置注意力机制参数
├── 学习率配置: 控制记忆更新速度
├── 个性配置: 调整认知风格偏好
└── 热更新支持: 不重启的认知参数调整
"""

import numpy as np
from typing import Dict, List, Optional, Any, Callable, Union
from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum, auto
import threading
import time
import json
import copy


class CognitiveProfile(Enum):
    """认知配置文件"""
    DEFAULT = "default"           # 默认配置
    CREATIVE = "creative"         # 创造性思维
    ANALYTICAL = "analytical"     # 分析性思维
    INTUITIVE = "intuitive"       # 直觉思维
    CONSERVATIVE = "conservative"  # 保守思维
    ADAPTIVE = "adaptive"         # 自适应


class AttentionMode(Enum):
    """注意力模式"""
    FOCUSED = "focused"           # 聚焦注意力
    DIVIDED = "divided"           # 分散注意力
    EXECUTIVE = "executive"       # 执行控制
    STIMULUS = "stimulus"         # 刺激驱动


class LearningMode(Enum):
    """学习模式"""
    SUPERVISED = "supervised"     # 监督学习
    REINFORCEMENT = "reinforcement"  # 强化学习
    UNSUPERVISED = "unsupervised"  # 无监督学习
    IMITATION = "imitation"       # 模仿学习
    EXPLORATION = "exploration"   # 探索学习


class ReasoningStrategy(Enum):
    """推理策略"""
    DEDUCTIVE = "deductive"       # 演绎推理
    INDUCTIVE = "inductive"       # 归纳推理
    ABDUCTIVE = "abductive"       # 溯因推理
    ANALOGICAL = "analogical"     # 类比推理
    CAUSAL = "causal"             # 因果推理


@dataclass
class ReasoningConfig:
    """推理配置"""
    max_depth: int = 5                  # 最大推理深度
    max_iterations: int = 10            # 最大迭代次数
    timeout_seconds: float = 30.0        # 超时时间
    confidence_threshold: float = 0.7    # 置信度阈值
    enable_uncertainty: bool = True     # 不确定性推理
    enable_counterfactual: bool = True  # 反事实推理
    enable_meta_cognition: bool = True  # 元认知
    strategy: ReasoningStrategy = ReasoningStrategy.ANALOGICAL
    parallel_branches: int = 3           # 并行分支数
    pruning_enabled: bool = True         # 剪枝启用


@dataclass
class MemoryConfig:
    """记忆配置"""
    working_capacity: int = 7           # 工作记忆容量 (Miller's Law)
    episodic_limit: int = 1000           # 情景记忆上限
    semantic_limit: int = 5000          # 语义记忆上限
    retention_decay: float = 0.1        # 记忆衰减率
    consolidation_threshold: float = 0.8  # 巩固阈值
    forget_threshold: float = 0.2        # 遗忘阈值
    auto_consolidate: bool = True        # 自动巩固
    emotional_enhancement: bool = True  # 情感增强
    context_encoding: bool = True        # 上下文编码


@dataclass
class AttentionConfig:
    """注意力配置"""
    mode: AttentionMode = AttentionMode.EXECUTIVE
    focus_duration: float = 20.0         # 聚焦持续时间(秒)
    attention_span: float = 10.0         # 注意力跨度
    switch_cost: float = 0.2             # 切换成本
    filtering_threshold: float = 0.5      # 过滤阈值
    priority_weights: Dict[str, float] = field(default_factory=lambda: {
        "novelty": 0.3,
        "relevance": 0.4,
        "emotional": 0.2,
        "recency": 0.1
    })
    enable_bottleneck: bool = True       # 瓶颈检测
    max_focus_items: int = 4             # 最大聚焦项


@dataclass
class LearningConfig:
    """学习配置"""
    learning_rate: float = 0.1           # 学习率
    batch_size: int = 32                 # 批处理大小
    exploration_rate: float = 0.2         # 探索率
    exploitation_rate: float = 0.7        # 利用率
    discount_factor: float = 0.9         # 折扣因子
    memory_importance_weight: float = 0.3  # 记忆重要性权重
    error_correction_rate: float = 0.5    # 错误纠正率
    generalization_enabled: bool = True   # 泛化启用
    transfer_learning: bool = True        # 迁移学习
    mode: LearningMode = LearningMode.REINFORCEMENT


@dataclass
class PersonalityConfig:
    """个性配置"""
    risk_tolerance: float = 0.5          # 风险承受度
    openness: float = 0.7                # 开放性
    conscientiousness: float = 0.6       # 尽责性
    creativity: float = 0.7              # 创造性
    conservatism: float = 0.4            # 保守性
    social_learning: float = 0.5          # 社会学习
    self_confidence: float = 0.6          # 自信度
    persistence: float = 0.7              # 坚持性
    flexibility: float = 0.5              # 灵活性


@dataclass
class CognitiveState:
    """认知状态快照"""
    timestamp: datetime
    reasoning: ReasoningConfig
    memory: MemoryConfig
    attention: AttentionConfig
    learning: LearningConfig
    personality: PersonalityConfig
    active_profile: CognitiveProfile
    performance_metrics: Dict[str, float] = field(default_factory=dict)


@dataclass
class ConfigChange:
    """配置变更记录"""
    id: str
    timestamp: datetime
    parameter_path: str
    old_value: Any
    new_value: Any
    change_type: str                      # "set", "increase", "decrease", "reset"
    source: str                           # "manual", "auto", "profile", "adaptive"
    reverted: bool = False


class CognitiveConfigManager:
    """
    认知配置管理系统

    实现动态认知参数管理:
    1. 推理深度配置: 控制推理的迭代次数
    2. 记忆容量配置: 调整记忆存储限制
    3. 注意力配置: 设置注意力机制参数
    4. 学习率配置: 控制记忆更新速度
    5. 个性配置: 调整认知风格偏好
    6. 热更新支持: 不重启的认知参数调整
    """

    # 默认配置
    DEFAULT_PROFILES = {
        CognitiveProfile.DEFAULT: {
            "reasoning": ReasoningConfig(),
            "memory": MemoryConfig(),
            "attention": AttentionConfig(),
            "learning": LearningConfig(),
            "personality": PersonalityConfig()
        },
        CognitiveProfile.CREATIVE: {
            "reasoning": ReasoningConfig(
                max_depth=8,
                max_iterations=15,
                enable_counterfactual=True,
                strategy=ReasoningStrategy.ABDUCTIVE,
                parallel_branches=5
            ),
            "memory": MemoryConfig(
                retention_decay=0.05,
                consolidation_threshold=0.6
            ),
            "attention": AttentionConfig(
                mode=AttentionMode.DIVIDED,
                focus_duration=10.0,
                switch_cost=0.1
            ),
            "learning": LearningConfig(
                exploration_rate=0.4,
                generalization_enabled=True
            ),
            "personality": PersonalityConfig(
                creativity=0.9,
                openness=0.9,
                risk_tolerance=0.8
            )
        },
        CognitiveProfile.ANALYTICAL: {
            "reasoning": ReasoningConfig(
                max_depth=10,
                max_iterations=20,
                confidence_threshold=0.85,
                enable_uncertainty=True,
                strategy=ReasoningStrategy.DEDUCTIVE,
                pruning_enabled=True
            ),
            "memory": MemoryConfig(
                working_capacity=9,
                retention_decay=0.15,
                consolidation_threshold=0.9
            ),
            "attention": AttentionConfig(
                mode=AttentionMode.FOCUSED,
                focus_duration=30.0,
                filtering_threshold=0.7
            ),
            "learning": LearningConfig(
                learning_rate=0.05,
                exploration_rate=0.1,
                mode=LearningMode.SUPERVISED
            ),
            "personality": PersonalityConfig(
                conscientiousness=0.9,
                conservatism=0.7,
                flexibility=0.3
            )
        },
        CognitiveProfile.INTUITIVE: {
            "reasoning": ReasoningConfig(
                max_depth=3,
                max_iterations=5,
                confidence_threshold=0.5,
                enable_counterfactual=False,
                strategy=ReasoningStrategy.INDUCTIVE
            ),
            "memory": MemoryConfig(
                retention_decay=0.08,
                emotional_enhancement=True
            ),
            "attention": AttentionConfig(
                mode=AttentionMode.STIMULUS,
                filtering_threshold=0.3
            ),
            "learning": LearningConfig(
                exploration_rate=0.3,
                mode=LearningMode.IMITATION
            ),
            "personality": PersonalityConfig(
                self_confidence=0.8,
                persistence=0.5
            )
        },
        CognitiveProfile.CONSERVATIVE: {
            "reasoning": ReasoningConfig(
                max_depth=4,
                max_iterations=8,
                confidence_threshold=0.9,
                enable_uncertainty=True,
                pruning_enabled=True
            ),
            "memory": MemoryConfig(
                retention_decay=0.2,
                consolidation_threshold=0.95
            ),
            "attention": AttentionConfig(
                mode=AttentionMode.FOCUSED,
                focus_duration=25.0,
                max_focus_items=2
            ),
            "learning": LearningConfig(
                exploration_rate=0.05,
                error_correction_rate=0.8
            ),
            "personality": PersonalityConfig(
                conservatism=0.9,
                risk_tolerance=0.2,
                flexibility=0.3
            )
        },
        CognitiveProfile.ADAPTIVE: {
            # 动态调整，由系统自动控制
            "reasoning": ReasoningConfig(),
            "memory": MemoryConfig(),
            "attention": AttentionConfig(),
            "learning": LearningConfig(),
            "personality": PersonalityConfig()
        }
    }

    def __init__(
        self,
        initial_profile: CognitiveProfile = CognitiveProfile.DEFAULT,
        enable_hot_reload: bool = True,
        enable_change_tracking: bool = True,
        config_file: Optional[str] = None
    ):
        """
        初始化认知配置管理器

        Args:
            initial_profile: 初始配置文件
            enable_hot_reload: 启用热更新
            enable_change_tracking: 启用变更追踪
            config_file: 配置文件路径
        """
        self.enable_hot_reload = enable_hot_reload
        self.enable_change_tracking = enable_change_tracking
        self.config_file = config_file

        # 加载配置
        self._current_profile = initial_profile
        self._load_profile(initial_profile)

        # 变更追踪
        self._change_history: List[ConfigChange] = []
        self._change_counter = 0

        # 回调函数
        self._change_callbacks: List[Callable[[str, Any, Any], None]] = []

        # 统计
        self._statistics = {
            "total_changes": 0,
            "manual_changes": 0,
            "auto_changes": 0,
            "profile_switches": 0,
            "reverts": 0
        }

        # 线程安全
        self._lock = threading.RLock()

    def _load_profile(self, profile: CognitiveProfile):
        """加载配置文件"""
        profile_config = self.DEFAULT_PROFILES.get(
            profile,
            self.DEFAULT_PROFILES[CognitiveProfile.DEFAULT]
        )

        self.reasoning = copy.deepcopy(profile_config["reasoning"])
        self.memory = copy.deepcopy(profile_config["memory"])
        self.attention = copy.deepcopy(profile_config["attention"])
        self.learning = copy.deepcopy(profile_config["learning"])
        self.personality = copy.deepcopy(profile_config["personality"])

    # ==================== 配置获取 ====================

    def get_reasoning(self) -> ReasoningConfig:
        """获取推理配置"""
        return self.reasoning

    def get_memory(self) -> MemoryConfig:
        """获取记忆配置"""
        return self.memory

    def get_attention(self) -> AttentionConfig:
        """获取注意力配置"""
        return self.attention

    def get_learning(self) -> LearningConfig:
        """获取学习配置"""
        return self.learning

    def get_personality(self) -> PersonalityConfig:
        """获取个性配置"""
        return self.personality

    def get_current_profile(self) -> CognitiveProfile:
        """获取当前配置文件"""
        return self._current_profile

    def get_state(self) -> CognitiveState:
        """获取完整状态"""
        return CognitiveState(
            timestamp=datetime.now(),
            reasoning=self.reasoning,
            memory=self.memory,
            attention=self.attention,
            learning=self.learning,
            personality=self.personality,
            active_profile=self._current_profile
        )

    # ==================== 配置修改 ====================

    def set_reasoning(self, **kwargs):
        """设置推理配置"""
        with self._lock:
            for key, value in kwargs.items():
                if hasattr(self.reasoning, key):
                    old_value = getattr(self.reasoning, key)
                    setattr(self.reasoning, key, value)
                    self._record_change(f"reasoning.{key}", old_value, value, "set")

    def set_memory(self, **kwargs):
        """设置记忆配置"""
        with self._lock:
            for key, value in kwargs.items():
                if hasattr(self.memory, key):
                    old_value = getattr(self.memory, key)
                    setattr(self.memory, key, value)
                    self._record_change(f"memory.{key}", old_value, value, "set")

    def set_attention(self, **kwargs):
        """设置注意力配置"""
        with self._lock:
            for key, value in kwargs.items():
                if hasattr(self.attention, key):
                    old_value = getattr(self.attention, key)
                    setattr(self.attention, key, value)
                    self._record_change(f"attention.{key}", old_value, value, "set")

    def set_learning(self, **kwargs):
        """设置学习配置"""
        with self._lock:
            for key, value in kwargs.items():
                if hasattr(self.learning, key):
                    old_value = getattr(self.learning, key)
                    setattr(self.learning, key, value)
                    self._record_change(f"learning.{key}", old_value, value, "set")

    def set_personality(self, **kwargs):
        """设置个性配置"""
        with self._lock:
            for key, value in kwargs.items():
                if hasattr(self.personality, key):
                    old_value = getattr(self.personality, key)
                    setattr(self.personality, key, value)
                    self._record_change(f"personality.{key}", old_value, value, "set")

    def set_by_path(self, path: str, value: Any, source: str = "manual"):
        """
        通过路径设置配置

        Args:
            path: 配置路径 (如 "reasoning.max_depth")
            value: 新值
            source: 来源
        """
        with self._lock:
            parts = path.split(".")
            if len(parts) != 2:
                return

            config_type, param_name = parts

            # 获取对应配置对象
            config_map = {
                "reasoning": self.reasoning,
                "memory": self.memory,
                "attention": self.attention,
                "learning": self.learning,
                "personality": self.personality
            }

            config = config_map.get(config_type)
            if not config or not hasattr(config, param_name):
                return

            old_value = getattr(config, param_name)
            setattr(config, param_name, value)

            # 记录变更
            self._record_change(path, old_value, value, "set", source)

            # 触发回调
            self._trigger_callbacks(path, old_value, value)

    def increase(self, path: str, delta: float):
        """增加配置值"""
        with self._lock:
            parts = path.split(".")
            if len(parts) != 2:
                return

            config_type, param_name = parts

            config_map = {
                "reasoning": self.reasoning,
                "memory": self.memory,
                "attention": self.attention,
                "learning": self.learning,
                "personality": self.personality
            }

            config = config_map.get(config_type)
            if not config or not hasattr(config, param_name):
                return

            old_value = getattr(config, param_name)
            if isinstance(old_value, (int, float)):
                new_value = old_value + delta
                setattr(config, param_name, new_value)
                self._record_change(path, old_value, new_value, "increase")
                self._trigger_callbacks(path, old_value, new_value)

    def decrease(self, path: str, delta: float):
        """减少配置值"""
        with self._lock:
            parts = path.split(".")
            if len(parts) != 2:
                return

            config_type, param_name = parts

            config_map = {
                "reasoning": self.reasoning,
                "memory": self.memory,
                "attention": self.attention,
                "learning": self.learning,
                "personality": self.personality
            }

            config = config_map.get(config_type)
            if not config or not hasattr(config, param_name):
                return

            old_value = getattr(config, param_name)
            if isinstance(old_value, (int, float)):
                new_value = old_value - delta
                setattr(config, param_name, new_value)
                self._record_change(path, old_value, new_value, "decrease")
                self._trigger_callbacks(path, old_value, new_value)

    # ==================== 配置文件切换 ====================

    def switch_profile(self, profile: CognitiveProfile):
        """
        切换配置文件

        Args:
            profile: 目标配置文件
        """
        with self._lock:
            old_profile = self._current_profile

            if profile == CognitiveProfile.ADAPTIVE:
                # 自适应模式：保持当前配置
                pass
            else:
                self._load_profile(profile)

            self._current_profile = profile
            self._statistics["profile_switches"] += 1

            # 记录变更
            self._record_change(
                "profile",
                old_profile.value,
                profile.value,
                "set",
                "profile"
            )

    def reset_to_default(self):
        """重置为默认配置"""
        with self._lock:
            self._load_profile(CognitiveProfile.DEFAULT)
            self._current_profile = CognitiveProfile.DEFAULT

    # ==================== 变更追踪 ====================

    def _record_change(
        self,
        path: str,
        old_value: Any,
        new_value: Any,
        change_type: str,
        source: str = "manual"
    ):
        """记录变更"""
        if not self.enable_change_tracking:
            return

        change_id = f"change_{self._change_counter}"
        self._change_counter += 1

        change = ConfigChange(
            id=change_id,
            timestamp=datetime.now(),
            parameter_path=path,
            old_value=old_value,
            new_value=new_value,
            change_type=change_type,
            source=source
        )

        self._change_history.append(change)

        # 更新统计
        self._statistics["total_changes"] += 1
        if source == "manual":
            self._statistics["manual_changes"] += 1
        else:
            self._statistics["auto_changes"] += 1

    def revert_change(self, change_id: str) -> bool:
        """
        回退变更

        Args:
            change_id: 变更ID

        Returns:
            是否成功
        """
        with self._lock:
            # 找到变更
            change = next(
                (c for c in self._change_history if c.id == change_id),
                None
            )

            if not change or change.reverted:
                return False

            # 回退
            self.set_by_path(change.parameter_path, change.old_value, "revert")
            change.reverted = True

            self._statistics["reverts"] += 1
            return True

    def get_change_history(
        self,
        limit: int = 50,
        path_filter: Optional[str] = None
    ) -> List[ConfigChange]:
        """
        获取变更历史

        Args:
            limit: 返回数量限制
            path_filter: 路径过滤

        Returns:
            变更列表
        """
        changes = list(self._change_history)

        if path_filter:
            changes = [c for c in changes if path_filter in c.parameter_path]

        return changes[-limit:]

    # ==================== 回调机制 ====================

    def register_callback(self, callback: Callable[[str, Any, Any], None]):
        """
        注册变更回调

        Args:
            callback: 回调函数 (path, old_value, new_value)
        """
        with self._lock:
            self._change_callbacks.append(callback)

    def _trigger_callbacks(self, path: str, old_value: Any, new_value: Any):
        """触发回调"""
        for callback in self._change_callbacks:
            try:
                callback(path, old_value, new_value)
            except Exception:
                pass

    # ==================== 持久化 ====================

    def save_to_file(self, file_path: Optional[str] = None):
        """
        保存到文件

        Args:
            file_path: 文件路径
        """
        path = file_path or self.config_file
        if not path:
            return

        with self._lock:
            state = self.get_state()
            data = {
                "profile": self._current_profile.value,
                "reasoning": vars(state.reasoning),
                "memory": vars(state.memory),
                "attention": vars(state.attention),
                "learning": vars(state.learning),
                "personality": vars(state.personality)
            }

            with open(path, "w", encoding="utf-8") as f:
                json.dump(data, f, indent=2, ensure_ascii=False)

    def load_from_file(self, file_path: Optional[str] = None) -> bool:
        """
        从文件加载

        Args:
            file_path: 文件路径

        Returns:
            是否成功
        """
        path = file_path or self.config_file
        if not path:
            return False

        try:
            with open(path, "r", encoding="utf-8") as f:
                data = json.load(f)

            # 应用配置
            if "profile" in data:
                profile = CognitiveProfile(data["profile"])
                self.switch_profile(profile)

            if "reasoning" in data:
                self.set_reasoning(**data["reasoning"])

            if "memory" in data:
                self.set_memory(**data["memory"])

            if "attention" in data:
                self.set_attention(**data["attention"])

            if "learning" in data:
                self.set_learning(**data["learning"])

            if "personality" in data:
                self.set_personality(**data["personality"])

            return True

        except Exception:
            return False

    # ==================== 自适应调整 ====================

    def adapt_from_performance(
        self,
        performance_metrics: Dict[str, float]
    ):
        """
        根据性能指标自适应调整

        Args:
            performance_metrics: 性能指标
        """
        if self._current_profile != CognitiveProfile.ADAPTIVE:
            return

        with self._lock:
            # 基于指标调整
            if "accuracy" in performance_metrics:
                acc = performance_metrics["accuracy"]
                if acc < 0.7:
                    # 准确率低：增加学习率，加强探索
                    self.increase("learning.exploration_rate", 0.1)
                    self.set_by_path("reasoning.max_depth", max(3, self.reasoning.max_depth - 1))
                elif acc > 0.95:
                    # 准确率高：减少探索，提高效率
                    self.decrease("learning.exploration_rate", 0.05)

            if "response_time" in performance_metrics:
                rt = performance_metrics["response_time"]
                if rt > 5.0:
                    # 响应慢：减少推理深度
                    self.decrease("reasoning.max_depth", 1)
                    self.set_attention(mode=AttentionMode.FOCUSED)

            if "memory_usage" in performance_metrics:
                mu = performance_metrics["memory_usage"]
                if mu > 0.9:
                    # 内存使用高：减少记忆容量
                    self.decrease("memory.episodic_limit", 100)

    # ==================== 统计和导出 ====================

    def get_statistics(self) -> Dict[str, Any]:
        """获取统计"""
        return {
            **self._statistics,
            "current_profile": self._current_profile.value,
            "total_changes_tracked": len(self._change_history)
        }

    def export_config(self) -> Dict[str, Any]:
        """导出配置"""
        state = self.get_state()
        return {
            "profile": state.active_profile.value,
            "reasoning": vars(state.reasoning),
            "memory": vars(state.memory),
            "attention": vars(state.attention),
            "learning": vars(state.learning),
            "personality": vars(state.personality)
        }

    def __repr__(self) -> str:
        return (f"CognitiveConfigManager(profile={self._current_profile.value}, "
                f"changes={self._statistics['total_changes']})")
