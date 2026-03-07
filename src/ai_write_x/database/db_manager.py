from typing import List, Optional, Dict, Any
from datetime import datetime
from sqlmodel import select, or_
from src.ai_write_x.database import (
    init_db, engine, get_session, 
    Topic, Article, AgentMemory, SystemSetting, 
    ScheduledTask, TaskLog, VisualAsset, TopicStatus, SystemEntropy
)
from src.ai_write_x.core.exceptions import DatabaseError, RecordNotFoundError, DuplicateRecordError
from src.ai_write_x.utils import log
import json

class DBManager:
    _instance = None
    _initialized = False

    def __new__(cls):
        if cls._instance is None:
            cls._instance = super(DBManager, cls).__new__(cls)
        return cls._instance

    def __init__(self):
        if not DBManager._initialized:
            init_db()
            DBManager._initialized = True

    # --- Topic Operations ---
    def add_topic(self, title: str, source_platform: str = "unknown", hot_score: int = 0) -> Optional[Topic]:
        from sqlmodel import SQLModel
        from sqlalchemy.exc import SQLAlchemyError
        
        try:
            with get_session() as session:
                # 首先尝试查询
                statement = select(Topic).where(Topic.title == title)
                topic = session.exec(statement).first()
                if not topic:
                    try:
                        topic = Topic(
                            title=title,
                            source_platform=source_platform,
                            hot_score=hot_score,
                            status=TopicStatus.PENDING
                        )
                        session.add(topic)
                        session.commit()
                        session.refresh(topic)
                    except SQLAlchemyError:
                        # 如果提交失败（可能是并发写入），尝试再次查询
                        session.rollback()
                        topic = session.exec(statement).first()
                return topic
        except SQLAlchemyError as e:
            log.print_log(f"[DBManager] 数据库错误 - 添加主题 '{title}': {e}", "error")
            raise DatabaseError(f"添加主题失败: {title}") from e
        except Exception as e:
            log.print_log(f"[DBManager] 未知错误 - 添加主题 '{title}': {e}", "error")
            raise DatabaseError(f"添加主题失败: {title}") from e

    def get_topic(self, title: str) -> Optional[Topic]:
        try:
            with get_session() as session:
                statement = select(Topic).where(Topic.title == title)
                return session.exec(statement).first()
        except DatabaseError:
            raise
        except Exception as e:
            log.print_log(f"[DBManager] Failed to get topic: {e}", "error")
            raise DatabaseError(f"获取主题失败: {title}") from e

    def update_topic_status(self, title: str, status: str) -> bool:
        try:
            with get_session() as session:
                statement = select(Topic).where(Topic.title == title)
                topic = session.exec(statement).first()
                if topic:
                    # Map string status to Enum
                    if status.lower() == "pending": topic.status = TopicStatus.PENDING
                    elif status.lower() == "processing": topic.status = TopicStatus.PROCESSING
                    elif status.lower() in ["completed", "done"]: topic.status = TopicStatus.COMPLETED
                    elif status.lower() == "failed": topic.status = TopicStatus.FAILED
                    
                    topic.updated_at = datetime.now()
                    session.add(topic)
                    session.commit()
                    return True
                return False
        except Exception as e:
            log.print_log(f"[DBManager] Failed to update topic status: {e}", "error")
            return False

    def is_topic_processed_recently(self, title: str, days: int = 3) -> bool:
        try:
            topic = self.get_topic(title)
            if not topic:
                return False
            delta = datetime.now() - topic.created_at
            return delta.days <= days
        except Exception:
            return False

    # --- Article Operations ---
    def save_article(self, topic_title: str, content: str, fmt: str = "HTML", version: int = 1) -> Optional[Article]:
        try:
            topic = self.get_topic(topic_title)
            if not topic:
                topic = self.add_topic(topic_title)
            
            with get_session() as session:
                article = Article(
                    topic_id=topic.id,
                    content=content,
                    format=fmt,
                    version=version,
                    human_rating=None  # 显式设置默认值
                )
                session.add(article)
                session.commit()
                session.refresh(article)
                return article
        except Exception as e:
            log.print_log(f"[DBManager] Failed to save article: {e}", "error")
            return None

    # --- Memory Operations ---
    def add_memory(self, agent_role: str, memory_text: str, vector: Optional[List[float]] = None) -> Optional[AgentMemory]:
        try:
            with get_session() as session:
                memory = AgentMemory(
                    agent_role=agent_role,
                    memory_text=memory_text,
                    vector_embedding=str(vector) if vector else None
                )
                session.add(memory)
                session.commit()
                session.refresh(memory)
                return memory
        except Exception as e:
            log.print_log(f"[DBManager] Failed to save memory: {e}", "error")
            return None

    def get_recent_memories(self, agent_role: str, limit: int = 5) -> List[AgentMemory]:
        try:
            with get_session() as session:
                statement = select(AgentMemory).where(AgentMemory.agent_role == agent_role).order_by(AgentMemory.created_at.desc()).limit(limit)
                return session.exec(statement).all()
        except Exception as e:
            log.print_log(f"[DBManager] Failed to retrieve memories: {e}", "error")
            return []

    # --- System Settings ---
    def set_setting(self, key: str, value: Any) -> bool:
        try:
            val_str = json.dumps(value) if not isinstance(value, str) else value
            with get_session() as session:
                statement = select(SystemSetting).where(SystemSetting.key == key)
                setting = session.exec(statement).first()
                if setting:
                    setting.value = val_str
                    setting.updated_at = datetime.now()
                else:
                    setting = SystemSetting(key=key, value=val_str)
                session.add(setting)
                session.commit()
            return True
        except Exception as e:
            log.print_log(f"[DBManager] Failed to save setting '{key}': {e}", "error")
            return False

    def get_setting(self, key: str, default: Any = None) -> Any:
        try:
            with get_session() as session:
                statement = select(SystemSetting).where(SystemSetting.key == key)
                setting = session.exec(statement).first()
                if setting:
                    try:
                        return json.loads(setting.value)
                    except:
                        return setting.value
                return default
        except Exception:
            return default

    # --- System Stats ---
    def get_system_stats(self) -> Dict[str, Any]:
        try:
            with get_session() as session:
                from sqlmodel import func
                total_topics = session.exec(select(func.count(Topic.id))).first()
                total_articles = session.exec(select(func.count(Article.id))).first()
                total_memories = session.exec(select(func.count(AgentMemory.id))).first()
                lessons = session.exec(select(func.count(AgentMemory.id)).where(AgentMemory.agent_role == "writer_lesson")).first()
                
                return {
                    "total_topics": total_topics or 0,
                    "total_articles": total_articles or 0,
                    "total_memories": total_memories or 0,
                    "lessons_learned": lessons or 0
                }
        except Exception as e:
            log.print_log(f"[DBManager] Failed to get system stats: {e}", "warning")
            return {"total_topics": 0, "total_articles": 0, "total_memories": 0, "lessons_learned": 0}

    # --- Scheduler Operations ---
    def get_active_tasks(self) -> List[ScheduledTask]:
        try:
            now = datetime.now()
            with get_session() as session:
                statement = select(ScheduledTask).where(
                    (ScheduledTask.status == 'enabled') & 
                    (ScheduledTask.execution_time <= now)
                )
                return session.exec(statement).all()
        except Exception as e:
            log.print_log(f"[DBManager] Failed to get active tasks: {e}", "error")
            return []

    def get_all_tasks(self) -> List[ScheduledTask]:
        try:
            with get_session() as session:
                return session.exec(select(ScheduledTask).order_by(ScheduledTask.execution_time.asc())).all()
        except Exception:
            return []

    def add_scheduled_task(self, topic: str, execution_time: datetime, platform: str = "wechat", 
                           is_recurring: bool = False, interval_hours: int = 0,
                           article_count: int = 1, use_ai_beautify: bool = True) -> Optional[ScheduledTask]:
        try:
            with get_session() as session:
                task = ScheduledTask(
                    topic=topic,
                    platform=platform,
                    execution_time=execution_time,
                    is_recurring=is_recurring,
                    interval_hours=interval_hours,
                    article_count=article_count,
                    use_ai_beautify=use_ai_beautify
                )
                session.add(task)
                session.commit()
                session.refresh(task)
                return task
        except Exception as e:
            log.print_log(f"[DBManager] Failed to add scheduled task: {e}", "error")
            return None

    def update_task_status(self, task_id: str, status: str) -> bool:
        try:
            from uuid import UUID
            tid = UUID(task_id) if isinstance(task_id, str) else task_id
            with get_session() as session:
                task = session.get(ScheduledTask, tid)
                if task:
                    task.status = status
                    task.updated_at = datetime.now()
                    session.add(task)
                    session.commit()
                    return True
                return False
        except Exception:
            return False

    def log_task_execution(self, task_id: str, status: str, message: str, article_id: str = None):
        try:
            from uuid import UUID
            tid = UUID(task_id) if isinstance(task_id, str) else task_id
            with get_session() as session:
                log_entry = TaskLog(
                    task_id=tid,
                    status=status,
                    message=message,
                    article_id=article_id
                )
                session.add(log_entry)
                session.commit()
        except Exception as e:
            log.print_log(f"[DBManager] Failed to log task execution: {e}", "error")

    def get_recent_task_logs(self, limit: int = 50) -> List[TaskLog]:
        try:
            with get_session() as session:
                return session.exec(select(TaskLog).order_by(TaskLog.run_time.desc()).limit(limit)).all()
        except Exception:
            return []

    def delete_task(self, task_id: str) -> bool:
        try:
            from uuid import UUID
            tid = UUID(task_id) if isinstance(task_id, str) else task_id
            with get_session() as session:
                task = session.get(ScheduledTask, tid)
                if task:
                    session.delete(task)
                    session.commit()
                    return True
                return False
        except Exception:
            return False

    # --- Visual Asset Operations ---
    def save_visual_asset(self, article_id: str, prompt: str, image_path: str, 
                          asset_type: str = "illustration", meta_data: Dict = None) -> Optional[VisualAsset]:
        try:
            with get_session() as session:
                asset = VisualAsset(
                    article=article_id,
                    prompt=prompt,
                    image_path=image_path,
                    asset_type=asset_type,
                    meta_data_json=json.dumps(meta_data) if meta_data else None
                )
                session.add(asset)
                session.commit()
                session.refresh(asset)
                return asset
        except Exception as e:
            log.print_log(f"[DBManager] Failed to save visual asset: {e}", "error")
            return None

    def get_article_assets(self, article_id: str) -> List[VisualAsset]:
        try:
            with get_session() as session:
                return session.exec(select(VisualAsset).where(VisualAsset.article == article_id)).all()
        except Exception:
            return []

    # --- Entropy Operations ---
    def save_system_entropy(self, entropy_value: float, reasoning_load: float, active_agents: int) -> Optional[SystemEntropy]:
        try:
            with get_session() as session:
                entry = SystemEntropy(
                    entropy_value=entropy_value,
                    reasoning_load=reasoning_load,
                    active_agents=active_agents,
                    timestamp=datetime.now()
                )
                session.add(entry)
                session.commit()
                session.refresh(entry)
                return entry
        except Exception as e:
            log.print_log(f"[DBManager] Failed to persist entropy state: {e}", "warning")
            return None

db_manager = DBManager()
