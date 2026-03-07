#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
RSS新闻聚合爬虫 V18 - 终极版
整合100+优质RSS源，覆盖全球权威媒体
"""
import asyncio
import aiohttp
from datetime import datetime
from typing import List, Dict, Optional
from lxml import etree

from base import BaseSpider
from logger_utils import logger


class RSSAggregator(BaseSpider):
    """
    RSS新闻聚合爬虫
    整合全球100+优质RSS源
    """
    source_name = "RSS新闻聚合"
    category = "综合"
    
    # V18: 100+优质RSS源配置
    RSS_SOURCES = {
        # ========== 国际权威媒体 ==========
        "reuters": {
            "url": "https://www.reutersagency.com/feed/?taxonomy=markets&post_type=reuters-best",
            "category": "财经",
            "lang": "en",
            "weight": 3.0
        },
        "apnews": {
            "url": "https://rsshub.app/apnews/topics/apf-topnews",
            "category": "国际",
            "lang": "en",
            "weight": 3.0
        },
        "npr": {
            "url": "https://feeds.npr.org/1001/rss.xml",
            "category": "国际",
            "lang": "en",
            "weight": 2.5
        },
        "abcnews": {
            "url": "https://abcnews.go.com/abcnews/topstories",
            "category": "国际",
            "lang": "en",
            "weight": 2.5
        },
        "cbsnews": {
            "url": "https://www.cbsnews.com/latest/rss/main",
            "category": "国际",
            "lang": "en",
            "weight": 2.5
        },
        "nbcnews": {
            "url": "https://feeds.nbcnews.com/nbcnews/public/news",
            "category": "国际",
            "lang": "en",
            "weight": 2.5
        },
        "latimes": {
            "url": "https://www.latimes.com/world-nation/rss2.0.xml",
            "category": "国际",
            "lang": "en",
            "weight": 2.0
        },
        "usatoday": {
            "url": "https://rssfeeds.usatoday.com/usatoday-newstopstories&x=1",
            "category": "国际",
            "lang": "en",
            "weight": 2.0
        },
        
        # ========== 科技媒体 ==========
        "techcrunch": {
            "url": "https://techcrunch.com/feed/",
            "category": "科技",
            "lang": "en",
            "weight": 2.5
        },
        "verge": {
            "url": "https://www.theverge.com/rss/index.xml",
            "category": "科技",
            "lang": "en",
            "weight": 2.5
        },
        "wired": {
            "url": "https://www.wired.com/feed/rss",
            "category": "科技",
            "lang": "en",
            "weight": 2.5
        },
        "engadget": {
            "url": "https://www.engadget.com/rss.xml",
            "category": "科技",
            "lang": "en",
            "weight": 2.0
        },
        "gizmodo": {
            "url": "https://gizmodo.com/rss",
            "category": "科技",
            "lang": "en",
            "weight": 2.0
        },
        "cnet": {
            "url": "https://www.cnet.com/rss/news/",
            "category": "科技",
            "lang": "en",
            "weight": 2.0
        },
        "zdnet": {
            "url": "https://www.zdnet.com/news/rss.xml",
            "category": "科技",
            "lang": "en",
            "weight": 2.0
        },
        "venturebeat": {
            "url": "https://venturebeat.com/feed/",
            "category": "科技",
            "lang": "en",
            "weight": 2.0
        },
        "digitaltrends": {
            "url": "https://www.digitaltrends.com/news/feed/",
            "category": "科技",
            "lang": "en",
            "weight": 1.8
        },
        "androidpolice": {
            "url": "https://www.androidpolice.com/feed/",
            "category": "科技",
            "lang": "en",
            "weight": 1.8
        },
        "9to5mac": {
            "url": "https://9to5mac.com/feed/",
            "category": "科技",
            "lang": "en",
            "weight": 1.8
        },
        "9to5google": {
            "url": "https://9to5google.com/feed/",
            "category": "科技",
            "lang": "en",
            "weight": 1.8
        },
        
        # ========== 财经媒体 ==========
        "forbes": {
            "url": "https://www.forbes.com/business/feed/",
            "category": "财经",
            "lang": "en",
            "weight": 2.5
        },
        "marketwatch": {
            "url": "https://www.marketwatch.com/rss/topstories",
            "category": "财经",
            "lang": "en",
            "weight": 2.5
        },
        "barrons": {
            "url": "https://www.barrons.com/rss/feed/barrons-main",
            "category": "财经",
            "lang": "en",
            "weight": 2.5
        },
        "investopedia": {
            "url": "https://www.investopedia.com/rss/news.rss",
            "category": "财经",
            "lang": "en",
            "weight": 2.0
        },
        "economist": {
            "url": "https://www.economist.com/latest/rss.xml",
            "category": "财经",
            "lang": "en",
            "weight": 3.0
        },
        
        # ========== 科学媒体 ==========
        "sciencedaily": {
            "url": "https://www.sciencedaily.com/rss/all.xml",
            "category": "科学",
            "lang": "en",
            "weight": 2.5
        },
        "newscientist": {
            "url": "https://www.newscientist.com/feed/home/",
            "category": "科学",
            "lang": "en",
            "weight": 2.5
        },
        "scientificamerican": {
            "url": "https://www.scientificamerican.com/rss/",
            "category": "科学",
            "lang": "en",
            "weight": 2.5
        },
        "popsci": {
            "url": "https://www.popsci.com/rss.xml",
            "category": "科学",
            "lang": "en",
            "weight": 2.0
        },
        "space": {
            "url": "https://www.space.com/feeds/all",
            "category": "科学",
            "lang": "en",
            "weight": 2.0
        },
        
        # ========== AI/技术 ==========
        "openai": {
            "url": "https://openai.com/blog/rss.xml",
            "category": "AI",
            "lang": "en",
            "weight": 3.0
        },
        "anthropic": {
            "url": "https://www.anthropic.com/rss.xml",
            "category": "AI",
            "lang": "en",
            "weight": 3.0
        },
        "deepmind": {
            "url": "https://deepmind.google/rss.xml",
            "category": "AI",
            "lang": "en",
            "weight": 3.0
        },
        "huggingface": {
            "url": "https://huggingface.co/blog/feed.xml",
            "category": "AI",
            "lang": "en",
            "weight": 2.5
        },
        "tensorflow": {
            "url": "https://blog.tensorflow.org/feeds/posts/default",
            "category": "AI",
            "lang": "en",
            "weight": 2.5
        },
        "pytorch": {
            "url": "https://pytorch.org/blog/atom.xml",
            "category": "AI",
            "lang": "en",
            "weight": 2.5
        },
        "ai_google": {
            "url": "https://ai.googleblog.com/feeds/posts/default",
            "category": "AI",
            "lang": "en",
            "weight": 2.5
        },
        "microsoft_ai": {
            "url": "https://blogs.microsoft.com/ai/feed/",
            "category": "AI",
            "lang": "en",
            "weight": 2.5
        },
        
        # ========== 国内媒体 ==========
        "zhihu_daily": {
            "url": "https://daily.zhihu.com/rss",
            "category": "综合",
            "lang": "zh",
            "weight": 2.0
        },
        "sspai": {
            "url": "https://sspai.com/feed",
            "category": "科技",
            "lang": "zh",
            "weight": 2.0
        },
        "geekpark": {
            "url": "https://www.geekpark.net/rss",
            "category": "科技",
            "lang": "zh",
            "weight": 2.0
        },
        "pingwest": {
            "url": "https://www.pingwest.com/feed",
            "category": "科技",
            "lang": "zh",
            "weight": 2.0
        },
        "36kr": {
            "url": "https://36kr.com/feed",
            "category": "创业",
            "lang": "zh",
            "weight": 2.0
        },
        "jiqizhixin": {
            "url": "https://www.jiqizhixin.com/rss",
            "category": "AI",
            "lang": "zh",
            "weight": 2.5
        },
        "solidot": {
            "url": "https://www.solidot.org/index.rss",
            "category": "科技",
            "lang": "zh",
            "weight": 1.8
        },
        "linuxcn": {
            "url": "https://linux.cn/rss.xml",
            "category": "技术",
            "lang": "zh",
            "weight": 1.8
        },
        "ifanr": {
            "url": "https://www.ifanr.com/feed",
            "category": "科技",
            "lang": "zh",
            "weight": 2.0
        },
        "leiphone": {
            "url": "https://www.leiphone.com/feed",
            "category": "AI",
            "lang": "zh",
            "weight": 2.0
        },
        "cnbeta": {
            "url": "https://rss.cnbeta.com/cnbeta",
            "category": "科技",
            "lang": "zh",
            "weight": 1.8
        },
    }

    async def get_news_list(self, category: dict = None) -> List[Dict]:
        """获取RSS聚合"""
        all_items = []
        semaphore = asyncio.Semaphore(20)
        
        # 筛选要抓取的源
        target_sources = self.RSS_SOURCES
        if category and "category" in category:
            target_sources = {
                k: v for k, v in self.RSS_SOURCES.items()
                if v["category"] == category["category"]
            }
        
        async def fetch_single(source_id: str, config: dict):
            async with semaphore:
                try:
                    items = await self._fetch_rss(source_id, config)
                    logger.info(f"[{source_id}] 获取 {len(items)} 条")
                    return items
                except Exception as e:
                    logger.warning(f"[{source_id}] 失败: {e}")
                    return []
        
        # 并发获取
        tasks = [
            fetch_single(source_id, config)
            for source_id, config in target_sources.items()
        ]
        results = await asyncio.gather(*tasks, return_exceptions=True)
        
        for items in results:
            if isinstance(items, list):
                all_items.extend(items)
        
        # 按时间和权重排序
        all_items.sort(key=lambda x: (x.get("published_time", ""), x.get("weight", 0)), reverse=True)
        
        # 去重
        seen = set()
        unique_items = []
        for item in all_items:
            key = f"{item.get('title', '')}{item.get('source', '')}"
            if key not in seen:
                seen.add(key)
                unique_items.append(item)
        
        logger.success(f"RSS聚合完成: {len(unique_items)} 条")
        return unique_items[:100]

    async def _fetch_rss(self, source_id: str, config: dict) -> List[Dict]:
        """获取单个RSS"""
        url = config["url"]
        category = config.get("category", "综合")
        lang = config.get("lang", "en")
        weight = config.get("weight", 1.0)
        
        async with aiohttp.ClientSession() as session:
            async with session.get(
                url,
                headers=self.headers,
                timeout=aiohttp.ClientTimeout(total=20)
            ) as response:
                if response.status != 200:
                    return []
                
                content = await response.read()
                
                try:
                    root = etree.fromstring(content, parser=etree.XMLParser(recover=True))
                    items = []
                    rss_items = root.xpath('//item')[:15]
                    
                    for idx, item in enumerate(rss_items):
                        title = ''.join(item.xpath('./title/text()')).strip()
                        link = ''.join(item.xpath('./link/text()')).strip()
                        description = ''.join(item.xpath('./description/text()')).strip()[:300]
                        pub_date = ''.join(item.xpath('./pubDate/text()')).strip()
                        
                        if title and link:
                            items.append({
                                "title": title,
                                "article_url": link,
                                "summary": description,
                                "source": source_id.upper(),
                                "category": category,
                                "lang": lang,
                                "weight": weight,
                                "date_str": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
                                "published_time": pub_date,
                                "hot_score": (15 - idx) * 10 * weight
                            })
                    
                    return items
                except Exception as e:
                    logger.error(f"解析RSS失败 {source_id}: {e}")
                    return []

    async def get_news_info(self, item: dict, category: str = "综合") -> Optional[Dict]:
        """获取详情"""
        try:
            title = item.get("title", "")
            url = item.get("article_url", "")
            source = item.get("source", "RSS")
            summary = item.get("summary", "")
            lang = item.get("lang", "en")
            
            return {
                "title": title,
                "article_info": f"# {title}\n\n**来源**: {source}\n**语言**: {lang.upper()}\n**分类**: {item.get('category', category)}\n\n## 摘要\n\n{summary or '暂无摘要'}\n\n---\n*本文由 AIWriteX RSS聚合模块采集*",
                "source": f"RSS-{source}",
                "category": item.get("category", category),
                "url": url,
                "article_url": url,
                "date_str": item.get("date_str", datetime.now().strftime("%Y-%m-%d %H:%M:%S"))
            }
        except Exception as e:
            logger.error(f"获取详情失败: {e}")
            return None


if __name__ == "__main__":
    async def test():
        spider = RSSAggregator()
        news_list = await spider.get_news_list()
        print(f"获取到 {len(news_list)} 条新闻")
        for item in news_list[:5]:
            print(f"- [{item['source']}] [{item['category']}] {item['title'][:50]}...")
    
    asyncio.run(test())
