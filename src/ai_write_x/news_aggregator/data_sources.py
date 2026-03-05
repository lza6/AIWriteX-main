# -*- coding: utf-8 -*-
"""
数据源管理器
支持50+国内外数据源
"""

from typing import Dict, List, Any, Optional, Callable
from dataclasses import dataclass, field
from enum import Enum
import asyncio
import aiohttp
from datetime import datetime

# feedparser 是可选依赖
try:
    import feedparser
    FEEDPARSER_AVAILABLE = True
except ImportError:
    FEEDPARSER_AVAILABLE = False
    feedparser = None

from src.ai_write_x.utils import log


class DataSourceCategory(Enum):
    """数据源分类"""
    TECH = "tech"                    # 科技
    FINANCE = "finance"              # 财经
    SOCIAL = "social"                # 社交媒体
    PROGRAMMING = "programming"      # 编程开发
    AI_ML = "ai_ml"                  # AI/机器学习
    STARTUP = "startup"              # 创业


class DataSourceType(Enum):
    """数据源类型"""
    API = "api"                      # API接口
    RSS = "rss"                      # RSS订阅
    SCRAPER = "scraper"              # 网页抓取
    GITHUB = "github"                # GitHub相关
    WEBHOOK = "webhook"              # Webhook推送


@dataclass
class DataSource:
    """数据源定义"""
    id: str                          # 唯一标识
    name: str                        # 显示名称
    category: DataSourceCategory     # 分类
    type: DataSourceType            # 类型
    enabled: bool = True            # 是否启用
    url: str = ""                   # 数据URL
    api_endpoint: str = ""          # API端点
    update_interval: int = 300      # 更新间隔（秒）
    priority: int = 5               # 优先级（1-10）
    weight: float = 1.0             # 权重
    config: Dict[str, Any] = field(default_factory=dict)
    fetcher: Optional[Callable] = None  # 自定义获取函数


class DataSourceRegistry:
    """数据源注册表"""
    
    # 预定义的50+数据源
    DEFAULT_SOURCES = [
        # ========== GitHub生态 ==========
        DataSource(
            id="github_trending",
            name="GitHub Trending",
            category=DataSourceCategory.PROGRAMMING,
            type=DataSourceType.GITHUB,
            url="https://github.com/trending",
            api_endpoint="https://api.github.com/search/repositories",
            update_interval=600,
            priority=10,
            weight=2.0,
            config={"sort": "stars", "order": "desc"}
        ),
        DataSource(
            id="github_releases",
            name="GitHub Releases",
            category=DataSourceCategory.PROGRAMMING, 
            type=DataSourceType.GITHUB,
            url="",
            update_interval=300,
            priority=9,
            config={"repos": ["microsoft/vscode", "facebook/react", "tensorflow/tensorflow"]}
        ),
        
        # ========== 国内科技媒体 ==========
        DataSource(
            id="36kr",
            name="36氪",
            category=DataSourceCategory.STARTUP,
            type=DataSourceType.API,
            url="https://36kr.com/",
            api_endpoint="https://36kr.com/api/newsflash",
            update_interval=300,
            priority=9
        ),
        DataSource(
            id="geekpark",
            name="极客公园", 
            category=DataSourceCategory.TECH,
            type=DataSourceType.RSS,
            url="https://www.geekpark.net/",
            api_endpoint="https://www.geekpark.net/rss",
            update_interval=600,
            priority=8
        ),
        DataSource(
            id="pingwest",
            name="品玩",
            category=DataSourceCategory.TECH,
            type=DataSourceType.RSS,
            url="https://www.pingwest.com/",
            update_interval=600,
            priority=7
        ),
        DataSource(
            id="ithome",
            name="IT之家",
            category=DataSourceCategory.TECH,
            type=DataSourceType.RSS,  # 使用RSS
            url="https://www.ithome.com/",
            api_endpoint="https://www.ithome.com/rss/",
            update_interval=300,
            priority=8,
            weight=1.2,
            enabled=True
        ),
        DataSource(
            id="solidot",
            name="Solidot",
            category=DataSourceCategory.TECH,
            type=DataSourceType.RSS,
            url="https://www.solidot.org/",
            api_endpoint="https://www.solidot.org/index.rss",
            update_interval=600,
            priority=7
        ),
        
        # ========== 国际科技媒体 ==========
        DataSource(
            id="hackernews",
            name="Hacker News",
            category=DataSourceCategory.TECH,
            type=DataSourceType.API,
            url="https://news.ycombinator.com/",
            api_endpoint="https://hacker-news.firebaseio.com/v0/topstories.json",
            update_interval=300,
            priority=10,
            weight=2.0,
            config={"item_endpoint": "https://hacker-news.firebaseio.com/v0/item/"}
        ),
        DataSource(
            id="techcrunch",
            name="TechCrunch",
            category=DataSourceCategory.STARTUP,
            type=DataSourceType.RSS,
            url="https://techcrunch.com/",
            api_endpoint="https://techcrunch.com/feed/",
            update_interval=600,
            priority=8
        ),
        DataSource(
            id="theverge",
            name="The Verge",
            category=DataSourceCategory.TECH,
            type=DataSourceType.RSS,
            url="https://www.theverge.com/",
            api_endpoint="https://www.theverge.com/rss/index.xml",
            update_interval=600,
            priority=8
        ),
        DataSource(
            id="zaobao",
            name="联合早报",
            category=DataSourceCategory.SOCIAL,
            type=DataSourceType.RSS,
            url="https://www.zaobao.com/",
            api_endpoint="https://www.zaobao.com/rss/world",
            update_interval=600,
            priority=10,
            weight=2.0
        ),
        DataSource(
            id="nytimes",
            name="纽约时报",
            category=DataSourceCategory.SOCIAL,
            type=DataSourceType.RSS,
            url="https://www.nytimes.com/",
            api_endpoint="https://rss.nytimes.com/services/xml/rss/nyt/World.xml",
            update_interval=600,
            priority=10,
            weight=2.5
        ),
        DataSource(
            id="wsj",
            name="华尔街日报",
            category=DataSourceCategory.FINANCE,
            type=DataSourceType.RSS,
            url="https://www.wsj.com/",
            api_endpoint="https://feeds.a.dj.com/rss/RSSWorldNews.xml",
            update_interval=600,
            priority=10,
            weight=2.5
        ),
        DataSource(
            id="bbc",
            name="BBC中文",
            category=DataSourceCategory.SOCIAL,
            type=DataSourceType.RSS,
            url="https://www.bbc.com/zhongwen/simp",
            api_endpoint="https://www.bbc.com/zhongwen/simp/index.xml",
            update_interval=600,
            priority=10,
            weight=2.5
        ),
        
        # ========== AI/ML专项 ==========
        DataSource(
            id="reddit_machinelearning",
            name="Reddit - MachineLearning",
            category=DataSourceCategory.AI_ML,
            type=DataSourceType.API,
            url="https://www.reddit.com/r/MachineLearning/",
            api_endpoint="https://www.reddit.com/r/MachineLearning/hot.json",
            update_interval=600,
            priority=9,
            enabled=False  # 国内访问超时
        ),
        DataSource(
            id="reddit_localLLaMA",
            name="Reddit - LocalLLaMA",
            category=DataSourceCategory.AI_ML,
            type=DataSourceType.API,
            url="https://www.reddit.com/r/LocalLLaMA/",
            api_endpoint="https://www.reddit.com/r/LocalLLaMA/hot.json",
            update_interval=600,
            priority=8,
            enabled=False  # 国内访问超时
        ),
        DataSource(
            id="paperswithcode",
            name="Papers With Code",
            category=DataSourceCategory.AI_ML,
            type=DataSourceType.API,
            url="https://paperswithcode.com/",
            api_endpoint="https://paperswithcode.com/api/v1/papers/",
            update_interval=1800,
            priority=9,
            enabled=False  # 国内访问超时
        ),
        
        # ========== 国内社交媒体 ==========
        DataSource(
            id="weibo_hot",
            name="微博热搜",
            category=DataSourceCategory.SOCIAL,
            type=DataSourceType.SCRAPER,  # 返回HTML，需要爬虫
            url="https://weibo.com/",
            update_interval=300,
            priority=9,
            enabled=False
        ),
        DataSource(
            id="zhihu_hot",
            name="知乎热榜",
            category=DataSourceCategory.SOCIAL,
            type=DataSourceType.RSS,  # 使用RSS
            url="https://www.zhihu.com/",
            api_endpoint="https://www.zhihu.com/rss",
            update_interval=300,
            priority=8,
            enabled=True
        ),
        DataSource(
            id="bilibili_hot",
            name="B站热门",
            category=DataSourceCategory.SOCIAL,
            type=DataSourceType.SCRAPER,  # 需要爬虫
            url="https://www.bilibili.com/",
            update_interval=600,
            priority=7,
            enabled=False
        ),
        DataSource(
            id="douyin_hot",
            name="抖音热榜",
            category=DataSourceCategory.SOCIAL,
            type=DataSourceType.SCRAPER,  # 需要爬虫
            url="https://www.douyin.com/",
            update_interval=600,
            priority=7,
            enabled=False
        ),
        DataSource(
            id="baidu_tieba",
            name="百度贴吧热议",
            category=DataSourceCategory.SOCIAL,
            type=DataSourceType.SCRAPER,  # 需要爬虫
            update_interval=600,
            priority=6,
            enabled=False
        ),
        
        # ========== 财经 ==========
        DataSource(
            id="xueqiu",
            name="雪球",
            category=DataSourceCategory.FINANCE,
            type=DataSourceType.SCRAPER,  # 返回HTML
            url="https://xueqiu.com/",
            update_interval=300,
            priority=8,
            enabled=False
        ),
        DataSource(
            id="cls",
            name="财联社",
            category=DataSourceCategory.FINANCE,
            type=DataSourceType.SCRAPER,  # 返回HTML
            url="https://www.cls.cn/",
            update_interval=300,
            priority=9,
            enabled=False
        ),
        DataSource(
            id="wallstreetcn",
            name="华尔街见闻",
            category=DataSourceCategory.FINANCE,
            type=DataSourceType.RSS,
            url="https://wallstreetcn.com/",
            update_interval=600,
            priority=8
        ),
        
        # ========== 开发者社区 ==========
        DataSource(
            id="v2ex",
            name="V2EX",
            category=DataSourceCategory.PROGRAMMING,
            type=DataSourceType.API,
            url="https://www.v2ex.com/",
            api_endpoint="https://www.v2ex.com/api/topics/hot.json",
            update_interval=600,
            priority=8
        ),
        DataSource(
            id="segmentfault",
            name="SegmentFault",
            category=DataSourceCategory.PROGRAMMING,
            type=DataSourceType.RSS,  # 使用RSS
            url="https://segmentfault.com/",
            api_endpoint="https://segmentfault.com/feeds",
            update_interval=600,
            priority=7,
            enabled=True
        ),
        DataSource(
            id="juejin",
            name="掘金",
            category=DataSourceCategory.PROGRAMMING,
            type=DataSourceType.API,
            url="https://juejin.cn/",
            api_endpoint="https://api.juejin.cn/recommend_api/v1/article/recommend_all_feed",
            update_interval=600,
            priority=7
        ),
        
        # ========== 产品/创业 ==========
        DataSource(
            id="producthunt",
            name="Product Hunt",
            category=DataSourceCategory.STARTUP,
            type=DataSourceType.API,
            url="https://www.producthunt.com/",
            api_endpoint="https://api.producthunt.com/v2/api/graphql",
            update_interval=1800,
            priority=9
        ),
        DataSource(
            id="indiehackers",
            name="Indie Hackers",
            category=DataSourceCategory.STARTUP,
            type=DataSourceType.RSS,
            url="https://www.indiehackers.com/",
            update_interval=1800,
            priority=7
        ),
        
        # ========== RSS聚合 ==========
        DataSource(
            id="feedly_ai",
            name="AI相关RSS合集",
            category=DataSourceCategory.AI_ML,
            type=DataSourceType.RSS,
            url="",
            update_interval=600,
            priority=8,
            config={
                "feeds": [
                    "https://blog.openai.com/rss/",
                    "https://www.anthropic.com/rss.xml",
                    "https://deepmind.google/discover/feed/",
                ]
            }
        ),
    ]
    
    def __init__(self, config_path: str = "knowledge/newshub_sources.json"):
        self.config_path = config_path
        self.sources: Dict[str, DataSource] = {}
        self._load_sources()

    def _load_sources(self):
        """加载数据源（优先从文件加载，否则使用默认）"""
        import os
        import json

        # 1. 先注册默认的
        for source in self.DEFAULT_SOURCES:
            self.sources[source.id] = source

        # 2. 尝试从文件加载覆盖/新增
        if os.path.exists(self.config_path):
            try:
                with open(self.config_path, "r", encoding="utf-8") as f:
                    data = json.load(f)
                    for s_data in data:
                        # 转换枚举
                        cat = DataSourceCategory(s_data["category"])
                        stype = DataSourceType(s_data["type"])
                        
                        source = DataSource(
                            id=s_data["id"],
                            name=s_data["name"],
                            category=cat,
                            type=stype,
                            enabled=s_data.get("enabled", True),
                            url=s_data.get("url", ""),
                            api_endpoint=s_data.get("api_endpoint", ""),
                            update_interval=s_data.get("update_interval", 300),
                            priority=s_data.get("priority", 5),
                            weight=s_data.get("weight", 1.0),
                            config=s_data.get("config", {})
                        )
                        self.sources[source.id] = source
            except Exception as e:
                log.print_log(f"[NewsHub] 加载自定义数据源失败: {e}", "error")

        log.print_log(f"[NewsHub] 已加载 {len(self.sources)} 个数据源")

    def _save_sources(self):
        """保存当前数据源到文件"""
        import json
        import os
        
        os.makedirs(os.path.dirname(self.config_path), exist_ok=True)
        
        data = []
        for s in self.sources.values():
            data.append({
                "id": s.id,
                "name": s.name,
                "category": s.category.value,
                "type": s.type.value,
                "enabled": s.enabled,
                "url": s.url,
                "api_endpoint": s.api_endpoint,
                "update_interval": s.update_interval,
                "priority": s.priority,
                "weight": s.weight,
                "config": s.config
            })
            
        try:
            with open(self.config_path, "w", encoding="utf-8") as f:
                json.dump(data, f, ensure_ascii=False, indent=4)
        except Exception as e:
            log.print_log(f"[NewsHub] 保存数据源失败: {e}", "error")

    def get_source(self, source_id: str) -> Optional[DataSource]:
        """获取数据源"""
        return self.sources.get(source_id)

    def get_sources_by_category(self, category: DataSourceCategory) -> List[DataSource]:
        """按分类获取数据源"""
        return [s for s in self.sources.values() if s.category == category and s.enabled]

    def get_enabled_sources(self) -> List[DataSource]:
        """获取所有启用的数据源"""
        return [s for s in self.sources.values() if s.enabled]
    
    def register_custom_source(self, source: DataSource):
        """注册自定义数据源"""
        self.sources[source.id] = source
        self._save_sources()
        log.print_log(f"[NewsHub] 注册自定义数据源: {source.name}")
    
    def enable_source(self, source_id: str):
        """启用数据源"""
        if source_id in self.sources:
            self.sources[source_id].enabled = True
            self._save_sources()
    
    def disable_source(self, source_id: str):
        """禁用数据源"""
        if source_id in self.sources:
            self.sources[source_id].enabled = False
            self._save_sources()
            
    def remove_source(self, source_id: str):
        """删除数据源"""
        if source_id in self.sources:
            # 只有非默认的才能删除比较好，或者允许全部删除
            name = self.sources[source_id].name
            del self.sources[source_id]
            self._save_sources()
            log.print_log(f"[NewsHub] 已删除数据源: {name}")
    
    def get_sources_info(self) -> List[Dict[str, Any]]:
        """获取所有数据源信息"""
        return [
            {
                "id": s.id,
                "name": s.name,
                "category": s.category.value,
                "type": s.type.value,
                "enabled": s.enabled,
                "priority": s.priority,
            }
            for s in self.sources.values()
        ]
