#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
网易新闻-财经新闻爬虫
https://money.163.com/
"""
import asyncio
import re
from datetime import datetime
from typing import List, Dict
from lxml import etree

from base import BaseSpider
from logger_utils import logger


class WangYiMoney(BaseSpider):
    """网易财经新闻爬虫"""
    source_name = "网易财经"
    category = "财经"
    
    headers = {
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/131.0.0.0 Safari/537.36",
    }

    async def get_news_list(self, category: dict = None) -> List[Dict]:
        """获取财经新闻列表"""
        try:
            url = "https://money.163.com/"
            
            content = await self.request(url=url)
            content_html = etree.HTML(content)
            
            result = []
            
            articles = content_html.xpath('//div[contains(@class, "news_item")]//a')
            if not articles:
                articles = content_html.xpath('//div[@class="item_top"]//a')
            if not articles:
                articles = content_html.xpath('//div[contains(@class, "item")]//a')
            if not articles:
                articles = content_html.xpath('//div[@class="data_row"]//a')
                
            for a in articles[:20]:
                title = ''.join(a.xpath('.//text()')).strip()
                href = a.get('href', '')
                
                if title and len(title) > 5 and href and ('money.163.com' in href or href.startswith('/')):
                    if href.startswith('/'):
                        href = 'https://money.163.com' + href
                    result.append({
                        "title": title,
                        "article_url": href,
                        "date_str": datetime.now().strftime("%Y-%m-%d %H:%M:%S")
                    })
            
            return result
        except Exception as e:
            logger.error(f"获取网易财经新闻列表失败: {e}")
            return []

    async def get_news_info(self, item: dict, category: str = "财经") -> Dict:
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
            
            content_div = content_html.xpath('//div[@class="post_body"]')
            if not content_div:
                content_div = content_html.xpath('//div[@id="content"]')
            if not content_div:
                content_div = content_html.xpath('//div[contains(@class, "article")]')
            
            paragraphs = []
            if content_div:
                p_tags = content_div[0].xpath('.//p//text()')
                paragraphs = [p.strip() for p in p_tags if p.strip() and len(p.strip()) > 10]
            
            article_content = "\n\n".join(paragraphs[:20]) if paragraphs else "暂无详细内容"
            
            if len(article_content) < 50:
                return None
                
            return {
                "title": title,
                "article_info": f"# {title}\n\n**来源**: 网易财经\n**发布日期**: {item.get('date_str', '')}\n\n## 内容\n\n{article_content}\n\n---\n*本文由 AIWriteX 自动采集*",
                "source": "网易财经",
                "category": category,
                "url": url,
                "article_url": url
            }
        except Exception as e:
            logger.error(f"获取网易财经新闻详情失败: {e}")
            return None
