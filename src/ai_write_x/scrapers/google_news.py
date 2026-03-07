#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
Google News RSS 聚合爬虫 V17
利用Google News的公开RSS feed，无需API Key即可获取全球新闻
支持多语言、多地区、多主题
"""
import asyncio
import aiohttp
import urllib.parse
from datetime import datetime
from typing import List, Dict, Optional
from lxml import etree

from base import BaseSpider
from logger_utils import logger


class GoogleNewsRSS(BaseSpider):
    """
    Google News RSS 爬虫
    基于Google News的公开RSS接口
    """
    source_name = "Google News"
    category = "国际"
    
    # Google News RSS 基础URL
    RSS_BASE = "https://news.google.com/rss"
    
    # V17: 预配置的多地区多主题RSS
    RSS_CONFIGS = {
        # 英文全球热点
        "en_top": {
            "url": "https://news.google.com/rss?hl=en-US&gl=US&ceid=US:en",
            "lang": "en",
            "weight": 2.0
        },
        # 英文科技
        "en_tech": {
            "url": "https://news.google.com/rss/topics/CAAqJggKIiBDQkFTRWdvSUwyMHZNRGRqTVhZU0FtVnVHZ0pWVXlnQVAB?hl=en-US&gl=US&ceid=US:en",
            "lang": "en",
            "weight": 2.0
        },
        # 英文商业
        "en_business": {
            "url": "https://news.google.com/rss/topics/CAAqJggKIiBDQkFTRWdvSUwyMHZNRGx6TVdZU0FtVnVHZ0pWVXlnQVAB?hl=en-US&gl=US&ceid=US:en",
            "lang": "en",
            "weight": 1.8
        },
        # 英文科学
        "en_science": {
            "url": "https://news.google.com/rss/topics/CAAqJggKIiBDQkFTRWdvSUwyMHZNRFp0Y1RjU0FtVnVHZ0pWVXlnQVAB?hl=en-US&gl=US&ceid=US:en",
            "lang": "en",
            "weight": 1.8
        },
        # 英文健康
        "en_health": {
            "url": "https://news.google.com/rss/topics/CAAqIQgKIhtDQkFTRGdvSUwyMHZNR3QwTlRFU0FtVnVLQUFQAQ?hl=en-US&gl=US&ceid=US:en",
            "lang": "en",
            "weight": 1.5
        },
        # 中文全球
        "zh_top": {
            "url": "https://news.google.com/rss?hl=zh-CN&gl=CN&ceid=CN:zh",
            "lang": "zh",
            "weight": 2.0
        },
        # 中文科技
        "zh_tech": {
            "url": "https://news.google.com/rss/topics/CAAqJggKIiBDQkFTRWdvSUwyMHZNRGRqTVhZU0FtVnVHZ0pWVXlnQVAB?hl=zh-CN&gl=CN&ceid=CN:zh",
            "lang": "zh",
            "weight": 2.0
        },
        # 中文商业
        "zh_business": {
            "url": "https://news.google.com/rss/topics/CAAqJggKIiBDQkFTRWdvSUwyMHZNRGx6TVdZU0FtVnVHZ0pWVXlnQVAB?hl=zh-CN&gl=CN&ceid=CN:zh",
            "lang": "zh",
            "weight": 1.8
        },
        # 台湾新闻
        "tw_top": {
            "url": "https://news.google.com/rss?hl=zh-TW&gl=TW&ceid=TW:zh",
            "lang": "zh-tw",
            "weight": 1.5
        },
        # 香港新闻
        "hk_top": {
            "url": "https://news.google.com/rss?hl=zh-HK&gl=HK&ceid=HK:zh",
            "lang": "zh-hk",
            "weight": 1.5
        },
    }
    
    # 热点搜索关键词
    HOT_SEARCHES = [
        "artificial intelligence",
        "machine learning",
        "ChatGPT",
        "cryptocurrency",
        "stock market",
        "climate change",
        "US China relations",
        "startup",
        "Apple",
        "Google",
        "Tesla",
        "Elon Musk",
    ]

    async def get_news_list(self, category: dict = None) -> List[Dict]:
        """
        获取Google News RSS聚合
        并发获取多个RSS源
        """
        all_items = []
        semaphore = asyncio.Semaphore(8)
        
        async def fetch_single(config_id: str, config: dict):
            async with semaphore:
                try:
                    items = await self._fetch_rss(config_id, config)
                    logger.info(f"[Google News {config_id}] 获取 {len(items)} 条")
                    return items
                except Exception as e:
                    logger.warning(f"[Google News {config_id}] 失败: {e}")
                    return []
        
        # 并发获取所有预配置RSS
        tasks = [
            fetch_single(config_id, config)
            for config_id, config in self.RSS_CONFIGS.items()
        ]
        results = await asyncio.gather(*tasks, return_exceptions=True)
        
        for items in results:
            if isinstance(items, list):
                all_items.extend(items)
        
        # 按时间排序
        all_items.sort(key=lambda x: x.get("published_time", ""), reverse=True)
        
        # 去重
        seen_urls = set()
        unique_items = []
        for item in all_items:
            url = item.get("article_url", "")
            if url and url not in seen_urls:
                seen_urls.add(url)
                unique_items.append(item)
        
        logger.success(f"Google News 共获取 {len(unique_items)} 条")
        return unique_items[:60]  # 返回前60条

    async def _fetch_rss(self, config_id: str, config: dict) -> List[Dict]:
        """获取单个RSS源"""
        url = config["url"]
        lang = config.get("lang", "en")
        weight = config.get("weight", 1.0)
        
        async with aiohttp.ClientSession() as session:
            async with session.get(
                url,
                headers=self.headers,
                timeout=aiohttp.ClientTimeout(total=20)
            ) as response:
                if response.status != 200:
                    raise Exception(f"HTTP {response.status}")
                
                content = await response.read()
                
                # 解析XML
                parser = etree.XMLParser(recover=True, no_network=True)
                root = etree.fromstring(content, parser=parser)
                
                items = []
                rss_items = root.xpath('//item')[:25]  # 每个源取前25条
                
                for idx, item in enumerate(rss_items):
                    title = ''.join(item.xpath('./title/text()')).strip()
                    link = ''.join(item.xpath('./link/text()')).strip()
                    description = ''.join(item.xpath('./description/text()')).strip()
                    pub_date = ''.join(item.xpath('./pubDate/text()')).strip()
                    source_elem = item.xpath('./source/text()')
                    source = source_elem[0] if source_elem else "Google News"
                    
                    # 解析发布时间
                    try:
                        if pub_date:
                            # RSS日期格式: Mon, 06 Mar 2024 12:00:00 GMT
                            from email.utils import parsedate_to_datetime
                            dt = parsedate_to_datetime(pub_date)
                            date_str = dt.strftime("%Y-%m-%d %H:%M:%S")
                        else:
                            date_str = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
                    except:
                        date_str = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
                    
                    if title and link:
                        items.append({
                            "title": title,
                            "article_url": link,
                            "summary": description,
                            "source": source,
                            "lang": lang,
                            "date_str": date_str,
                            "published_time": date_str,
                            "hot_score": (25 - idx) * 10 * weight
                        })
                
                return items

    async def search_news(self, query: str, lang: str = "en", max_results: int = 20) -> List[Dict]:
        """
        搜索Google News (通过RSS搜索)
        """
        # URL编码查询词
        encoded_query = urllib.parse.quote(query)
        
        # 构建搜索RSS URL
        if lang == "zh":
            search_url = f"https://news.google.com/rss/search?q={encoded_query}&hl=zh-CN&gl=CN&ceid=CN:zh"
        else:
            search_url = f"https://news.google.com/rss/search?q={encoded_query}&hl=en-US&gl=US&ceid=US:en"
        
        config = {
            "url": search_url,
            "lang": lang,
            "weight": 1.0
        }
        
        try:
            items = await self._fetch_rss("search", config)
            return items[:max_results]
        except Exception as e:
            logger.error(f"Google News搜索失败: {e}")
            return []

    async def get_news_info(self, item: dict, category: str = "国际") -> Optional[Dict]:
        """获取新闻详情"""
        try:
            title = item.get("title", "")
            url = item.get("article_url", "")
            summary = item.get("summary", "")
            source = item.get("source", "Google News")
            lang = item.get("lang", "en")
            
            # 清理标题中的来源后缀
            if " - " in title:
                parts = title.rsplit(" - ", 1)
                if len(parts) == 2 and source in parts[1]:
                    title = parts[0]
            
            return {
                "title": title,
                "article_info": f"# {title}\n\n**来源**: {source}\n**语言**: {lang.upper()}\n**发布**: {item.get('date_str', '')}\n**链接**: {url}\n\n## 摘要\n\n{summary or '暂无摘要'}\n\n---\n*本文由 AIWriteX Google News模块采集*",
                "source": f"GoogleNews-{source}",
                "category": category,
                "url": url,
                "article_url": url,
                "date_str": item.get("date_str", datetime.now().strftime("%Y-%m-%d %H:%M:%S"))
            }
        except Exception as e:
            logger.error(f"获取Google News详情失败: {e}")
            return None


# 兼容旧版
class GoogleNews(GoogleNewsRSS):
    pass


if __name__ == "__main__":
    async def test():
        spider = GoogleNewsRSS()
        news_list = await spider.get_news_list()
        print(f"获取到 {len(news_list)} 条新闻")
        for item in news_list[:5]:
            print(f"- [{item['lang']}] [{item['source']}] {item['title'][:50]}...")
        
        # 测试搜索
        print("\n搜索 'AI':")
        search_results = await spider.search_news("artificial intelligence", max_results=5)
        for item in search_results:
            print(f"- {item['title'][:50]}...")
    
    asyncio.run(test())
