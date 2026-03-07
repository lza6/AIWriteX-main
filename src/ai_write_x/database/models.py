from datetime import datetime
from typing import Optional, List
from uuid import UUID, uuid4
from sqlmodel import SQLModel, Field, Relationship
from enum import Enum

class TopicStatus(str, Enum):
    PENDING = "待处理"
    PROCESSING = "处理中"
    COMPLETED = "已完成"
    FAILED = "失败"

class Topic(SQLModel, table=True):
    __tablename__ = "topics"
    
    id: UUID = Field(default_factory=uuid4, primary_key=True)
    title: str = Field(index=True, nullable=False)
    source_platform: str = Field(index=True)
    hot_score: int = Field(default=0)
    status: TopicStatus = Field(default=TopicStatus.PENDING)
    
    # V13.0: 语义哈希 - 用于跨平台话题聚类与去重
    semantic_hash: Optional[str] = Field(default=None, index=True)
    
    created_at: datetime = Field(default_factory=datetime.now)
    updated_at: datetime = Field(default_factory=datetime.now)
    
    articles: List["Article"] = Relationship(back_populates="topic")

class Article(SQLModel, table=True):
    __tablename__ = "articles"
    
    id: UUID = Field(default_factory=uuid4, primary_key=True)
    topic_id: UUID = Field(foreign_key="topics.id")
    content: str = Field(nullable=False)
    format: str = Field(default="Markdown")
    version: int = Field(default=1)
    
    # V13.0: 质量指纹 - 记录反思侧写与抗AI得分
    ai_probability: Optional[float] = Field(default=None) # 越低越好
    continuity_score: Optional[float] = Field(default=None) # 越高越好
    
    human_rating: Optional[int] = Field(default=None, nullable=True)
    created_at: datetime = Field(default_factory=datetime.now)
    
    topic: Topic = Relationship(back_populates="articles")

class AgentMemory(SQLModel, table=True):
    __tablename__ = "agent_memories"
    
    id: UUID = Field(default_factory=uuid4, primary_key=True)
    agent_role: str = Field(index=True)
    memory_text: str
    vector_embedding: Optional[str] = Field(default=None)
    
    # V13.0: 神经元元数据 - 存储工具调用轨迹等
    metadata_json: Optional[str] = Field(default=None)
    
    created_at: datetime = Field(default_factory=datetime.now)

class SystemSetting(SQLModel, table=True):
    __tablename__ = "system_settings"
    
    key: str = Field(primary_key=True)
    value: str  # Store as JSON string
    updated_at: datetime = Field(default_factory=datetime.now)

class ScheduledTask(SQLModel, table=True):
    __tablename__ = "scheduled_tasks"
    
    id: UUID = Field(default_factory=uuid4, primary_key=True)
    topic: str = Field(index=True)
    platform: str = Field(default="wechat")
    execution_time: datetime
    status: str = Field(default="enabled")
    is_recurring: bool = Field(default=False)
    interval_hours: int = Field(default=0)
    article_count: int = Field(default=1)
    use_ai_beautify: bool = Field(default=True)
    created_at: datetime = Field(default_factory=datetime.now)
    updated_at: datetime = Field(default_factory=datetime.now)

    @staticmethod
    def get_by_id(task_id: str) -> Optional["ScheduledTask"]:
        from src.ai_write_x.database.db_manager import get_session
        from uuid import UUID
        try:
            tid = UUID(task_id) if isinstance(task_id, str) else task_id
            with get_session() as session:
                return session.get(ScheduledTask, tid)
        except Exception:
            return None

    def save(self):
        from src.ai_write_x.database.db_manager import get_session
        with get_session() as session:
            session.add(self)
            session.commit()
            session.refresh(self)

class TaskLog(SQLModel, table=True):
    __tablename__ = "task_logs"
    
    id: UUID = Field(default_factory=uuid4, primary_key=True)
    task_id: UUID = Field(index=True)
    status: str
    message: str
    run_time: datetime = Field(default_factory=datetime.now)
    article_id: Optional[str] = Field(default=None)

    @staticmethod
    def get_by_id(log_id: str) -> Optional["TaskLog"]:
        from src.ai_write_x.database.db_manager import get_session
        from uuid import UUID
        try:
            lid = UUID(log_id) if isinstance(log_id, str) else log_id
            with get_session() as session:
                return session.get(TaskLog, lid)
        except Exception:
            return None

class VisualAsset(SQLModel, table=True):
    __tablename__ = "visual_assets"
    
    id: UUID = Field(default_factory=uuid4, primary_key=True)
    article: str = Field(index=True)
    prompt: str
    image_path: str
    asset_type: str = Field(default="illustration")
    meta_data_json: Optional[str] = Field(default=None)
    created_at: datetime = Field(default_factory=datetime.now)

class SystemEntropy(SQLModel, table=True):
    __tablename__ = "system_entropy"
    
    id: Optional[int] = Field(default=None, primary_key=True)
    entropy_value: float
    reasoning_load: float
    active_agents: int
    timestamp: datetime = Field(default_factory=datetime.now)

class ArticleAesthetic(SQLModel, table=True):
    """V19.6: 审美评价表 - 记录用户对文章或模板的视觉反馈"""
    __tablename__ = "article_aesthetics"
    
    id: UUID = Field(default_factory=uuid4, primary_key=True)
    article_id: Optional[UUID] = Field(default=None, foreign_key="articles.id", index=True)
    article_path: Optional[str] = Field(default=None, index=True)  # 文章路径，用于检查重复投票
    template_id: Optional[str] = Field(default=None, index=True) # 也可以针对模板投票
    
    # 评价维度 (存储为 JSON 字符串)
    # 正面标签: 布局精美, 配色合理, UI/CSS 高级, 叙事流畅, 视觉呼吸感强
    # 负面标签: 结构单薄, 副标题缺失, 颜色单调, 插图畸变, 样式错乱
    positive_tags: str = Field(default="[]") 
    negative_tags: str = Field(default="[]")
    
    rating: int = Field(default=5) # 1-5 分
    comment: Optional[str] = Field(default=None)
    
    # 审美特征快照 (存储当时生成的 design_data JSON)
    design_dna: Optional[str] = Field(default=None)
    
    created_at: datetime = Field(default_factory=datetime.now)
