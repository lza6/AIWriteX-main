# -*- coding: UTF-8 -*-
"""
数据库仓储模式 (Repository Pattern)
提供数据访问的统一抽象层
"""

from .base import BaseRepository
from .topic_repo import TopicRepository
from .article_repo import ArticleRepository
from .memory_repo import MemoryRepository

__all__ = [
    "BaseRepository",
    "TopicRepository",
    "ArticleRepository",
    "MemoryRepository",
]
