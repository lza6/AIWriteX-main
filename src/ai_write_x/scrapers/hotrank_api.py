#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
全网热榜聚合爬虫 V17 - 最强热点抓取
整合：知乎、微博、头条、百度、V2EX、GitHub、HackerNews、抖音等
"""
import asyncio
import aiohttp
import json
from datetime import datetime
from typing import List, Dict, Optional
from lxml import etree

from base import BaseSpider
from logger_utils import logger


class HotRankAggregator(BaseSpider):
    """
    全网热榜聚合爬虫
    基于各种公开API和RSS，无需登录即可获取热榜数据
    """
    source_name = "全网热榜聚合"
    category = "热点"
    
    # V17: 热榜API配置 (基于开源项目和网络公开API)
    HOT_APIS = {
        # 知乎热榜
        "zhihu": {
            "url": "https://www.zhihu.com/api/v3/feed/topstory/hot-lists/total",
            "headers": {
                "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36"
            },
            "weight": 2.0
        },
        # V2EX热门
        "v2ex": {
            "url": "https://www.v2ex.com/api/topics/hot.json",
            "headers": {},
            "weight": 1.5
        },
        # GitHub Trending
        "github": {
            "url": "https://api.github.com/search/repositories",
            "params": {"q": "created:>2024-01-01", "sort": "stars", "order": "desc", "per_page": 30},
            "headers": {},
            "weight": 1.8
        },
        # Hacker News
        "hackernews": {
            "url": "https://hacker-news.firebaseio.com/v0/topstories.json",
            "headers": {},
            "weight": 2.0
        },
        # 百度热搜 (通过RSSHub或第三方)
        "baidu": {
            "url": "https://rsshub.app/baidu/topwords/1",
            "headers": {},
            "is_rss": True,
            "weight": 1.5
        },
        # 少数派热门
        "sspai": {
            "url": "https://sspai.com/api/v1/article/tag/feed",
            "headers": {},
            "weight": 1.2
        },
        # 掘金热门
        "juejin": {
            "url": "https://api.juejin.cn/recommend_api/v1/article/recommend_all_feed",
            "params": {"page_type": 0, "cursor": "0", "sort_type": 200, "limit": 30},
            "headers": {},
            "weight": 1.3
        }
    }

    async def get_news_list(self, category: dict = None) -> List[Dict]:
        """
        获取全网热榜聚合
        并发获取所有热榜API，合并去重后返回
        """
        all_items = []
        semaphore = asyncio.Semaphore(10)  # 限制并发
        
        async def fetch_single(source_id: str, config: dict):
            async with semaphore:
                try:
                    items = await self._fetch_api(source_id, config)
                    logger.info(f"[{source_id}] 获取到 {len(items)} 条热榜")
                    return items
                except Exception as e:
                    logger.warning(f"[{source_id}] 获取失败: {e}")
                    return []
        
        # 并发获取所有热榜
        tasks = [
            fetch_single(source_id, config) 
            for source_id, config in self.HOT_APIS.items()
        ]
        results = await asyncio.gather(*tasks, return_exceptions=True)
        
        # 合并结果
        for items in results:
            if isinstance(items, list):
                all_items.extend(items)
        
        # 按热度权重排序
        all_items.sort(key=lambda x: x.get("hot_score", 0), reverse=True)
        
        logger.success(f"全网热榜聚合完成，共 {len(all_items)} 条")
        return all_items[:50]  # 返回前50条

    async def _fetch_api(self, source_id: str, config: dict) -> List[Dict]:
        """获取单个热榜API"""
        url = config["url"]
        headers = config.get("headers", {})
        params = config.get("params", {})
        weight = config.get("weight", 1.0)
        is_rss = config.get("is_rss", False)
        
        async with aiohttp.ClientSession() as session:
            async with session.get(
                url, 
                headers=headers, 
                params=params,
                timeout=aiohttp.ClientTimeout(total=15)
            ) as response:
                if response.status != 200:
                    return []
                
                data = await response.text()
                
                if is_rss:
                    return self._parse_rss(data, source_id, weight)
                else:
                    json_data = json.loads(data)
                    return self._parse_json(source_id, json_data, weight)

    def _parse_json(self, source_id: str, data: dict, weight: float) -> List[Dict]:
        """解析JSON格式热榜"""
        items = []
        
        try:
            if source_id == "zhihu":
                # 知乎热榜格式
                for idx, item in enumerate(data.get("data", [])[:20]):
                    target = item.get("target", {})
                    title = target.get("title", "")
                    if title:
                        items.append({
                            "title": title,
                            "article_url": f"https://zhihu.com/question/{target.get('id', '')}",
                            "hot_score": (30 - idx) * 100 * weight,
                            "source": "知乎热榜",
                            "date_str": datetime.now().strftime("%Y-%m-%d %H:%M:%S")
                        })
            
            elif source_id == "v2ex":
                # V2EX格式
                for idx, item in enumerate(data[:20]):
                    title = item.get("title", "")
                    if title:
                        items.append({
                            "title": title,
                            "article_url": item.get("url", ""),
                            "hot_score": (20 - idx) * 50 * weight,
                            "source": "V2EX",
                            "date_str": datetime.now().strftime("%Y-%m-%d %H:%M:%S")
                        })
            
            elif source_id == "github":
                # GitHub Trending格式
                for idx, item in enumerate(data.get("items", [])[:20]):
                    title = item.get("full_name", "")
                    desc = item.get("description", "")
                    if title:
                        items.append({
                            "title": f"[GitHub] {title}: {desc[:50]}..." if desc else f"[GitHub] {title}",
                            "article_url": item.get("html_url", ""),
                            "hot_score": item.get("stargazers_count", 0) * weight,
                            "source": "GitHub Trending",
                            "date_str": datetime.now().strftime("%Y-%m-%d %H:%M:%S")
                        })
            
            elif source_id == "hackernews":
                # Hacker News需要单独获取详情
                story_ids = data[:20] if isinstance(data, list) else []
                for idx, story_id in enumerate(story_ids):
                    items.append({
                        "title": f"[HN] Story {story_id}",
                        "article_url": f"https://news.ycombinator.com/item?id={story_id}",
                        "hot_score": (30 - idx) * 100 * weight,
                        "source": "Hacker News",
                        "date_str": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
                        "need_detail": True,
                        "story_id": story_id
                    })
            
            elif source_id == "juejin":
                # 掘金格式
                for idx, item in enumerate(data.get("data", [])[:20]):
                    article_info = item.get("item_info", {}).get("article_info", {})
                    title = article_info.get("title", "")
                    if title:
                        items.append({
                            "title": title,
                            "article_url": f"https://juejin.cn/post/{article_info.get('article_id', '')}",
                            "hot_score": article_info.get("view_count", 0) * weight,
                            "source": "掘金热门",
                            "date_str": datetime.now().strftime("%Y-%m-%d %H:%M:%S")
                        })
            
            elif source_id == "sspai":
                # 少数派格式
                for idx, item in enumerate(data.get("data", [])[:15]):
                    title = item.get("title", "")
                    if title:
                        items.append({
                            "title": title,
                            "article_url": item.get("web_url", ""),
                            "hot_score": (15 - idx) * 50 * weight,
                            "source": "少数派",
                            "date_str": datetime.now().strftime("%Y-%m-%d %H:%M:%S")
                        })
        
        except Exception as e:
            logger.error(f"解析 {source_id} 失败: {e}")
        
        return items

    def _parse_rss(self, data: str, source_id: str, weight: float) -> List[Dict]:
        """解析RSS格式热榜"""
        items = []
        try:
            root = etree.fromstring(data.encode('utf-8'))
            rss_items = root.xpath('//item')[:20]
            
            for idx, item in enumerate(rss_items):
                title = ''.join(item.xpath('./title/text()')).strip()
                link = ''.join(item.xpath('./link/text()')).strip()
                
                if title:
                    items.append({
                        "title": title,
                        "article_url": link,
                        "hot_score": (20 - idx) * 50 * weight,
                        "source": source_id.upper(),
                        "date_str": datetime.now().strftime("%Y-%m-%d %H:%M:%S")
                    })
        except Exception as e:
            logger.error(f"解析RSS失败: {e}")
        
        return items

    async def get_news_info(self, item: dict, category: str = "热点") -> Optional[Dict]:
        """获取热榜详情"""
        try:
            url = item.get("article_url", "")
            title = item.get("title", "")
            source = item.get("source", "热榜聚合")
            
            # 如果是Hacker News需要获取详情
            if item.get("need_detail") and item.get("story_id"):
                try:
                    async with aiohttp.ClientSession() as session:
                        async with session.get(
                            f"https://hacker-news.firebaseio.com/v0/item/{item['story_id']}.json",
                            timeout=aiohttp.ClientTimeout(total=10)
                        ) as response:
                            if response.status == 200:
                                story_data = await response.json()
                                title = story_data.get("title", title)
                                url = story_data.get("url", url)
                except:
                    pass
            
            # 清理标题前缀
            for prefix in ["[GitHub]", "[HN]"]:
                if title.startswith(prefix):
                    title = title[len(prefix):].strip()
            
            return {
                "title": title,
                "article_info": f"# {title}\n\n**来源**: {source}\n**热度**: {item.get('hot_score', 0):.0f}\n**链接**: {url}\n\n---\n*本文由 AIWriteX 热榜聚合系统自动采集*",
                "source": source,
                "category": category,
                "url": url,
                "article_url": url,
                "date_str": item.get("date_str", datetime.now().strftime("%Y-%m-%d %H:%M:%S"))
            }
        except Exception as e:
            logger.error(f"获取热榜详情失败: {e}")
            return None


# 兼容旧版
class HotRankSpider(HotRankAggregator):
    pass


if __name__ == "__main__":
    # 测试运行
    async def test():
        spider = HotRankAggregator()
        news_list = await spider.get_news_list()
        print(f"获取到 {len(news_list)} 条热榜")
        for item in news_list[:5]:
            print(f"- [{item['source']}] {item['title']} (热度: {item['hot_score']:.0f})")
    
    asyncio.run(test())
