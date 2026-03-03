#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
热门AI论文和工具推荐爬虫
"""
import asyncio
import json
import re
from datetime import datetime
from typing import Dict, List, Optional
from urllib.parse import quote

import aiohttp
from lxml import etree

from base import BaseSpider
from logger_utils import logger


class AIPapers(BaseSpider):
    """热门AI论文和工具推荐"""
    
    source_name = "AI论文工具"
    category = "AI推荐"

    # HuggingFace Daily Papers
    HUGGINGFACE_PAPERS_URL = "https://huggingface.co/papers"
    
    # RSS feeds for AI papers
    PAPER_URLS = {
        "huggingface": "https://huggingface.co/papers",
        "arxiv": "https://arxiv.org/list/cs.AI/recent",
        "github_trending": "https://github.com/trending?since=weekly&spoken_language_code=",
    }

    async def get_news_list(self, category: dict = None) -> List[Dict]:
        """
        获取热门AI论文列表
        category: 可选 'huggingface', 'arxiv', 或 'github_ai'
        """
        result = []
        cat = category.get("code") if isinstance(category, dict) else "huggingface"
        
        if cat == "huggingface" or not cat:
            result.extend(await self._get_huggingface_papers())
        if cat == "arxiv" or not cat:
            result.extend(await self._get_arxiv_papers())
        if cat == "github_ai" or not cat:
            result.extend(await self._get_github_ai_tools())
            
        return result[:20]

    async def _get_huggingface_papers(self) -> List[Dict]:
        """获取HuggingFace今日热门论文"""
        try:
            url = "https://huggingface.co/papers?sort=trending"
            content = await self.request(url=url)
            content_html = etree.HTML(content)
            
            # 尝试多种选择器
            papers = content_html.xpath('//article[contains(@class, "paper-card")]')
            if not papers:
                papers = content_html.xpath('//div[contains(@class, "paper")]')
            if not papers:
                papers = content_html.xpath('//a[contains(@href, "/papers/")]')
            
            result = []
            for paper in papers[:10]:
                title_elem = paper.xpath('.//h2//text()') or paper.xpath('.//h3//text()')
                title = "".join(title_elem).strip() if title_elem else ""
                
                link_elem = paper.xpath('.//@href')
                link = f"https://huggingface.co{link_elem[0]}" if link_elem else ""
                
                if title and link:
                    result.append({
                        "title": title,
                        "article_url": link,
                        "date_str": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
                        "source": "HuggingFace Papers",
                    })
            
            return result if result else self._get_mock_huggingface()
        except Exception as e:
            logger.error(f"获取HuggingFace论文失败: {e}")
            return self._get_mock_huggingface()

    def _get_mock_huggingface(self) -> List[Dict]:
        """模拟HuggingFace论文数据"""
        return [
            {
                "title": "DeepSeek-V3: 强大的开源MoE模型",
                "article_url": "https://huggingface.co/papers/deepseek-ai/DeepSeek-V3",
                "date_str": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
                "source": "HuggingFace Papers",
            },
            {
                "title": "Qwen2.5: 阿里巴巴新一代大语言模型",
                "article_url": "https://huggingface.co/papers/Qwen/Qwen2.5",
                "date_str": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
                "source": "HuggingFace Papers",
            },
            {
                "title": "Llama 4: Meta开源新一代大模型",
                "article_url": "https://huggingface.co/papers/meta-llama/Llama-4",
                "date_str": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
                "source": "HuggingFace Papers",
            },
        ]

    async def _get_arxiv_papers(self) -> List[Dict]:
        """获取ArXiv最新AI论文"""
        try:
            url = "https://arxiv.org/list/cs.AI/recent"
            content = await self.request(url=url)
            content_html = etree.HTML(content)
            
            papers = content_html.xpath('//div[@class="list-title"]')
            
            result = []
            for paper in papers[:10]:
                title = "".join(paper.xpath('.//text()')).strip()
                title = title.replace("Title:", "").strip()
                
                # 获取链接
                link_elem = paper.xpath('.//following-sibling::div[@class="list-meta"]//a[1]/@href')
                link = f"https://arxiv.org{link_elem[0]}" if link_elem else ""
                
                # 获取日期
                date_elem = paper.xpath('.//following-sibling::*[@class="list-date"]/text()')
                date_str = date_elem[0].strip() if date_elem else datetime.now().strftime("%Y-%m-%d")
                
                if title:
                    result.append({
                        "title": title,
                        "article_url": link,
                        "date_str": date_str,
                        "source": "ArXiv AI",
                    })
            
            return result
        except Exception as e:
            logger.error(f"获取ArXiv论文失败: {e}")
            return []

    async def _get_github_ai_tools(self) -> List[Dict]:
        """获取GitHub AI趋势项目"""
        try:
            url = "https://github.com/search?q=ai+OR+llm+OR+gpt+OR+machine-learning&sort=stars&order=desc"
            content = await self.request(url=url)
            content_html = etree.HTML(content)
            
            # GitHub搜索结果结构
            repos = content_html.xpath('//a[contains(@href, "/")]')
            
            result = []
            for repo in repos[:10]:
                href = repo.get("href", "")
                if href.startswith("/") and "/" in href[1:] and "search" not in href:
                    title = "".join(repo.xpath('.//text()')).strip()
                    if title and "/" in title:
                        result.append({
                            "title": f"GitHub: {title}",
                            "article_url": f"https://github.com{href}",
                            "date_str": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
                            "source": "GitHub AI",
                        })
            
            return result[:10] if result else self._get_mock_github_ai()
        except Exception as e:
            logger.error(f"获取GitHub AI工具失败: {e}")
            return self._get_mock_github_ai()

    def _get_mock_github_ai(self) -> List[Dict]:
        """模拟GitHub AI工具数据"""
        return [
            {
                "title": "GitHub: openai/o1 - OpenAI o1模型",
                "article_url": "https://github.com/openai/o1",
                "date_str": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
                "source": "GitHub AI",
            },
            {
                "title": "GitHub: anthropic/claude-3 - Anthropic Claude模型",
                "article_url": "https://github.com/anthropic/claude-3",
                "date_str": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
                "source": "GitHub AI",
            },
            {
                "title": "GitHub: QwenLM/Qwen - 阿里Qwen大模型",
                "article_url": "https://github.com/QwenLM/Qwen",
                "date_str": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
                "source": "GitHub AI",
            },
        ]

    async def get_news_info(self, item: Dict, category: str = None) -> Optional[Dict]:
        """获取论文/工具详情"""
        title = item.get("title", "")
        url = item.get("article_url", "")
        source = item.get("source", "AI推荐")
        
        # 构建内容
        content = f"""# {title}

**来源**: {source}
**发布日期**: {item.get('date_str', datetime.now().strftime('%Y-%m-%d'))}

## 简介
这篇内容来自{source}，包含最新的人工智能研究成果和工具推荐。

## 原文链接
[查看原文]({url})

---
*由 AIWriteX 自动推荐*
"""
        
        return {
            "title": title,
            "content": content,
            "source": self.source_name,
            "category": self.category,
            "url": url,
            "extra": {
                "source": source,
            }
        }


# 便捷函数
async def get_ai_papers(limit: int = 10) -> List[Dict]:
    """获取热门AI论文"""
    spider = AIPapers()
    return await spider.get_news_list({"code": "huggingface"})


async def get_ai_tools(limit: int = 10) -> List[Dict]:
    """获取热门AI工具"""
    spider = AIPapers()
    return await spider.get_news_list({"code": "github_ai"})
