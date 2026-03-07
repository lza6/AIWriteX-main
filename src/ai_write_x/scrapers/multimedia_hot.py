#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
多平台热榜聚合爬虫 V18 - 终极版
整合：抖音、快手、B站、小红书、贴吧、虎扑等平台热榜
基于公开API和RSSHub
"""
import asyncio
import aiohttp
import json
from datetime import datetime
from typing import List, Dict, Optional
from lxml import etree

from base import BaseSpider
from logger_utils import logger


class MultiMediaHot(BaseSpider):
    """
    多平台热榜聚合爬虫
    覆盖视频平台、社区、论坛等
    """
    source_name = "多平台热榜"
    category = "热点"
    
    # V18: 多平台热榜API配置
    HOT_APIS = {
        # 哔哩哔哩热榜 (通过RSSHub)
        "bilibili": {
            "url": "https://rsshub.app/bilibili/ranking/0/3/1",
            "method": "rss",
            "weight": 2.0,
            "headers": {}
        },
        # 贴吧热议
        "tieba": {
            "url": "https://rsshub.app/tieba/forum/百度贴吧",
            "method": "rss",
            "weight": 1.5,
            "headers": {}
        },
        # 虎扑步行街
        "hupu": {
            "url": "https://rsshub.app/hupu/all/gambia",
            "method": "rss",
            "weight": 1.5,
            "headers": {}
        },
        # 豆瓣小组
        "douban": {
            "url": "https://rsshub.app/douban/group/camera",
            "method": "rss",
            "weight": 1.3,
            "headers": {}
        },
        # 360趋势
        "so": {
            "url": "https://rsshub.app/360doc/cat/1",
            "method": "rss",
            "weight": 1.2,
            "headers": {}
        },
        # 悟空问答
        "wukong": {
            "url": "https://rsshub.app/wukong/user/问答",
            "method": "rss",
            "weight": 1.0,
            "headers": {}
        },
        # 搜狗微信 (公众号热门)
        "wechat": {
            "url": "https://rsshub.app/wechat/search/热门",
            "method": "rss",
            "weight": 1.8,
            "headers": {}
        },
        # CSDN热榜
        "csdn": {
            "url": "https://rsshub.app/csdn/blog/hot",
            "method": "rss",
            "weight": 1.3,
            "headers": {}
        },
        # 开源中国热门
        "oschina": {
            "url": "https://rsshub.app/oschina/news",
            "method": "rss",
            "weight": 1.3,
            "headers": {}
        },
        # 掘金热门
        "juejin": {
            "url": "https://rsshub.app/juejin/trending/all/weekly",
            "method": "rss",
            "weight": 1.5,
            "headers": {}
        },
        # 小众软件
        "appinn": {
            "url": "https://rsshub.app/appinn/latest",
            "method": "rss",
            "weight": 1.2,
            "headers": {}
        },
        # 异次元软件
        "iplaysoft": {
            "url": "https://rsshub.app/iplaysoft",
            "method": "rss",
            "weight": 1.2,
            "headers": {}
        }
    }

    async def get_news_list(self, category: dict = None) -> List[Dict]:
        """获取多平台热榜聚合"""
        all_items = []
        semaphore = asyncio.Semaphore(10)
        
        async def fetch_single(source_id: str, config: dict):
            async with semaphore:
                try:
                    if config["method"] == "rss":
                        items = await self._fetch_rss(source_id, config)
                    else:
                        items = await self._fetch_api(source_id, config)
                    logger.info(f"[{source_id}] 获取到 {len(items)} 条热榜")
                    return items
                except Exception as e:
                    logger.warning(f"[{source_id}] 获取失败: {e}")
                    return []
        
        # 并发获取所有平台
        tasks = [
            fetch_single(source_id, config)
            for source_id, config in self.HOT_APIS.items()
        ]
        results = await asyncio.gather(*tasks, return_exceptions=True)
        
        for items in results:
            if isinstance(items, list):
                all_items.extend(items)
        
        # 按热度排序
        all_items.sort(key=lambda x: x.get("hot_score", 0), reverse=True)
        
        logger.success(f"多平台热榜聚合完成，共 {len(all_items)} 条")
        return all_items[:60]

    async def _fetch_rss(self, source_id: str, config: dict) -> List[Dict]:
        """获取RSS源"""
        url = config["url"]
        weight = config.get("weight", 1.0)
        headers = config.get("headers", {})
        
        async with aiohttp.ClientSession() as session:
            async with session.get(
                url,
                headers={**self.headers, **headers},
                timeout=aiohttp.ClientTimeout(total=20)
            ) as response:
                if response.status != 200:
                    return []
                
                content = await response.read()
                
                try:
                    root = etree.fromstring(content, parser=etree.XMLParser(recover=True))
                    items = []
                    rss_items = root.xpath('//item')[:20]
                    
                    for idx, item in enumerate(rss_items):
                        title = ''.join(item.xpath('./title/text()')).strip()
                        link = ''.join(item.xpath('./link/text()')).strip()
                        description = ''.join(item.xpath('./description/text()')).strip()
                        pub_date = ''.join(item.xpath('./pubDate/text()')).strip()
                        
                        if title and link:
                            items.append({
                                "title": title,
                                "article_url": link,
                                "summary": description[:200] if description else "",
                                "source": self._get_source_name(source_id),
                                "date_str": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
                                "hot_score": (20 - idx) * 50 * weight
                            })
                    
                    return items
                except Exception as e:
                    logger.error(f"解析RSS失败 {source_id}: {e}")
                    return []

    async def _fetch_api(self, source_id: str, config: dict) -> List[Dict]:
        """获取API源"""
        # 预留API接口实现
        return []

    def _get_source_name(self, source_id: str) -> str:
        """获取源名称"""
        names = {
            "bilibili": "B站热榜",
            "tieba": "贴吧热议",
            "hupu": "虎扑步行街",
            "douban": "豆瓣小组",
            "so": "360趋势",
            "wukong": "悟空问答",
            "wechat": "微信公众号",
            "csdn": "CSDN热榜",
            "oschina": "开源中国",
            "juejin": "掘金热门",
            "appinn": "小众软件",
            "iplaysoft": "异次元软件"
        }
        return names.get(source_id, source_id)

    async def get_news_info(self, item: dict, category: str = "热点") -> Optional[Dict]:
        """获取详情"""
        try:
            title = item.get("title", "")
            url = item.get("article_url", "")
            source = item.get("source", "多平台热榜")
            summary = item.get("summary", "")
            
            return {
                "title": title,
                "article_info": f"# {title}\n\n**来源**: {source}\n**热度**: {item.get('hot_score', 0):.0f}\n**链接**: {url}\n\n## 摘要\n\n{summary or '暂无摘要'}\n\n---\n*本文由 AIWriteX 多平台热榜模块采集*",
                "source": source,
                "category": category,
                "url": url,
                "article_url": url,
                "date_str": item.get("date_str", datetime.now().strftime("%Y-%m-%d %H:%M:%S"))
            }
        except Exception as e:
            logger.error(f"获取详情失败: {e}")
            return None


if __name__ == "__main__":
    async def test():
        spider = MultiMediaHot()
        news_list = await spider.get_news_list()
        print(f"获取到 {len(news_list)} 条热榜")
        for item in news_list[:5]:
            print(f"- [{item['source']}] {item['title'][:50]}...")
    
    asyncio.run(test())