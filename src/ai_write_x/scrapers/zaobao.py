#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
联合早报爬虫
https://www.zaobao.com.sg
"""
import asyncio
import re
from datetime import datetime
from typing import List, Dict
from lxml import etree

from base import BaseSpider
from logger_utils import logger


class ZaoBao(BaseSpider):
    """联合早报新闻爬虫"""
    source_name = "联合早报"
    category = "国际"
    
    headers = {
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/131.0.0.0 Safari/537.36",
        "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
    }

    async def get_news_list(self, category: dict = None) -> List[Dict]:
        """获取新闻列表 (增强实时模式)"""
        try:
            # 优先尝试官方实时世界新闻页面
            url = "https://www.zaobao.com.sg/realtime/world"
            content = await self.request(url=url)
            content_html = etree.HTML(content)
            
            # 联合早报特定选择器 (更新以匹配新布局)
            articles = content_html.xpath('//div[contains(@class, "news-list")]//a') or \
                       content_html.xpath('//div[contains(@id, "main-content")]//a[contains(@href, "/realtime/")]') or \
                       content_html.xpath('//a[contains(@href, "/realtime/")]')
            
            result = []
            seen_urls = set()
            
            for a in articles[:100]: # 扩大扫描范围
                title = ''.join(a.xpath('.//text()')).strip()
                href = a.get('href', '')
                
                # 排除分页、标签等广告链接
                if title and len(title) > 8 and href and "/realtime/" in href:
                    if not href.startswith('http'):
                        href = 'https://www.zaobao.com.sg' + href
                    if href not in seen_urls:
                        seen_urls.add(href)
                        result.append({
                            "title": title,
                            "article_url": href,
                            "date_str": datetime.now().strftime("%Y-%m-%d %H:%M:%S")
                        })
            
            if result:
                return result
            
            # 手动触发 Google News 备份探测
            return await self.get_news_list_google_news()
            
        except Exception as e:
            logger.error(f"获取联合早报新闻列表失败: {e}")
            return await self.get_news_list_google_news()

    async def get_news_list_google_news(self) -> List[Dict]:
        """使用 Google News 作为联合早报的备份源"""
        try:
            url = "https://news.google.com/rss/search?q=when:24h+source:Lianhe+Zaobao&hl=zh-CN&gl=CN&ceid=CN:zh-Hans"
            content_bytes = await self.request_bytes(url=url)
            parser = etree.XMLParser(recover=True, no_network=True)
            content_xml = etree.fromstring(content_bytes, parser=parser)
            result = []
            items = content_xml.xpath('//item')
            for item in items[:20]:
                title = ''.join(item.xpath('./title/text()')).strip()
                href = ''.join(item.xpath('./link/text()')).strip()
                if title and href:
                    if " - " in title: title = title.rsplit(" - ", 1)[0]
                    result.append({"title": title, "article_url": href, "date_str": datetime.now().strftime("%Y-%m-%d %H:%M:%S")})
            return result
        except: return []

    async def get_news_list_rsshub(self) -> List[Dict]:
        """RSSHub 备选方案"""
        try:
            url = "https://rsshub.app/zaobao/realtime/world"
            content = await self.request(url=url)
            content_xml = etree.XML(content.encode('utf-8'))
            result = []
            items = content_xml.xpath('//item')
            for item in items[:15]:
                title = ''.join(item.xpath('./title/text()')).strip()
                href = ''.join(item.xpath('./link/text()')).strip()
                if title and href:
                    result.append({
                        "title": title,
                        "article_url": href,
                        "date_str": datetime.now().strftime("%Y-%m-%d %H:%M:%S")
                    })
            return result
        except:
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
                title_elem = content_html.xpath('//h1[contains(@class, "title")]/text()')
                title = title_elem[0].strip() if title_elem else ""
            
            # 提取正文内容
            content_div = content_html.xpath('//div[contains(@class, "article-content")]')
            if not content_div:
                content_div = content_html.xpath('//div[contains(@class, "content")]')
            if not content_div:
                content_div = content_html.xpath('//div[@class="article-body"]')
            
            paragraphs = []
            if content_div:
                p_tags = content_div[0].xpath('.//p//text()')
                paragraphs = [p.strip() for p in p_tags if p.strip() and len(p.strip()) > 10]
            
            article_content = "\n\n".join(paragraphs[:20]) if paragraphs else "暂无详细内容"
            
            if len(article_content) < 50:
                return None
                
            return {
                "title": title,
                "content": f"# {title}\n\n**来源**: 联合早报\n**发布日期**: {item.get('date_str', '')}\n\n## 内容\n\n{article_content}\n\n---\n*本文由 AIWriteX 自动采集*",
                "source": "联合早报",
                "category": category,
                "url": url,
                "article_url": url
            }
        except Exception as e:
            logger.error(f"获取联合早报详情失败: {e}")
            return None
