# -*- coding: UTF-8 -*-
"""
话题去重器 - 数据库(SQLite)版
防止连续多日生成相同热点话题，解决 JSON 文件读写锁死及高并发问题。
"""
import json
from datetime import datetime
from src.ai_write_x.utils.path_manager import PathManager
from src.ai_write_x.utils import log
from src.ai_write_x.database import db_manager, Topic

class TopicDeduplicator:
    def __init__(self, dedup_days: int = 3):
        self.dedup_days = dedup_days
        self.data_dir = PathManager.get_app_data_dir() / "data"
        self.history_file = self.data_dir / "topics_history.json"
        
        self._migrate_legacy_json()

    def _migrate_legacy_json(self):
        """将旧的 topics_history.json 完美灌入 SQLite (单次执行)"""
        if not self.history_file.exists():
            return
            
        try:
            with open(self.history_file, 'r', encoding='utf-8') as f:
                legacy_data = json.load(f)
                
            if legacy_data:
                count = 0
                for topic_title, date_str in legacy_data.items():
                    if db_manager.add_topic(title=topic_title.strip()):
                        count += 1
                log.print_log(f"成功将 {count} 条遗留 JSON 数据迁移至 SQLite", "info")
                
            # 重命名作为备份，避免未来重复读取
            backup_file = self.data_dir / "topics_history.json.bak"
            self.history_file.rename(backup_file)
        except Exception as e:
            log.print_log(f"旧数据迁移至 SQLite 失败: {e}", "warning")

    def is_duplicate(self, topic: str) -> bool:
        """检查话题是否已经在 SQLite 数据库中并处于近日"""
        topic = topic.strip()
        return db_manager.is_topic_processed_recently(topic, self.dedup_days)

    def add_topic(self, topic: str):
        """将新生成话题加入 SQLite"""
        topic = topic.strip()
        if not topic:
            return
        db_manager.add_topic(topic)

