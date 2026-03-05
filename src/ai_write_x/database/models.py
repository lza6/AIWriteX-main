import datetime
import uuid
import json
from peewee import *
from src.ai_write_x.utils.path_manager import PathManager

# Database setup
data_dir = PathManager.get_app_data_dir() / "data"
data_dir.mkdir(parents=True, exist_ok=True)
db_path = data_dir / "aiwritex_v6.db"

db = SqliteDatabase(
    str(db_path),
    pragmas={
        'journal_mode': 'wal',
        'cache_size': -1 * 64000,  # 64MB cache
        'foreign_keys': 1,
        'ignore_check_constraints': 0,
        'synchronous': 0
    }
)

class JSONField(TextField):
    """Custom field for storing JSON data in SQLite"""
    def db_value(self, value):
        return json.dumps(value, ensure_ascii=False) if value is not None else None

    def python_value(self, value):
        if value is not None:
            try:
                return json.loads(value)
            except (TypeError, ValueError):
                return value
        return None

class BaseModel(Model):
    class Meta:
        database = db

class Topic(BaseModel):
    id = CharField(primary_key=True, default=lambda: str(uuid.uuid4()))
    title = CharField(unique=True, null=False)
    source_platform = CharField(default="unknown")
    hot_score = IntegerField(default=0)
    status = CharField(default="pending")  # pending, processing, completed, failed
    created_at = DateTimeField(default=datetime.datetime.now)
    updated_at = DateTimeField(default=datetime.datetime.now)

    class Meta:
        table_name = 'topics'

class Article(BaseModel):
    id = CharField(primary_key=True, default=lambda: str(uuid.uuid4()))
    topic = ForeignKeyField(Topic, backref='articles')
    content = TextField()
    format = CharField(default="HTML")
    version = IntegerField(default=1)
    human_rating = IntegerField(default=0)
    created_at = DateTimeField(default=datetime.datetime.now)

    class Meta:
        table_name = 'articles'

class AgentMemory(BaseModel):
    id = CharField(primary_key=True, default=lambda: str(uuid.uuid4()))
    agent_role = CharField()
    memory_text = TextField()
    vector_embedding = JSONField(null=True)
    created_at = DateTimeField(default=datetime.datetime.now)

    class Meta:
        table_name = 'agent_memories'

class SystemSetting(BaseModel):
    key = CharField(primary_key=True)
    value = JSONField()
    updated_at = DateTimeField(default=datetime.datetime.now)

    class Meta:
        table_name = 'system_settings'

class ScheduledTask(BaseModel):
    id = CharField(primary_key=True, default=lambda: str(uuid.uuid4()))
    topic = CharField(null=False)
    platform = CharField(default="wechat")
    execution_time = DateTimeField(null=False)
    is_recurring = BooleanField(default=False)
    interval_hours = IntegerField(default=0)
    status = CharField(default="enabled")  # enabled, disabled, running, completed, failed
    article_count = IntegerField(default=1) 
    use_ai_beautify = BooleanField(default=True)
    last_run_at = DateTimeField(null=True)
    created_at = DateTimeField(default=datetime.datetime.now)

    class Meta:
        table_name = 'scheduled_tasks'

class TaskLog(BaseModel):
    id = CharField(primary_key=True, default=lambda: str(uuid.uuid4()))
    task = ForeignKeyField(ScheduledTask, backref='logs', on_delete='CASCADE')
    status = CharField()  # success, failed, running
    message = TextField()
    article_id = CharField(null=True)
    run_time = DateTimeField(default=datetime.datetime.now)

    class Meta:
        table_name = 'task_logs'

def init_db():
    db.connect(reuse_if_open=True)
    db.create_tables([Topic, Article, AgentMemory, SystemSetting, ScheduledTask, TaskLog])
    db.close()

if __name__ == '__main__':
    init_db()
