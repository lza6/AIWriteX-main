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
    SENTENCE_VARIETY = "sentence_variety" # 句式多样性
    AI_LIKELIHOOD = "ai_likelihood"       # AI生成概率
    SEMANTIC_DEPTH = "semantic_depth"     # 语义深度
    EMOTIONAL_POLARITY = "emotional_polarity" # V4: 情感极性
    HOOK_CTA = "hook_cta"                 # V4: Hook/CTA
    TOPIC_TRANSITION = "topic_transition" # V4: 主题过渡
    DECEPTIVE_FEATURES = "deceptive_features" # V7.0: 迷惑性特征（拟人度）


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
        self.min_originality_threshold = self.config.get("min_originality", 75.0)
        self.max_ai_likelihood_threshold = self.config.get("max_ai_likelihood", 30.0)
        self.max_optimization_iterations = self.config.get("max_iterations", 5)
        
    def analyze_content(self, content: str) -> ContentAnalysisResult:
        """V4: 分析内容质量（新增情感极性+Hook/CTA+主题过渡三大维度）"""
        result = ContentAnalysisResult(original_content=content)
        
        # 执行各项质量检测
        result.quality_scores["originality"] = self._analyze_originality(content)
        result.quality_scores["readability"] = self._analyze_readability(content)
        result.quality_scores["coherence"] = self._analyze_coherence(content)
        result.quality_scores["vocabulary"] = self._analyze_vocabulary_richness(content)
        result.quality_scores["sentence_variety"] = self._analyze_sentence_variety(content)
        result.quality_scores["ai_likelihood"] = self._analyze_ai_likelihood(content)
        result.quality_scores["semantic_depth"] = self._analyze_semantic_depth(content)
        
        # V4: 新增三大分析维度
        result.quality_scores["emotional_polarity"] = self._analyze_emotional_polarity(content)
        result.quality_scores["hook_cta"] = self._analyze_hook_and_cta(content)
        result.quality_scores["topic_transition"] = self._analyze_topic_transition(content)
        result.quality_scores["deceptive_features"] = self._analyze_deceptive_features(content) # V7.0
        
        # 计算综合分数
        result.overall_score = self._calculate_overall_score(result.quality_scores)
        result.ai_detection_score = result.quality_scores["ai_likelihood"].score
        result.originality_score = result.quality_scores["originality"].score
        result.deceptive_score = result.quality_scores["deceptive_features"].score # V7.0
        
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
                result.quality_scores["ai_likelihood"].score = min(100, result.quality_scores["ai_likelihood"].score + 8)
                result.quality_scores["ai_likelihood"].suggestions.append("V3信息熵过低，内容可能存在大量重复模式")
            if v3_ngram.get("3gram_repeat_ratio", 0) > 0.15:
                result.quality_scores["ai_likelihood"].score = min(100, result.quality_scores["ai_likelihood"].score + 6)
                result.quality_scores["ai_likelihood"].suggestions.append("V3 N-gram检测到高频短语重复，建AI特征明显")
        if "readability" in result.quality_scores:
            result.quality_scores["readability"].details["v3_reading_time"] = v3_reading_time
        
        # 重新计算综合分（因为AI分数可能已被调整）
        result.overall_score = self._calculate_overall_score(result.quality_scores)
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
        personal_count = sum(1 for p in personal_patterns if re.search(p, content))
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
            avg_sentence_length = sum(len(s) for s in sentences) / len(sentences)
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
            advanced_chars = set("缜密 渊博 璀璨 斑斓 恢弘 磅礴 深邃 精湛 卓越 非凡".replace(" ", ""))
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
            modifier_count = sum(len(re.findall(p, content)) for p in modifier_patterns)
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
        starter_diversity = unique_starters / len(sentences) if sentences else 0
        
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
            variance = sum((l - avg_length) ** 2 for l in lengths) / len(lengths)
            
            # AI生成的文本通常方差较小
            if variance < 50:
                score += 10
                details["regular_structure"] = True
                suggestions.append("文章结构过于规律，增加自然变化")
        
        # 4. 段落长度方差分析（AI段落长度高度一致）
        paragraphs = [p.strip() for p in content.split('\n\n') if p.strip() and not p.strip().startswith('#')]
        if len(paragraphs) >= 3:
            para_lengths = [len(p) for p in paragraphs]
            avg_para_len = sum(para_lengths) / len(para_lengths)
            para_variance = sum((l - avg_para_len) ** 2 for l in para_lengths) / len(para_lengths)
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
                details["paragraph_starter_diversity"] = round(starter_diversity, 2)
                
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
        personal_count = sum(1 for p in personal_patterns if re.search(p, content))
        
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
        evidence_count = sum(1 for p in evidence_patterns if re.search(p, content))
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
        entropy = -sum((count / total) * math.log2(count / total) for count in freq.values())
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
            result[f"{n}gram_top_repeats"] = [ng for ng, c in freq.most_common(5) if c > 1]
        
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
        zipf_products = [(i + 1) * (f / total) for i, f in enumerate(sorted_freqs[:20])]
        if len(zipf_products) < 2:
            return 0.0
        
        avg_product = sum(zipf_products) / len(zipf_products)
        variance = sum((p - avg_product) ** 2 for p in zipf_products) / len(zipf_products)
        
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

    def _analyze_deceptive_features(self, content: str) -> QualityScore:
        """V7.0: 迷惑性特征评分 - 检测文章中对抗AI检测的拟人特征"""
        score = 0.0
        details = {}
        suggestions = []

        # 1. 语气词与呼吸感连接词 (Anti-AI V7 新增)
        breathing_patterns = [
            "其实，", "说到底，", "换句话说，", "不过话说回来，",
            "其实吧，", "倒是可以这么看，", "仔细一想，", "说句掏心窝子的话"
        ]
        found_breathing = [p for p in breathing_patterns if p in content]
        score += min(len(found_breathing) * 15, 45)
        details["breathing_features"] = found_breathing

        # 2. 句式长度的“爆发力” (长短句极端差异)
        sentences = re.split(r'[。！？]', content)
        lengths = [len(s.strip()) for s in sentences if s.strip()]
        if lengths:
            max_len = max(lengths)
            min_len = min(lengths)
            if max_len > 80 and min_len < 10:
                score += 25
                details["length_burst"] = True
            else:
                suggestions.append("建议增加长短句的极端对比")

        # 3. 语义微调标记 (或者说, 其实本质上)
        micro_patterns = ["或者说", "准确地说", "换个说法", "老实说"]
        found_micro = [p for p in micro_patterns if p in content]
        score += min(len(found_micro) * 10, 30)
        details["micro_adjustments"] = found_micro

        score = max(0, min(100, score))
        return QualityScore(
            metric=QualityMetric.DECEPTIVE_FEATURES,
            score=score,
            details=details,
            suggestions=suggestions
        )

    def _analyze_hook_and_cta(self, content: str) -> QualityScore:
        """V4新增：开头Hook + 结尾CTA(行动号召) 评分
        
        好文章开头要有"钩子"吸引读者继续阅读，结尾要有行动号召或引发思考。
        """
        score = 100.0
        details = {}
        suggestions = []
        
        paragraphs = [p.strip() for p in content.split('\n\n') if p.strip() and not p.strip().startswith('#')]
        if len(paragraphs) < 2:
            return QualityScore(metric=QualityMetric.HOOK_CTA, score=60.0, details={"error": "段落过少"}, suggestions=[])
        
        first_para = paragraphs[0]
        last_para = paragraphs[-1]
        
        # ===== 开头 Hook 评分 =====
        hook_score = 0
        
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
        cta_signals = ['不妨试试', '赶紧', '值得一试', '推荐', '建议大家', '你怎么看', '欢迎留言', '转发', '收藏']
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
        
        score = max(0, min(100, 50 + hook_score + cta_score))  # 基础50分 + hook + cta
        
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
        
        paragraphs = [p.strip() for p in content.split('\n\n') if p.strip() and not p.strip().startswith('#') and len(p.strip()) > 20]
        
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
            "originality": 0.15,
            "readability": 0.10,     # V5: 从0.12降至0.10
            "coherence": 0.12,
            "vocabulary": 0.08,
            "sentence_variety": 0.08,
            "ai_likelihood": 0.20,   # V5: 从0.18提升至0.20
            "semantic_depth": 0.08,
            # V4 新增维度
            "emotional_polarity": 0.06,
            "hook_cta": 0.07,
            "topic_transition": 0.06,
            "deceptive_features": 0.06, # V7.0
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
            from src.ai_write_x.llm import LiteLLMClient
            
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

            llm = LiteLLMClient()
            ai_response = await llm.acomplete(
                prompt=ai_prompt,
                temperature=0.7,
                max_tokens=800
            )
            
            # 解析AI返回的建议
            ai_suggestions = [s.strip() for s in ai_response.strip().split('\n') if s.strip()]
            
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
            from src.ai_write_x.llm import LiteLLMClient
            
            # 准备内容摘要（前800字）
            content_summary = content[:800] if len(content) > 800 else content
            
            # 构建平台特定的要求
            platform_requirements = {
                "微信公众号": "适合朋友圈传播，要有情感共鸣，可以适当使用悬念",
                "今日头条": "强调新闻性和热点，标题要直接、有冲击力，适合算法推荐",
                "知乎": "要有知识性和深度，引发好奇心和讨论欲",
                "抖音": "简短有力，口语化，适合短视频时代的快速阅读",
                "小红书": "亲和力强，使用emoji，注重实用性和分享感",
                "": "通用平台，平衡传播性和专业性"
            }
            
            platform_hint = platform_requirements.get(platform, platform_requirements[""])
            
            prompt = f"""你是一位资深的新媒体标题优化专家。请为以下文章生成5个更具吸引力的标题。

## 原标题
{title}

## 内容摘要
{content_summary}

## 平台要求
{platform_hint}

## 要求
1. 生成5个不同风格的标题供选择：
   - 标题1：悬念型（引发好奇心）
   - 标题2：数字型（使用具体数据）
   - 标题3：情感型（引发共鸣）
   - 标题4：热点型（结合时事）
   - 标题5：实用型（突出价值）

2. 每个标题都要：
   - 长度在15-30字之间
   - 符合平台调性
   - 避免标题党，但要有吸引力
   - 突出文章核心卖点

3. 对每个标题给出简短说明（为什么这个标题有效）

## 输出格式
标题1：[标题内容]
说明：[为什么有效]

标题2：[标题内容]
说明：[为什么有效]

...以此类推"""

            llm = LiteLLMClient()
            response = await llm.acomplete(
                prompt=prompt,
                temperature=0.8,
                max_tokens=1000
            )
            
            # 解析响应
            lines = response.strip().split('\n')
            titles = []
            current_title = {}
            
            for line in lines:
                line = line.strip()
                if line.startswith('标题') and '：' in line:
                    if current_title:
                        titles.append(current_title)
                    current_title = {
                        'type': line.split('：')[0],
                        'title': line.split('：', 1)[1].strip(),
                        'explanation': ''
                    }
                elif line.startswith('说明') and '：' in line and current_title:
                    current_title['explanation'] = line.split('：', 1)[1].strip()
            
            if current_title:
                titles.append(current_title)
            
            # 如果解析失败，返回原标题
            if not titles:
                return {
                    "original_title": title,
                    "optimized_titles": [],
                    "recommended": title
                }
            
            # 返回第一个作为推荐
            return {
                "original_title": title,
                "optimized_titles": titles,
                "recommended": titles[0]['title'] if titles else title
            }
            
        except Exception as e:
            # 出错时返回原标题
            return {
                "original_title": title,
                "optimized_titles": [],
                "recommended": title,
                "error": str(e)
            }
