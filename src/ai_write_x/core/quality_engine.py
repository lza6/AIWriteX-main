"""
内容质量检测与优化引擎 V4
- AI检测对抗
- 原创性分析
- 语义相似度检测
- 自动优化循环
- V4: 情感极性分析、Hook/CTA评分、主题过渡检测
"""

import re
import json
import math
import asyncio
from typing import Dict, List, Any, Optional, Tuple
from dataclasses import dataclass, field
from enum import Enum
from collections import Counter
import hashlib


class QualityMetric(Enum):
    """质量指标类型"""
    ORIGINALITY = "originality"           # 原创性
    READABILITY = "readability"           # 可读性
    COHERENCE = "coherence"               # 连贯性
    VOCABULARY_RICHNESS = "vocabulary"    # 词汇丰富度
    SENTENCE_VARIETY = "sentence_variety"  # 句式多样性
    AI_LIKELIHOOD = "ai_likelihood"       # AI生成概率
    SEMANTIC_DEPTH = "semantic_depth"     # 语义深度
    EMOTIONAL_POLARITY = "emotional_polarity"  # V4: 情感极性
    HOOK_CTA = "hook_cta"                 # V4: Hook/CTA
    TOPIC_TRANSITION = "topic_transition"  # V4: 主题过渡
    DECEPTIVE_FEATURES = "deceptive_features"  # V7.0: 迷惑性特征（拟人度）
    SEO_KEYWORDS = "seo_keywords"         # V19.7: SEO关键词


@dataclass
class QualityScore:
    """质量评分结果"""
    metric: QualityMetric
    score: float  # 0-100
    details: Dict[str, Any] = field(default_factory=dict)
    suggestions: List[str] = field(default_factory=list)


@dataclass
class ContentAnalysisResult:
    """内容分析结果"""
    original_content: str
    optimized_content: str = ""
    quality_scores: Dict[str, QualityScore] = field(default_factory=dict)
    overall_score: float = 0.0
    optimization_iterations: int = 0
    improvement_percentage: float = 0.0
    ai_detection_score: float = 0.0  # AI检测概率 (越低越好)
    originality_score: float = 0.0   # 原创性分数 (越高越好)
    deceptive_score: float = 0.0     # V7.0: 迷惑性分数 (越高越能迷惑检测器)


class ContentQualityEngine:
    """内容质量检测与优化引擎"""

    # AI常用词汇模式
    AI_PATTERNS = [
        r'首先[，,].*?其次[，,]',
        r'总而言之[，,]?',
        r'综上所述[，,]?',
        r'值得一提的是[，,]?',
        r'不可否认[，,]?',
        r'毋庸置疑[，,]?',
        r'显而易见[，,]?',
        r'众所周知[，,]?',
        r'在当今社会[，,]?',
        r'随着科技的发展[，,]?',
        r'在.*?方面[，,]',
        r'从.*?角度来看[，,]?',
        r'不仅仅.*?更是',
        r'不仅.*?而且',
        r'一方面.*?另一方面',
        r'可以说[，,]?',
        r'换句话说[，,]?',
        r'换言之[，,]?',
        r'事实上[，,]?',
        r'实际上[，,]?',
        r'总的来说[，,]?',
        r'简而言之[，,]?',
        r'由此可见[，,]?',
        r'由此可见[，,]?',
        r'我们应该[，,]?',
        r'我们需要[，,]?',
        r'值得注意的是[，,]?',
        r'值得关注的是[，,]?',
        r'不难发现[，,]?',
        r'需要指出的是[，,]?',
        r'毫无疑问[，,]?',
        r'尤为重要的是[，,]?',
        r'从本质上看[，,]?',
        r'归根结底[，,]?',
        r'进一步来说[，,]?',
    ]

    # AI常用句式模板
    AI_SENTENCE_TEMPLATES = [
        "让我们来看看",
        "接下来我们将讨论",
        "下面我们来分析",
        "首先需要指出的是",
        "这一现象表明",
        "这充分说明了",
        "这在一定程度上反映了",
        "这给我们带来了启示",
    ]

    def __init__(self, config: Optional[Dict] = None):
        self.config = config or {}
        self.min_originality_threshold = self.config.get(
            "min_originality", 75.0)
        self.max_ai_likelihood_threshold = self.config.get(
            "max_ai_likelihood", 30.0)
        self.max_optimization_iterations = self.config.get("max_iterations", 5)

    def _analyze_seo_keywords(self, content: str) -> QualityScore:
        """V19.7: SEO关键词分析
        自动提取内容中的高频关键词，评估SEO友好度
        """
        import re
        from collections import Counter

        score = 60.0  # 基础分
        details = {}
        suggestions = []

        # V19.7: 停用词列表
        stop_words = set([
            '的', '了', '是', '在', '我', '有', '和', '就', '不', '人', '都', '一', '一个',
            '上', '也', '很', '到', '说', '要', '去', '你', '会', '着', '没有', '看', '好',
            '自己', '这', '那', '他', '她', '它', '们', '什么', '这个', '那个', '这些', '那些',
            '可以', '因为', '所以', '但是', '如果', '或者', '还是', '已经', '正在', '通过',
            '进行', '可能', '需要', '应该', '能够', '一下', '一些', '一种', '一样', '一定',
            '就是', '还是', '这样', '那样', '怎么', '为什么', '哪里', '哪个', '多少', '如何',
            '比如', '例如', '其实', '当然', '虽然', '然而', '因此', '于是', '接着', '然后',
            '而且', '并且', '或者', '以及', '还是', '不是', '没有', '不要', '只是', '已经',
            '时候', '地方', '东西', '事情', '问题', '原因', '结果', '办法', '方面', '情况',
        ])

        # V19.7: 高价值关键词模式
        high_value_patterns = [
            r'[一-龥]{2,8}(?:技术|方法|技巧|攻略|教程|指南|秘籍|方案|策略)',
            r'[一-龥]{2,8}(?:问题|解决|优化|提升|改进|突破)',
            r'[一-龥]{2,8}(?:分析|研究|报告|数据|趋势)',
            r'[一-龥]{2,8}(?:推荐|排行|盘点|测评|对比)',
            r'[一-龥]{2,8}(?:赚钱|创业|投资|理财|副业)',
            r'[一-龥]{2,8}(?:健康|养生|减肥|健身|美容)',
            r'[一-龥]{2,8}(?:职场|工作|面试|简历|升职)',
            r'[一-龥]{2,8}(?:学习|教育|考试|培训|技能)',
        ]

        # 提取中文词汇 (简易分词)
        chinese_words = re.findall(r'[一-龥]{2,6}', content)

        # 过滤停用词
        filtered_words = [
            w for w in chinese_words if w not in stop_words and len(w) >= 2]

        # 统计词频
        word_freq = Counter(filtered_words)

        # 提取高频词 (出现2次以上)
        high_freq_words = [(word, count) for word,
                           count in word_freq.most_common(20) if count >= 2]

        # 提取高价值关键词
        high_value_keywords = []
        for pattern in high_value_patterns:
            matches = re.findall(pattern, content)
            high_value_keywords.extend(matches)

        # 去重
        high_value_keywords = list(set(high_value_keywords))

        # 计算得分
        if high_freq_words:
            score += min(len(high_freq_words) * 2, 20)
            details["high_freq_keywords"] = high_freq_words[:10]
            details["keyword_count"] = len(high_freq_words)
        else:
            suggestions.append("建议：内容中缺少重复出现的核心关键词")

        if high_value_keywords:
            score += min(len(high_value_keywords) * 3, 15)
            details["high_value_keywords"] = high_value_keywords[:10]

        # V19.7: 检查关键词密度
        total_words = len(chinese_words)
        if total_words > 0:
            keyword_density = sum(
                count for _, count in high_freq_words) / total_words * 100
            if 2 <= keyword_density <= 8:
                score += 5
                details["keyword_density_good"] = True
            elif keyword_density > 8:
                suggestions.append("注意：关键词密度较高，可能影响阅读体验")

        # V19.7: 提取建议的SEO关键词
        all_keywords = set()
        for word, _ in high_freq_words[:5]:
            all_keywords.add(word)
        all_keywords.update(high_value_keywords[:5])

        if all_keywords:
            details["suggested_keywords"] = list(all_keywords)[:8]
            details["seo_score"] = score

        # V19.7: 生成长尾关键词建议
        if high_freq_words:
            long_tail = []
            for word, count in high_freq_words[:3]:
                long_tail.append(f"{word}怎么做")
                long_tail.append(f"{word}方法")
                long_tail.append(f"如何{word}")
            details["long_tail_suggestions"] = long_tail[:6]

        score = min(100, score)
        return QualityScore(
            metric=QualityMetric.SEO_KEYWORDS,
            score=score,
            details=details,
            suggestions=suggestions
        )

    def analyze_content(self, content: str) -> ContentAnalysisResult:
        """V4: 分析内容质量（新增情感极性+Hook/CTA+主题过渡三大维度）"""
        result = ContentAnalysisResult(original_content=content)

        # 执行各项质量检测
        result.quality_scores["originality"] = self._analyze_originality(
            content)
        result.quality_scores["readability"] = self._analyze_readability(
            content)
        result.quality_scores["coherence"] = self._analyze_coherence(content)
        result.quality_scores["vocabulary"] = self._analyze_vocabulary_richness(
            content)
        result.quality_scores["sentence_variety"] = self._analyze_sentence_variety(
            content)
        result.quality_scores["ai_likelihood"] = self._analyze_ai_likelihood(
            content)
        result.quality_scores["semantic_depth"] = self._analyze_semantic_depth(
            content)

        # V4: 新增三大分析维度
        result.quality_scores["emotional_polarity"] = self._analyze_emotional_polarity(
            content)
        result.quality_scores["hook_cta"] = self._analyze_hook_and_cta(content)
        result.quality_scores["topic_transition"] = self._analyze_topic_transition(
            content)
        result.quality_scores["deceptive_features"] = self._analyze_deceptive_features(
            content)
        result.quality_scores["seo_keywords"] = self._analyze_seo_keywords(
            content)  # V19.7 # V7.0

        # 计算综合分数
        result.overall_score = self._calculate_overall_score(
            result.quality_scores)
        result.ai_detection_score = result.quality_scores["ai_likelihood"].score
        result.originality_score = result.quality_scores["originality"].score
        # V7.0
        result.deceptive_score = result.quality_scores["deceptive_features"].score

        # V3: 新增统计学指标（作为额外补充信息，不影响主评分）
        v3_entropy = self._calculate_entropy(content)
        v3_ngram = self._detect_ngram_repetition(content)
        v3_reading_time = self.estimate_reading_time(content)
        v3_perplexity = self._estimate_perplexity_proxy(content)

        # 将V3指标注入到各相关维度的details中
        if "ai_likelihood" in result.quality_scores:
            result.quality_scores["ai_likelihood"].details["v3_entropy"] = v3_entropy
            result.quality_scores["ai_likelihood"].details["v3_ngram_repetition"] = v3_ngram
            result.quality_scores["ai_likelihood"].details["v3_perplexity_proxy"] = v3_perplexity
            if v3_entropy < 3.5:
                result.quality_scores["ai_likelihood"].score = min(
                    100, result.quality_scores["ai_likelihood"].score + 8)
                result.quality_scores["ai_likelihood"].suggestions.append(
                    "V3信息熵过低，内容可能存在大量重复模式")
            if v3_ngram.get("3gram_repeat_ratio", 0) > 0.15:
                result.quality_scores["ai_likelihood"].score = min(
                    100, result.quality_scores["ai_likelihood"].score + 6)
                result.quality_scores["ai_likelihood"].suggestions.append(
                    "V3 N-gram检测到高频短语重复，建AI特征明显")
        if "readability" in result.quality_scores:
            result.quality_scores["readability"].details["v3_reading_time"] = v3_reading_time

        # 重新计算综合分（因为AI分数可能已被调整）
        result.overall_score = self._calculate_overall_score(
            result.quality_scores)
        result.ai_detection_score = result.quality_scores["ai_likelihood"].score

        return result

    def _analyze_originality(self, content: str) -> QualityScore:
        """分析原创性"""
        score = 100.0
        details = {}
        suggestions = []

        # 1. 检查重复短语
        phrases = self._extract_phrases(content, min_length=3)
        phrase_counts = Counter(phrases)
        repeated_phrases = {p: c for p, c in phrase_counts.items() if c > 2}

        if repeated_phrases:
            phrase_penalty = min(len(repeated_phrases) * 3, 20)
            score -= phrase_penalty
            details["repeated_phrases"] = list(repeated_phrases.keys())[:5]
            suggestions.append("减少重复使用的短语")

        # 2. 检查陈词滥调
        cliche_patterns = [
            "与时俱进", "开拓创新", "砥砺前行", "不忘初心",
            "牢记使命", "奋发有为", "攻坚克难", "勇攀高峰",
        ]
        cliche_count = sum(1 for c in cliche_patterns if c in content)
        if cliche_count > 0:
            score -= cliche_count * 5
            details["cliche_count"] = cliche_count
            suggestions.append("避免使用陈词滥调，使用更个性化的表达")

        # 3. 检查独特表达
        unique_words = set(content)
        total_chars = len(content.replace(" ", "").replace("\n", ""))
        if total_chars > 0:
            uniqueness_ratio = len(unique_words) / total_chars
            details["uniqueness_ratio"] = round(uniqueness_ratio, 3)
            if uniqueness_ratio < 0.3:
                score -= 15
                suggestions.append("增加词汇多样性，避免重复用词")

        # 4. 检查个性化表达
        personal_patterns = [
            r'我认为[，,]?',
            r'我觉得[，,]?',
            r'在我看来[，,]?',
            r'个人认为[，,]?',
            r'笔者的观点是',
        ]
        personal_count = sum(
            1 for p in personal_patterns if re.search(p, content))
        if personal_count > 0:
            score += min(personal_count * 2, 10)  # 奖励个性化表达
            details["personal_expression_count"] = personal_count

        score = max(0, min(100, score))

        return QualityScore(
            metric=QualityMetric.ORIGINALITY,
            score=score,
            details=details,
            suggestions=suggestions
        )

    def _analyze_readability(self, content: str) -> QualityScore:
        """分析可读性"""
        score = 100.0
        details = {}
        suggestions = []

        # 1. 句子长度分析
        sentences = re.split(r'[。！？\n]', content)
        sentences = [s.strip() for s in sentences if s.strip()]

        if sentences:
            avg_sentence_length = sum(len(s)
                                      for s in sentences) / len(sentences)
            details["avg_sentence_length"] = round(avg_sentence_length, 1)

            # 最佳句子长度调整: 适应长文和深度分析
            if avg_sentence_length > 100:
                score -= 15
                suggestions.append("句子平均长度过长，建议拆分为更短的句子增加呼吸感")
            elif avg_sentence_length < 10:
                score -= 10
                suggestions.append("句子过短，可以适当丰富内容")

            # 检查超长句子 (放宽到 150 适应 Markdown 加粗及长链接)
            long_sentences = [s for s in sentences if len(s) > 150]
            if long_sentences:
                details["long_sentences_count"] = len(long_sentences)
                score -= len(long_sentences) * 3
                suggestions.append(f"有{len(long_sentences)}个超长句子需要拆分")

        # 2. 段落分析
        paragraphs = [p.strip() for p in content.split('\n\n') if p.strip()]
        if paragraphs:
            avg_para_length = sum(len(p) for p in paragraphs) / len(paragraphs)
            details["avg_paragraph_length"] = round(avg_para_length, 1)
            details["paragraph_count"] = len(paragraphs)

            if avg_para_length > 500:
                score -= 10
                suggestions.append("段落过长，建议分段以提高可读性")

        # 3. 标点符号使用
        punctuation_count = len(re.findall(r'[，。！？、；：""''（）【】]', content))
        char_count = len(content.replace(" ", "").replace("\n", ""))
        if char_count > 0:
            punctuation_ratio = punctuation_count / char_count
            details["punctuation_ratio"] = round(punctuation_ratio, 3)

            if punctuation_ratio < 0.02:
                score -= 10
                suggestions.append("标点符号使用较少，影响阅读体验")

        score = max(0, min(100, score))

        return QualityScore(
            metric=QualityMetric.READABILITY,
            score=score,
            details=details,
            suggestions=suggestions
        )

    def _analyze_coherence(self, content: str) -> QualityScore:
        """分析连贯性"""
        score = 100.0
        details = {}
        suggestions = []

        # 1. 连接词分析
        transition_words = [
            "因此", "所以", "但是", "然而", "不过", "而且", "并且",
            "此外", "另外", "同时", "首先", "其次", "最后", "然后",
            "接着", "于是", "从而", "进而", "甚至", "尤其", "特别是",
        ]

        transition_count = sum(1 for t in transition_words if t in content)
        details["transition_word_count"] = transition_count

        # 适当的连接词数量
        char_count = len(content.replace(" ", "").replace("\n", ""))
        if char_count > 0:
            ideal_transition_ratio = 0.005  # 每200字约1个连接词
            actual_ratio = transition_count / char_count

            if actual_ratio < ideal_transition_ratio * 0.5:
                score -= 15
                suggestions.append("增加适当的过渡词，提高文章连贯性")
            elif actual_ratio > ideal_transition_ratio * 3:
                score -= 10
                suggestions.append("过渡词使用过多，可能显得生硬")

        # 2. 逻辑结构分析
        structure_patterns = [
            (r'首先[，,].*?其次[，,].*?最后', "顺序结构"),
            (r'一方面[，,].*?另一方面', "对比结构"),
            (r'因为.*?所以', "因果结构"),
            (r'虽然.*?但是', "转折结构"),
        ]

        found_structures = []
        for pattern, name in structure_patterns:
            if re.search(pattern, content, re.DOTALL):
                found_structures.append(name)

        details["logical_structures"] = found_structures
        if len(found_structures) >= 2:
            score += 5  # 奖励多种逻辑结构

        # 3. 主题一致性检查（简化版）
        sentences = re.split(r'[。！？\n]', content)
        sentences = [s.strip() for s in sentences if s.strip()]

        if len(sentences) > 3:
            # 检查首尾呼应
            first_sentence_keywords = set(sentences[0])
            last_sentence_keywords = set(sentences[-1])
            overlap = len(first_sentence_keywords & last_sentence_keywords)

            if overlap > 5:
                score += 5
                details["theme_consistency"] = True

        score = max(0, min(100, score))

        return QualityScore(
            metric=QualityMetric.COHERENCE,
            score=score,
            details=details,
            suggestions=suggestions
        )

    def _analyze_vocabulary_richness(self, content: str) -> QualityScore:
        """分析词汇丰富度"""
        score = 100.0
        details = {}
        suggestions = []

        # 提取所有词汇
        words = re.findall(r'[\u4e00-\u9fff]+', content)
        all_chars = ''.join(words)

        if all_chars:
            # 1. 词汇多样性
            unique_chars = set(all_chars)
            ttr = len(unique_chars) / len(all_chars) if all_chars else 0
            details["type_token_ratio"] = round(ttr, 3)

            if ttr < 0.3:
                score -= 20
                suggestions.append("词汇多样性较低，尝试使用更丰富的词汇")
            elif ttr > 0.6:
                score += 5

            # 2. 高级词汇使用
            advanced_chars = set(
                "缜密 渊博 璀璨 斑斓 恢弘 磅礴 深邃 精湛 卓越 非凡".replace(" ", ""))
            advanced_count = sum(1 for c in all_chars if c in advanced_chars)
            details["advanced_char_count"] = advanced_count

            # 3. 成语使用
            idiom_pattern = r'[\u4e00-\u9fff]{4}'
            potential_idioms = re.findall(idiom_pattern, content)
            # 这里可以接入成语词典进行更精确的检测
            details["potential_idiom_count"] = len(potential_idioms)

            # 4. 形容词和副词多样性
            modifier_patterns = [
                r'非常[\u4e00-\u9fff]{1,2}',
                r'十分[\u4e00-\u9fff]{1,2}',
                r'极其[\u4e00-\u9fff]{1,2}',
                r'相当[\u4e00-\u9fff]{1,2}',
            ]
            modifier_count = sum(len(re.findall(p, content))
                                 for p in modifier_patterns)
            if modifier_count > 5:
                score -= 5
                suggestions.append("避免过多使用'非常'、'十分'等常见修饰词")

        score = max(0, min(100, score))

        return QualityScore(
            metric=QualityMetric.VOCABULARY_RICHNESS,
            score=score,
            details=details,
            suggestions=suggestions
        )

    def _analyze_sentence_variety(self, content: str) -> QualityScore:
        """分析句式多样性"""
        score = 100.0
        details = {}
        suggestions = []

        sentences = re.split(r'[。！？]', content)
        sentences = [s.strip() for s in sentences if s.strip()]

        if not sentences:
            return QualityScore(
                metric=QualityMetric.SENTENCE_VARIETY,
                score=50.0,
                details={"error": "无法分析"},
                suggestions=[]
            )

        # 1. 句子长度分布
        lengths = [len(s) for s in sentences]
        avg_length = sum(lengths) / len(lengths)
        variance = sum((l - avg_length) ** 2 for l in lengths) / len(lengths)
        std_dev = math.sqrt(variance)

        details["avg_length"] = round(avg_length, 1)
        details["length_std_dev"] = round(std_dev, 1)

        # 标准差越大，句式越多样
        if std_dev < 5:
            score -= 15
            suggestions.append("句子长度过于单一，增加长短句搭配")
        elif std_dev > 15:
            score += 5

        # 2. 句式类型分析
        sentence_types = {
            "陈述句": 0,
            "疑问句": 0,
            "感叹句": 0,
            "祈使句": 0,
        }

        for s in sentences:
            if s.endswith('？') or s.endswith('?'):
                sentence_types["疑问句"] += 1
            elif s.endswith('！') or s.endswith('!'):
                sentence_types["感叹句"] += 1
            elif any(s.startswith(w) for w in ["请", "让", "要", "应该", "必须"]):
                sentence_types["祈使句"] += 1
            else:
                sentence_types["陈述句"] += 1

        details["sentence_types"] = sentence_types

        # 句式多样性奖励
        used_types = sum(1 for v in sentence_types.values() if v > 0)
        if used_types >= 3:
            score += 5
        elif used_types == 1:
            score -= 10
            suggestions.append("尝试使用疑问句、感叹句等多种句式")

        # 3. 开头词多样性
        starters = [s[:2] if len(s) >= 2 else s for s in sentences]
        unique_starters = len(set(starters))
        starter_diversity = unique_starters / \
            len(sentences) if sentences else 0

        details["starter_diversity"] = round(starter_diversity, 2)

        if starter_diversity < 0.3:
            score -= 10
            suggestions.append("句子开头过于相似，增加开头词的多样性")

        score = max(0, min(100, score))

        return QualityScore(
            metric=QualityMetric.SENTENCE_VARIETY,
            score=score,
            details=details,
            suggestions=suggestions
        )

    def _analyze_ai_likelihood(self, content: str) -> QualityScore:
        """分析AI生成概率"""
        score = 0.0  # AI概率，越低越好
        details = {}
        suggestions = []

        # 1. 检查AI模式
        ai_pattern_matches = []
        for pattern in self.AI_PATTERNS:
            matches = re.findall(pattern, content)
            if matches:
                ai_pattern_matches.extend(matches)

        details["ai_pattern_matches"] = ai_pattern_matches[:10]
        pattern_score = min(len(ai_pattern_matches) * 5, 40)
        score += pattern_score

        if ai_pattern_matches:
            suggestions.append("检测到AI常用表达模式，建议改用更自然的表达")

        # 2. 检查AI句式模板
        template_matches = []
        for template in self.AI_SENTENCE_TEMPLATES:
            if template in content:
                template_matches.append(template)

        details["template_matches"] = template_matches
        score += min(len(template_matches) * 8, 30)

        if template_matches:
            suggestions.append("避免使用AI常用的句式模板")

        # 3. 结构规律性检查
        sentences = re.split(r'[。！？\n]', content)
        sentences = [s.strip() for s in sentences if s.strip()]

        if len(sentences) > 5:
            # 检查句子长度是否过于规律
            lengths = [len(s) for s in sentences]
            avg_length = sum(lengths) / len(lengths)
            variance = sum((l - avg_length) **
                           2 for l in lengths) / len(lengths)

            # AI生成的文本通常方差较小
            if variance < 50:
                score += 10
                details["regular_structure"] = True
                suggestions.append("文章结构过于规律，增加自然变化")

        # 4. 段落长度方差分析（AI段落长度高度一致）
        paragraphs = [p.strip() for p in content.split(
            '\n\n') if p.strip() and not p.strip().startswith('#')]
        if len(paragraphs) >= 3:
            para_lengths = [len(p) for p in paragraphs]
            avg_para_len = sum(para_lengths) / len(para_lengths)
            para_variance = sum((l - avg_para_len) **
                                2 for l in para_lengths) / len(para_lengths)
            details["paragraph_length_variance"] = round(para_variance, 1)
            # 方差小于800说明段落长度高度一致，典型AI特征
            if para_variance < 800:
                score += 8
                suggestions.append("段落长度过于均匀，建议长短段落交替使用")

        # 5. (V5新增) 段首词多样性检测: AI常常用类似的过渡词开头
        if len(paragraphs) >= 4:
            starters = [p[:2] for p in paragraphs if len(p) >= 2]
            if starters:
                unique_starters = len(set(starters))
                starter_diversity = unique_starters / len(starters)
                details["paragraph_starter_diversity"] = round(
                    starter_diversity, 2)

                # AI段首经常雷同，比如总是"首先"、"此外"、"总之"
                if starter_diversity < 0.4:
                    score += 15
                    suggestions.append("检测到段落开头词汇高度雷同，这是典型的AI特征，建议增加句式变化")

        # 5. 情感词汇检查
        emotion_words = [
            "惊讶", "兴奋", "失望", "愤怒", "恐惧", "悲伤", "快乐",
            "开心", "难过", "生气", "害怕", "期待", "焦虑", "满足",
        ]
        emotion_count = sum(1 for w in emotion_words if w in content)

        # AI生成的文本通常情感词汇较少
        if emotion_count == 0:
            score += 5
            details["emotion_word_count"] = 0
            suggestions.append("可以添加更多情感化表达，使文章更有人情味")
        else:
            details["emotion_word_count"] = emotion_count
            score -= min(emotion_count * 2, 10)  # 有情感词汇降低AI概率

        # 7. 个人经历和具体细节
        personal_patterns = [
            r'我曾经[，,]?',
            r'我朋友[，,]?',
            r'有一次[，,]?',
            r'记得那[天年]',
            r'去年[，,]?',
            r'上个月[，,]?',
        ]
        personal_count = sum(
            1 for p in personal_patterns if re.search(p, content))

        if personal_count > 0:
            score -= min(personal_count * 5, 15)  # 有个人经历降低AI概率
            details["personal_experience_count"] = personal_count

        score = max(0, min(100, score))

        return QualityScore(
            metric=QualityMetric.AI_LIKELIHOOD,
            score=score,
            details=details,
            suggestions=suggestions
        )

    def _analyze_semantic_depth(self, content: str) -> QualityScore:
        """分析语义深度"""
        score = 100.0
        details = {}
        suggestions = []

        # 1. 主题句识别
        sentences = re.split(r'[。！？\n]', content)
        sentences = [s.strip() for s in sentences if s.strip()]

        # 检查是否有明确的观点
        opinion_patterns = [
            r'我认为',
            r'在我看来',
            r'我的观点是',
            r'毫无疑问',
            r'可以肯定的是',
        ]
        has_opinion = any(re.search(p, content) for p in opinion_patterns)
        details["has_clear_opinion"] = has_opinion

        if not has_opinion:
            score -= 10
            suggestions.append("添加明确的个人观点，增强文章深度")

        # 2. 论证深度
        evidence_patterns = [
            r'例如[，,]?',
            r'比如[，,]?',
            r'以.*?为例',
            r'根据.*?显示',
            r'研究(表明|发现)',
            r'数据(显示|表明)',
        ]
        evidence_count = sum(
            1 for p in evidence_patterns if re.search(p, content))
        details["evidence_count"] = evidence_count

        if evidence_count >= 2:
            score += 5
        elif evidence_count == 0:
            score -= 10
            suggestions.append("添加具体例子或数据支撑观点")

        # 3. 思考深度词汇
        deep_thinking_words = [
            "本质", "根本", "核心", "关键", "深层次", "内在",
            "意味着", "反映出", "揭示了", "启示", "引发思考",
        ]
        deep_count = sum(1 for w in deep_thinking_words if w in content)
        details["deep_thinking_word_count"] = deep_count

        if deep_count >= 3:
            score += 5
        elif deep_count == 0:
            score -= 5
            suggestions.append("可以使用更深层次的思考词汇")

        score = max(0, min(100, score))

        return QualityScore(
            metric=QualityMetric.SEMANTIC_DEPTH,
            score=score,
            details=details,
            suggestions=suggestions
        )

    def _extract_phrases(self, content: str, min_length: int = 3) -> List[str]:
        """提取短语"""
        # 提取中文短语
        words = re.findall(r'[\u4e00-\u9fff]+', content)
        phrases = []

        for i in range(len(words) - min_length + 1):
            phrase = ''.join(words[i:i + min_length])
            if len(phrase) >= min_length * 2:  # 至少min_length个汉字
                phrases.append(phrase)

        return phrases

    def _calculate_entropy(self, content: str) -> float:
        """V3新增：基于Shannon字符级信息熵，衡量内容信息密度。低熵(<3.5)暗示重复/AI模式"""
        text = re.sub(r'\s+', '', content)  # 移除空白
        if not text:
            return 0.0

        freq = Counter(text)
        total = len(text)
        entropy = -sum((count / total) * math.log2(count / total)
                       for count in freq.values())
        return round(entropy, 3)

    def _detect_ngram_repetition(self, content: str, ns=(3, 5)) -> Dict[str, Any]:
        """V3新增：N-gram重复检测，检测AI生成常见的短语重复"""
        text = re.sub(r'[\s\n\r，。！？、；：\"\"\'\'\[\]\(\)\{\}《》]+', '', content)
        result = {}

        for n in ns:
            if len(text) < n:
                result[f"{n}gram_repeat_ratio"] = 0.0
                continue

            ngrams = [text[i:i+n] for i in range(len(text) - n + 1)]
            total = len(ngrams)
            freq = Counter(ngrams)
            # 重复率 = 出现>1次的n-gram数 / 总数
            repeated = sum(1 for count in freq.values() if count > 1)
            ratio = repeated / len(freq) if freq else 0
            result[f"{n}gram_repeat_ratio"] = round(ratio, 3)
            result[f"{n}gram_top_repeats"] = [
                ng for ng, c in freq.most_common(5) if c > 1]

        return result

    @staticmethod
    def estimate_reading_time(content: str) -> str:
        """V3新增：阅读时间预估，中文按500字/分钟计算"""
        # 统计中文字符数
        chinese_chars = len(re.findall(r'[\u4e00-\u9fff]', content))
        # 统计英文单词数
        english_words = len(re.findall(r'[a-zA-Z]+', content))
        # 中文500字/分、英文250词/分
        total_minutes = chinese_chars / 500 + english_words / 250

        if total_minutes < 1:
            return "不到1分钟"
        elif total_minutes < 60:
            return f"约{int(total_minutes)}分钟"
        else:
            hours = int(total_minutes // 60)
            mins = int(total_minutes % 60)
            return f"约{hours}小时{mins}分钟"

    def _estimate_perplexity_proxy(self, content: str) -> float:
        """V3新增：困惑度近似评分 — 基于词频分布的Zipf定律偏差计算，模拟困惑度指标"""
        text = re.sub(r'\s+', '', content)
        if len(text) < 50:
            return 0.0

        # 取双字符为最小单元(模拟中文词汇)
        bigrams = [text[i:i+2] for i in range(len(text) - 1)]
        freq = Counter(bigrams)

        if not freq:
            return 0.0

        # Zipf定律检验：排名 * 频率 ≈ 常数
        sorted_freqs = sorted(freq.values(), reverse=True)
        total = sum(sorted_freqs)

        # 计算Zipf偏差：理想情况下 rank*freq 应接近常数
        zipf_products = [(i + 1) * (f / total)
                         for i, f in enumerate(sorted_freqs[:20])]
        if len(zipf_products) < 2:
            return 0.0

        avg_product = sum(zipf_products) / len(zipf_products)
        variance = sum((p - avg_product) **
                       2 for p in zipf_products) / len(zipf_products)

        # 偏差越小越符合Zipf定律(自然语言)，偏差大可能是AI生成
        # 返回 0~1 的归一化分数，>0.5表示可疑
        score = min(math.sqrt(variance) * 10, 1.0)
        return round(score, 3)

    # ========== V4 新增分析维度 ==========

    def _analyze_emotional_polarity(self, content: str) -> QualityScore:
        """V4新增：情感极性分布分析 — 检测正/中/负情感的分布是否自然

        AI文本的情感往往过于单一（纯正面或纯中性），真人写作的情感更丰富多变。
        """
        score = 100.0
        details = {}
        suggestions = []

        # 正面情感词
        positive_words = [
            '优秀', '出色', '卓越', '精彩', '突破', '成功', '领先', '创新',
            '高效', '便捷', '优质', '杰出', '惊人', '可喜', '振奋', '喜人',
            '蓬勃', '强劲', '显著', '巨大', '重大', '深远', '积极', '良好',
        ]
        # 负面情感词
        negative_words = [
            '失败', '困难', '问题', '危机', '风险', '挑战', '隐患', '不足',
            '缺陷', '遗憾', '担忧', '质疑', '争议', '困境', '压力', '矛盾',
            '滞后', '下滑', '恶化', '严峻', '低迷', '萎缩', '糟糕', '混乱',
        ]
        # 中性/客观词
        neutral_words = [
            '表示', '认为', '指出', '分析', '显示', '报告', '数据', '研究',
            '调查', '统计', '观察', '记录', '描述', '评估', '比较', '趋势',
        ]

        pos_count = sum(1 for w in positive_words if w in content)
        neg_count = sum(1 for w in negative_words if w in content)
        neu_count = sum(1 for w in neutral_words if w in content)
        total = pos_count + neg_count + neu_count

        if total > 0:
            pos_ratio = pos_count / total
            neg_ratio = neg_count / total
            neu_ratio = neu_count / total

            details["positive_ratio"] = round(pos_ratio, 2)
            details["negative_ratio"] = round(neg_ratio, 2)
            details["neutral_ratio"] = round(neu_ratio, 2)
            details["total_emotion_words"] = total

            # 理想分布：不应过度偏向任何一极
            if pos_ratio > 0.7:
                score -= 20
                suggestions.append("正面情感词过多(>70%)，AI倾向明显")
            elif neg_ratio > 0.7:
                score -= 15
                suggestions.append("负面情感词过多")
            elif neg_count == 0 and total > 5:
                score -= 10
                suggestions.append("缺少批判性视角")
            elif 0.2 <= pos_ratio <= 0.5 and neg_ratio >= 0.1:
                score += 5
        else:
            details["total_emotion_words"] = 0
            score -= 5

        score = max(0, min(100, score))
        return QualityScore(
            metric=QualityMetric.EMOTIONAL_POLARITY,
            score=score,
            details=details,
            suggestions=suggestions
        )

    def _analyze_hook_and_cta(self, content: str) -> QualityScore:
        """V4/V7.0/V19.7: 分析黄金开头 (Golden Start) 与 行动号召 (CTA)

        V19.7优化：全面重构评分逻辑，更容易达到高分
        - 基础分提升至50分
        - 扩展词汇库至100+个
        - 新增内容质量加分项
        - 移除惩罚机制
        """
        score = 50.0  # V19.7: 基础分50分
        details = {}
        suggestions = []

        # 1. 黄金开头检测 (Golden Start) - 前 200 字
        hook_text = content[:250].strip()

        # V19.7: 超大情感冲击力词汇库 (60+个)
        emotional_hooks = [
            # 震惊类
            '震惊', '惊人', '震撼', '大跌眼镜', '目瞪口呆', '难以置信',
            # 悬念类
            '竟然', '没想到', '万万没想到', '谁也没想到', '意想不到', '令人意外',
            '出人意料', '谁料', '不料', '原来', '其实', '实际上',
            # 真相类
            '真相', '秘密', '揭秘', '曝光', '内幕', '幕后', '真正原因',
            '原来如此', '找到了', '发现了', '破案了',
            # 警示类
            '千万不要', '注意', '警惕', '小心', '当心', '切记', '务必',
            '必须知道', '一定要', '千万别', '千万别做',
            # 冲击类
            '重磅', '重磅消息', '大事件', '关键', '核心', '致命', '颠覆',
            '革命性', '划时代', '突破', '彻底', '完全', '绝对',
            # 深度类
            '深度', '底层逻辑', '本质', '真相', '原理', '规律',
            # 紧迫类
            '紧急', '速看', '必看', '收藏', '转发', '分享',
        ]

        # V19.7: 超大问句钩子库 (25+个)
        question_hooks = [
            '？', '?', '为什么', '如何', '怎么', '怎样', '难道',
            '怎么回事', '什么情况', '到底', '究竟', '凭什么',
            '你猜', '猜猜', '想知道', '有没有想过', '是否',
            '怎么办', '怎么做', '什么原因', '为何', '何以',
            '岂能', '怎能', '怎会', '是不是', '对不对',
        ]

        # V19.7: 超大爆点词库 (30+个)
        bang_hooks = [
            '！', '!', '：', ':', '——', '……',
            '说白了', '讲真的', '说实话', '老实说', '坦白讲',
            '重点来了', '重点是', '关键是', '值得注意的是',
            '有意思的是', '更关键的是', '更重要的是',
            '换句话说', '换言之', '简单来说', '通俗点说',
            '这就引出了', '这就说明了', '这就解释了',
            '好消息', '坏消息', '大新闻', '重磅消息',
        ]

        # V19.7: 数字冲击模式
        number_patterns = [
            r'\d+[万亿亿]', r'\d+%', r'\d+倍', r'\d+个', r'\d+年',
            r'第\d+', r'Top\s*\d+', r'NO\.\d+', r'\d+强', r'\d+大',
            r'\d+小时', r'\d+分钟', r'\d+天', r'\d+元', r'\d+万',
        ]

        # V19.7: 对比冲突词汇 (20+个)
        contrast_hooks = [
            '但是', '然而', '不过', '可是', '却', '反而', '其实',
            '与其', '不如', '并非', '不是', '不同于', '相反',
            '很多人以为', '大家都以为', '普遍认为', '一般人都',
            '表面上看', '看似', '好像', '似乎', '实际上',
        ]

        # V19.7: 故事代入词汇 (15+个)
        story_hooks = [
            '那天', '去年', '曾经', '有一次', '记得', '当时',
            '有个人', '有个朋友', '我朋友', '我认识', '话说',
            '前两天', '昨天', '今天', '最近', '前段时间',
        ]

        # V19.7: 新增 - 情感共鸣词汇
        emotion_words = [
            '感动', '暖心', '泪目', '破防', '心疼', '心疼了',
            '太香了', '太绝了', '太棒了', '太好了', '太强了',
            '绝了', '绝了绝了', '绝绝子', 'YYDS', 'yyds',
        ]

        # V19.7: 新增 - 专业权威词汇
        authority_words = [
            '专家', '研究', '数据', '调查', '报告', '分析',
            '发现', '证明', '证实', '表明', '显示', '揭示',
            '科学家', '学者', '教授', '博士', '权威',
        ]

        # 计算各项得分 - V19.7优化为更容易得分
        hook_points = 0

        # 情感冲击力 (每匹配+5分，最多25分)
        emotional_count = sum(1 for h in emotional_hooks if h in hook_text)
        hook_points += min(emotional_count * 5, 25)

        # 问句钩子 (每匹配+3分，最多15分)
        question_count = sum(1 for h in question_hooks if h in hook_text)
        hook_points += min(question_count * 3, 15)

        # 爆点词 (每匹配+3分，最多15分)
        bang_count = sum(1 for h in bang_hooks if h in hook_text)
        hook_points += min(bang_count * 3, 15)

        # 数字冲击 (每匹配+3分，最多12分)
        number_count = sum(1 for pattern in number_patterns if re.search(
            pattern, hook_text[:100]))
        hook_points += min(number_count * 3, 12)

        # 对比冲突 (每匹配+2分，最多8分)
        contrast_count = sum(1 for h in contrast_hooks if h in hook_text[:150])
        hook_points += min(contrast_count * 2, 8)

        # 故事代入 (每匹配+2分，最多8分)
        story_count = sum(1 for h in story_hooks if h in hook_text[:150])
        hook_points += min(story_count * 2, 8)

        # V19.7新增 - 情感共鸣加分
        emotion_count = sum(1 for e in emotion_words if e in content[:500])
        hook_points += min(emotion_count * 2, 6)

        # V19.7新增 - 专业权威加分
        authority_count = sum(1 for a in authority_words if a in content[:500])
        hook_points += min(authority_count * 2, 6)

        # V19.7: 检查开头质量 - 移除惩罚，改为提示
        filler_starts = ['在当今', '随着', '首先', '众所周知', '大家好', '近年来', '随着科技']
        if any(hook_text.startswith(f) for f in filler_starts):
            suggestions.append("建议：开头可以更具吸引力，尝试直接切入核心或设置悬念")

        # 记录各项统计
        details["hook_emotional_count"] = emotional_count
        details["hook_question_count"] = question_count
        details["hook_bang_count"] = bang_count
        details["hook_number_count"] = number_count
        details["hook_contrast_count"] = contrast_count
        details["hook_story_count"] = story_count
        details["hook_emotion_count"] = emotion_count
        details["hook_authority_count"] = authority_count

        score += hook_points
        details["golden_start_score"] = score

        # 2. 尾部互动/CTA 检测 - V19.7大幅优化
        cta_text = content[-400:].strip()

        # V19.7: 超大CTA词汇库 (40+个)
        cta_patterns = [
            # 基础互动
            '欢迎分享', '你的看法', '讨论', '留言', '关注', '点击', '公众号',
            '评论', '点赞', '转发', '收藏', '分享给', '推荐给',
            # 询问互动
            '有什么想法', '说说你的看法', '你怎么看', '你认同吗',
            '你会怎么做', '一起来讨论', '大家觉得呢',
            # 引导互动
            '欢迎在评论区', '在评论区留言', '评论区见', '期待你的',
            '你怎么认为', '你们觉得呢', '各位怎么看', '快来评论',
            # 行动号召
            '赶紧', '马上', '立即', '现在就', '别犹豫', '抓紧',
            '动动手指', '一键', '点击链接', '扫码', '关注我',
            # 情感互动
            '同意的请', '认可请', '喜欢请', '有共鸣请',
        ]

        cta_count = sum(1 for p in cta_patterns if p in cta_text)
        if cta_count > 0:
            # V19.7: CTA更容易得分
            score += min(10 + cta_count * 4, 25)
            details["has_cta"] = True
            details["cta_count"] = cta_count
        else:
            suggestions.append("建议：结尾可以添加互动引导，如'你怎么看？欢迎评论区留言'")

        # V19.7新增 - 全文CTA检测
        full_cta_count = sum(1 for p in cta_patterns if p in content)
        if full_cta_count > 2:
            score += min(full_cta_count * 2, 10)
            details["full_cta_count"] = full_cta_count

        score = min(100, score)
        return QualityScore(
            metric=QualityMetric.HOOK_CTA,
            score=score,
            details=details,
            suggestions=suggestions
        )

    def _analyze_deceptive_features(self, content: str) -> QualityScore:
        """V7.0/V19.7: 迷惑性特征（拟人度/Deception Index）

        V19.7优化：全面重构评分逻辑，更容易达到高分
        - 基础分提升至50分
        - 扩展口语词库至80+个
        - 新增多项人性化检测
        - 大幅降低AI惩罚
        """
        score = 50.0  # V19.7: 基础分50分
        details = {}
        suggestions = []

        # V19.7: 超大口语化转折词库 (80+个)
        human_connectors = [
            # 原有核心词
            '说白了', '说来也怪', '有意思的是', '平心而论', '换个接地气的角度',
            # 口语化开场
            '讲真的', '说实话', '老实说', '坦白讲', '说句掏心窝子的话',
            '不得不说', '不得不承认', '实话实说', '说真的', '确实',
            # 转折过渡
            '话又说回来', '说回来', '言归正传', '回归正题', '话说回来',
            '但是话又说回来', '不过话说回来', '再说回来',
            # 解释说明
            '简单来说', '简而言之', '换句话说', '换言之', '通俗点说',
            '直白点说', '说白了就是', '简单来讲', '打个比方', '比如',
            '举个例子', '比如说', '也就是说', '换句话说就是',
            # 强调重点
            '重点是', '关键在于', '值得注意的是', '更关键的是',
            '更重要的是', '不得不提的是', '特别值得一提的是',
            '最关键的是', '最重要的是', '核心是',
            # 推理引导
            '这就引出了', '这就说明了', '这就解释了', '这表明',
            '这意味着', '这说明了', '从中可以看出', '由此可见',
            # 情感表达
            '说来也巧', '说来惭愧', '不得不佩服', '不得不感叹', '不得不提',
            '真是没想到', '真是太', '真是绝了', '说实在的',
            # 肯定/否定
            '说实话确实', '确实是这样', '真的', '确实没错', '一点没错',
            '不是我说', '说句不好听的', '说句实在话',
        ]
        conn_count = sum(1 for c in human_connectors if c in content)
        score += min(conn_count * 5, 30)  # V19.7: 每个5分，最多30分
        details["human_connector_count"] = conn_count

        # V19.7: 超大拟人化语气词库 (40+个)
        tone_words = [
            # 互动类
            '你看', '你想想', '你想想看', '你想啊', '你猜怎么着',
            '咱们', '咱', '咱们来', '咱来说', '咱们看看',
            # 推理类
            '讲道理', '按理说', '理论上', '逻辑上说', '照理说',
            '照理', '一般来说', '通常来说', '按说', '理应',
            # 强调类
            '我就说嘛', '我就知道', '果然', '不出所料', '果然不出所料',
            '跟你讲', '跟你说', '悄悄告诉你', '偷偷告诉你',
            # 感叹类
            '我的天', '天哪', '哇', '哇塞', '绝了', '太绝了',
            '没开玩笑', '不开玩笑', '认真的', '说认真的',
        ]
        tone_count = sum(1 for t in tone_words if t in content)
        score += min(tone_count * 3, 15)  # V19.7: 每个3分，最多15分
        details["tone_word_count"] = tone_count

        # 2. 叙事呼吸感 (Structural entropy) - V19.7大幅优化
        paragraphs = [p for p in content.split('\n\n') if len(p.strip()) > 5]
        if len(paragraphs) >= 2:  # V19.7: 只需2段即可
            lengths = [len(p) for p in paragraphs]
            avg = sum(lengths) / len(lengths)
            var = sum((x - avg)**2 for x in lengths) / len(lengths)
            # V19.7: 大幅降低阈值
            if var > 300:
                score += 15
                details["high_structural_entropy"] = True
            elif var > 100:
                score += 10
                details["medium_structural_entropy"] = True
            else:
                score += 5  # V19.7: 即使均衡也给基础分
                details["low_structural_entropy"] = True
                suggestions.append("建议：段落长度可以更有变化，增加节奏感")

        # 3. 细节感知 (Specific details) - V19.7大幅优化
        specific_patterns = [
            r'\d+(?:\.\d+)?%',  # 百分比
            r'\d+万', r'\d+亿', r'\d+千万',  # 大数字
            r'【.*?】', r'「.*?」', r'『.*?』',  # 强调符号
            r'\d+个', r'\d+次', r'\d+种', r'\d+项',  # 量词
            r'\d+小时', r'\d+分钟', r'\d+秒', r'\d+天',  # 时间
            r'\d+年', r'\d+月', r'\d+日',  # 日期
            r'第\d+', r'Top\s*\d+', r'NO\.\d+',  # 排名
            r'\d+元', r'\d+块', r'\d+角',  # 金额
        ]
        specific_matches = []
        for pattern in specific_patterns:
            specific_matches.extend(re.findall(pattern, content))
        # V19.7: 只要有细节就给分
        if len(specific_matches) >= 1:
            score += min(8 + len(specific_matches) * 2, 20)
            details["specific_details_count"] = len(specific_matches)

        # V19.7新增 - 引用和对话检测
        quote_patterns = ['"', '"', '「', '」', '『', '』', '「', '」']
        quote_count = sum(1 for q in quote_patterns if q in content)
        if quote_count >= 1:
            score += 8
            details["has_quotes"] = True

        # V19.7新增 - 情感表达检测
        emotion_words = [
            '哈哈', '呵呵', '嘿嘿', '嘻嘻', '啊', '呀', '呢', '吧', '嘛',
            '！', '？', '～', '……', '——',  # 强调标点
        ]
        emotion_count = sum(1 for e in emotion_words if e in content)
        if emotion_count > 5:
            score += 5
            details["has_emotion"] = True

        # 4. 反检测惩罚 (AI patterns) - V19.7大幅降低
        ai_markers = [
            '综上所述', '总而言之',  # 重灾区 - 也只扣3分
            '首先.*?其次',  # 列举模式
            '我们应该', '我们需要',  # 说教词
        ]
        ai_count = 0
        for m in ai_markers:
            if m in content:
                ai_count += 1
        score -= min(ai_count * 3, 10)  # V19.7: 惩罚从-20降到-3，封顶-10

        # V19.7新增 - 奖励：多样化标点
        special_puncts = ['——', '……', '～', '~', '·', '；', '：']
        special_count = sum(1 for p in special_puncts if p in content)
        if special_count > 0:
            score += min(special_count * 2, 8)
            details["special_punctuation_count"] = special_count

        # V19.7新增 - 奖励：有标题/小标题
        if '##' in content or '###' in content or '**' in content:
            score += 5
            details["has_headers"] = True

        # V19.7新增 - 奖励：有列表
        if '-' in content or '•' in content or '·' in content:
            score += 3
            details["has_list"] = True

        score = max(30, min(100, score))  # V19.7: 最低分提高到30
        if score < 60:
            suggestions.append("建议：可以添加更多口语化表达，让内容更接地气")

        return QualityScore(
            metric=QualityMetric.DECEPTIVE_FEATURES,
            score=score,
            details=details,
            suggestions=suggestions
        )

        # 数据开头（用数字震撼读者）
        if re.search(r'^\d+|[\d]+[%％亿万]', first_para[:50]):
            hook_score += 30
            details["hook_type_data"] = True

        # 疑问开头（激发好奇心）
        if '？' in first_para[:80] or '?' in first_para[:80]:
            hook_score += 30
            details["hook_type_question"] = True

        # 场景/故事开头（代入感）
        story_signals = ['那天', '去年', '曾经', '有一次', '记得', '当时', '彼时']
        if any(s in first_para[:60] for s in story_signals):
            hook_score += 25
            details["hook_type_story"] = True

        # 争议/颠覆开头
        controversy_signals = ['很多人以为', '你可能不知道', '颠覆', '震惊', '没想到', '万万没想到']
        if any(s in first_para[:80] for s in controversy_signals):
            hook_score += 25
            details["hook_type_controversy"] = True

        # 如果没有任何Hook类型
        if hook_score == 0:
            score -= 15
            suggestions.append("开头缺少吸引力，建议使用数据、疑问、故事或争议性开头")

        hook_score = min(hook_score, 40)  # 封顶加40
        details["hook_score"] = hook_score

        # ===== 结尾 CTA 评分 =====
        cta_score = 0

        # 行动号召
        cta_signals = ['不妨试试', '赶紧', '值得一试', '推荐',
                       '建议大家', '你怎么看', '欢迎留言', '转发', '收藏']
        if any(s in last_para for s in cta_signals):
            cta_score += 25
            details["cta_type_action"] = True

        # 引发思考
        think_signals = ['值得深思', '引人深思', '我们该如何', '未来将会', '这意味着', '或许', '也许正是']
        if any(s in last_para for s in think_signals):
            cta_score += 25
            details["cta_type_thinking"] = True

        # 总结升华
        summary_signals = ['归根结底', '说到底', '总而言之', '一句话', '最重要的是']
        if any(s in last_para for s in summary_signals):
            cta_score += 15
            details["cta_type_summary"] = True

        if cta_score == 0:
            score -= 10
            suggestions.append("结尾缺少行动号召或思考引导，建议增加互动性")

        cta_score = min(cta_score, 35)
        details["cta_score"] = cta_score

        # 基础50分 + hook + cta
        score = max(0, min(100, 50 + hook_score + cta_score))

        return QualityScore(
            metric=QualityMetric.HOOK_CTA,
            score=score,
            details=details,
            suggestions=suggestions
        )

    def _analyze_topic_transition(self, content: str) -> QualityScore:
        """V4新增：主题过渡平滑度评分 — 检测相邻段落间的主题是否平滑衔接

        通过计算相邻段落的关键词重叠度来判断过渡是否自然。
        过渡太生硬(重叠<10%)或太重复(重叠>60%)都会扣分。
        """
        score = 100.0
        details = {}
        suggestions = []

        paragraphs = [p.strip() for p in content.split('\n\n') if p.strip(
        ) and not p.strip().startswith('#') and len(p.strip()) > 20]

        if len(paragraphs) < 3:
            return QualityScore(metric=QualityMetric.TOPIC_TRANSITION, score=70.0, details={"error": "段落数不足"}, suggestions=[])

        # 提取每段的关键词集合（去掉停用词）
        stop_words = set('的了是在有和与等也都不人这那些被把将从到对于就而且')

        def extract_keywords(text):
            """提取中文关键词（字符bi-gram作为简易分词）"""
            chars = re.findall(r'[\u4e00-\u9fff]', text)
            words = set()
            for i in range(len(chars) - 1):
                bigram = chars[i] + chars[i+1]
                if not any(c in stop_words for c in bigram):
                    words.add(bigram)
            return words

        overlaps = []
        for i in range(len(paragraphs) - 1):
            kw1 = extract_keywords(paragraphs[i])
            kw2 = extract_keywords(paragraphs[i + 1])

            if kw1 and kw2:
                overlap = len(kw1 & kw2) / min(len(kw1), len(kw2))
                overlaps.append(round(overlap, 3))

        if overlaps:
            avg_overlap = sum(overlaps) / len(overlaps)
            min_overlap = min(overlaps)
            max_overlap = max(overlaps)

            details["avg_overlap"] = round(avg_overlap, 3)
            details["min_overlap"] = round(min_overlap, 3)
            details["max_overlap"] = round(max_overlap, 3)
            details["transition_count"] = len(overlaps)

            # 评分逻辑
            # 平均重叠 < 5% → 段落跳跃太大
            if avg_overlap < 0.05:
                score -= 25
                suggestions.append("段落间主题跳跃过大，建议增加过渡语句")
            # 平均重叠 5%-15% → 偏低但可接受
            elif avg_overlap < 0.15:
                score -= 10
                suggestions.append("段落衔接稍显生硬，可以考虑在段首增加承上启下的句子")
            # 平均重叠 > 60% → 段落内容重复
            elif avg_overlap > 0.6:
                score -= 20
                suggestions.append("相邻段落内容高度重复，建议精简或合并")
            # 存在某个过渡特别差(<3%)
            if min_overlap < 0.03 and len(overlaps) > 2:
                score -= 8
                suggestions.append("存在主题断裂点，某些段落之间几乎没有关联")

        score = max(0, min(100, score))

        return QualityScore(
            metric=QualityMetric.TOPIC_TRANSITION,
            score=score,
            details=details,
            suggestions=suggestions
        )

    def _calculate_overall_score(self, scores: Dict[str, QualityScore]) -> float:
        """V5: 计算综合分数（提升ai_likelihood权重检测突发性和段首词）"""
        weights = {
            "originality": 0.12,
            "readability": 0.08,
            "coherence": 0.10,
            "vocabulary": 0.06,
            "sentence_variety": 0.06,
            "ai_likelihood": 0.15,
            "semantic_depth": 0.06,
            # V4 新增维度
            "emotional_polarity": 0.05,
            "hook_cta": 0.10,            # V19.7: 提升权重
            "topic_transition": 0.05,
            "deceptive_features": 0.10,  # V19.7: 提升权重
            "seo_keywords": 0.07,        # V19.7: 新增SEO权重
        }

        total_score = 0.0
        for metric, weight in weights.items():
            if metric in scores:
                metric_score = scores[metric].score
                if metric == "ai_likelihood":
                    metric_score = 100 - metric_score
                total_score += metric_score * weight

        return round(total_score, 1)

    def compare_contents(self, original: str, optimized: str) -> Dict[str, Any]:
        """对比原文和优化后的内容"""
        original_result = self.analyze_content(original)
        optimized_result = self.analyze_content(optimized)

        # 计算改进幅度
        improvements = {}
        for metric in original_result.quality_scores:
            if metric in optimized_result.quality_scores:
                orig_score = original_result.quality_scores[metric].score
                opt_score = optimized_result.quality_scores[metric].score

                if metric == "ai_likelihood":
                    # AI概率降低是改进
                    improvement = orig_score - opt_score
                else:
                    improvement = opt_score - orig_score

                improvements[metric] = {
                    "original": orig_score,
                    "optimized": opt_score,
                    "improvement": round(improvement, 1),
                    "percentage": round((improvement / orig_score * 100) if orig_score != 0 else 0, 1)
                }

        # 计算相似度
        similarity = self._calculate_similarity(original, optimized)

        return {
            "original_analysis": {
                "overall_score": original_result.overall_score,
                "ai_detection_score": original_result.ai_detection_score,
                "originality_score": original_result.originality_score,
            },
            "optimized_analysis": {
                "overall_score": optimized_result.overall_score,
                "ai_detection_score": optimized_result.ai_detection_score,
                "originality_score": optimized_result.originality_score,
            },
            "improvements": improvements,
            "similarity": similarity,
            "overall_improvement": round(
                optimized_result.overall_score - original_result.overall_score, 1
            ),
        }

    def _calculate_similarity(self, text1: str, text2: str) -> float:
        """计算文本相似度 (简化的Jaccard相似度)"""
        # 分词
        words1 = set(re.findall(r'[\u4e00-\u9fff]+', text1))
        words2 = set(re.findall(r'[\u4e00-\u9fff]+', text2))

        if not words1 or not words2:
            return 0.0

        intersection = words1 & words2
        union = words1 | words2

        return round(len(intersection) / len(union) * 100, 1) if union else 0.0

    async def generate_optimization_suggestions(self, analysis_result: ContentAnalysisResult) -> List[str]:
        """
        生成优化建议 - AI动态生成个性化建议

        结合固定规则建议和AI分析，生成针对实际内容的个性化优化建议
        """
        import asyncio

        # 1. 先收集基础建议（来自各个指标的固定建议）
        base_suggestions = []
        for metric, score in analysis_result.quality_scores.items():
            base_suggestions.extend(score.suggestions)

        # 根据AI检测分数添加优先建议
        if analysis_result.ai_detection_score > 30:
            base_suggestions.insert(0, "【优先】AI检测概率较高，需要重点优化表达方式")

        # 根据原创性分数添加建议
        if analysis_result.originality_score < 70:
            base_suggestions.insert(0, "【优先】原创性较低，需要增加独特观点和表达")

        # 2. 调用AI生成个性化建议
        try:
            from src.ai_write_x.core.llm_client import LLMClient

            # 构建分析数据
            analysis_data = {
                "overall_score": analysis_result.overall_score,
                "ai_detection_score": analysis_result.ai_detection_score,
                "originality_score": analysis_result.originality_score,
                "metrics": {
                    metric: {
                        "score": score.score,
                        "details": score.details
                    }
                    for metric, score in analysis_result.quality_scores.items()
                }
            }

            # 获取内容样本（前1000字用于分析）
            content_sample = analysis_result.original_content[:1000]

            ai_prompt = f"""你是一位资深的内容编辑和写作专家。请根据以下质量分析数据，为这篇文章生成3-5条具体、可操作的优化建议。

## 质量分析数据：
- 综合评分: {analysis_data['overall_score']:.1f}/100
- AI检测概率: {analysis_data['ai_detection_score']:.1f}% (越低越好)
- 原创性评分: {analysis_data['originality_score']:.1f}% (越高越好)

## 详细指标：
{json.dumps(analysis_data['metrics'], ensure_ascii=False, indent=2)}

## 内容样本：
{content_sample}

## 基础建议参考：
{chr(10).join([f"- {s}" for s in base_suggestions[:5]])}

## 要求：
1. 基于实际内容问题，给出具体、可操作的改进建议
2. 避免空泛的套话，每条建议都要针对这篇文章的实际情况
3. 建议要具体，比如"将第3段的排比句改为递进关系"而不是"改善句式"
4. 返回3-5条建议，按优先级排序
5. 格式：每条建议一行，不要编号

## 个性化优化建议："""

            llm = LLMClient()
            messages = [
                {"role": "system", "content": "你是一位资深的内容编辑和写作专家。"},
                {"role": "user", "content": ai_prompt}
            ]
            # 禁用语义缓存
            ai_response = llm.chat(
                messages=messages,
                temperature=0.7,
                max_tokens=800,
                use_v15=False  # 禁用语义缓存
            )

            # 解析AI返回的建议
            ai_suggestions = [s.strip()
                              for s in ai_response.strip().split('\n') if s.strip()]

            # 合并基础建议和AI建议（AI建议优先）
            all_suggestions = ai_suggestions + base_suggestions

        except Exception as e:
            # AI生成失败时，使用基础建议
            all_suggestions = base_suggestions

        # 去重
        seen = set()
        unique_suggestions = []
        for s in all_suggestions:
            # 规范化后去重
            normalized = s.lower().replace(' ', '').replace('，', ',').replace('。', '.')
            if normalized not in seen and len(s) > 5:  # 过滤太短的建议
                seen.add(normalized)
                unique_suggestions.append(s)

        return unique_suggestions[:8]  # 最多返回8条建议


# Backwards-compatible alias
QualityEngine = ContentQualityEngine


class AutoOptimizer:
    """自动优化器"""

    def __init__(self, quality_engine: ContentQualityEngine):
        self.quality_engine = quality_engine
        self.optimization_history: List[Dict] = []

    async def auto_optimize(
        self,
        content: str,
        target_originality: float = 75.0,
        max_ai_likelihood: float = 30.0,
        max_iterations: int = 5,
        progress_callback=None,
    ) -> Tuple[str, ContentAnalysisResult]:
        """
        自动优化内容

        Args:
            content: 原始内容
            target_originality: 目标原创性分数
            max_ai_likelihood: 最大允许的AI检测概率
            max_iterations: 最大迭代次数
            progress_callback: 进度回调函数

        Returns:
            优化后的内容和最终分析结果
        """
        current_content = content
        iteration = 0
        self.optimization_history = []

        # 初始分析
        result = self.quality_engine.analyze_content(current_content)

        while iteration < max_iterations:
            # 检查是否达到目标
            if (result.originality_score >= target_originality and
                    result.ai_detection_score <= max_ai_likelihood):
                break

            # 记录历史
            history_entry = {
                "iteration": iteration,
                "originality_score": result.originality_score,
                "ai_likelihood": result.ai_detection_score,
                "overall_score": result.overall_score,
            }
            self.optimization_history.append(history_entry)

            # 生成优化内容
            optimization_result = await self._optimize_iteration(
                current_content, result, iteration
            )

            if optimization_result:
                current_content = optimization_result["content"]
                result = self.quality_engine.analyze_content(current_content)

                if progress_callback:
                    await progress_callback({
                        "iteration": iteration + 1,
                        "max_iterations": max_iterations,
                        "current_score": result.overall_score,
                        "ai_likelihood": result.ai_detection_score,
                        "originality": result.originality_score,
                    })

            iteration += 1

        result.optimized_content = current_content
        result.optimization_iterations = iteration

        return current_content, result

    async def _optimize_iteration(
        self,
        content: str,
        analysis: ContentAnalysisResult,
        iteration: int
    ) -> Optional[Dict[str, Any]]:
        """执行一次优化迭代"""
        suggestions = await self.quality_engine.generate_optimization_suggestions(analysis)

        # 这里返回优化提示，实际的AI优化由调用方执行
        return {
            "content": content,  # 占位，实际由外部AI处理
            "suggestions": suggestions,
            "iteration": iteration,
        }

    def get_optimization_history(self) -> List[Dict]:
        """获取优化历史"""
        return self.optimization_history


class TitleOptimizer:
    """标题优化器 - 使用AI生成更具吸引力的标题"""

    @staticmethod
    async def optimize_title(title: str, content: str, platform: str = "") -> Dict[str, Any]:
        """
        使用AI优化标题

        Args:
            title: 原标题
            content: 文章内容
            platform: 目标平台（如微信公众号、今日头条、知乎等）

        Returns:
            包含优化后标题和变体的字典
        """
        try:
            from src.ai_write_x.core.llm_client import LLMClient

            # 准备内容摘要（前800字）
            content_summary = content[:800] if len(content) > 800 else content

            # 构建平台特定的要求
            platform_requirements = {
                "微信公众号": "适合朋友圈传播，要有情感共鸣，可以适当使用悬念",
                "今日头条": "强调新闻性和热点，标题要直接、有冲击力，适合算法推荐",
                "知乎": "要有知识性和深度，引发好奇心和讨论欲",
                "抖音": "简短有力，口语化，适合短视频时代的快速阅读",
                "小红书": "亲和力强，注重实用性和分享感，语气活泼但不使用表情符号",
                "": "通用平台，平衡传播性和专业性"
            }

            platform_hint = platform_requirements.get(
                platform, platform_requirements[""])

            prompt = f"""你是一位资深的新媒体标题优化专家。请为以下文章生成5个更具吸引力的标题。

## 原标题
{title}

## 内容摘要
{content_summary}

## 平台要求
{platform_hint}

## 爆款标题公式（必须遵循）
标题必须包含以下元素中的至少2个：
- 问号？（制造悬念）
- 感叹号！（情绪强烈）
- 引号""（引用或强调）
- 数字（具体可信）
- 省略号...（意犹未尽）

**注意：标题中禁止使用Emoji表情符号，确保在所有平台都能正常显示**

## 爆款标题类型（5种必须全生成）
1. **悬念型**：用"为什么""竟然""真相是""揭秘"等词制造悬念
   示例：《为什么90%的人都在错误理财？真相让人震惊！》

2. **数字型**：用具体数据增强可信度
   示例：《月入3000到3万，我只做了这3件事》

3. **冲突型**：制造强烈反差或对立
   示例：《年薪百万的他，却在凌晨3点捡垃圾》

4. **情绪型**：激发恐惧、愤怒、好奇或共鸣
   示例：《小心！你家的这种电器正在偷走你的寿命》

5. **实用型**：突出价值和利益点
   示例：《3分钟学会这个技巧，让你效率提升10倍》

**重要：所有标题禁止包含Emoji表情，只使用纯文字和标点符号**

## 要求
1. 生成5个不同风格的标题（严格按上述5种类型）
2. 每个标题长度在15-30字之间
3. 每个标题必须包含至少2个爆款元素（问号、感叹号、数字、省略号等）
4. **严禁使用Emoji表情符号**，确保标题在所有平台都能正常显示
5. 符合平台调性，避免低俗标题党
6. 突出文章核心卖点

## 输出格式（严格遵循）
标题1：[悬念型标题]
说明：[为什么这个标题能吸引点击，包含哪些爆款元素]

标题2：[数字型标题]
说明：[为什么这个标题能吸引点击，包含哪些爆款元素]

标题3：[冲突型标题]
说明：[为什么这个标题能吸引点击，包含哪些爆款元素]

标题4：[情绪型标题]
说明：[为什么这个标题能吸引点击，包含哪些爆款元素]

标题5：[实用型标题]
说明：[为什么这个标题能吸引点击，包含哪些爆款元素]

## 推荐标记
在最有吸引力的标题后面加上 [⭐推荐]

## 开始生成"""

            llm = LLMClient()
            messages = [
                {"role": "system", "content": "你是一位资深的新媒体标题优化专家，擅长创作爆款标题。"},
                {"role": "user", "content": prompt}
            ]
            # 禁用语义缓存，确保每次生成不同的标题
            response = llm.chat(
                messages=messages,
                temperature=0.9,  # 提高温度增加多样性
                max_tokens=1000,
                use_v15=False  # 禁用V15语义缓存，确保每次生成不同结果
            )

            # ===== 调试日志：打印完整AI响应到控制台 =====
            print("=" * 80)
            print("[TitleOptimizer] AI原始响应内容:")
            print("=" * 80)
            print(response)
            print("=" * 80)
            print(f"[TitleOptimizer] 响应长度: {len(response)} 字符")
            print("=" * 80)

            # 辅助函数：移除Emoji表情符号
            def remove_emoji(text):
                import re
                # 匹配Emoji的正则表达式
                emoji_pattern = re.compile("["
                                           u"\U0001F600-\U0001F64F"  # emoticons
                                           u"\U0001F300-\U0001F5FF"  # symbols & pictographs
                                           u"\U0001F680-\U0001F6FF"  # transport & map symbols
                                           # flags (iOS)
                                           u"\U0001F1E0-\U0001F1FF"
                                           u"\U00002702-\U000027B0"
                                           u"\U000024C2-\U0001F251"
                                           u"\U0001F900-\U0001F9FF"  # supplemental symbols
                                           u"\U0001FA00-\U0001FA6F"  # chess symbols
                                           u"\U0001FA70-\U0001FAFF"  # symbols and pictographs extended-a
                                           u"\U00002600-\U000026FF"  # misc symbols
                                           u"\U00002700-\U000027BF"  # dingbats
                                           "]+", flags=re.UNICODE)
                return emoji_pattern.sub(r'', text).strip()

            # 解析响应
            lines = response.strip().split('\n')
            titles = []
            current_title = {}
            recommended_index = 0

            # 打印原始响应用于调试
            print(f"[TitleOptimizer] AI原始响应:\n{response[:500]}...")

            for i, line in enumerate(lines):
                line = line.strip()
                if not line:
                    continue

                # 匹配标题行（支持多种格式）
                # 格式1: 标题1：《标题内容》
                # 格式2: 标题1：标题内容
                # 格式3: 1. 《标题内容》
                # 格式4: 1、标题内容
                title_match = None

                # 优先匹配 "标题X：" 格式（最可靠）
                if line.startswith('标题') and ('：' in line or ':' in line):
                    sep = '：' if '：' in line else ':'
                    parts = line.split(sep, 1)
                    if len(parts) == 2:
                        # 验证标题编号（必须是1-5）
                        title_num_match = re.match(
                            r'^标题(\d+)$', parts[0].strip())
                        if title_num_match and 1 <= int(title_num_match.group(1)) <= 5:
                            title_match = parts

                # 备选：匹配 "X. 标题" 或 "X、标题" 格式，但只匹配1-5
                elif title_match is None:
                    # 只匹配标题编号1-5，且后面要有实际内容（至少5个字符）
                    num_title_match = re.match(r'^(\d+)[\.、\s]+(.{5,})$', line)
                    if num_title_match:
                        num = int(num_title_match.group(1))
                        if 1 <= num <= 5:
                            title_match = [f"标题{num}",
                                           num_title_match.group(2)]

                if title_match and len(title_match) == 2:
                    if current_title:
                        titles.append(current_title)

                    title_type = title_match[0].strip()
                    title_text = title_match[1].strip()

                    # ===== 调试：显示每一步处理前后的内容 =====
                    print(
                        f"[TitleOptimizer] 【DEBUG】分割结果: type='{title_type}', raw_text='{title_text[:50]}'")

                    # 移除书名号《》
                    title_text = re.sub(r'[《》]', '', title_text)
                    print(
                        f"[TitleOptimizer] 【DEBUG】移除书名号后: '{title_text[:50]}'")

                    # 检查是否有推荐标记（直接在原始文本上处理，不移除emoji）
                    is_recommended = False
                    if '[⭐推荐]' in title_text or '⭐推荐' in title_text:
                        title_text = title_text.replace(
                            '[⭐推荐]', '').replace('⭐推荐', '').strip()
                        is_recommended = True
                        recommended_index = len(titles)
                        print(
                            f"[TitleOptimizer] 【DEBUG】移除推荐标记后: '{title_text[:50]}'")

                    print(
                        f"[TitleOptimizer] 解析到标题: type={title_type}, title={title_text[:30]}...")

                    current_title = {
                        'type': title_type,
                        'title': title_text,
                        'explanation': '',
                        'is_recommended': is_recommended
                    }

                # 匹配说明行
                elif line.startswith('说明') and ('：' in line or ':' in line) and current_title:
                    explanation = line.split(
                        '：' if '：' in line else ':', 1)[1].strip()
                    current_title['explanation'] = explanation
                # 如果没有说明行，但有其他描述文字，也作为说明
                elif current_title and not current_title['explanation'] and len(line) > 10 and not line.startswith('标题'):
                    # 可能是说明文字，但不是下一行的标题
                    if not re.match(r'^\d+[\.、\s]', line) and not line.startswith('标题'):
                        current_title['explanation'] = line

            if current_title:
                titles.append(current_title)

            # ===== 调试日志：打印解析结果 =====
            print("\n" + "=" * 80)
            print(f"[TitleOptimizer] 解析完成，共 {len(titles)} 个标题:")
            print("=" * 80)
            for idx, t in enumerate(titles):
                print(f"  [{idx+1}] {t['type']}: {t['title']}")
                if t.get('explanation'):
                    print(f"      说明: {t['explanation'][:50]}...")
                if t.get('is_recommended'):
                    print(f"      ⭐ 推荐")
            print("=" * 80 + "\n")

            # 如果解析失败，返回原标题
            if not titles:
                print("[TitleOptimizer] 警告: 未能解析到任何标题，返回原标题")
                return {
                    "original_title": title,
                    "optimized_titles": [],
                    "recommended": title
                }

            # 返回推荐的标题（默认第一个）
            recommended = titles[recommended_index]['title'] if recommended_index < len(
                titles) else titles[0]['title']
            print(f"[TitleOptimizer] 推荐标题: {recommended}")

            return {
                "original_title": title,
                "optimized_titles": titles,
                "recommended": recommended
            }

        except Exception as e:
            import traceback
            traceback.print_exc()
            # 出错时返回原标题
            return {
                "original_title": title,
                "optimized_titles": [],
                "recommended": title,
                "error": str(e)
            }
