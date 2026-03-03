# -*- coding: utf-8 -*-
"""
语义去重和聚类引擎
实现智能去重、相似度计算、新闻聚类
"""

from typing import Dict, List, Any, Optional, Set, Tuple
from dataclasses import dataclass, field
from datetime import datetime, timedelta
import hashlib
import re
from difflib import SequenceMatcher
from collections import defaultdict

from src.ai_write_x.utils import log


@dataclass
class NewsItem:
    """新闻项"""
    id: str
    title: str
    content: str = ""
    url: str = ""
    source: str = ""
    published_at: datetime = field(default_factory=datetime.now)
    keywords: List[str] = field(default_factory=list)
    hash: str = ""
    
    def __post_init__(self):
        if not self.hash:
            self.hash = self._calculate_hash()
    
    def _calculate_hash(self) -> str:
        """计算内容哈希"""
        content = f"{self.title}{self.content[:500]}"
        return hashlib.md5(content.encode('utf-8')).hexdigest()


@dataclass
class DuplicateGroup:
    """重复新闻组"""
    group_id: str
    main_item: NewsItem                    # 主新闻（最新或权重最高的）
    duplicates: List[NewsItem] = field(default_factory=list)  # 重复项
    similarity_scores: Dict[str, float] = field(default_factory=dict)
    merged_content: str = ""                # 合并后的内容


class SemanticDeduplicator:
    """语义去重器"""
    
    def __init__(self, 
                 title_threshold: float = 0.85,
                 content_threshold: float = 0.75,
                 keyword_overlap_threshold: float = 0.6):
        """
        初始化去重器
        
        Args:
            title_threshold: 标题相似度阈值
            content_threshold: 内容相似度阈值
            keyword_overlap_threshold: 关键词重叠度阈值
        """
        self.title_threshold = title_threshold
        self.content_threshold = content_threshold
        self.keyword_overlap_threshold = keyword_overlap_threshold
        
        # 已处理的新闻缓存
        self.processed_cache: Dict[str, NewsItem] = {}
        self.cache_max_size = 10000
        self.cache_ttl = timedelta(hours=24)
    
    def deduplicate(self, items: List[NewsItem]) -> Tuple[List[NewsItem], List[DuplicateGroup]]:
        """
        对新闻列表进行去重
        
        Returns:
            (去重后的新闻列表, 重复新闻组列表)
        """
        unique_items = []
        duplicate_groups = []
        processed_hashes = set()
        
        for item in items:
            # 快速哈希检查
            if item.hash in processed_hashes:
                continue
            
            # 语义相似度检查
            is_duplicate, similar_item, similarity = self._check_similarity(item, unique_items)
            
            if is_duplicate and similar_item:
                # 找到重复，加入重复组
                group = self._find_or_create_group(duplicate_groups, similar_item)
                group.duplicates.append(item)
                group.similarity_scores[item.id] = similarity
            else:
                # 新新闻
                unique_items.append(item)
                processed_hashes.add(item.hash)
                
                # 更新缓存
                self._update_cache(item)
        
        log.print_log(f"[Deduplicator] 去重完成: {len(items)} -> {len(unique_items)} (去重率: {(1-len(unique_items)/max(1,len(items)))*100:.1f}%)")
        
        return unique_items, duplicate_groups
    
    def _check_similarity(self, item: NewsItem, 
                         candidates: List[NewsItem]) -> Tuple[bool, Optional[NewsItem], float]:
        """
        检查新闻是否与候选列表中的任何新闻相似
        
        Returns:
            (是否重复, 相似的候选项, 相似度分数)
        """
        # 首先检查缓存
        for cached_item in self.processed_cache.values():
            similarity = self._calculate_similarity(item, cached_item)
            if similarity >= self.title_threshold:
                return True, cached_item, similarity
        
        # 检查候选列表
        for candidate in candidates:
            similarity = self._calculate_similarity(item, candidate)
            if similarity >= self.title_threshold:
                return True, candidate, similarity
        
        return False, None, 0.0
    
    def _calculate_similarity(self, item1: NewsItem, item2: NewsItem) -> float:
        """
        计算两条新闻的综合相似度
        """
        # 标题相似度（权重最高）
        title_sim = self._text_similarity(item1.title, item2.title)
        
        # 如果标题完全不同，直接返回低相似度
        if title_sim < 0.5:
            return title_sim * 0.5
        
        # 内容相似度
        content_sim = self._text_similarity(
            item1.content[:1000], 
            item2.content[:1000]
        ) if item1.content and item2.content else 0
        
        # 关键词重叠度
        keyword_sim = self._keyword_overlap(
            item1.keywords, 
            item2.keywords
        ) if item1.keywords and item2.keywords else 0
        
        # 综合相似度（加权）
        combined_sim = (
            title_sim * 0.5 +
            content_sim * 0.3 +
            keyword_sim * 0.2
        )
        
        return combined_sim
    
    def _text_similarity(self, text1: str, text2: str) -> float:
        """计算文本相似度"""
        if not text1 or not text2:
            return 0.0
        
        # 使用SequenceMatcher
        similarity = SequenceMatcher(None, text1.lower(), text2.lower()).ratio()
        
        # 如果长文本中包含短文本作为子串，提高相似度
        if len(text1) > len(text2) and text2.lower() in text1.lower():
            similarity = max(similarity, 0.9)
        elif len(text2) > len(text1) and text1.lower() in text2.lower():
            similarity = max(similarity, 0.9)
        
        return similarity
    
    def _keyword_overlap(self, keywords1: List[str], keywords2: List[str]) -> float:
        """计算关键词重叠度"""
        if not keywords1 or not keywords2:
            return 0.0
        
        set1 = set(k.lower() for k in keywords1)
        set2 = set(k.lower() for k in keywords2)
        
        intersection = len(set1 & set2)
        union = len(set1 | set2)
        
        if union == 0:
            return 0.0
        
        return intersection / union
    
    def _find_or_create_group(self, groups: List[DuplicateGroup], 
                             main_item: NewsItem) -> DuplicateGroup:
        """查找或创建重复组"""
        for group in groups:
            if group.main_item.id == main_item.id:
                return group
        
        # 创建新组
        new_group = DuplicateGroup(
            group_id=f"dup_{main_item.hash[:8]}",
            main_item=main_item
        )
        groups.append(new_group)
        return new_group
    
    def _update_cache(self, item: NewsItem):
        """更新缓存"""
        # 清理过期缓存
        now = datetime.now()
        expired_keys = [
            k for k, v in self.processed_cache.items()
            if now - v.published_at > self.cache_ttl
        ]
        for k in expired_keys:
            del self.processed_cache[k]
        
        # 如果缓存已满，移除最旧的
        if len(self.processed_cache) >= self.cache_max_size:
            oldest_key = min(
                self.processed_cache.keys(),
                key=lambda k: self.processed_cache[k].published_at
            )
            del self.processed_cache[oldest_key]
        
        # 添加新项
        self.processed_cache[item.hash] = item
    
    def cluster_news(self, items: List[NewsItem], 
                    min_cluster_size: int = 2) -> Dict[str, List[NewsItem]]:
        """
        对新闻进行聚类
        
        Args:
            items: 新闻列表
            min_cluster_size: 最小聚类大小
            
        Returns:
            聚类结果 {主题: 新闻列表}
        """
        clusters = defaultdict(list)
        
        for item in items:
            # 提取主题标签
            topic = self._extract_topic(item)
            clusters[topic].append(item)
        
        # 过滤小聚类
        clusters = {
            topic: items 
            for topic, items in clusters.items() 
            if len(items) >= min_cluster_size
        }
        
        return dict(clusters)
    
    def _extract_topic(self, item: NewsItem) -> str:
        """从新闻中提取主题"""
        # 使用关键词进行主题分类
        topic_keywords = {
            "AI/大模型": ['AI', '人工智能', '大模型', 'LLM', 'ChatGPT', 'Claude', 'GPT'],
            "开源项目": ['开源', 'GitHub', '仓库', '项目', 'release', 'version'],
            "产品发布": ['发布', '上线', '推出', '新品', 'launch', 'product'],
            "技术架构": ['架构', '性能', '优化', '重构', '升级'],
            "编程语言": ['Python', 'JavaScript', 'Rust', 'Go', 'TypeScript'],
            "创业融资": ['融资', '投资', '创业', 'startup', 'funding'],
            "行业动态": ['行业', '市场', '趋势', '报告'],
        }
        
        text = item.title + " " + " ".join(item.keywords)
        topic_scores = {}
        
        for topic, keywords in topic_keywords.items():
            score = sum(1 for kw in keywords if kw.lower() in text.lower())
            if score > 0:
                topic_scores[topic] = score
        
        if topic_scores:
            return max(topic_scores.items(), key=lambda x: x[1])[0]
        
        return "其他"
    
    def merge_duplicate_content(self, group: DuplicateGroup) -> str:
        """合并重复新闻的内容"""
        all_items = [group.main_item] + group.duplicates
        
        # 选择最长的内容作为主内容
        main_content = max(all_items, key=lambda x: len(x.content)).content
        
        # 收集所有来源
        sources = list(set(item.source for item in all_items if item.source))
        
        # 合并信息
        merged = main_content
        if len(sources) > 1:
            merged += f"\n\n（综合{len(sources)}个来源: {', '.join(sources)}）"
        
        return merged


class SimHashDeduplicator:
    """基于SimHash的去重器（用于大规模数据）"""
    
    def __init__(self, hash_bits: int = 64, hamming_threshold: int = 3):
        self.hash_bits = hash_bits
        self.hamming_threshold = hamming_threshold
        self.hash_buckets = defaultdict(set)
    
    def simhash(self, text: str) -> int:
        """计算SimHash"""
        # 分词（简单实现）
        words = re.findall(r'[\u4e00-\u9fa5]{2,4}|[a-zA-Z]+', text)
        
        # 计算词频
        word_freq = {}
        for word in words:
            word_freq[word] = word_freq.get(word, 0) + 1
        
        # 计算哈希
        hash_vector = [0] * self.hash_bits
        
        for word, freq in word_freq.items():
            word_hash = hashlib.md5(word.encode()).hexdigest()
            for i in range(self.hash_bits):
                bit = int(word_hash[i % 32], 16) >> (i % 4) & 1
                hash_vector[i] += freq if bit else -freq
        
        # 生成SimHash
        simhash_value = 0
        for i, v in enumerate(hash_vector):
            if v > 0:
                simhash_value |= (1 << i)
        
        return simhash_value
    
    def hamming_distance(self, hash1: int, hash2: int) -> int:
        """计算汉明距离"""
        xor = hash1 ^ hash2
        distance = 0
        while xor:
            distance += 1
            xor &= xor - 1
        return distance
    
    def is_duplicate(self, text: str) -> bool:
        """检查是否是重复内容"""
        hash_value = self.simhash(text)
        
        # 检查相近的哈希值
        for bucket_hash in self.hash_buckets.keys():
            if self.hamming_distance(hash_value, bucket_hash) <= self.hamming_threshold:
                return True
        
        # 添加到桶
        self.hash_buckets[hash_value].add(text[:100])
        return False
