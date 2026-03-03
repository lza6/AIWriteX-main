# -*- coding: UTF-8 -*-
"""
话题去重器 - 使用 JSON 文件持久化历史话题
防止连续多日生成相同热点话题
"""
import json
from datetime import datetime, timedelta
from pathlib import Path
from src.ai_write_x.utils.path_manager import PathManager
from src.ai_write_x.utils import log

class TopicDeduplicator:
    def __init__(self, dedup_days: int = 3):
        self.dedup_days = dedup_days
        # 将文件存放在配置目录或数据目录下
        self.data_dir = PathManager.get_app_data_dir() / "data"
        self.data_dir.mkdir(parents=True, exist_ok=True)
        self.history_file = self.data_dir / "topics_history.json"
        self.history = self._load_history()
        self._cleanup_old_records()

    def _load_history(self) -> dict:
        """加载历史记录字典 {topic_name: "YYYY-MM-DD HH:MM:SS"}"""
        if not self.history_file.exists():
            return {}
        try:
            with open(self.history_file, 'r', encoding='utf-8') as f:
                return json.load(f)
        except Exception as e:
            log.print_log(f"加载话题历史记录失败: {e}", "warning")
            return {}

    def _save_history(self):
        """保存历史记录"""
        try:
            with open(self.history_file, 'w', encoding='utf-8') as f:
                json.dump(self.history, f, ensure_ascii=False, indent=2)
        except Exception as e:
            log.print_log(f"保存话题历史记录失败: {e}", "error")

    def _cleanup_old_records(self):
        """清理超过 N 天的旧记录"""
        if not self.history:
            return
            
        cutoff_date = datetime.now() - timedelta(days=self.dedup_days)
        cleaned_history = {}
        cleaned_count = 0
        
        for topic, date_str in self.history.items():
            try:
                topic_date = datetime.strptime(date_str, "%Y-%m-%d %H:%M:%S")
                if topic_date >= cutoff_date:
                    cleaned_history[topic] = date_str
                else:
                    cleaned_count += 1
            except ValueError:
                # 忽略解析错误的过往异常数据
                pass
                
        if cleaned_count > 0:
            self.history = cleaned_history
            self._save_history()
            log.print_log(f"[TopicDeduplicator] 已自动清理 {cleaned_count} 条过期话题记录", "info")

    def is_duplicate(self, topic: str) -> bool:
        """检查话题是否已经在历史记录中"""
        # 可以升级为模糊匹配，目前先采用精准匹配
        return topic.strip() in self.history

    def add_topic(self, topic: str):
        """将话题加入历史记录"""
        topic = topic.strip()
        if topic:
            self.history[topic] = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
            self._save_history()
