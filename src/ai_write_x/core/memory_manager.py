# -*- coding: utf-8 -*-
import json
import os
from datetime import datetime, timedelta

class MemoryManager:
    """
    V3: 长期记忆管理器 (Topic Memory System)
    负责记录最近 30 天生成过的话题指纹，防止 AI 库产生同质化内容，并在提示词中增加避让要求。
    """
    
    def __init__(self, memory_file="topic_memory.json"):
        # 存储在项目根目录或指定目录下
        self.base_dir = os.path.abspath(os.path.join(os.path.dirname(__file__), "../../../"))
        self.memory_file = os.path.join(self.base_dir, memory_file)
        self.memory = self._load()
        self._clean_expired()

    def _load(self):
        if os.path.exists(self.memory_file):
            try:
                with open(self.memory_file, 'r', encoding='utf-8') as f:
                    return json.load(f)
            except Exception:
                return {"topics": []}
        return {"topics": []}

    def _save(self):
        try:
            with open(self.memory_file, 'w', encoding='utf-8') as f:
                json.dump(self.memory, f, ensure_ascii=False, indent=2)
        except Exception as e:
            print(f"写入记忆配置失败: {e}")

    def _clean_expired(self):
        """清理 30 天前的记忆"""
        now = datetime.now()
        valid_topics = []
        for item in self.memory.get("topics", []):
            try:
                ts = datetime.fromisoformat(item["timestamp"])
                if now - ts <= timedelta(days=30):
                    valid_topics.append(item)
            except:
                pass
        
        # 始终最多保留 200 条，防止内存爆炸
        self.memory["topics"] = valid_topics[-200:]
        self._save()

    def add_topic(self, topic: str):
        """添加话题到记忆库"""
        # 如果已经存在完全相同的，只更新时间
        for item in self.memory["topics"]:
            if item["term"] == topic:
                item["timestamp"] = datetime.now().isoformat()
                self._save()
                return

        self.memory["topics"].append({
            "term": topic,
            "timestamp": datetime.now().isoformat()
        })
        self._save()

    def get_similarity_context(self, topic: str) -> str:
        """
        根据当前 topic 提取过去相似的历史上下文。
        这里使用简单的基于公共子串/关键词匹配的轻量级检测。
        """
        import jieba
        import jieba.analyse
        
        # 提取当前话题核心词
        current_keywords = set(jieba.analyse.extract_tags(topic, topK=3))
        if not current_keywords:
            return ""

        similar_topics = []
        now = datetime.now()

        for item in self.memory.get("topics", []):
            term = item["term"]
            if term == topic:
                continue
            
            past_keywords = set(jieba.analyse.extract_tags(term, topK=3))
            # 取交集判断相似度
            intersection = current_keywords.intersection(past_keywords)
            if len(intersection) >= 1:  # 有至少一个公共核心词
                days_ago = (now - datetime.fromisoformat(item["timestamp"])).days
                time_str = f"{days_ago}天前" if days_ago > 0 else "刚不久前"
                similar_topics.append(f"[{term}] ({time_str})")

        if similar_topics:
            context = "【系统历史写入记忆】：你之前已经写过关于以下类似话题的文章，请注意在本次创作中避开它们已经覆盖的内容角度，尝试寻找全新的切入点："
            context += "、".join(similar_topics[-3:]) + "。"
            return context
        
        return ""
