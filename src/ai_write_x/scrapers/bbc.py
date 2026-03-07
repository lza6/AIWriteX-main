#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
BBC中文网爬虫
https://www.bbc.com/zhongwen/simp
"""
import asyncio
import re
from datetime import datetime
from typing import List, Dict
from lxml import etree

from base import BaseSpider
from logger_utils import logger


class BBCChinese(BaseSpider):
    """BBC中文网爬虫"""
    source_name = "BBC中文网"
    category = "国际"
    
    headers = {
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/131.0.0.0 Safari/537.36",
    }

    async def get_news_list(self, category: dict = None) -> List[Dict]:
        """获取新闻列表（官方RSS模式）"""
        try:
            url = "https://feeds.bbci.co.uk/zhongwen/trad/rss.xml"
            # 使用原始字节解析，让 lxml 自动处理 XML 声明中的编码
            content_bytes = await self.request_bytes(url=url)
            parser = etree.XMLParser(recover=True, no_network=True)
            content_xml = etree.fromstring(content_bytes, parser=parser)
            
            result = []
            items = content_xml.xpath('//item')
            
            for item in items[:20]:
                title = ''.join(item.xpath('./title/text()')).strip()
                href = ''.join(item.xpath('./link/text()')).strip()
                
                if title and href:
                    result.append({
                        "title": title,
                        "article_url": href,
                        "date_str": datetime.now().strftime("%Y-%m-%d %H:%M:%S")
                    })
            
            return result
        except Exception as e:
            logger.error(f"获取BBC中文网新闻列表失败: {e}")
            # 备用方案: 尝试主页抓取
            return await self.get_news_list_fallback()

    async def get_news_list_fallback(self) -> List[Dict]:
        """备用 HTML 抓取"""
        try:
            url = "https://www.bbc.com/zhongwen/simp"
            content = await self.request(url=url)
            content_html = etree.HTML(content)
            articles = content_html.xpath('//a[contains(@href, "/news/") or contains(@href, "/articles/")]')
            
            result = []
            for a in articles[:15]:
                title = ''.join(a.xpath('.//text()')).strip()
                href = a.get('href', '')
                if title and len(title) > 5 and href:
                    if not href.startswith('http'):
                        href = 'https://www.bbc.com' + href
                    result.append({
                        "title": title,
                        "article_url": href,
                        "date_str": datetime.now().strftime("%Y-%m-%d %H:%M:%S")
                    })
            return result
        except Exception as e:
            logger.error(f"BBC备用抓取也失败: {e}")
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
                "article_info": f"# {title}\n\n**来源**: BBC中文网\n**发布日期**: {item.get('date_str', '')}\n\n## 内容\n\n{article_content}\n\n---\n*本文由 AIWriteX 自动采集*",
                "source": "BBC中文网",
                "category": category,
                "url": url,
                "article_url": url
            }
        except Exception as e:
            logger.error(f"获取BBC中文网详情失败: {e}")
            return None
