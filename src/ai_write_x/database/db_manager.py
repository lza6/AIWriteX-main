from typing import List, Optional, Dict, Any
from datetime import datetime
from peewee import DoesNotExist, JOIN
from src.ai_write_x.database.models import db, init_db, Topic, Article, AgentMemory, SystemSetting, ScheduledTask, TaskLog
from src.ai_write_x.utils import log

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
        try:
            topic, created = Topic.get_or_create(
                title=title,
                defaults={
                    'source_platform': source_platform,
                    'hot_score': hot_score,
                    'status': 'pending'
                }
            )
            return topic
        except Exception as e:
            log.print_log(f"[DBManager] Failed to add topic '{title}': {e}", "error")
            return None

    def get_topic(self, title: str) -> Optional[Topic]:
        try:
            return Topic.get(Topic.title == title)
        except DoesNotExist:
            return None

    def update_topic_status(self, title: str, status: str) -> bool:
        try:
            topic = Topic.get(Topic.title == title)
            topic.status = status
            topic.updated_at = datetime.now()
            topic.save()
            return True
        except DoesNotExist:
            return False
        except Exception as e:
            log.print_log(f"[DBManager] Failed to update topic status: {e}", "error")
            return False

    def is_topic_processed_recently(self, title: str, days: int = 3) -> bool:
        try:
            topic = Topic.get_or_none(Topic.title == title)
            if not topic:
                return False
            # If created within 'days', consider it recently processed
            delta = datetime.now() - topic.created_at
            return delta.days <= days
        except Exception as e:
            return False

    # --- Article Operations ---
    def save_article(self, topic_title: str, content: str, fmt: str = "HTML", version: int = 1) -> Optional[Article]:
        try:
            topic = self.get_topic(topic_title)
            if not topic:
                topic = self.add_topic(topic_title)
            
            article = Article.create(
                topic=topic,
                content=content,
                format=fmt,
                version=version
            )
            return article
        except Exception as e:
            log.print_log(f"[DBManager] Failed to save article: {e}", "error")
            return None

    # --- Memory Operations ---
    def add_memory(self, agent_role: str, memory_text: str, vector: Optional[List[float]] = None) -> Optional[AgentMemory]:
        try:
            memory = AgentMemory.create(
                agent_role=agent_role,
                memory_text=memory_text,
                vector_embedding=vector
            )
            return memory
        except Exception as e:
            log.print_log(f"[DBManager] Failed to save memory: {e}", "error")
            return None

    def get_recent_memories(self, agent_role: str, limit: int = 5) -> List[AgentMemory]:
        try:
            return list(AgentMemory.select().where(AgentMemory.agent_role == agent_role).order_by(AgentMemory.created_at.desc()).limit(limit))
        except Exception as e:
            log.print_log(f"[DBManager] Failed to retrieve memories: {e}", "error")
            return []

    # --- System Settings ---
    def set_setting(self, key: str, value: Any) -> bool:
        try:
            setting, created = SystemSetting.get_or_create(
                key=key,
                defaults={'value': value}
            )
            if not created:
                setting.value = value
                setting.updated_at = datetime.now()
                setting.save()
            return True
        except Exception as e:
            log.print_log(f"[DBManager] Failed to save setting '{key}': {e}", "error")
            return False

    def get_setting(self, key: str, default: Any = None) -> Any:
        try:
            setting = SystemSetting.get(SystemSetting.key == key)
            return setting.value
        except DoesNotExist:
            return default
        except Exception as e:
            return default

    # --- System Stats ---
    def get_system_stats(self) -> Dict[str, Any]:
        """V6新增: 获取系统沉淀数据大盘统计"""
        try:
            return {
                "total_topics": Topic.select().count(),
                "total_articles": Article.select().count(),
                "total_memories": AgentMemory.select().count(),
                "lessons_learned": AgentMemory.select().where(AgentMemory.agent_role == "writer_lesson").count()
            }
        except Exception as e:
            log.print_log(f"[DBManager] Failed to get system stats: {e}", "warning")
            return {
                "total_topics": 0, "total_articles": 0, "total_memories": 0, "lessons_learned": 0
            }

    # --- Scheduler Operations ---
    def get_active_tasks(self) -> List[ScheduledTask]:
        """获取所有处于启用状态且到达执行时间的任务"""
        try:
            now = datetime.now()
            return list(ScheduledTask.select().where(
                (ScheduledTask.status == 'enabled') & 
                (ScheduledTask.execution_time <= now)
            ))
        except Exception as e:
            log.print_log(f"[DBManager] Failed to get active tasks: {e}", "error")
            return []

    def get_all_tasks(self) -> List[ScheduledTask]:
        try:
            return list(ScheduledTask.select().order_by(ScheduledTask.execution_time.asc()))
        except Exception as e:
            return []

    def add_scheduled_task(self, topic: str, execution_time: datetime, platform: str = "wechat", 
                           is_recurring: bool = False, interval_hours: int = 0,
                           article_count: int = 1, use_ai_beautify: bool = True) -> Optional[ScheduledTask]:
        try:
            task = ScheduledTask.create(
                topic=topic,
                platform=platform,
                execution_time=execution_time,
                is_recurring=is_recurring,
                interval_hours=interval_hours,
                article_count=article_count,
                use_ai_beautify=use_ai_beautify
            )
            return task
        except Exception as e:
            log.print_log(f"[DBManager] Failed to add scheduled task: {e}", "error")
            return None

    def update_task_status(self, task_id: str, status: str) -> bool:
        try:
            task = ScheduledTask.get(ScheduledTask.id == task_id)
            task.status = status
            task.updated_at = datetime.now()
            task.save()
            return True
        except DoesNotExist:
            return False

    def log_task_execution(self, task_id: str, status: str, message: str, article_id: str = None):
        try:
            TaskLog.create(
                task_id=task_id,
                status=status,
                message=message,
                article_id=article_id
            )
        except Exception as e:
            log.print_log(f"[DBManager] Failed to log task execution: {e}", "error")

    def get_recent_task_logs(self, limit: int = 50) -> List[TaskLog]:
        try:
            return list(TaskLog.select().order_by(TaskLog.run_time.desc()).limit(limit))
        except Exception as e:
            return []

    def delete_task(self, task_id: str) -> bool:
        try:
            task = ScheduledTask.get(ScheduledTask.id == task_id)
            task.delete_instance(recursive=True)
            return True
        except DoesNotExist:
            return False

db_manager = DBManager()
