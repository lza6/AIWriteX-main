#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
纽约时报中文网爬虫
https://m.cn.nytimes.com
"""
import asyncio
import re
from datetime import datetime
from typing import List, Dict
from lxml import etree

from base import BaseSpider
from logger_utils import logger


class NYTimes(BaseSpider):
    """纽约时报中文网爬虫"""
    source_name = "纽约时报中文网"
    category = "国际"
    
    headers = {
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/131.0.0.0 Safari/537.36",
    }

    async def get_news_list(self, category: dict = None) -> List[Dict]:
        """获取新闻列表 (增强RSS模式)"""
        urls = [
            "https://cn.nytimes.com/rss",
            "https://feedx.net/rss/nytimes.xml"
        ]
        
        for url in urls:
            try:
                content_bytes = await self.request_bytes(url=url)
                if not content_bytes: continue
                
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
                if result:
                    return result
            except Exception as e:
                logger.warning(f"纽约时报源 {url} 探测失败: {e}")
        
        return []

    async def get_news_info(self, item: dict, category: str = "国际") -> Dict:
        """获取新闻详情"""
        try:
            url = item.get("article_url", "")
            if not url:
                return None
                
            content = await self.request(url=url)
            content_html = etree.HTML(content)
            
            # 提取标题
            title = item.get("title", "")
            if not title:
                title_elem = content_html.xpath('//h1/text()')
                title = title_elem[0].strip() if title_elem else ""
            
            # 提取正文
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
                "article_info": f"# {title}\n\n**来源**: 纽约时报中文网\n**发布日期**: {item.get('date_str', '')}\n\n## 内容\n\n{article_content}\n\n---\n*本文由 AIWriteX 自动采集*",
                "source": "纽约时报中文网",
                "category": category,
                "url": url,
                "article_url": url
            }
        except Exception as e:
            logger.error(f"获取纽约时报详情失败: {e}")
            return None
