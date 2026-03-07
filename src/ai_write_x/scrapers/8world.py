#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
8world爬虫 - 新加坡中文媒体
https://www.8world.com
"""
import asyncio
import re
from datetime import datetime
from typing import List, Dict
from lxml import etree

from base import BaseSpider
from logger_utils import logger


class World8(BaseSpider):
    """8world新闻爬虫"""
    source_name = "8world"
    category = "国际"
    
    headers = {
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/131.0.0.0 Safari/537.36",
    }

    async def get_news_list(self, category: dict = None) -> List[Dict]:
        """获取新闻列表"""
        try:
            url = "https://www.8world.com/world"
            
            content = await self.request(url=url)
            content_html = etree.HTML(content)
            
            result = []
            
            articles = content_html.xpath('//div[contains(@class, "article")]//a')
            if not articles:
                articles = content_html.xpath('//div[contains(@class, "news-item")]//a')
            if not articles:
                articles = content_html.xpath('//article//a')
            if not articles:
                articles = content_html.xpath('//div[@class="story-item"]//a')
                
            for a in articles[:20]:
                title = ''.join(a.xpath('.//text()')).strip()
                href = a.get('href', '')
                
                if title and len(title) > 5 and href:
                    if not href.startswith('http'):
                        href = 'https://www.8world.com' + href
                    result.append({
                        "title": title,
                        "article_url": href,
                        "date_str": datetime.now().strftime("%Y-%m-%d %H:%M:%S")
                    })
            
            return result
        except Exception as e:
            logger.error(f"获取8world新闻列表失败: {e}")
            return []

    async def get_news_info(self, item: dict, category: str = "国际") -> Dict:
        """获取新闻详情"""
        try:
            url = item.get("article_url", "")
            if not url:
                return None
                
            content = await self.request(url=url)
            content_html = etree.HTML(content)
            
            title = item.get("title", "")
            if not title:
                title_elem = content_html.xpath('//h1/text()')
                title = title_elem[0].strip() if title_elem else ""
            
            content_div = content_html.xpath('//div[contains(@class, "article-body")]')
            if not content_div:
                content_div = content_html.xpath('//div[contains(@class, "content")]')
            
            paragraphs = []
            if content_div:
                p_tags = content_div[0].xpath('.//p//text()')
                paragraphs = [p.strip() for p in p_tags if p.strip() and len(p.strip()) > 10]
            
            article_content = "\n\n".join(paragraphs[:20]) if paragraphs else "暂无详细内容"
            
            if len(article_content) < 50:
                return None
                
            return {
                "title": title,
                "article_info": f"# {title}\n\n**来源**: 8world\n**发布日期**: {item.get('date_str', '')}\n\n## 内容\n\n{article_content}\n\n---\n*本文由 AIWriteX 自动采集*",
                "source": "8world",
                "category": category,
                "url": url,
                "article_url": url
            }
        except Exception as e:
            logger.error(f"获取8world详情失败: {e}")
            return None
