# -*- coding: utf-8 -*-
"""
NewsHub 主管理器
整合所有组件，提供统一接口
"""

from typing import Dict, List, Any, Optional
from dataclasses import dataclass, field
from datetime import datetime, timedelta
import asyncio
import json

from .data_sources import DataSourceRegistry, DataSourceCategory, DataSource
from .ai_processor import AIContentProcessor, ProcessedContent
from .deduplication import SemanticDeduplicator, NewsItem, DuplicateGroup
from .trend_analyzer import TrendAnalyzer, TrendReport, RealtimeTrendDetector

from src.ai_write_x.utils import log


@dataclass
class AggregationResult:
    """聚合结果"""
    contents: List[ProcessedContent] = field(default_factory=list)
    trends: TrendReport = field(default_factory=TrendReport)
    duplicates: List[DuplicateGroup] = field(default_factory=list)
    stats: Dict[str, Any] = field(default_factory=dict)
    generated_at: datetime = field(default_factory=datetime.now)


class NewsHubManager:
    """
    新闻聚合中心管理器
    
    整合功能：
    1. 多源数据采集
    2. AI智能处理
    3. 语义去重
    4. 趋势分析
    5. 智能通知
    """
    
    def __init__(self, llm_client=None):
        """初始化"""
        self.source_registry = DataSourceRegistry()
        self.ai_processor = AIContentProcessor(llm_client)
        self.deduplicator = SemanticDeduplicator()
        self.trend_analyzer = TrendAnalyzer()
        self.realtime_detector = RealtimeTrendDetector()
        
        self.running = False
        self.aggregation_task = None
        self.callbacks = []
        
        # 缓存路径
        self.cache_path = "knowledge/newshub_cache.json"
        
        log.print_log("[NewsHub] 管理器初始化完成")
    
    async def aggregate_once(self, 
                           categories: Optional[List[DataSourceCategory]] = None,
                           min_score: float = 6.0,
                           enable_ai_processing: bool = True,
                           target_count: int = 100,
                           filter_processed: bool = False) -> AggregationResult:
        """
        执行一次聚合 (V17大规模抓取优化)
        
        Args:
            categories: 指定分类（None表示全部）
            min_score: 最小分数阈值
            enable_ai_processing: 是否启用AI处理
            target_count: 目标获取数量，默认100条
            filter_processed: 是否过滤已处理的主题
            
        Returns:
            聚合结果
        """
        log.print_log(f"[NewsHub V17] 开始新闻聚合，目标: {target_count}条...")
        
        result = AggregationResult()
        start_time = datetime.now()
        
        try:
            # 1. 获取数据源
            if categories:
                sources = []
                for cat in categories:
                    sources.extend(self.source_registry.get_sources_by_category(cat))
            else:
                sources = self.source_registry.get_enabled_sources()
            
            # V17: 按优先级排序，优先高质量源
            sources.sort(key=lambda s: s.priority, reverse=True)
            
            log.print_log(f"[NewsHub] 激活数据源: {len(sources)} 个")
            
            # 2. 采集数据（异步，V17支持大规模抓取）
            raw_contents = await self._fetch_from_sources(sources, target_count)
            log.print_log(f"[NewsHub] 原始内容: {len(raw_contents)} 条 (目标: {target_count})")
            
            # 3. 转换为新闻项
            news_items = self._convert_to_news_items(raw_contents)
            
            # V15.2: 过滤已处理的主题
            if filter_processed:
                from src.ai_write_x.utils.topic_deduplicator import TopicDeduplicator
                dedup = TopicDeduplicator(dedup_days=30) # 过滤最近30天已处理的
                original_count = len(news_items)
                news_items = [
                    item for item in news_items 
                    if not dedup.is_duplicate(item.title)
                ]
                log.print_log(f"[NewsHub] 过滤已处理话题: {original_count} -> {len(news_items)} (过滤数: {original_count - len(news_items)})")
            
            # 4. 去重
            unique_items, duplicate_groups = self.deduplicator.deduplicate(news_items)
            log.print_log(f"[NewsHub] 去重后: {len(unique_items)} 条 (去重率: {(1-len(unique_items)/max(1,len(news_items)))*100:.1f}%)")
            
            result.duplicates = duplicate_groups
            
            # 5. AI处理
            if enable_ai_processing:
                processed_contents = await self._process_with_ai(unique_items)
                
                # 按分数过滤
                processed_contents = [
                    c for c in processed_contents 
                    if c.score.overall >= min_score
                ]
                log.print_log(f"[NewsHub] AI处理后: {len(processed_contents)} 条 (分数>={min_score})")
            else:
                processed_contents = self._basic_process(unique_items)
            
            result.contents = processed_contents
            
            # 6. 趋势分析
            trend_data = [
                {
                    "keywords": c.keywords,
                    "category": c.category,
                    "source": c.metadata.get("source", ""),
                    "published_at": c.metadata.get("published_at", datetime.now()),
                    "sentiment": c.sentiment.sentiment.value,
                }
                for c in processed_contents
            ]
            
            trends = self.trend_analyzer.analyze_trends(trend_data)
            result.trends = trends
            
            # 7. 更新实时检测器
            for content in processed_contents:
                self.realtime_detector.add_item({
                    "keywords": content.keywords,
                    "category": content.category,
                })
            
            # 8. 生成统计
            elapsed = (datetime.now() - start_time).total_seconds()
            result.stats = {
                "elapsed_time": elapsed,
                "total_sources": len(sources),
                "raw_contents": len(raw_contents),
                "unique_contents": len(unique_items),
                "final_contents": len(processed_contents),
                "duplicates_removed": len(news_items) - len(unique_items),
                "trends_found": len(trends.top_trends),
                "avg_score": sum(c.score.overall for c in processed_contents) / max(1, len(processed_contents)),
            }
            
            log.print_log(f"[NewsHub] 聚合完成，耗时: {elapsed:.2f}s")
            
            # 9. 缓存结果到本地文件供其他模块共享
            self._cache_results(result)
            
            # 触发回调
            await self._trigger_callbacks(result)
            
        except Exception as e:
            log.print_log(f"[NewsHub] 聚合失败: {e}", "error")
        
        return result
    
    async def start_continuous_aggregation(self, 
                                         interval: int = 300,
                                         callback=None):
        """
        启动持续聚合
        
        Args:
            interval: 聚合间隔（秒）
            callback: 回调函数
        """
        if callback:
            self.callbacks.append(callback)
        
        self.running = True
        log.print_log(f"[NewsHub] 启动持续聚合，间隔: {interval}s")
        
        while self.running:
            try:
                result = await self.aggregate_once()
                
                # 等待间隔
                await asyncio.sleep(interval)
                
            except Exception as e:
                log.print_log(f"[NewsHub] 持续聚合出错: {e}", "error")
                await asyncio.sleep(60)  # 出错后等待1分钟
    
    def stop(self):
        """停止聚合"""
        self.running = False
        log.print_log("[NewsHub] 已停止")
    
    async def _fetch_from_sources(self, sources: List[DataSource], target_count: int = 100) -> List[Dict[str, Any]]:
        """
        从多个数据源获取数据 (V17大规模抓取优化)
        
        Args:
            sources: 数据源列表
            target_count: 目标获取数量，用于动态调整策略
        """
        all_contents = []
        
        # V17: 提升并发数以支持大规模抓取 (20->50)
        concurrency_limit = min(50, max(20, target_count // 5))
        semaphore = asyncio.Semaphore(concurrency_limit)
        
        log.print_log(f"[NewsHub V17] 从 {len(sources)} 个数据源获取，目标: {target_count}条，并发: {concurrency_limit}")
        
        async def fetch_with_limit(source: DataSource):
            async with semaphore:
                try:
                    # V17: 延长超时以支持大规模抓取
                    contents = await asyncio.wait_for(
                        self._fetch_single_source(source),
                        timeout=30.0
                    )
                    log.print_log(f"[NewsHub] ✓ {source.name}: {len(contents)}条")
                    return contents
                except asyncio.TimeoutError:
                    log.print_log(f"[NewsHub] ✗ {source.name}: 超时", "warning")
                    return []
                except Exception as e:
                    log.print_log(f"[NewsHub] ✗ {source.name}: {e}", "warning")
                    return []
        
        # 分批并行获取，避免一次性创建过多任务
        batch_size = 20
        for i in range(0, len(sources), batch_size):
            batch = sources[i:i+batch_size]
            tasks = [fetch_with_limit(source) for source in batch]
            results = await asyncio.gather(*tasks)
            
            for contents in results:
                all_contents.extend(contents)
            
            # 如果已经达到目标数量，提前结束
            if len(all_contents) >= target_count:
                log.print_log(f"[NewsHub] 已达成目标数量: {len(all_contents)}条")
                break
        
        return all_contents
    
    async def _fetch_single_source(self, source: DataSource) -> List[Dict[str, Any]]:
        """从单个数据源获取数据"""
        # 如果有自定义获取函数，使用它
        if source.fetcher:
            return await source.fetcher()
        
        # 根据类型选择获取方式
        if source.type.value == "api":
            return await self._fetch_api_source(source)
        elif source.type.value == "rss":
            return await self._fetch_rss_source(source)
        elif source.type.value == "github":
            return await self._fetch_github_source(source)
        else:
            # 默认返回空
            return []
    
    async def _fetch_api_source(self, source: DataSource) -> List[Dict[str, Any]]:
        """获取API数据源"""
        import aiohttp
        
        contents = []
        
        try:
            # Hacker News 特殊处理
            if source.id == "hackernews":
                return await self._fetch_hackernews(source)
            
            # 获取全局代理
            from src.ai_write_x.config.config import Config
            proxy = Config.get_instance().proxy or None
            
            async with aiohttp.ClientSession() as session:
                async with session.get(
                    source.api_endpoint or source.url,
                    proxy=proxy,
                    timeout=aiohttp.ClientTimeout(total=10)
                ) as response:
                    if response.status == 200:
                        data = await response.json()
                        # 解析响应数据（简化实现）
                        if isinstance(data, list):
                            for item in data:
                                # 处理可能是整数ID的情况（如Hacker News）
                                if isinstance(item, int):
                                    continue  # 跳过ID，需要单独获取详情
                                elif isinstance(item, dict):
                                    contents.append({
                                        "id": str(item.get("id", hash(str(item)))),
                                        "title": item.get("title", ""),
                                        "content": item.get("content", item.get("summary", "")),
                                        "url": item.get("url", ""),
                                        "source": source.name,
                                        "published_at": item.get("published_at", datetime.now()),
                                    })
        except Exception as e:
            log.print_log(f"[NewsHub] API获取失败 {source.name}: {e}", "warning")
        
        return contents
    
    async def _fetch_hackernews(self, source: DataSource) -> List[Dict[str, Any]]:
        """获取Hacker News热门故事"""
        import aiohttp
        
        contents = []
        item_endpoint = source.config.get("item_endpoint", "https://hacker-news.firebaseio.com/v0/item/")
        
        try:
            # 获取全局代理
            from src.ai_write_x.config.config import Config
            proxy = Config.get_instance().proxy or None

            async with aiohttp.ClientSession() as session:
                # 先获取热门故事ID列表
                async with session.get(
                    source.api_endpoint,
                    proxy=proxy,
                    timeout=aiohttp.ClientTimeout(total=10)
                ) as response:
                    if response.status == 200:
                        story_ids = await response.json()
                        if isinstance(story_ids, list):
                            # 只取前10个故事
                            for story_id in story_ids[:10]:
                                try:
                                    # 获取每个故事的详情
                                    async with session.get(
                                        f"{item_endpoint}{story_id}.json",
                                        proxy=proxy,
                                        timeout=aiohttp.ClientTimeout(total=10)
                                    ) as story_response:
                                        if story_response.status == 200:
                                            story = await story_response.json()
                                            if story and isinstance(story, dict):
                                                contents.append({
                                                    "id": str(story.get("id", story_id)),
                                                    "title": story.get("title", "No Title"),
                                                    "content": story.get("text", ""),
                                                    "url": story.get("url", f"https://news.ycombinator.com/item?id={story_id}"),
                                                    "source": source.name,
                                                    "published_at": datetime.fromtimestamp(story.get("time", 0)) if story.get("time") else datetime.now(),
                                                })
                                except Exception as e:
                                    continue  # 单个故事获取失败，继续下一个
        except Exception as e:
            log.print_log(f"[NewsHub] Hacker News获取失败: {e}", "warning")
        
        return contents
    
    async def _fetch_rss_source(self, source: DataSource) -> List[Dict[str, Any]]:
        """获取RSS数据源"""
        # 检查 feedparser 是否可用
        try:
            import feedparser
        except ImportError:
            log.print_log("[NewsHub] feedparser 未安装，跳过 RSS 源", "warning")
            return []
        
        import aiohttp
        
        contents = []
        
        try:
            # 获取全局代理
            from src.ai_write_x.config.config import Config
            proxy = Config.get_instance().proxy or None

            async with aiohttp.ClientSession() as session:
                async with session.get(
                    source.api_endpoint or source.url,
                    proxy=proxy,
                    timeout=aiohttp.ClientTimeout(total=10)
                ) as response:
                    if response.status == 200:
                        text = await response.text()
                        feed = feedparser.parse(text)
                        
                        for entry in feed.entries[:20]:  # 限制数量
                            contents.append({
                                "id": entry.get("id", hash(entry.title)),
                                "title": entry.title,
                                "content": entry.get("summary", entry.get("description", "")),
                                "url": entry.link,
                                "source": source.name,
                                "published_at": datetime(*entry.published_parsed[:6]) if hasattr(entry, 'published_parsed') else datetime.now(),
                            })
        except Exception as e:
            log.print_log(f"[NewsHub] RSS获取失败 {source.name}: {e}", "warning")
        
        return contents
    
    async def _fetch_github_source(self, source: DataSource) -> List[Dict[str, Any]]:
        """获取GitHub数据源"""
        # 简化实现：使用GitHub API
        contents = []
        
        try:
            trending_url = "https://api.github.com/search/repositories"
            params = {
                "q": "created:>2024-01-01",
                "sort": "stars",
                "order": "desc",
                "per_page": 20
            }
            
            # 获取全局代理
            from src.ai_write_x.config.config import Config
            proxy = Config.get_instance().proxy or None

            import aiohttp
            async with aiohttp.ClientSession() as session:
                async with session.get(trending_url, params=params, proxy=proxy) as response:
                    if response.status == 200:
                        data = await response.json()
                        for repo in data.get("items", []):
                            contents.append({
                                "id": f"github_{repo['id']}",
                                "title": f"{repo['full_name']} - {repo['description'] or 'No description'}",
                                "content": f"⭐ {repo['stargazers_count']} stars | {repo['language'] or 'Unknown'} | {repo['description'] or ''}",
                                "url": repo["html_url"],
                                "source": "GitHub Trending",
                                "published_at": datetime.now(),
                                "metadata": {
                                    "stars": repo["stargazers_count"],
                                    "language": repo["language"],
                                    "forks": repo["forks_count"],
                                }
                            })
        except Exception as e:
            log.print_log(f"[NewsHub] GitHub获取失败: {e}", "warning")
        
        return contents
    
    def _convert_to_news_items(self, raw_contents: List[Dict[str, Any]]) -> List[NewsItem]:
        """将原始内容转换为新闻项"""
        items = []
        
        for content in raw_contents:
            item = NewsItem(
                id=content.get("id", str(hash(content.get("title", "")))),
                title=content.get("title", ""),
                content=content.get("content", ""),
                url=content.get("url", ""),
                source=content.get("source", ""),
                published_at=content.get("published_at", datetime.now()),
                keywords=content.get("keywords", []),
            )
            items.append(item)
        
        return items
    
    async def _process_with_ai(self, items: List[NewsItem]) -> List[ProcessedContent]:
        """使用AI处理新闻"""
        contents = [
            {
                "id": item.id,
                "title": item.title,
                "content": item.content,
                "source": item.source,
            }
            for item in items
        ]
        
        return await self.ai_processor.batch_process(contents)
    
    def _basic_process(self, items: List[NewsItem]) -> List[ProcessedContent]:
        """基础处理（无AI）"""
        processed = []
        
        for item in items:
            pc = ProcessedContent(
                id=item.id,
                title=item.title,
                original_content=item.content,
                summary=item.content[:200] + "..." if len(item.content) > 200 else item.content,
                keywords=item.keywords,
            )
            processed.append(pc)
        
        return processed
    
    async def _trigger_callbacks(self, result: AggregationResult):
        """触发回调"""
        for callback in self.callbacks:
            try:
                if asyncio.iscoroutinefunction(callback):
                    await callback(result)
                else:
                    callback(result)
            except Exception as e:
                log.print_log(f"[NewsHub] 回调执行失败: {e}", "warning")
    
    def get_sources_info(self) -> List[Dict[str, Any]]:
        """获取数据源信息"""
        return self.source_registry.get_sources_info()
    
    def enable_source(self, source_id: str):
        """启用数据源"""
        self.source_registry.enable_source(source_id)
    
    def disable_source(self, source_id: str):
        """禁用数据源"""
        self.source_registry.disable_source(source_id)
    
    def get_realtime_trends(self, top_n: int = 10) -> List[str]:
        """获取实时趋势"""
        return self.realtime_detector.get_current_trends(top_n)
    
    def is_trending(self, keyword: str) -> bool:
        """检查关键词是否正在 trending"""
        return self.realtime_detector.is_trending(keyword)

    def _cache_results(self, result: AggregationResult):
        """缓存聚合结果到文件"""
        import os
        try:
            os.makedirs(os.path.dirname(self.cache_path), exist_ok=True)
            
            data = {
                "generated_at": result.generated_at.isoformat(),
                "contents": [
                    {
                        "id": c.id,
                        "title": c.title,
                        "summary": c.summary,
                        "url": c.metadata.get("url", ""),
                        "source": c.metadata.get("source", "热点聚合"),
                        "score": c.score.overall,
                        "keywords": c.keywords,
                        "published_at": c.metadata.get("published_at", datetime.now()).isoformat() if isinstance(c.metadata.get("published_at"), datetime) else str(c.metadata.get("published_at"))
                    }
                    for c in result.contents
                ],
                "trends": [
                    {"keyword": t.keyword, "score": t.hot_score}
                    for t in result.trends.top_trends
                ]
            }
            
            with open(self.cache_path, "w", encoding="utf-8") as f:
                json.dump(data, f, ensure_ascii=False, indent=4)
        except Exception as e:
            log.print_log(f"[NewsHub] 缓存结果失败: {e}", "error")

    def get_cached_news(self, limit: int = 100) -> List[Dict[str, Any]]:
        """从缓存加载最近的新闻"""
        import os
        if not os.path.exists(self.cache_path):
            return []
            
        try:
            with open(self.cache_path, "r", encoding="utf-8") as f:
                data = json.load(f)
                return data.get("contents", [])[:limit]
        except Exception as e:
            return []


# 便捷函数
async def aggregate_news(categories: List[str] = None, 
                        min_score: float = 6.0) -> AggregationResult:
    """便捷函数：执行一次新闻聚合"""
    manager = NewsHubManager()
    
    # 转换分类字符串为枚举
    cat_enums = None
    if categories:
        cat_map = {
            "tech": DataSourceCategory.TECH,
            "finance": DataSourceCategory.FINANCE,
            "social": DataSourceCategory.SOCIAL,
            "programming": DataSourceCategory.PROGRAMMING,
            "ai": DataSourceCategory.AI_ML,
            "startup": DataSourceCategory.STARTUP,
        }
        cat_enums = [cat_map.get(c.lower()) for c in categories if cat_map.get(c.lower())]
    
    return await manager.aggregate_once(
        categories=cat_enums,
        min_score=min_score
    )
