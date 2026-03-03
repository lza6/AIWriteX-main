#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
新华网爬虫
https://www.news.cn/world/jsxw/index.html
"""
import asyncio
import re
from datetime import datetime
from typing import List, Dict
from lxml import etree

from base import BaseSpider
from logger_utils import logger


class XinhuaNews(BaseSpider):
    """新华网爬虫"""
    source_name = "新华网"
    category = "国际"
    
    headers = {
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/131.0.0.0 Safari/537.36",
    }

    async def get_news_list(self, category: dict = None) -> List[Dict]:
        """获取新闻列表（多源探测模式）"""
        urls = [
            "https://news.google.com/rss/search?q=when:24h+source:Xinhua&hl=zh-CN&gl=CN&ceid=CN:zh-Hans",
            "https://english.news.cn/rss/world.xml",
            "http://www.news.cn/world/rss.xml"
        ]
        
        for url in urls:
            try:
                headers = {
                    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36"
                }
                content_bytes = await self.request_bytes(url=url, verify_ssl=False, headers=headers, timeout=10)
                if not content_bytes: continue
                
                parser = etree.XMLParser(recover=True, no_network=True)
                content_xml = etree.fromstring(content_bytes, parser=parser)
                
                result = []
                items = content_xml.xpath('//item')
                
                for item in items[:20]:
                    title = ''.join(item.xpath('./title/text()')).strip()
                    href = ''.join(item.xpath('./link/text()')).strip()
                    if title and href:
                        if " - " in title:
                            title = title.rsplit(" - ", 1)[0]
                        result.append({
                            "title": title,
                            "article_url": href,
                            "date_str": datetime.now().strftime("%Y-%m-%d %H:%M:%S")
                        })
                if result:
                    return result
            except Exception as e:
                logger.warning(f"新华网源 {url} 探测失败: {e}")
        
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
            
            content_div = content_html.xpath('//div[contains(@class, "article-content")]')
            if not content_div:
                content_div = content_html.xpath('//div[contains(@class, "text")]')
            if not content_div:
                content_div = content_html.xpath('//div[@class="content"]')
            
            paragraphs = []
            if content_div:
                p_tags = content_div[0].xpath('.//p//text()')
                paragraphs = [p.strip() for p in p_tags if p.strip() and len(p.strip()) > 10]
            
            article_content = "\n\n".join(paragraphs[:20]) if paragraphs else "暂无详细内容"
            
            if len(article_content) < 50:
                return None
                
            return {
                "title": title,
                "content": f"# {title}\n\n**来源**: 新华网\n**发布日期**: {item.get('date_str', '')}\n\n## 内容\n\n{article_content}\n\n---\n*本文由 AIWriteX 自动采集*",
                "source": "新华网",
                "category": category,
                "url": url,
                "article_url": url
            }
        except Exception as e:
            logger.error(f"获取新华网详情失败: {e}")
            return None
