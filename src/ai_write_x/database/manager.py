import os
from sqlmodel import SQLModel, create_engine, Session, select
from .models import Topic, Article, AgentMemory, SystemSetting
from typing import List, Optional

# Database path
DB_PATH = os.path.join("data", "ai_writex_v12.db")
DATABASE_URL = f"sqlite:///{DB_PATH}"

# Create engine
engine = create_engine(DATABASE_URL, echo=False)

def init_db():
    """Initialize the database and create tables with V13 migrations."""
    import textwrap
    os.makedirs(os.path.dirname(DB_PATH), exist_ok=True)
    SQLModel.metadata.create_all(engine)
    
    # V13.0 Database Migration logic: SQLite ALTER TABLE 
    # Because SQLModel.create_all() does not add columns to existing tables
    from sqlalchemy import text
    migrations = [
        "ALTER TABLE topics ADD COLUMN semantic_hash VARCHAR",
        "ALTER TABLE articles ADD COLUMN ai_probability FLOAT",
        "ALTER TABLE articles ADD COLUMN continuity_score FLOAT",
        "ALTER TABLE articles ADD COLUMN human_rating INTEGER",
        "ALTER TABLE agent_memories ADD COLUMN metadata_json VARCHAR"
    ]
    with engine.connect() as conn:
        for stmt in migrations:
            try:
                conn.execute(text(stmt))
                conn.commit()
            except Exception as e:
                # OperationalError or similar if column already exists
                pass

def get_session():
    """Get a new database session."""
    return Session(engine)

class DataManager:
    """High-level data management for V12.0."""
    
    @staticmethod
    def add_topic(title: str, source: str, hot_score: int = 0) -> Topic:
        with get_session() as session:
            topic = Topic(title=title, source_platform=source, hot_score=hot_score)
            session.add(topic)
            session.commit()
            session.refresh(topic)
            return topic

    @staticmethod
    def get_pending_topics() -> List[Topic]:
        with get_session() as session:
            statement = select(Topic).where(Topic.status == "待处理")
            return session.exec(statement).all()

    @staticmethod
    def save_article(topic_id, content: str, format: str = "Markdown") -> Article:
        with get_session() as session:
            article = Article(topic_id=topic_id, content=content, format=format)
            session.add(article)
            session.commit()
            session.refresh(article)
            return article
