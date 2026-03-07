#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
Universal Scraper Engine V17 - 通用新闻抓取引擎
全网最强新闻热点抓取系统核心引擎

特性:
- 智能抓取调度
- 多源聚合
- 自动去重
- 热点预测
- 流量分析
"""
import asyncio
import aiohttp
import json
import hashlib
import time
from datetime import datetime, timedelta
from typing import List, Dict, Optional, Set, Tuple
from dataclasses import dataclass, field
from enum import Enum
import threading

from logger_utils import logger


class SourcePriority(Enum):
    """数据源优先级"""
    CRITICAL = 10    # 权威媒体: BBC, NYT, Reuters等
    HIGH = 8         # 重要媒体: 卫报, CNN等
    MEDIUM = 6       # 普通媒体
    LOW = 4          # 社交媒体/热榜
    BACKUP = 2       # 备用源


class ContentCategory(Enum):
    """内容分类"""
    BREAKING = "breaking"      # 突发新闻
    TECH = "tech"              # 科技
    BUSINESS = "business"      # 商业
    POLITICS = "politics"      # 政治
    SCIENCE = "science"        # 科学
    ENTERTAINMENT = "ent"      # 娱乐
    SPORTS = "sports"          # 体育
    SOCIAL = "social"          # 社会


@dataclass
class NewsItem:
    """统一新闻项"""
    id: str
    title: str
    url: str
    summary: str
    source: str
    source_priority: int
    category: str
    published_at: datetime
    hot_score: float = 0.0
    keywords: List[str] = field(default_factory=list)
    language: str = "zh"
    author: str = ""
    image_url: str = ""
    
    @property
    def unique_key(self) -> str:
        """生成唯一键用于去重"""
        return hashlib.md5(f"{self.title}{self.source}".encode()).hexdigest()


@dataclass
class FetchResult:
    """抓取结果"""
    source: str
    items: List[NewsItem]
    success: bool
    error: str = ""
    fetch_time: float = 0.0


class UniversalScraperEngine:
    """
    通用新闻抓取引擎 V17
    全网最强新闻热点抓取系统
    """
    
    def __init__(self):
        self.session: Optional[aiohttp.ClientSession] = None
        self.semaphore = asyncio.Semaphore(30)  # 并发限制
        self.cache: Dict[str, NewsItem] = {}
        self.cache_expiry = 300  # 缓存5分钟
        self.cache_timestamp: Dict[str, float] = {}
        
        # V17: 爬虫注册表
        self.scrapers: Dict[str, dict] = {}
        self._register_all_scrapers()
        
        # 统计信息
        self.stats = {
            "total_fetched": 0,
            "total_unique": 0,
            "last_run": None
        }
    
    def _register_all_scrapers(self):
        """注册所有爬虫"""
        # 权威国际媒体
        self.scrapers["bbc"] = {
            "module": "bbc",
            "class": "BBCChinese",
            "priority": SourcePriority.CRITICAL,
            "category": [ContentCategory.BREAKING, ContentCategory.POLITICS],
            "weight": 3.0
        }
        self.scrapers["nytimes"] = {
            "module": "nytimes",
            "class": "NYTimes",
            "priority": SourcePriority.CRITICAL,
            "category": [ContentCategory.BREAKING, ContentCategory.POLITICS],
            "weight": 3.0
        }
        self.scrapers["wsj"] = {
            "module": "wsj",
            "class": "WSJ",
            "priority": SourcePriority.CRITICAL,
            "category": [ContentCategory.BUSINESS],
            "weight": 3.0
        }
        self.scrapers["zaobao"] = {
            "module": "zaobao",
            "class": "ZaoBao",
            "priority": SourcePriority.HIGH,
            "category": [ContentCategory.BREAKING],
            "weight": 2.5
        }
        self.scrapers["xinhua"] = {
            "module": "xinhua",
            "class": "XinhuaNews",
            "priority": SourcePriority.HIGH,
            "category": [ContentCategory.BREAKING, ContentCategory.POLITICS],
            "weight": 2.5
        }
        
        # 新增国际媒体
        self.scrapers["cnn"] = {
            "module": "international_media",
            "class": "CNN",
            "priority": SourcePriority.HIGH,
            "category": [ContentCategory.BREAKING],
            "weight": 2.5
        }
        self.scrapers["guardian"] = {
            "module": "international_media",
            "class": "TheGuardian",
            "priority": SourcePriority.HIGH,
            "category": [ContentCategory.BREAKING],
            "weight": 2.5
        }
        self.scrapers["ft"] = {
            "module": "international_media",
            "class": "FinancialTimes",
            "priority": SourcePriority.HIGH,
            "category": [ContentCategory.BUSINESS],
            "weight": 2.5
        }
        self.scrapers["aljazeera"] = {
            "module": "international_media",
            "class": "AlJazeera",
            "priority": SourcePriority.HIGH,
            "category": [ContentCategory.BREAKING],
            "weight": 2.5
        }
        self.scrapers["arstechnica"] = {
            "module": "international_media",
            "class": "ArsTechnica",
            "priority": SourcePriority.MEDIUM,
            "category": [ContentCategory.TECH],
            "weight": 2.0
        }
        
        # V17: 新增聚合爬虫
        self.scrapers["hotrank"] = {
            "module": "hotrank_api",
            "class": "HotRankAggregator",
            "priority": SourcePriority.LOW,
            "category": [ContentCategory.SOCIAL],
            "weight": 1.5
        }
        self.scrapers["google_news"] = {
            "module": "google_news",
            "class": "GoogleNewsRSS",
            "priority": SourcePriority.HIGH,
            "category": [ContentCategory.BREAKING],
            "weight": 2.5
        }
        self.scrapers["newsapi"] = {
            "module": "newsapi_org",
            "class": "NewsAPIOrg",
            "priority": SourcePriority.HIGH,
            "category": [ContentCategory.BREAKING],
            "weight": 2.5
        }
        
        # 国内媒体
        self.scrapers["wangyi"] = {
            "module": "wangyi",
            "class": "WangYi",
            "priority": SourcePriority.MEDIUM,
            "category": [ContentCategory.BREAKING],
            "weight": 1.5
        }
        self.scrapers["pengpai"] = {
            "module": "pengpai",
            "class": "PengPai",
            "priority": SourcePriority.MEDIUM,
            "category": [ContentCategory.BREAKING],
            "weight": 1.5
        }
        self.scrapers["souhu"] = {
            "module": "souhu",
            "class": "SouHu",
            "priority": SourcePriority.LOW,
            "category": [ContentCategory.BREAKING],
            "weight": 1.0
        }
        
        # 科技媒体
        self.scrapers["ithome"] = {
            "module": "ithome",
            "class": "ITHome",
            "priority": SourcePriority.MEDIUM,
            "category": [ContentCategory.TECH],
            "weight": 1.5
        }
        self.scrapers["aipapers"] = {
            "module": "aipapers",
            "class": "AIPapers",
            "priority": SourcePriority.MEDIUM,
            "category": [ContentCategory.TECH, ContentCategory.SCIENCE],
            "weight": 1.5
        }
        self.scrapers["hellogithub"] = {
            "module": "hellogithub",
            "class": "HelloGithub",
            "priority": SourcePriority.LOW,
            "category": [ContentCategory.TECH],
            "weight": 1.2
        }
    
    async def fetch_all(
        self,
        target_count: int = 100,
        categories: Optional[List[str]] = None,
        min_priority: SourcePriority = SourcePriority.LOW,
        languages: Optional[List[str]] = None
    ) -> List[NewsItem]:
        """
        智能抓取所有新闻
        
        Args:
            target_count: 目标获取数量
            categories: 指定分类列表
            min_priority: 最小优先级
            languages: 指定语言列表
            
        Returns:
            去重后的新闻列表
        """
        start_time = time.time()
        self.stats["last_run"] = datetime.now()
        
        logger.info(f"[Universal Engine] 启动大规模抓取 | 目标: {target_count}条")
        
        # 筛选爬虫
        selected_scrapers = self._filter_scrapers(
            min_priority=min_priority,
            categories=categories
        )
        
        logger.info(f"[Universal Engine] 选中 {len(selected_scrapers)} 个爬虫")
        
        # 并发抓取
        all_results: List[FetchResult] = []
        tasks = [
            self._fetch_single_scraper(name, config, target_count // len(selected_scrapers))
            for name, config in selected_scrapers.items()
        ]
        
        results = await asyncio.gather(*tasks, return_exceptions=True)
        
        for result in results:
            if isinstance(result, FetchResult):
                all_results.append(result)
            elif isinstance(result, Exception):
                logger.error(f"[Universal Engine] 爬虫异常: {result}")
        
        # 合并所有新闻
        all_items: List[NewsItem] = []
        for result in all_results:
            all_items.extend(result.items)
        
        self.stats["total_fetched"] = len(all_items)
        
        # 智能去重
        unique_items = self._deduplicate(all_items)
        
        # 热度排序
        unique_items.sort(key=lambda x: x.hot_score, reverse=True)
        
        # 语言过滤
        if languages:
            unique_items = [item for item in unique_items if item.language in languages]
        
        self.stats["total_unique"] = len(unique_items)
        
        elapsed = time.time() - start_time
        logger.success(
            f"[Universal Engine] 抓取完成 | 原始: {len(all_items)} | "
            f"去重后: {len(unique_items)} | 耗时: {elapsed:.2f}s"
        )
        
        return unique_items[:target_count]
    
    def _filter_scrapers(
        self,
        min_priority: SourcePriority,
        categories: Optional[List[str]] = None
    ) -> Dict[str, dict]:
        """筛选爬虫"""
        filtered = {}
        for name, config in self.scrapers.items():
            if config["priority"].value >= min_priority.value:
                if categories:
                    # 检查是否有重叠的分类
                    scraper_cats = [cat.value for cat in config["category"]]
                    if any(cat in scraper_cats for cat in categories):
                        filtered[name] = config
                else:
                    filtered[name] = config
        return filtered
    
    async def _fetch_single_scraper(
        self,
        name: str,
        config: dict,
        target_per_scraper: int
    ) -> FetchResult:
        """获取单个爬虫数据"""
        start_time = time.time()
        
        async with self.semaphore:
            try:
                # 动态导入爬虫
                module = __import__(config["module"], fromlist=[config["class"]])
                spider_class = getattr(module, config["class"])
                spider = spider_class()
                
                # 获取新闻列表
                news_list = await asyncio.wait_for(
                    spider.get_news_list(),
                    timeout=30.0
                )
                
                # 转换为统一格式
                items = []
                for idx, news in enumerate(news_list[:target_per_scraper]):
                    try:
                        item = NewsItem(
                            id=news.get("article_url", "") or str(hash(news.get("title", ""))),
                            title=news.get("title", ""),
                            url=news.get("article_url", ""),
                            summary=news.get("summary", news.get("content", "")[:200]),
                            source=name,
                            source_priority=config["priority"].value,
                            category=config["category"][0].value if config["category"] else "general",
                            published_at=datetime.now(),
                            hot_score=(target_per_scraper - idx) * config["weight"],
                            language=news.get("lang", "zh")
                        )
                        items.append(item)
                    except Exception as e:
                        logger.warning(f"转换新闻项失败: {e}")
                
                fetch_time = time.time() - start_time
                logger.info(f"[{name}] 获取 {len(items)} 条 | 耗时: {fetch_time:.2f}s")
                
                return FetchResult(
                    source=name,
                    items=items,
                    success=True,
                    fetch_time=fetch_time
                )
                
            except asyncio.TimeoutError:
                logger.warning(f"[{name}] 超时")
                return FetchResult(source=name, items=[], success=False, error="Timeout")
            except Exception as e:
                logger.error(f"[{name}] 错误: {e}")
                return FetchResult(source=name, items=[], success=False, error=str(e))
    
    def _deduplicate(self, items: List[NewsItem]) -> List[NewsItem]:
        """智能去重"""
        seen_keys: Set[str] = set()
        unique_items: List[NewsItem] = []
        
        for item in items:
            # 使用标题+来源作为唯一键
            key = item.unique_key
            
            # 检查相似标题（简单实现）
            is_duplicate = False
            for existing in unique_items:
                if self._is_similar_title(item.title, existing.title):
                    # 保留优先级更高的
                    if item.source_priority > existing.source_priority:
                        existing.title = item.title
                        existing.url = item.url
                        existing.source = item.source
                        existing.source_priority = item.source_priority
                    is_duplicate = True
                    break
            
            if not is_duplicate and key not in seen_keys:
                seen_keys.add(key)
                unique_items.append(item)
        
        return unique_items
    
    def _is_similar_title(self, title1: str, title2: str, threshold: float = 0.7) -> bool:
        """检查标题是否相似（简化版）"""
        # 转为小写并去除标点
        t1 = title1.lower().replace(" ", "").replace("，", "").replace("。", "")
        t2 = title2.lower().replace(" ", "").replace("，", "").replace("。", "")
        
        if len(t1) < 10 or len(t2) < 10:
            return t1 == t2
        
        # 简单计算共同子串比例
        from difflib import SequenceMatcher
        similarity = SequenceMatcher(None, t1, t2).ratio()
        return similarity > threshold
    
    def get_stats(self) -> Dict:
        """获取统计信息"""
        return {
            **self.stats,
            "registered_scrapers": len(self.scrapers),
            "cache_size": len(self.cache)
        }


# 全局引擎实例
_universal_engine: Optional[UniversalScraperEngine] = None


def get_universal_engine() -> UniversalScraperEngine:
    """获取全局引擎实例"""
    global _universal_engine
    if _universal_engine is None:
        _universal_engine = UniversalScraperEngine()
    return _universal_engine


if __name__ == "__main__":
    async def test():
        engine = get_universal_engine()
        
        # 测试抓取
        news = await engine.fetch_all(target_count=50)
        
        print(f"\n获取到 {len(news)} 条新闻:")
        for item in news[:10]:
            print(f"[{item.source}] [{item.hot_score:.0f}] {item.title[:60]}...")
        
        print(f"\n统计: {engine.get_stats()}")
    
    asyncio.run(test())
