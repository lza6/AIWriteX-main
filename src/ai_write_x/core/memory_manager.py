# -*- coding: utf-8 -*-
import json
import math
import os
import re
import threading
from collections import Counter
from datetime import datetime, timedelta
from typing import List, Dict, Any, Optional

class MemoryManager:
    """
    V4: 长期记忆管理器 (Topic Memory System)
    负责记录最近 30 天生成过的话题指纹，防止 AI 库产生同质化内容。
    V4新增: TF-IDF语义相似度、质量反馈循环、时间衰减权重。
    """
    
    def __init__(self, memory_file="topic_memory.json"):
        self.base_dir = os.path.abspath(os.path.join(os.path.dirname(__file__), "../../../"))
        self.memory_file = os.path.join(self.base_dir, memory_file)
        self._lock = threading.RLock()
        self.memory = self._load()
        self._clean_expired()

    def _load(self):
        with self._lock:
            if os.path.exists(self.memory_file):
                try:
                    with open(self.memory_file, 'r', encoding='utf-8') as f:
                        return json.load(f)
                except Exception:
                    return {"topics": []}
            return {"topics": []}

    def _save(self):
        with self._lock:
            try:
                # V5: 原子写入，防止在写入过程中崩溃导致整个记忆库损坏
                tmp_file = self.memory_file + ".tmp"
                with open(tmp_file, 'w', encoding='utf-8') as f:
                    json.dump(self.memory, f, ensure_ascii=False, indent=2)
                os.replace(tmp_file, self.memory_file)
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
        
        self.memory["topics"] = valid_topics[-200:]
        self._save()

    def add_topic(self, topic: str, quality_score: Optional[float] = None):
        """V5: 添加话题到记忆库，支持质量反馈记录与相似度去重"""
        with self._lock:
            # V5: 去重检测 (不仅仅是完全相等，相似度过高也视为同话题更新)
            for item in self.memory["topics"]:
                if item["term"] == topic or self._tfidf_similarity(item["term"], topic) > 0.85:
                    item["timestamp"] = datetime.now().isoformat()
                    item["term"] = topic # 更新为最新的表述形式
                    if quality_score is not None:
                        item["quality_score"] = quality_score
                    self._save()
                    return

            entry = {
                "term": topic,
                "timestamp": datetime.now().isoformat()
            }
            if quality_score is not None:
                entry["quality_score"] = quality_score
            self.memory["topics"].append(entry)
            self._save()

    def add_topics_batch(self, topics: List[str]):
        """V3: 批量添加话题 — 减少I/O次数"""
        with self._lock:
            for topic in topics:
                exists = False
                for item in self.memory["topics"]:
                    if item["term"] == topic:
                        item["timestamp"] = datetime.now().isoformat()
                        exists = True
                        break
                if not exists:
                    self.memory["topics"].append({
                        "term": topic,
                        "timestamp": datetime.now().isoformat()
                    })
            self._save()

    def get_embedding_ready_data(self) -> List[Dict[str, Any]]:
        """V3: 向量相似度预留接口 — 返回标准化的(text, metadata)格式"""
        with self._lock:
            results = []
            for item in self.memory.get("topics", []):
                results.append({
                    "text": item["term"],
                    "metadata": {
                        "timestamp": item.get("timestamp", ""),
                        "quality_score": item.get("quality_score"),
                        "source": "topic_memory",
                        "type": "topic"
                    }
                })
            return results

    def get_stats(self) -> dict:
        """V5新增: 获取记忆库统计摘要"""
        with self._lock:
            topics = self.memory.get("topics", [])
            total = len(topics)
            if total == 0:
                return {"total_topics": 0, "avg_quality": 0.0, "recent_30d": 0, "scored_ratio": 0.0}
            
            recent_30d = 0
            now = datetime.now()
            quality_scores = []
            
            for item in topics:
                try:
                    ts = datetime.fromisoformat(item["timestamp"])
                    if now - ts <= timedelta(days=30):
                        recent_30d += 1
                except:
                    pass
                if "quality_score" in item and item["quality_score"] is not None:
                    quality_scores.append(item["quality_score"])
            
            avg_quality = sum(quality_scores) / len(quality_scores) if quality_scores else 0.0
            
            return {
                "total_topics": total,
                "recent_30d": recent_30d,
                "avg_quality": round(avg_quality, 2),
                "scored_ratio": round(len(quality_scores) / total * 100, 1) if total > 0 else 0
            }

    # ========== V4 新增核心算法 ==========

    @staticmethod
    def _tokenize(text: str) -> List[str]:
        """V4: 轻量级中文分词（bi-gram + 单字混合），无需 jieba 依赖"""
        chars = re.findall(r'[\u4e00-\u9fff]', text)
        tokens = []
        # 单字
        tokens.extend(chars)
        # bi-gram
        for i in range(len(chars) - 1):
            tokens.append(chars[i] + chars[i+1])
        # 英文单词
        tokens.extend(re.findall(r'[a-zA-Z]+', text.lower()))
        return tokens

    def _tfidf_similarity(self, text_a: str, text_b: str) -> float:
        """V4新增: TF-IDF 余弦相似度 — 比纯关键词匹配精度更高
        
        使用记忆库所有话题作为语料库计算 IDF，然后计算两个文本的 TF-IDF 向量余弦距离。
        """
        tokens_a = self._tokenize(text_a)
        tokens_b = self._tokenize(text_b)
        
        if not tokens_a or not tokens_b:
            return 0.0
        
        # 构建 IDF（基于记忆库中的所有话题作为背景语料）
        all_docs = [item["term"] for item in self.memory.get("topics", [])]
        all_docs.extend([text_a, text_b])  # 加入当前两个文本
        
        doc_count = len(all_docs)
        # 每个 token 出现在多少个文档中
        df = Counter()
        for doc in all_docs:
            doc_tokens = set(self._tokenize(doc))
            for t in doc_tokens:
                df[t] += 1
        
        # 计算 TF-IDF 向量
        def tfidf_vector(tokens):
            tf = Counter(tokens)
            total = len(tokens)
            vec = {}
            for t, count in tf.items():
                tf_val = count / total
                idf_val = math.log((doc_count + 1) / (df.get(t, 0) + 1)) + 1
                vec[t] = tf_val * idf_val
            return vec
        
        vec_a = tfidf_vector(tokens_a)
        vec_b = tfidf_vector(tokens_b)
        
        # 余弦相似度
        all_keys = set(vec_a.keys()) | set(vec_b.keys())
        dot_product = sum(vec_a.get(k, 0) * vec_b.get(k, 0) for k in all_keys)
        norm_a = math.sqrt(sum(v ** 2 for v in vec_a.values()))
        norm_b = math.sqrt(sum(v ** 2 for v in vec_b.values()))
        
        if norm_a == 0 or norm_b == 0:
            return 0.0
        
        return dot_product / (norm_a * norm_b)

    @staticmethod
    def _time_decay_weight(timestamp_str: str, half_life_days: float = 7.0) -> float:
        """V4新增: 时间衰减权重 — 半衰期7天，近期话题权重更高
        
        使用指数衰减: weight = 2^(-age_days/half_life)
        7天前的话题权重 = 0.5, 14天前 = 0.25, 21天前 = 0.125
        """
        try:
            ts = datetime.fromisoformat(timestamp_str)
            age_days = (datetime.now() - ts).total_seconds() / 86400
            return 2 ** (-age_days / half_life_days)
        except Exception:
            return 0.1  # 无法解析时给极低权重

    def get_similarity_context(self, topic: str) -> str:
        """V4: 基于 TF-IDF + 时间衰减 + 质量反馈 的智能话题避重
        
        - 使用 TF-IDF 余弦相似度替代简单关键词匹配
        - 近期话题通过时间衰减给予更高的避让权重
        - 历史质量分数高的话题会标注"高质量"，引导 AI 超越而非简单避让
        """
        with self._lock:
            scored_matches = []
            
            for item in self.memory.get("topics", []):
                term = item["term"]
                if term == topic:
                    continue
                
                # TF-IDF 余弦相似度
                sim = self._tfidf_similarity(topic, term)
                if sim < 0.15:  # 相似度阈值
                    continue
                
                # 时间衰减权重
                decay = self._time_decay_weight(item.get("timestamp", ""))
                
                # 综合分 = 语义相似度 × 时间衰减权重
                combined_score = sim * decay
                
                days_ago = 0
                try:
                    days_ago = (datetime.now() - datetime.fromisoformat(item["timestamp"])).days
                except:
                    pass
                
                quality = item.get("quality_score")
                scored_matches.append({
                    "term": term,
                    "similarity": round(sim, 2),
                    "combined_score": round(combined_score, 3),
                    "days_ago": days_ago,
                    "quality_score": quality
                })
            
            if not scored_matches:
                return ""
            
            # 按综合分排序，取 top 5
            scored_matches.sort(key=lambda x: x["combined_score"], reverse=True)
            top_matches = scored_matches[:5]
            
            parts = []
            for m in top_matches:
                time_str = f"{m['days_ago']}天前" if m['days_ago'] > 0 else "刚不久前"
                quality_hint = ""
                if m.get("quality_score") is not None:
                    if m["quality_score"] >= 4.0:
                        quality_hint = " ★高质量"
                    elif m["quality_score"] <= 2.5:
                        quality_hint = " ⚠低质量"
                parts.append(f"[{m['term']}] (相似度{m['similarity']}, {time_str}{quality_hint})")
            
            context = "【系统历史写入记忆 V4】：以下是你之前写过的相似话题（按相似度×时间权重排序）：\n"
            context += "、".join(parts) + "\n"
            context += "请在本次创作中避开已覆盖的角度，寻找全新的切入点。对标注★高质量的话题，尝试超越而非重复。"
            return context

    # ========== V6 新增 RAG 记忆检索 ==========
    def get_rag_context(self) -> str:
        """V6: 从本地数据库 AgentMemory 提取历史高分写作经验及排坑指南"""
        try:
            from src.ai_write_x.database import db_manager
            lessons = db_manager.get_recent_memories(agent_role="writer_lesson", limit=3)
            if not lessons:
                return ""
            
            context = "\n【V6 RAG 进化潜意识检索 (Critical Writing Lessons)】：\n回顾过去被 FinalReviewer 打回的深刻教训与重做经验，必须严格避免：\n"
            for idx, lesson in enumerate(lessons, 1):
                context += f"{idx}. {lesson.memory_text}\n"
            
            return context
        except Exception as e:
            return ""

    def save_rag_lesson(self, lesson_text: str):
        """V6: 将新的经验教训写入 RAG 记忆"""
        try:
            from src.ai_write_x.database import db_manager
            db_manager.add_memory(agent_role="writer_lesson", memory_text=lesson_text)
        except Exception as e:
            pass

