# -*- coding: utf-8 -*-
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
    V7.0新增: 知识图谱联动。
    V9.0新增: 跨域知识共鸣 (Knowledge Resonance)，打破领域孤岛。
    V13.0: 迁移至 SQLite 神经记忆引擎
    """
    
    def __init__(self, memory_file="topic_memory.json"):
        from src.ai_write_x.core.knowledge_graph import get_semantic_analyzer
        self.semantic_analyzer = get_semantic_analyzer()
        self.base_dir = os.path.abspath(os.path.join(os.path.dirname(__file__), "../../../"))
        self.memory_file = os.path.join(self.base_dir, memory_file)
        self._lock = threading.RLock()

    def add_topic(self, topic: str, content: Optional[str] = None, quality_score: Optional[float] = None):
        """V13.0: 将话题写入 SQLite 神经记忆引擎，并同步生成语义哈希"""
        try:
            from src.ai_write_x.database import get_session
            from src.ai_write_x.database.models import Topic
            from sqlmodel import select, or_
            import hashlib
            
            # 生成语义哈希 (基础版：清理后的标题哈希，后续可升级为向量索引哈希)
            clean_term = re.sub(r'[^\u4e00-\u9fffA-Za-z0-9]', '', topic).lower()
            semantic_hash = hashlib.md5(clean_term.encode()).hexdigest()
            
            with get_session() as session:
                # 检查语义哈希或标题是否存在
                statement = select(Topic).where(or_(Topic.semantic_hash == semantic_hash, Topic.title == topic))
                existing = session.exec(statement).first()
                if existing:
                    existing.updated_at = datetime.now()
                    if quality_score is not None:
                        # 权重累加更新热点分
                        existing.hot_score = int(quality_score * 20)
                    session.add(existing)
                else:
                    new_topic = Topic(
                        title=topic,
                        source_platform="V13-Logic-Nexus",
                        semantic_hash=semantic_hash,
                        hot_score=int(quality_score * 20) if quality_score else 50
                    )
                    session.add(new_topic)
                session.commit()
            
            # 兼容性调用
            # V14.6: 如果有文章正文内容，优先分析正文以构建更丰富的知识图谱
            analysis_text = content if content else topic
            self.semantic_analyzer.analyze(analysis_text)
        except Exception as e:
            from src.ai_write_x.utils import log
            log.print_log(f"SQLite 记忆写入失败: {e}", "error")

    def _save_memory(self):
        """兼容测试的桩函数"""
        pass

    def get_stats(self) -> dict:
        try:
            from src.ai_write_x.database import get_session
            from src.ai_write_x.database.models import Topic
            from sqlmodel import select, func

            with get_session() as session:
                total = session.exec(select(func.count(Topic.id))).one()
                if total == 0:
                    return {"total_topics": 0, "avg_quality": 0.0, "recent_30d": 0, "scored_ratio": 0.0}

                # 最近 30 天
                now = datetime.now()
                thirty_days_ago = now - timedelta(days=30)
                recent_30d = session.exec(select(func.count(Topic.id)).where(Topic.created_at >= thirty_days_ago)).one()

                # 平均热度 (模拟质量分)
                avg_hot = session.exec(select(func.avg(Topic.hot_score))).one() or 0.0

                return {
                    "total_topics": total,
                    "recent_30d": recent_30d,
                    "avg_quality": round(avg_hot / 20.0, 2),
                    "scored_ratio": 100.0  # SQLite 版全量记录
                }
        except:
            return {"total_topics": 0, "avg_quality": 0.0, "recent_30d": 0, "scored_ratio": 0.0}

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
        """V13.0: 神经记忆检索 - 从 SQLite 获取语义相似历史"""
        try:
            from src.ai_write_x.database import get_session
            from src.ai_write_x.database.models import Topic
            from sqlmodel import select, desc
            
            with get_session() as session:
                # 获取最近 200 条作为语义语料
                statement = select(Topic).order_by(desc(Topic.created_at)).limit(200)
                db_topics = session.exec(statement).all()
                
                scored_matches = []
                for item in db_topics:
                    if item.title == topic: continue
                    
                    sim = self._tfidf_similarity(topic, item.title)
                    if sim < 0.15: continue
                    
                    age_days = (datetime.now() - item.created_at).days
                    decay = self._time_decay_weight(item.created_at.isoformat())
                    combined_score = sim * decay
                    
                    scored_matches.append({
                        "term": item.title,
                        "similarity": round(sim, 2),
                        "combined_score": round(combined_score, 3),
                        "days_ago": age_days,
                        "quality_score": item.hot_score / 20.0 if item.hot_score else None
                    })
                
                if not scored_matches:
                    return ""
                
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
            
            return context
        except Exception as e:
            from src.ai_write_x.utils import log
            log.print_log(f"Similarity context generation failed: {e}", "warning")
            return ""

    def get_resonance_context(self, topic: str) -> str:
        """V13.0: 神经共振映射 (Neural Resonance) - 从 SQLite 挖掘高维对撞素材"""
        try:
            from src.ai_write_x.database import get_session
            from src.ai_write_x.database.models import Topic
            from sqlmodel import select, desc
            import random
            
            with get_session() as session:
                # 寻找高质量 (hot_score >= 80) 且非当前话题的历史记录
                statement = select(Topic).where(Topic.hot_score >= 80).order_by(desc(Topic.created_at)).limit(50)
                candidates = session.exec(statement).all()
                
                if len(candidates) < 3:
                    return ""
                
                # 随机选取 1 个进行维度对撞
                resonance_target = random.choice(candidates)
                
                anchors = [
                    "【热力学第二定律】: 系统的熵总是增加的。尝试将话题中的‘秩序’视为低熵态，将‘混乱/争议’视为高熵释放过程。",
                    "【量子纠缠】: 寻找话题中表面无关但底层利益深度绑定的两个对立面。",
                    "【生物拟态】: 分析话题中的参与者是如何通过‘伪装’或‘模拟’主流叙事来获取生存空间的。",
                    "【控制论反馈】: 分析话题中哪些行为在强化现状，哪些在引发震荡。",
                    "【建筑结构主义】: 深挖话题现象背后的‘底层支撑结构’是否已经腐朽。"
                ]
                logic_anchor = random.choice(anchors)
                
                return (
                    "【V13.0 神经共振：维度对撞 (Neural Resonance)】：\n"
                    f"借调历史高维案例 [{resonance_target.title}] 的逻辑原子，并结合 {logic_anchor}\n"
                    "目标：粉碎陈冗的行业套路，产生具备降维打击感的原创洞见。"
                )
        except:
            return ""

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

