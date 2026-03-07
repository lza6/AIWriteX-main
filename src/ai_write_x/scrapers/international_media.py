#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
国际权威媒体爬虫合集 V17
包含：CNN、华盛顿邮报、卫报、金融时报、彭博、路透、半岛电视台等
"""
import asyncio
import aiohttp
from datetime import datetime
from typing import List, Dict, Optional
from lxml import etree

from base import BaseSpider
from logger_utils import logger


class CNN(BaseSpider):
    """CNN新闻爬虫"""
    source_name = "CNN"
    category = "国际"
    
    RSS_URLS = {
        "top": "http://rss.cnn.com/rss/edition.rss",
        "world": "http://rss.cnn.com/rss/edition_world.rss",
        "tech": "http://rss.cnn.com/rss/edition_technology.rss",
        "business": "http://rss.cnn.com/rss/money_news_international.rss"
    }
    
    async def get_news_list(self, category: dict = None) -> List[Dict]:
        items = []
        for feed_name, url in self.RSS_URLS.items():
            try:
                feed_items = await self._fetch_rss(url, feed_name)
                items.extend(feed_items)
            except Exception as e:
                logger.warning(f"[CNN {feed_name}] 失败: {e}")
        return items[:30]
    
    async def _fetch_rss(self, url: str, feed_name: str) -> List[Dict]:
        async with aiohttp.ClientSession() as session:
            async with session.get(url, timeout=aiohttp.ClientTimeout(total=15)) as response:
                content = await response.read()
                root = etree.fromstring(content, parser=etree.XMLParser(recover=True))
                
                items = []
                for idx, item in enumerate(root.xpath('//item')[:15]):
                    title = ''.join(item.xpath('./title/text()')).strip()
                    link = ''.join(item.xpath('./link/text()')).strip()
                    description = ''.join(item.xpath('./description/text()')).strip()
                    
                    if title and link:
                        items.append({
                            "title": title,
                            "article_url": link,
                            "summary": description,
                            "feed": feed_name,
                            "date_str": datetime.now().strftime("%Y-%m-%d %H:%M:%S")
                        })
                return items
    
    async def get_news_info(self, item: dict, category: str = "国际") -> Optional[Dict]:
        return {
            "title": item["title"],
            "article_info": f"# {item['title']}\n\n**来源**: CNN\n**分类**: {item.get('feed', 'news')}\n\n## 摘要\n\n{item.get('summary', '暂无摘要')}\n\n---\n*本文由 AIWriteX 国际媒体模块采集*",
            "source": "CNN",
            "category": category,
            "article_url": item["article_url"],
            "date_str": item["date_str"]
        }


class TheGuardian(BaseSpider):
    """卫报新闻爬虫"""
    source_name = "The Guardian"
    category = "国际"
    
    RSS_URLS = {
        "world": "https://www.theguardian.com/world/rss",
        "technology": "https://www.theguardian.com/technology/rss",
        "business": "https://www.theguardian.com/business/rss",
        "science": "https://www.theguardian.com/science/rss"
    }
    
    async def get_news_list(self, category: dict = None) -> List[Dict]:
        items = []
        for feed_name, url in self.RSS_URLS.items():
            try:
                feed_items = await self._fetch_rss(url, feed_name)
                items.extend(feed_items)
            except Exception as e:
                logger.warning(f"[Guardian {feed_name}] 失败: {e}")
        return items[:30]
    
    async def _fetch_rss(self, url: str, feed_name: str) -> List[Dict]:
        async with aiohttp.ClientSession() as session:
            async with session.get(url, timeout=aiohttp.ClientTimeout(total=15)) as response:
                content = await response.read()
                root = etree.fromstring(content, parser=etree.XMLParser(recover=True))
                
                items = []
                for idx, item in enumerate(root.xpath('//item')[:15]):
                    title = ''.join(item.xpath('./title/text()')).strip()
                    link = ''.join(item.xpath('./link/text()')).strip()
                    description = ''.join(item.xpath('./description/text()')).strip()
                    
                    if title and link:
                        items.append({
                            "title": title,
                            "article_url": link,
                            "summary": description,
                            "feed": feed_name,
                            "date_str": datetime.now().strftime("%Y-%m-%d %H:%M:%S")
                        })
                return items
    
    async def get_news_info(self, item: dict, category: str = "国际") -> Optional[Dict]:
        return {
            "title": item["title"],
            "article_info": f"# {item['title']}\n\n**来源**: The Guardian\n**分类**: {item.get('feed', 'news')}\n\n## 摘要\n\n{item.get('summary', '暂无摘要')}\n\n---\n*本文由 AIWriteX 国际媒体模块采集*",
            "source": "The Guardian",
            "category": category,
            "article_url": item["article_url"],
            "date_str": item["date_str"]
        }


class FinancialTimes(BaseSpider):
    """金融时报爬虫"""
    source_name = "Financial Times"
    category = "财经"
    
    RSS_URLS = {
        "world": "https://www.ft.com/world?format=rss",
        "technology": "https://www.ft.com/technology?format=rss",
        "markets": "https://www.ft.com/markets?format=rss"
    }
    
    async def get_news_list(self, category: dict = None) -> List[Dict]:
        items = []
        for feed_name, url in self.RSS_URLS.items():
            try:
                feed_items = await self._fetch_rss(url, feed_name)
                items.extend(feed_items)
            except Exception as e:
                logger.warning(f"[FT {feed_name}] 失败: {e}")
        return items[:25]
    
    async def _fetch_rss(self, url: str, feed_name: str) -> List[Dict]:
        async with aiohttp.ClientSession() as session:
            async with session.get(url, timeout=aiohttp.ClientTimeout(total=15)) as response:
                content = await response.read()
                root = etree.fromstring(content, parser=etree.XMLParser(recover=True))
                
                items = []
                for idx, item in enumerate(root.xpath('//item')[:15]):
                    title = ''.join(item.xpath('./title/text()')).strip()
                    link = ''.join(item.xpath('./link/text()')).strip()
                    description = ''.join(item.xpath('./description/text()')).strip()
                    
                    if title and link:
                        items.append({
                            "title": title,
                            "article_url": link,
                            "summary": description,
                            "feed": feed_name,
                            "date_str": datetime.now().strftime("%Y-%m-%d %H:%M:%S")
                        })
                return items
    
    async def get_news_info(self, item: dict, category: str = "财经") -> Optional[Dict]:
        return {
            "title": item["title"],
            "article_info": f"# {item['title']}\n\n**来源**: Financial Times\n**分类**: {item.get('feed', 'news')}\n\n## 摘要\n\n{item.get('summary', '暂无摘要')}\n\n---\n*本文由 AIWriteX 国际媒体模块采集*",
            "source": "Financial Times",
            "category": category,
            "article_url": item["article_url"],
            "date_str": item["date_str"]
        }


class AlJazeera(BaseSpider):
    """半岛电视台爬虫"""
    source_name = "Al Jazeera"
    category = "国际"
    
    RSS_URLS = {
        "all": "https://www.aljazeera.com/xml/rss/all.xml",
        "middle-east": "https://www.aljazeera.com/xml/rss/all.xml"
    }
    
    async def get_news_list(self, category: dict = None) -> List[Dict]:
        items = []
        for feed_name, url in self.RSS_URLS.items():
            try:
                feed_items = await self._fetch_rss(url, feed_name)
                items.extend(feed_items)
            except Exception as e:
                logger.warning(f"[AlJazeera {feed_name}] 失败: {e}")
        return items[:25]
    
    async def _fetch_rss(self, url: str, feed_name: str) -> List[Dict]:
        async with aiohttp.ClientSession() as session:
            async with session.get(url, timeout=aiohttp.ClientTimeout(total=15)) as response:
                content = await response.read()
                root = etree.fromstring(content, parser=etree.XMLParser(recover=True))
                
                items = []
                for idx, item in enumerate(root.xpath('//item')[:15]):
                    title = ''.join(item.xpath('./title/text()')).strip()
                    link = ''.join(item.xpath('./link/text()')).strip()
                    description = ''.join(item.xpath('./description/text()')).strip()
                    
                    if title and link:
                        items.append({
                            "title": title,
                            "article_url": link,
                            "summary": description,
                            "feed": feed_name,
                            "date_str": datetime.now().strftime("%Y-%m-%d %H:%M:%S")
                        })
                return items
    
    async def get_news_info(self, item: dict, category: str = "国际") -> Optional[Dict]:
        return {
            "title": item["title"],
            "article_info": f"# {item['title']}\n\n**来源**: Al Jazeera\n**分类**: {item.get('feed', 'news')}\n\n## 摘要\n\n{item.get('summary', '暂无摘要')}\n\n---\n*本文由 AIWriteX 国际媒体模块采集*",
            "source": "Al Jazeera",
            "category": category,
            "article_url": item["article_url"],
            "date_str": item["date_str"]
        }


class ArsTechnica(BaseSpider):
    """Ars Technica科技新闻"""
    source_name = "Ars Technica"
    category = "科技"
    
    RSS_URL = "http://feeds.arstechnica.com/arstechnica/index"
    
    async def get_news_list(self, category: dict = None) -> List[Dict]:
        items = []
        try:
            async with aiohttp.ClientSession() as session:
                async with session.get(self.RSS_URL, timeout=aiohttp.ClientTimeout(total=15)) as response:
                    content = await response.read()
                    root = etree.fromstring(content, parser=etree.XMLParser(recover=True))
                    
                    for idx, item in enumerate(root.xpath('//item')[:20]):
                        title = ''.join(item.xpath('./title/text()')).strip()
                        link = ''.join(item.xpath('./link/text()')).strip()
                        description = ''.join(item.xpath('./description/text()')).strip()
                        
                        if title and link:
                            items.append({
                                "title": title,
                                "article_url": link,
                                "summary": description,
                                "date_str": datetime.now().strftime("%Y-%m-%d %H:%M:%S")
                            })
        except Exception as e:
            logger.warning(f"[ArsTechnica] 失败: {e}")
        return items
    
    async def get_news_info(self, item: dict, category: str = "科技") -> Optional[Dict]:
        return {
            "title": item["title"],
            "article_info": f"# {item['title']}\n\n**来源**: Ars Technica\n**分类**: 科技\n\n## 摘要\n\n{item.get('summary', '暂无摘要')}\n\n---\n*本文由 AIWriteX 国际媒体模块采集*",
            "source": "Ars Technica",
            "category": category,
            "article_url": item["article_url"],
            "date_str": item["date_str"]
        }


if __name__ == "__main__":
    async def test():
        spiders = [
            CNN(),
            TheGuardian(),
            FinancialTimes(),
            AlJazeera(),
            ArsTechnica()
        ]
        
        for spider in spiders:
            try:
                news = await spider.get_news_list()
                print(f"[{spider.source_name}] 获取 {len(news)} 条")
                if news:
                    print(f"  示例: {news[0]['title'][:60]}...")
            except Exception as e:
                print(f"[{spider.source_name}] 错误: {e}")
    
    asyncio.run(test())
