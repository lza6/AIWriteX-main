#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
GitHub Trending 爬虫 - 基于 HelloGithub API
"""
import asyncio
import json
import re
from typing import Any, Dict, List, Optional
from datetime import datetime

import aiohttp
from lxml import etree


class HelloGithub:
    """HelloGithub 热门项目爬虫"""
    
    source_name = "HelloGithub"
    category = "GitHubTrending"
    
    BASE_URL = "https://hellogithub.com"
    API_URL = "https://abroad.hellogithub.com/v1"
    
    # 分类映射
    CATEGORIES = {
        "all": {"tid": "juBLV86qa5", "name": "全部"},
        "python": {"tid": "RKRzlWgmE", "name": "Python"},
        "javascript": {"tid": "9ciqyp5UnN", "name": "JavaScript"},
        "go": {"tid": "5mwKR98qEm", "name": "Go"},
        "java": {"tid": "ZmzV5WN5yK", "name": "Java"},
        "rust": {"tid": "wgbLqxU5D8", "name": "Rust"},
        "ai": {"tid": "AI", "name": "AI"},
    }
    
    async def request(self, url: str, **kwargs) -> str:
        """发送HTTP请求"""
        async with aiohttp.ClientSession() as session:
            async with session.get(url, **kwargs) as response:
                return await response.text()
    
    async def get_hot_items(self, page: int = 1, category: str = "all") -> List[Dict]:
        """
        获取热门仓库列表
        """
        try:
            tid = self.CATEGORIES.get(category, self.CATEGORIES["all"])["tid"]
            url = f"{self.API_URL}/?sort_by=featured&page={page}&rank_by=newest&tid={tid}"
            
            text = await self.request(url)
            data = json.loads(text)
            
            if not data.get("success"):
                return []
            
            items = []
            for item in data.get("data", []):
                items.append({
                    "item_id": item.get("item_id"),
                    "full_name": item.get("full_name"),
                    "author": item.get("author"),
                    "title": item.get("title"),
                    "title_en": item.get("title_en"),
                    "name": item.get("name"),
                    "description": item.get("summary", ""),
                    "description_en": item.get("summary_en", ""),
                    "url": f"https://github.com/{item.get('author')}/{item.get('name')}",
                    "language": item.get("primary_lang"),
                    "clicks": item.get("clicks_total", 0),
                    "updated_at": item.get("updated_at", ""),
                })
            
            return items
            
        except Exception as e:
            print(f"获取热门项目失败: {e}")
            return []
    
    async def get_item_detail(self, item_id: str) -> Optional[Dict]:
        """
        获取项目详情
        """
        try:
            url = f"{self.BASE_URL}/repository/{item_id}"
            text = await self.request(url)
            
            # 提取 __NEXT_DATA__
            match = re.search(r'<script id="__NEXT_DATA__"[^>]*>([^<]+)</script>', text)
            if not match:
                return None
            
            next_data = json.loads(match.group(1))
            repo_data = next_data.get("props", {}).get("pageProps", {}).get("repo", {})
            
            if not repo_data:
                return None
            
            # 提取标签
            tags = [tag.get("name") for tag in repo_data.get("tags", [])]
            
            # 提取相关链接
            related_urls = []
            if repo_data.get("homepage") and repo_data.get("homepage") != repo_data.get("url"):
                related_urls.append({"url": repo_data.get("homepage"), "title": "官网"})
            if repo_data.get("document") and repo_data.get("document") != repo_data.get("url"):
                related_urls.append({"url": repo_data.get("document"), "title": "文档"})
            
            # 计算上周获得的star数
            star_history = repo_data.get("star_history", {})
            last_week_stars = star_history.get("increment", 0)
            
            return {
                "item_id": item_id,
                "author": repo_data.get("author"),
                "title": repo_data.get("title"),
                "name": repo_data.get("name"),
                "url": repo_data.get("url"),
                "description": repo_data.get("summary"),
                "language": repo_data.get("primary_lang"),
                "total_stars": repo_data.get("stars", 0),
                "total_issues": repo_data.get("open_issues", 0),
                "total_forks": repo_data.get("forks", 0),
                "contributors": repo_data.get("contributors", []),
                "last_week_stars": last_week_stars,
                "tags": tags,
                "related_urls": related_urls,
            }
            
        except Exception as e:
            print(f"获取项目详情失败: {e}")
            return None
    
    async def get_news_list(self, category: str = "all") -> List[Dict]:
        """获取项目列表（兼容接口）"""
        return await self.get_hot_items(page=1, category=category)
    
    async def get_news_info(self, item: Dict, category: str = None) -> Optional[Dict]:
        """获取项目详情"""
        item_id = item.get("item_id")
        detail = await self.get_item_detail(item_id) if item_id else None
        
        if not detail:
            # 使用列表页的基本信息
            content = f"""# {item.get('title')}

**项目地址**: {item.get('url')}

## 项目简介
{item.get('description', '暂无简介')}

"""
            if item.get('title_en'):
                content += f"**英文标题**: {item.get('title_en')}\n\n"
            if item.get('description_en'):
                content += f"**英文简介**: {item.get('description_en')}\n\n"
            content += f"**编程语言**: {item.get('language', '未知')}\n"
            content += f"**更新时间**: {item.get('updated_at', '未知')}\n"
            
            return {
                "title": item.get('title', 'Untitled'),
                "content": content,
                "source": self.source_name,
                "category": self.category,
                "url": item.get('url', ''),
                "extra": {
                    "language": item.get('language'),
                    "author": item.get('author'),
                }
            }
        
        # 构建文章内容
        content = f"""# {detail['title']}

**项目地址**: {detail['url']}

## 项目简介
{detail['description']}

## 统计数据
- 👀 总点击: {item.get('clicks', 0)}
- 🍴 总Forks: {detail['total_forks']}
- 🐛 开放Issues: {detail['total_issues']}
- 📈 上周新增Stars: {detail['last_week_stars']}

## 编程语言
{detail['language'] or '未分类'}

## 标签
{', '.join(detail['tags']) if detail['tags'] else '无'}

## 相关链接
"""
        for link in detail.get("related_urls", []):
            content += f"- [{link['title']}]({link['url']})\n"
        
        return {
            "title": f"{detail['title']} - {detail['total_stars']} Stars",
            "content": content,
            "source": self.source_name,
            "category": self.category,
            "url": detail['url'],
            "extra": {
                "stars": detail['total_stars'],
                "forks": detail['total_forks'],
                "language": detail['language'],
                "tags": detail['tags'],
            }
        }


class AITools:
    """热门AI工具爬虫"""
    
    source_name = "AITools"
    category = "AI工具"
    
    # AI工具导航站
    URLS = [
        "https://www.producthunt.com/categories/artificial-intelligence",
        "https://www.futurepedia.io/",
    ]
    
    async def request(self, url: str, **kwargs) -> str:
        """发送HTTP请求"""
        async with aiohttp.ClientSession() as session:
            async with session.get(url, **kwargs) as response:
                return await response.text()
    
    async def get_news_list(self, code=None) -> List[Dict]:
        """获取AI工具列表"""
        # 这里可以添加更多AI工具网站
        # 目前返回空列表，需要时可扩展
        return []
    
    async def get_news_info(self, item: Dict, category: str = None) -> Optional[Dict]:
        """获取工具详情"""
        return None


class AIPapers:
    """热门AI论文爬虫"""
    
    source_name = "AIPapers"
    category = "AI论文"
    
    # AI论文资源
    URLS = [
        "https://paperswithcode.com/",
        "https://arxiv.org/list/cs.AI/recent",
    ]
    
    async def request(self, url: str, **kwargs) -> str:
        """发送HTTP请求"""
        async with aiohttp.ClientSession() as session:
            async with session.get(url, **kwargs) as response:
                return await response.text()
    
    async def get_news_list(self, code=None) -> List[Dict]:
        """获取AI论文列表"""
        # 这里可以添加论文网站
        # 目前返回空列表，需要时可扩展
        return []
    
    async def get_news_info(self, item: Dict, category: str = None) -> Optional[Dict]:
        """获取论文详情"""
        return None
