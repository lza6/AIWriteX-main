# -*- coding: UTF-8 -*-
"""
话题去重器 - 数据库(SQLite)版
防止连续多日生成相同热点话题，解决 JSON 文件读写锁死及高并发问题。
"""
import json
import sqlite3
from datetime import datetime, timedelta
from pathlib import Path
from src.ai_write_x.utils.path_manager import PathManager
from src.ai_write_x.utils import log

class TopicDeduplicator:
    def __init__(self, dedup_days: int = 3):
        self.dedup_days = dedup_days
        self.data_dir = PathManager.get_app_data_dir() / "data"
        self.data_dir.mkdir(parents=True, exist_ok=True)
        
        self.db_file = self.data_dir / "aiwritex_v2.db"
        self.history_file = self.data_dir / "topics_history.json"
        
        self._init_db()
        self._migrate_legacy_json()
        self._cleanup_old_records()

    def _get_conn(self):
        """获取 SQLite 连接，开启 WAL 模式支持高并发并发写入"""
        conn = sqlite3.connect(
            str(self.db_file),
            timeout=10, 
            check_same_thread=False
        )
        conn.execute("PRAGMA journal_mode=WAL")
        return conn

    def _init_db(self):
        """初始化 V2 表结构"""
        try:
            with self._get_conn() as conn:
                conn.execute('''
                    CREATE TABLE IF NOT EXISTS topics (
                        id INTEGER PRIMARY KEY AUTOINCREMENT,
                        topic_name TEXT UNIQUE NOT NULL,
                        created_at DATETIME DEFAULT CURRENT_TIMESTAMP
                    )
                ''')
                conn.execute('CREATE INDEX IF NOT EXISTS idx_topic_name ON topics(topic_name)')
        except Exception as e:
            log.print_log(f"初始化数据库失败: {e}", "error")

    def _migrate_legacy_json(self):
        """将旧的 topics_history.json 完美灌入 SQLite (单次执行)"""
        if not self.history_file.exists():
            return
            
        try:
            with open(self.history_file, 'r', encoding='utf-8') as f:
                legacy_data = json.load(f)
                
            if legacy_data:
                with self._get_conn() as conn:
                    # 批量插入遗留数据，IGNORE 避免主键冲突
                    cursor = conn.cursor()
                    for topic, date_str in legacy_data.items():
                        try:
                            # 确保存入正确的 SQLite datetime 格式 YYYY-MM-DD HH:MM:SS
                            dt = datetime.strptime(date_str, "%Y-%m-%d %H:%M:%S")
                            cursor.execute(
                                "INSERT OR IGNORE INTO topics (topic_name, created_at) VALUES (?, ?)",
                                (topic.strip(), dt.strftime("%Y-%m-%d %H:%M:%S"))
                            )
                        except ValueError:
                            pass
                    conn.commit()
                log.print_log(f"成功将 {len(legacy_data)} 条遗留 JSON 数据迁移至 SQLite", "info")
                
            # 重命名作为备份，避免未来重复读取
            backup_file = self.data_dir / "topics_history.json.bak"
            self.history_file.rename(backup_file)
        except Exception as e:
            log.print_log(f"旧数据迁移至 SQLite 失败: {e}", "warning")

    def _cleanup_old_records(self):
        """清理超过 N 天的旧记录"""
        cutoff_date = (datetime.now() - timedelta(days=self.dedup_days)).strftime("%Y-%m-%d %H:%M:%S")
        try:
            with self._get_conn() as conn:
                cursor = conn.cursor()
                cursor.execute("DELETE FROM topics WHERE created_at < ?", (cutoff_date,))
                cleaned_count = cursor.rowcount
                conn.commit()
                
            if cleaned_count > 0:
                log.print_log(f"[TopicDeduplicator] DB已自动清理 {cleaned_count} 条过期话题记录", "info")
        except Exception as e:
            log.print_log(f"清理 SQLite 过期记录失败: {e}", "error")

    def is_duplicate(self, topic: str) -> bool:
        """检查话题是否已经在 SQLite 数据库中"""
        topic = topic.strip()
        try:
            with self._get_conn() as conn:
                cursor = conn.cursor()
                cursor.execute("SELECT 1 FROM topics WHERE topic_name = ?", (topic,))
                return cursor.fetchone() is not None
        except Exception as e:
            log.print_log(f"检查话题库重复异常: {e}", "error")
            return False

    def add_topic(self, topic: str):
        """将新生成话题加入 SQLite"""
        topic = topic.strip()
        if not topic:
            return
            
        try:
            with self._get_conn() as conn:
                cursor = conn.cursor()
                cursor.execute(
                    "INSERT OR IGNORE INTO topics (topic_name, created_at) VALUES (?, datetime('now', 'localtime'))",
                    (topic,)
                )
                conn.commit()
        except Exception as e:
            log.print_log(f"保存话题入库异常: {e}", "error")
