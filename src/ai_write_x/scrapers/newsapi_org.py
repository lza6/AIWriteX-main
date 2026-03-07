#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
NewsAPI.org 国际新闻爬虫 V17
支持15万+国际新闻源，实时获取全球新闻
官网: https://newsapi.org/
"""
import asyncio
import aiohttp
import json
from datetime import datetime, timedelta
from typing import List, Dict, Optional

from base import BaseSpider
from logger_utils import logger


class NewsAPIOrg(BaseSpider):
    """
    NewsAPI.org 新闻爬虫
    免费版: 100请求/天
    付费版: 更多请求和高级功能
    """
    source_name = "NewsAPI国际"
    category = "国际"
    
    # NewsAPI端点
    BASE_URL = "https://newsapi.org/v2"
    
    # 预配置的分类关键词（用于everything端点）
    CATEGORY_QUERIES = {
        "headlines": {"category": "general", "pageSize": 30},
        "technology": {"category": "technology", "pageSize": 25},
        "business": {"category": "business", "pageSize": 25},
        "science": {"category": "science", "pageSize": 20},
        "health": {"category": "health", "pageSize": 20},
        "sports": {"category": "sports", "pageSize": 15},
        "entertainment": {"category": "entertainment", "pageSize": 10},
    }
    
    # 热点关键词搜索
    TRENDING_QUERIES = [
        "AI artificial intelligence",
        "machine learning",
        "ChatGPT OpenAI",
        "cryptocurrency bitcoin",
        "stock market",
        "climate change",
        "US China",
        "Russia Ukraine",
        "Apple iPhone",
        "Google Meta",
        "Tesla Elon Musk",
        "startup funding",
    ]

    def __init__(self):
        super().__init__()
        # 从配置文件读取API Key
        try:
            from src.ai_write_x.config.config import Config
            config = Config.get_instance()
            self.api_key = getattr(config, 'newsapi_key', None) or config.config.get("newsapi", {}).get("api_key", "")
        except:
            self.api_key = ""
    
    async def get_news_list(self, category: dict = None) -> List[Dict]:
        """
        获取NewsAPI新闻列表
        优先使用top-headlines，然后搜索热点
        """
        if not self.api_key:
            logger.warning("NewsAPI.org API Key未配置，跳过此源")
            return await self._get_sample_news()  # 返回示例数据
        
        all_articles = []
        
        try:
            # 1. 获取头条新闻
            headlines = await self._fetch_top_headlines()
            all_articles.extend(headlines)
            logger.info(f"NewsAPI头条: {len(headlines)}条")
            
            # 2. 获取各分类新闻
            for cat_name, params in list(self.CATEGORY_QUERIES.items())[1:4]:  # 只取前3个分类避免超过限额
                try:
                    articles = await self._fetch_by_category(**params)
                    all_articles.extend(articles)
                    logger.info(f"NewsAPI {cat_name}: {len(articles)}条")
                    await asyncio.sleep(0.5)  # 避免请求过快
                except Exception as e:
                    logger.warning(f"获取分类 {cat_name} 失败: {e}")
            
            # 3. 搜索热点话题
            for query in self.TRENDING_QUERIES[:3]:  # 只搜索前3个热点
                try:
                    articles = await self._fetch_everything(query, page_size=10)
                    all_articles.extend(articles)
                    logger.info(f"NewsAPI搜索 '{query}': {len(articles)}条")
                    await asyncio.sleep(0.5)
                except Exception as e:
                    logger.warning(f"搜索 {query} 失败: {e}")
        
        except Exception as e:
            logger.error(f"NewsAPI获取失败: {e}")
        
        # 去重
        seen_urls = set()
        unique_articles = []
        for article in all_articles:
            url = article.get("article_url", "")
            if url and url not in seen_urls:
                seen_urls.add(url)
                unique_articles.append(article)
        
        logger.success(f"NewsAPI.org 共获取 {len(unique_articles)} 条新闻")
        return unique_articles[:50]  # 返回前50条

    async def _fetch_top_headlines(self, category: str = "general", page_size: int = 30) -> List[Dict]:
        """获取头条新闻"""
        url = f"{self.BASE_URL}/top-headlines"
        params = {
            "apiKey": self.api_key,
            "language": "en",
            "pageSize": page_size,
            "sortBy": "publishedAt"
        }
        if category != "general":
            params["category"] = category
        
        return await self._make_request(url, params)

    async def _fetch_by_category(self, category: str, page_size: int = 25) -> List[Dict]:
        """按分类获取新闻"""
        return await self._fetch_top_headlines(category, page_size)

    async def _fetch_everything(self, query: str, page_size: int = 15) -> List[Dict]:
        """搜索新闻"""
        url = f"{self.BASE_URL}/everything"
        
        # 获取最近3天的新闻
        from_date = (datetime.now() - timedelta(days=3)).strftime("%Y-%m-%d")
        
        params = {
            "apiKey": self.api_key,
            "q": query,
            "from": from_date,
            "language": "en",
            "sortBy": "relevancy",
            "pageSize": page_size
        }
        
        return await self._make_request(url, params)

    async def _make_request(self, url: str, params: dict) -> List[Dict]:
        """发起API请求"""
        async with aiohttp.ClientSession() as session:
            async with session.get(
                url,
                params=params,
                headers=self.headers,
                timeout=aiohttp.ClientTimeout(total=15)
            ) as response:
                data = await response.json()
                
                if data.get("status") != "ok":
                    error_msg = data.get("message", "未知错误")
                    if "rateLimited" in error_msg.lower():
                        logger.warning("NewsAPI达到请求限额")
                    raise Exception(f"API错误: {error_msg}")
                
                articles = data.get("articles", [])
                results = []
                
                for article in articles:
                    title = article.get("title", "")
                    if not title or title == "[Removed]":
                        continue
                    
                    # 解析发布时间
                    published_at = article.get("publishedAt", "")
                    try:
                        if published_at:
                            dt = datetime.fromisoformat(published_at.replace("Z", "+00:00"))
                            date_str = dt.strftime("%Y-%m-%d %H:%M:%S")
                        else:
                            date_str = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
                    except:
                        date_str = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
                    
                    results.append({
                        "title": title,
                        "article_url": article.get("url", ""),
                        "cover_url": article.get("urlToImage", ""),
                        "summary": article.get("description", ""),
                        "source": article.get("source", {}).get("name", "NewsAPI"),
                        "author": article.get("author", ""),
                        "date_str": date_str,
                        "content": article.get("content", "")
                    })
                
                return results

    async def _get_sample_news(self) -> List[Dict]:
        """当没有API Key时返回示例/空数据"""
        logger.info("NewsAPI未配置API Key，请访问 https://newsapi.org/ 获取免费API Key")
        return []

    async def get_news_info(self, item: dict, category: str = "国际") -> Optional[Dict]:
        """获取新闻详情"""
        try:
            title = item.get("title", "")
            url = item.get("article_url", "")
            summary = item.get("summary", "")
            content = item.get("content", "")
            source = item.get("source", "NewsAPI")
            author = item.get("author", "")
            
            # 组合正文
            article_body = summary
            if content and content != summary:
                article_body += "\n\n" + content
            
            if not article_body:
                article_body = "暂无详细内容"
            
            return {
                "title": title,
                "article_info": f"# {title}\n\n**来源**: {source}\n**作者**: {author}\n**发布**: {item.get('date_str', '')}\n**链接**: {url}\n\n## 摘要\n\n{article_body}\n\n---\n*本文由 AIWriteX NewsAPI模块采集*",
                "source": f"NewsAPI-{source}",
                "category": category,
                "url": url,
                "article_url": url,
                "cover_url": item.get("cover_url", ""),
                "date_str": item.get("date_str", datetime.now().strftime("%Y-%m-%d %H:%M:%S"))
            }
        except Exception as e:
            logger.error(f"获取NewsAPI详情失败: {e}")
            return None


# 兼容旧版
class NewsAPI(NewsAPIOrg):
    pass


if __name__ == "__main__":
    async def test():
        spider = NewsAPIOrg()
        news_list = await spider.get_news_list()
        print(f"获取到 {len(news_list)} 条新闻")
        for item in news_list[:5]:
            print(f"- [{item['source']}] {item['title'][:50]}...")
    
    asyncio.run(test())
