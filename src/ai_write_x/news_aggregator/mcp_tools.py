# -*- coding: utf-8 -*-
"""
NewsHub MCP 工具
为AI提供热点新闻查询能力
"""

from typing import Dict, List, Any, Optional
from crewai.tools import BaseTool
from pydantic import BaseModel, Field
from datetime import datetime, timedelta

from .hub_manager import NewsHubManager, aggregate_news
from .data_sources import DataSourceCategory
from src.ai_write_x.utils import log


class NewsQueryInput(BaseModel):
    """新闻查询输入"""
    query: str = Field(..., description="查询关键词或主题")
    category: str = Field(default="", description="分类筛选: tech/finance/social/ai/programming/startup")
    limit: int = Field(default=10, description="返回数量")
    min_score: float = Field(default=6.0, description="最小分数")


class TrendQueryInput(BaseModel):
    """趋势查询输入"""
    time_window: str = Field(default="24h", description="时间窗口: 1h/24h/7d")
    category: str = Field(default="", description="分类筛选")
    top_n: int = Field(default=10, description="返回Top N")


class GitHubTrendingInput(BaseModel):
    """GitHub趋势查询输入"""
    language: str = Field(default="", description="编程语言筛选")
    since: str = Field(default="daily", description="时间范围: daily/weekly/monthly")
    min_stars: int = Field(default=100, description="最小星标数")


class NewsHubMCPTool(BaseTool):
    """
    NewsHub MCP 工具
    
    提供热点新闻聚合和趋势分析能力
    """
    name: str = "news_hub_tool"
    description: str = """智能新闻聚合工具，获取全网热点资讯。

功能：
1. 热点新闻聚合 - 从50+数据源获取最新资讯
2. 趋势分析 - 识别当前热门话题和趋势
3. GitHub趋势 - 获取开源项目热榜
4. 智能搜索 - 基于关键词搜索相关新闻

使用场景：
- 获取最新科技动态
- 追踪热点话题
- 发现热门开源项目
- 了解行业趋势

示例：
- "获取今天最热门的AI新闻"
- "GitHub上有什么新的热门项目"
- "最近有什么创业融资消息"
"""
    args_schema: type[BaseModel] = NewsQueryInput
    
    def _run(self, query: str, category: str = "", 
            limit: int = 10, min_score: float = 6.0) -> str:
        """同步执行"""
        import asyncio
        
        try:
            loop = asyncio.new_event_loop()
            asyncio.set_event_loop(loop)
            result = loop.run_until_complete(
                self._async_run(query, category, limit, min_score)
            )
            loop.close()
            return result
        except Exception as e:
            return f"新闻查询失败: {str(e)}"
    
    async def _async_run(self, query: str, category: str,
                        limit: int, min_score: float) -> str:
        """异步执行"""
        try:
            # 解析分类
            categories = self._parse_categories(category)
            
            # 创建管理器并执行聚合
            hub_manager = NewsHubManager()
            result = await hub_manager.aggregate_once(
                categories=categories,
                min_score=min_score
            )
            
            # 格式化输出
            return self._format_result(result, query, limit)
            
        except Exception as e:
            log.print_log(f"[NewsHub MCP] 查询失败: {e}", "error")
            return f"查询失败: {str(e)}"
    
    def _parse_categories(self, category_str: str) -> Optional[List[DataSourceCategory]]:
        """解析分类字符串"""
        if not category_str:
            return None
        
        cat_map = {
            "tech": DataSourceCategory.TECH,
            "finance": DataSourceCategory.FINANCE,
            "social": DataSourceCategory.SOCIAL,
            "programming": DataSourceCategory.PROGRAMMING,
            "ai": DataSourceCategory.AI_ML,
            "startup": DataSourceCategory.STARTUP,
        }
        
        categories = []
        for cat in category_str.split(","):
            cat = cat.strip().lower()
            if cat in cat_map:
                categories.append(cat_map[cat])
        
        return categories if categories else None
    
    def _format_result(self, result, query: str, limit: int) -> str:
        """格式化结果"""
        lines = []
        
        lines.append(f"=== 热点新闻聚合结果 [{query}] ===\n")
        lines.append(f"生成时间: {result.generated_at.strftime('%Y-%m-%d %H:%M')}")
        lines.append(f"数据来源: {result.stats.get('total_sources', 0)} 个")
        lines.append(f"精选内容: {len(result.contents)} 条\n")
        
        # 趋势概览
        if result.trends.top_trends:
            lines.append("【当前热点趋势】")
            for i, trend in enumerate(result.trends.top_trends[:5], 1):
                lines.append(f"{i}. {trend.keyword} (热度: {trend.hot_score:.1f})")
            lines.append("")
        
        # 精选内容
        if result.contents:
            lines.append("【精选内容】\n")
            for i, content in enumerate(result.contents[:limit], 1):
                lines.append(f"{i}. {content.title}")
                lines.append(f"   分类: {content.category} | 评分: {content.score.overall}/10")
                if content.summary:
                    lines.append(f"   摘要: {content.summary[:100]}...")
                if content.keywords:
                    lines.append(f"   关键词: {', '.join(content.keywords[:5])}")
                lines.append("")
        
        return "\n".join(lines)


class TrendAnalysisTool(BaseTool):
    """
    趋势分析工具
    分析热点趋势和预测
    """
    name: str = "trend_analysis_tool"
    description: str = """分析热点趋势和话题热度。

功能：
- 识别当前最热门的话题
- 分析趋势增长/下降
- 预测未来趋势
- 发现突发热点

示例：
- "分析最近24小时的热门话题"
- "AI领域有什么新趋势"
- "哪些话题正在降温"
"""
    args_schema: type[BaseModel] = TrendQueryInput
    
    def _run(self, time_window: str = "24h", category: str = "",
            top_n: int = 10) -> str:
        """执行趋势分析"""
        try:
            # 模拟趋势数据（实际应该从数据库获取）
            trends = self._get_mock_trends(time_window, category)
            
            lines = []
            lines.append(f"=== 热点趋势分析 [{time_window}] ===\n")
            
            # Top趋势
            lines.append("【热门话题 Top 10】")
            for i, trend in enumerate(trends[:top_n], 1):
                growth = "📈" if trend.get('growth', 0) > 0 else "📉" if trend.get('growth', 0) < 0 else "➡️"
                lines.append(f"{i}. {trend['keyword']} {growth}")
                lines.append(f"   热度: {trend['hot_score']:.1f} | 增长: {trend.get('growth', 0):.1%}")
            
            lines.append("")
            
            # 新兴趋势
            emerging = [t for t in trends if t.get('growth', 0) > 0.5]
            if emerging:
                lines.append("【新兴趋势 🔥】")
                for trend in emerging[:5]:
                    lines.append(f"• {trend['keyword']} (增长: {trend['growth']:.1%})")
                lines.append("")
            
            # 预测
            lines.append("【趋势预测】")
            lines.append("基于当前数据分析，以下话题可能在未来24小时内持续升温：")
            hot_topics = [t['keyword'] for t in trends[:3]]
            lines.append(f"• {'、'.join(hot_topics)}")
            
            return "\n".join(lines)
            
        except Exception as e:
            return f"趋势分析失败: {str(e)}"
    
    def _get_mock_trends(self, time_window: str, category: str) -> List[Dict]:
        """获取模拟趋势数据（实际应该从数据库读取）"""
        # 这里应该查询实际的趋势数据
        mock_trends = [
            {"keyword": "AI大模型", "hot_score": 95.5, "growth": 0.35},
            {"keyword": "GitHub开源项目", "hot_score": 88.2, "growth": 0.28},
            {"keyword": "ChatGPT", "hot_score": 82.1, "growth": -0.05},
            {"keyword": "Python", "hot_score": 78.5, "growth": 0.15},
            {"keyword": "创业公司融资", "hot_score": 75.3, "growth": 0.42},
            {"keyword": "Claude", "hot_score": 72.8, "growth": 0.55},
            {"keyword": "React", "hot_score": 68.5, "growth": 0.08},
            {"keyword": "Docker", "hot_score": 65.2, "growth": 0.12},
            {"keyword": "Kubernetes", "hot_score": 62.1, "growth": 0.18},
            {"keyword": "区块链", "hot_score": 58.5, "growth": -0.15},
        ]
        return mock_trends


class GitHubTrendingTool(BaseTool):
    """
    GitHub趋势工具
    获取GitHub热门项目
    """
    name: str = "github_trending_tool"
    description: str = """获取GitHub热门开源项目。

功能：
- 获取今日/本周/本月热门项目
- 按编程语言筛选
- 查看星标增长趋势

示例：
- "今天GitHub有什么热门项目"
- "Python领域有什么新项目"
- "本周增长最快的开源项目"
"""
    args_schema: type[BaseModel] = GitHubTrendingInput
    
    def _run(self, language: str = "", since: str = "daily",
            min_stars: int = 100) -> str:
        """获取GitHub趋势"""
        try:
            import asyncio
            
            loop = asyncio.new_event_loop()
            asyncio.set_event_loop(loop)
            
            # 获取GitHub数据
            result = loop.run_until_complete(
                self._fetch_github_trending(language, since, min_stars)
            )
            
            loop.close()
            
            return self._format_github_result(result, since, language)
            
        except Exception as e:
            return f"获取GitHub趋势失败: {str(e)}"
    
    async def _fetch_github_trending(self, language: str, since: str,
                                     min_stars: int) -> List[Dict]:
        """获取GitHub趋势数据"""
        import aiohttp
        
        repos = []
        
        try:
            # 计算日期范围
            if since == "weekly":
                date_filter = (datetime.now() - timedelta(days=7)).strftime("%Y-%m-%d")
            elif since == "monthly":
                date_filter = (datetime.now() - timedelta(days=30)).strftime("%Y-%m-%d")
            else:
                date_filter = (datetime.now() - timedelta(days=1)).strftime("%Y-%m-%d")
            
            # 构建查询
            query_parts = [f"created:>{date_filter}"]
            if language:
                query_parts.append(f"language:{language}")
            
            query = " ".join(query_parts)
            
            url = "https://api.github.com/search/repositories"
            params = {
                "q": query,
                "sort": "stars",
                "order": "desc",
                "per_page": 20
            }
            
            async with aiohttp.ClientSession() as session:
                async with session.get(url, params=params) as response:
                    if response.status == 200:
                        data = await response.json()
                        for repo in data.get("items", []):
                            if repo["stargazers_count"] >= min_stars:
                                repos.append({
                                    "name": repo["full_name"],
                                    "description": repo["description"] or "No description",
                                    "stars": repo["stargazers_count"],
                                    "language": repo["language"] or "Unknown",
                                    "url": repo["html_url"],
                                    "forks": repo["forks_count"],
                                })
        except Exception as e:
            log.print_log(f"[GitHubTool] 获取失败: {e}", "warning")
        
        return repos
    
    def _format_github_result(self, repos: List[Dict], since: str,
                             language: str) -> str:
        """格式化GitHub结果"""
        lines = []
        
        lang_str = f" [{language}]" if language else ""
        lines.append(f"=== GitHub Trending{lang_str} [{since}] ===\n")
        
        if not repos:
            lines.append("暂无符合条件的热门项目")
            return "\n".join(lines)
        
        for i, repo in enumerate(repos[:10], 1):
            lines.append(f"{i}. {repo['name']}")
            lines.append(f"   ⭐ {repo['stars']:,} | 🍴 {repo['forks']:,} | {repo['language']}")
            lines.append(f"   {repo['description'][:80]}...")
            lines.append(f"   🔗 {repo['url']}")
            lines.append("")
        
        return "\n".join(lines)


# 工具注册类列表
NEWSHUB_TOOLS = [
    NewsHubMCPTool,
    TrendAnalysisTool,
    GitHubTrendingTool,
]