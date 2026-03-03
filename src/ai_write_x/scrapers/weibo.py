#!/usr/bin/python
# -*- coding: UTF-8 -*-
import asyncio
from typing import List, Dict, Optional
from base import BaseSpider
from src.ai_write_x.tools.hotnews import get_platform_news

class WeiboSpider(BaseSpider):
    source_name = "微博"
    category = "热搜"

    async def get_news_list(self, code=None) -> List[Dict]:
        """获取微博热搜列表"""
        try:
            topics = get_platform_news("微博", cnt=20)
            return [{"title": topic, "article_url": f"https://s.weibo.com/weibo?q={topic}", "source": "微博"} for topic in topics]
        except Exception:
            return []

    async def get_news_info(self, item: Dict, category=None) -> Optional[Dict]:
        """微博热搜通常只有标题，直接返回"""
        return {
            "title": item["title"],
            "article_url": item["article_url"],
            "content": item["title"],
            "article_info": item["title"],
            "source": "微博",
            "category": category or self.category,
            "date_str": __import__('datetime').datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        }
