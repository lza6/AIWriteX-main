# -*- coding: utf-8 -*-
"""
AI内容处理管道
实现评分、摘要、情感分析、关键词提取
"""

from typing import Dict, List, Any, Optional
from dataclasses import dataclass, field
from enum import Enum
import asyncio
import json

from src.ai_write_x.utils import log


class ContentScoreCategory(Enum):
    """内容评分维度"""
    TECHNICAL_DEPTH = "technical_depth"      # 技术深度
    NOVELTY = "novelty"                      # 新颖性
    IMPACT = "impact"                        # 影响力
    TIMELINESS = "timeliness"                # 时效性
    CREDIBILITY = "credibility"              # 可信度
    READABILITY = "readability"              # 可读性


class SentimentType(Enum):
    """情感类型"""
    POSITIVE = "positive"
    NEUTRAL = "neutral"
    NEGATIVE = "negative"


@dataclass
class ContentScore:
    """内容评分"""
    overall: float = 0.0                     # 综合评分 (0-10)
    categories: Dict[str, float] = field(default_factory=dict)  # 各维度评分
    ai_confidence: float = 0.0              # AI置信度
    reasoning: str = ""                     # 评分理由


@dataclass
class SentimentAnalysis:
    """情感分析结果"""
    sentiment: SentimentType = SentimentType.NEUTRAL
    score: float = 0.0                       # 情感分数 (-1 到 1)
    emotions: List[str] = field(default_factory=list)  # 检测到的情绪
    keywords: List[str] = field(default_factory=list)  # 情感关键词


@dataclass
class ProcessedContent:
    """处理后的内容"""
    id: str
    title: str
    original_content: str
    summary: str = ""                        # AI摘要
    key_points: List[str] = field(default_factory=list)  # 关键要点
    keywords: List[str] = field(default_factory=list)    # 关键词
    entities: List[str] = field(default_factory=list)    # 命名实体
    score: ContentScore = field(default_factory=ContentScore)
    sentiment: SentimentAnalysis = field(default_factory=SentimentAnalysis)
    category: str = ""                       # 自动分类
    tags: List[str] = field(default_factory=list)
    reading_time: int = 0                    # 预计阅读时间（分钟）
    language: str = "zh"                     # 语言
    metadata: Dict[str, Any] = field(default_factory=dict)


class AIContentProcessor:
    """AI内容处理器"""
    
    def __init__(self, llm_client=None):
        self.llm_client = llm_client
        self.processing_stats = {
            "total_processed": 0,
            "avg_processing_time": 0,
            "cache_hits": 0
        }
    
    async def process_content(self, content_id: str, title: str, 
                             content: str, source: str = "") -> ProcessedContent:
        """
        处理单条内容
        
        Args:
            content_id: 内容ID
            title: 标题
            content: 正文内容
            source: 来源
            
        Returns:
            处理后的内容对象
        """
        processed = ProcessedContent(
            id=content_id,
            title=title,
            original_content=content
        )
        
        try:
            # 并行执行多个AI任务
            tasks = [
                self._generate_summary(title, content),
                self._extract_keywords(title, content),
                self._analyze_sentiment(title, content),
                self._score_content(title, content),
                self._classify_content(title, content),
                self._extract_entities(title, content),
            ]
            
            results = await asyncio.gather(*tasks, return_exceptions=True)
            
            # 填充结果
            processed.summary = results[0] if not isinstance(results[0], Exception) else ""
            processed.keywords = results[1] if not isinstance(results[1], Exception) else []
            processed.sentiment = results[2] if not isinstance(results[2], Exception) else SentimentAnalysis()
            processed.score = results[3] if not isinstance(results[3], Exception) else ContentScore()
            processed.category = results[4] if not isinstance(results[4], Exception) else ""
            processed.entities = results[5] if not isinstance(results[5], Exception) else []
            
            # 计算阅读时间
            word_count = len(content)
            processed.reading_time = max(1, word_count // 400)  # 假设400字/分钟
            
            # 提取关键要点（基于摘要）
            processed.key_points = await self._extract_key_points(processed.summary or content)
            
            self.processing_stats["total_processed"] += 1
            
            log.print_log(f"[AIProcessor] 处理完成: {title[:30]}... 综合评分: {processed.score.overall}")
            
        except Exception as e:
            log.print_log(f"[AIProcessor] 处理失败: {e}", "error")
        
        return processed
    
    async def _generate_summary(self, title: str, content: str, max_length: int = 200) -> str:
        """生成AI摘要"""
        if not self.llm_client:
            # 降级方案：提取前几句
            return content[:max_length] + "..." if len(content) > max_length else content
        
        prompt = f"""请为以下文章生成一个简洁的摘要（不超过{max_length}字）：

标题：{title}

内容：
{content[:2000]}

要求：
1. 突出核心观点和关键信息
2. 使用客观、简洁的语言
3. 不要包含主观评价

摘要："""
        
        try:
            response = await self.llm_client.acomplete(prompt)
            summary = response.text if hasattr(response, 'text') else str(response)
            return summary.strip()[:max_length]
        except Exception as e:
            log.print_log(f"[AIProcessor] 摘要生成失败: {e}", "warning")
            return content[:max_length] + "..."
    
    async def _extract_keywords(self, title: str, content: str, num_keywords: int = 8) -> List[str]:
        """提取关键词"""
        # 简单的关键词提取（基于词频）
        import re
        from collections import Counter
        
        # 合并标题和内容
        text = f"{title} {content}"
        
        # 提取中文词汇（2-8个字符）
        chinese_words = re.findall(r'[\u4e00-\u9fa5]{2,8}', text)
        
        # 提取英文词汇
        english_words = re.findall(r'[a-zA-Z]{3,20}', text.lower())
        
        # 统计词频
        word_freq = Counter(chinese_words + english_words)
        
        # 停用词过滤
        stopwords = {'的', '了', '在', '是', '我', '有', '和', '就', '不', '人', '都', '一', 'the', 'and', 'for', 'are', 'but', 'not', 'you', 'all'}
        
        keywords = [
            word for word, count in word_freq.most_common(num_keywords * 2)
            if word not in stopwords and len(word) > 1
        ][:num_keywords]
        
        return keywords
    
    async def _analyze_sentiment(self, title: str, content: str) -> SentimentAnalysis:
        """分析情感"""
        # 简单的情感词典匹配
        positive_words = ['好', '棒', '优秀', '成功', '突破', '创新', '增长', '利好', '赞赏', '支持',
                         'good', 'great', 'excellent', 'amazing', 'breakthrough', 'innovation']
        negative_words = ['坏', '差', '失败', '问题', '危机', '下降', '亏损', '批评', '反对', '担忧',
                         'bad', 'terrible', 'failure', 'crisis', 'problem', 'loss', 'decline']
        
        text = (title + " " + content).lower()
        
        positive_count = sum(1 for word in positive_words if word in text)
        negative_count = sum(1 for word in negative_words if word in text)
        
        total = positive_count + negative_count
        if total == 0:
            return SentimentAnalysis(
                sentiment=SentimentType.NEUTRAL,
                score=0.0,
                emotions=["neutral"]
            )
        
        score = (positive_count - negative_count) / total
        
        if score > 0.2:
            sentiment = SentimentType.POSITIVE
            emotions = ["optimistic", "enthusiastic"] if score > 0.5 else ["positive"]
        elif score < -0.2:
            sentiment = SentimentType.NEGATIVE
            emotions = ["concerned", "worried"] if score < -0.5 else ["negative"]
        else:
            sentiment = SentimentType.NEUTRAL
            emotions = ["neutral", "objective"]
        
        return SentimentAnalysis(
            sentiment=sentiment,
            score=round(score, 2),
            emotions=emotions,
            keywords=[word for word in positive_words + negative_words if word in text][:5]
        )
    
    async def _score_content(self, title: str, content: str) -> ContentScore:
        """评分内容"""
        score = ContentScore()
        
        # 技术深度评分（基于关键词密度）
        tech_keywords = ['技术', '算法', '模型', '架构', '代码', 'API', '框架', '技术', 'algorithm', 'model', 'framework']
        tech_score = min(10, sum(1 for kw in tech_keywords if kw in content.lower()) * 1.5)
        
        # 新颖性评分（基于时效性词汇）
        novelty_keywords = ['新', '首次', '突破', '创新', '发布', '推出', 'new', 'breakthrough', 'innovation', 'launch']
        novelty_score = min(10, sum(1 for kw in novelty_keywords if kw in title.lower()) * 2 + 3)
        
        # 影响力评分（基于热度指标）
        impact_score = 6.0  # 基础分
        if 'GitHub' in title or '开源' in title:
            impact_score += 2
        if any(word in title for word in ['AI', '人工智能', '大模型', 'LLM']):
            impact_score += 1.5
        
        # 时效性评分
        timeliness_score = 8.0 if '今日' in title or '最新' in title or 'breaking' in title.lower() else 6.0
        
        # 可读性评分（基于段落长度）
        avg_para_length = len(content) / max(1, content.count('\n\n'))
        readability_score = 10 if 100 < avg_para_length < 500 else 7
        
        # 综合评分
        score.categories = {
            "technical_depth": round(tech_score, 1),
            "novelty": round(novelty_score, 1),
            "impact": round(min(10, impact_score), 1),
            "timeliness": round(timeliness_score, 1),
            "readability": round(readability_score, 1),
        }
        
        # 加权计算综合分
        weights = {
            "technical_depth": 0.25,
            "novelty": 0.20,
            "impact": 0.25,
            "timeliness": 0.15,
            "readability": 0.15,
        }
        
        score.overall = round(
            sum(score.categories[k] * weights[k] for k in weights.keys()),
            1
        )
        
        score.reasoning = f"技术深度:{score.categories['technical_depth']}, 新颖性:{score.categories['novelty']}, 影响力:{score.categories['impact']}"
        
        return score
    
    async def _classify_content(self, title: str, content: str) -> str:
        """内容分类"""
        categories = {
            "AI/人工智能": ['AI', '人工智能', '大模型', 'LLM', '深度学习', '机器学习', 'ChatGPT', 'Claude'],
            "编程开发": ['代码', '编程', '开发', '开源', 'GitHub', '框架', 'API', 'coding', 'programming'],
            "产品发布": ['发布', '推出', '上线', '新品', 'Release', 'Launch', 'Product'],
            "创业公司": ['融资', '创业', '投资', 'startup', 'funding', 'venture'],
            "技术架构": ['架构', '系统', '性能', '优化', 'Architecture', 'System'],
            "行业动态": ['行业', '市场', '趋势', '报告', 'Industry', 'Market'],
        }
        
        text = title + " " + content
        scores = {}
        
        for category, keywords in categories.items():
            score = sum(2 if kw in title else 1 for kw in keywords if kw in text)
            if score > 0:
                scores[category] = score
        
        if scores:
            return max(scores.items(), key=lambda x: x[1])[0]
        return "综合"
    
    async def _extract_entities(self, title: str, content: str) -> List[str]:
        """提取命名实体"""
        import re
        
        entities = []
        
        # 公司/产品名称（大写字母组合）
        companies = re.findall(r'[A-Z][a-zA-Z]*(?:\s+[A-Z][a-zA-Z]*)*(?:\s*(?:公司|科技|集团|实验室))?', content)
        entities.extend(companies[:5])
        
        # 人名（中文）
        chinese_names = re.findall(r'[\u4e00-\u9fa5]{2,4}(?:先生|女士|博士|教授|CEO|创始人)', content)
        entities.extend(chinese_names[:3])
        
        # 技术术语
        tech_terms = re.findall(r'[A-Z]+[a-z]*[0-9]*(?:\s*[\u4e00-\u9fa5]+)?', content)
        entities.extend([t for t in tech_terms if len(t) > 2][:5])
        
        return list(set(entities))[:10]
    
    async def _extract_key_points(self, content: str, num_points: int = 3) -> List[str]:
        """提取关键要点"""
        # 简单的要点提取（基于句子重要性）
        sentences = content.split('。')
        
        # 评分每个句子
        scored_sentences = []
        for sent in sentences:
            score = 0
            # 包含数字加分
            if any(c.isdigit() for c in sent):
                score += 2
            # 长度适中加分
            if 20 < len(sent) < 100:
                score += 1
            # 包含关键词加分
            keywords = ['关键', '重要', '核心', '主要', '突破', '创新', '结果', '结论']
            score += sum(1 for kw in keywords if kw in sent)
            
            scored_sentences.append((sent, score))
        
        # 排序并返回前N个
        scored_sentences.sort(key=lambda x: x[1], reverse=True)
        return [s[0] for s in scored_sentences[:num_points] if s[0]]
    
    async def batch_process(self, contents: List[Dict[str, str]], 
                           batch_size: int = 5) -> List[ProcessedContent]:
        """批量处理内容"""
        results = []
        
        for i in range(0, len(contents), batch_size):
            batch = contents[i:i+batch_size]
            tasks = [
                self.process_content(
                    content_id=c.get('id', str(i+idx)),
                    title=c['title'],
                    content=c['content'],
                    source=c.get('source', '')
                )
                for idx, c in enumerate(batch)
            ]
            batch_results = await asyncio.gather(*tasks)
            results.extend(batch_results)
        
        return results
    
    def get_stats(self) -> Dict[str, Any]:
        """获取处理统计"""
        return self.processing_stats.copy()
