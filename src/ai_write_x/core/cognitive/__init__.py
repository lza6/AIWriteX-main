"""
AIWriteX V19.0 - Cognitive Architecture
认知架构模块 - 类人推理链、长期记忆、持续学习
"""

from .reasoning_chain import ReasoningChain, ReasoningStep, ReasoningType
from .long_term_memory import LongTermMemory, MemoryType, MemoryEntry
from .learning_engine import LearningEngine, LearningMode, Experience

__all__ = [
    'ReasoningChain',
    'ReasoningStep',
    'ReasoningType',
    'LongTermMemory',
    'MemoryType',
    'MemoryEntry',
    'LearningEngine',
    'LearningMode',
    'Experience'
]
