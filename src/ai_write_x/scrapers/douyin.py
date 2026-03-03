#!/usr/bin/python
# -*- coding: UTF-8 -*-
import asyncio
from typing import List, Dict, Optional
from base import BaseSpider
from src.ai_write_x.tools.hotnews import get_platform_news

class DouyinSpider(BaseSpider):
    source_name = "抖音"
    category = "热搜"

    async def get_news_list(self, code=None) -> List[Dict]:
        """获取抖音热搜列表"""
        try:
            # get_platform_news 返回的是字符串列表
            topics = get_platform_news("抖音", cnt=20)
            return [{"title": topic, "article_url": f"https://www.douyin.com/search/{topic}", "source": "抖音"} for topic in topics]
        except Exception:
            return []

    async def get_news_info(self, item: Dict, category=None) -> Optional[Dict]:
        """抖音热搜通常只有标题，直接返回"""
        return {
            "title": item["title"],
            "article_url": item["article_url"],
            "content": item["title"], # 热搜话题本身就是内容
            "article_info": item["title"],
            "source": "抖音",
            "category": category or self.category,
            "date_str": __import__('datetime').datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        }
