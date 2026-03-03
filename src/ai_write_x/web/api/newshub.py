# -*- coding: utf-8 -*-
"""
NewsHub Web API
提供热点新闻聚合的HTTP接口
"""

from typing import List, Optional
from datetime import datetime
from fastapi import APIRouter, HTTPException, Query
from pydantic import BaseModel

from src.ai_write_x.news_aggregator import NewsHubManager, DataSourceCategory
from src.ai_write_x.utils import log

router = APIRouter(prefix="/api/newshub", tags=["newshub"])

# 全局管理器实例
hub_manager: Optional[NewsHubManager] = None


def get_hub_manager() -> NewsHubManager:
    """获取NewsHub管理器"""
    global hub_manager
    if hub_manager is None:
        hub_manager = NewsHubManager()
    return hub_manager


# 请求/响应模型
class AggregateRequest(BaseModel):
    """聚合请求"""
    categories: List[str] = []
    min_score: float = 0
    limit: int = 200


class NewsItemResponse(BaseModel):
    """新闻项响应"""
    id: str
    title: str
    summary: str
    category: str
    keywords: List[str]
    score: float
    sentiment: str
    source: str
    published_at: datetime


class TrendItemResponse(BaseModel):
    """趋势项响应"""
    keyword: str
    count: int
    hot_score: float
    growth_rate: float
    sources: List[str]


class AggregateResponse(BaseModel):
    """聚合响应"""
    status: str
    data: List[NewsItemResponse]
    trends: List[TrendItemResponse]
    stats: dict
    generated_at: datetime


class SourcesResponse(BaseModel):
    """数据源响应"""
    sources: List[dict]
    total: int
    enabled: int


@router.post("/aggregate", response_model=AggregateResponse)
async def aggregate_news(request: AggregateRequest):
    """
    执行新闻聚合
    
    从多个数据源获取热点新闻，进行AI处理和去重
    """
    try:
        manager = get_hub_manager()
        
        # 转换分类
        categories = None
        if request.categories:
            cat_map = {
                "tech": DataSourceCategory.TECH,
                "finance": DataSourceCategory.FINANCE,
                "social": DataSourceCategory.SOCIAL,
                "programming": DataSourceCategory.PROGRAMMING,
                "ai": DataSourceCategory.AI_ML,
                "startup": DataSourceCategory.STARTUP,
            }
            categories = [
                cat_map[c] for c in request.categories 
                if c in cat_map
            ]
        
        # 执行聚合
        result = await manager.aggregate_once(
            categories=categories,
            min_score=request.min_score
        )
        
        # 构建响应
        news_items = [
            NewsItemResponse(
                id=str(c.id),
                title=c.title,
                summary=c.summary[:200] if c.summary else "",
                category=c.category,
                keywords=c.keywords[:8],
                score=c.score.overall,
                sentiment=c.sentiment.sentiment.value,
                source=c.metadata.get("source", ""),
                published_at=result.generated_at,
            )
            for c in result.contents[:request.limit]
        ]
        
        trends = [
            TrendItemResponse(
                keyword=t.keyword,
                count=t.count,
                hot_score=t.hot_score,
                growth_rate=t.growth_rate,
                sources=t.sources,
            )
            for t in result.trends.top_trends[:10]
        ]
        
        return AggregateResponse(
            status="success",
            data=news_items,
            trends=trends,
            stats=result.stats,
            generated_at=result.generated_at,
        )
        
    except Exception as e:
        log.print_log(f"[NewsHub API] 聚合失败: {e}", "error")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/trends")
async def get_trends(
    category: str = Query("", description="分类筛选"),
    limit: int = Query(10, ge=1, le=50),
):
    """
    获取当前热点趋势
    """
    try:
        manager = get_hub_manager()
        trends = manager.get_realtime_trends(top_n=limit)
        
        return {
            "status": "success",
            "data": [
                {"keyword": t, "rank": i+1}
                for i, t in enumerate(trends)
            ],
            "generated_at": datetime.now(),
        }
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/sources", response_model=SourcesResponse)
async def get_sources():
    """
    获取所有数据源信息
    """
    try:
        manager = get_hub_manager()
        sources = manager.get_sources_info()
        
        return SourcesResponse(
            sources=sources,
            total=len(sources),
            enabled=sum(1 for s in sources if s.get("enabled", False)),
        )
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/sources/{source_id}/enable")
async def enable_source(source_id: str):
    """启用数据源"""
    try:
        manager = get_hub_manager()
        manager.enable_source(source_id)
        return {"status": "success", "message": f"数据源 {source_id} 已启用"}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/sources/{source_id}/disable")
async def disable_source(source_id: str):
    """禁用数据源"""
    try:
        manager = get_hub_manager()
        manager.disable_source(source_id)
        return {"status": "success", "message": f"数据源 {source_id} 已禁用"}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/github/trending")
async def get_github_trending(
    language: str = Query("", description="编程语言"),
    since: str = Query("daily", description="时间范围: daily/weekly/monthly"),
    limit: int = Query(10, ge=1, le=50),
):
    """
    获取GitHub热门项目
    """
    try:
        # 直接调用异步方法而非经过 _run 同步包装（避免嵌套事件循环）
        from src.ai_write_x.news_aggregator.mcp_tools import GitHubTrendingTool
        
        tool = GitHubTrendingTool()
        repos = await tool._fetch_github_trending(
            language=language,
            since=since,
            min_stars=100,
        )
        result = tool._format_github_result(repos, since, language)
        
        return {
            "status": "success",
            "data": result,
            "generated_at": datetime.now(),
        }
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/stats")
async def get_stats():
    """
    获取聚合统计信息
    """
    try:
        manager = get_hub_manager()
        
        # 获取处理统计
        ai_stats = manager.ai_processor.get_stats()
        
        return {
            "status": "success",
            "data": {
                "ai_processing": ai_stats,
                "sources": len(manager.get_sources_info()),
                "last_update": datetime.now(),
            }
        }
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
