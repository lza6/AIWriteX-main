#!/usr/bin/env python
# -*- coding: UTF-8 -*-
"""
爬虫管理 API
"""
import asyncio
from fastapi import APIRouter, HTTPException
from pydantic import BaseModel
from typing import Optional, List, Dict

from src.ai_write_x.tools.spider_runner import spider_runner

router = APIRouter(prefix="/api/spider", tags=["spider"])


class RunSpiderRequest(BaseModel):
    """运行爬虫请求"""
    spider_name: Optional[str] = None  # 如果为空，则运行所有爬虫
    limit: int = 10  # 每次爬取的文章数量


@router.get("/list")
async def get_spider_list():
    """获取爬虫列表"""
    return {
        "success": True,
        "spiders": spider_runner.get_spider_list()
    }


@router.get("/stats")
async def get_spider_stats():
    """获取爬虫统计"""
    return {
        "success": True,
        "stats": spider_runner.get_stats()
    }


@router.get("/articles")
async def get_articles(
    limit: int = 100,
    source: Optional[str] = None,
    category: Optional[str] = None
):
    """获取爬取的文章列表 (整合 NewsHub 缓存)"""
    # 1. 获取基础爬虫文章
    articles = spider_runner.get_articles(limit, source, category)
    
    # 2. 如果没有指定源或指定了 NewsHub，则加入 NewsHub 缓存
    if not source or source == "newshub":
        try:
            from src.ai_write_x.web.api.newshub import get_hub_manager
            hub_manager = get_hub_manager()
            cached_news = hub_manager.get_cached_news(limit=50)
            
            # 转换为兼容格式
            for item in cached_news:
                articles.append({
                    "id": item.get("id"),
                    "title": item.get("title"),
                    "source": "热点聚合", # 统一标记为热点聚合
                    "url": item.get("url"),
                    "save_date": item.get("published_at", "")[:10] if item.get("published_at") else ""
                })
        except Exception as e:
            print(f"Merge NewsHub error: {e}")

    # 3. 按日期/ID排序（简单处理）
    articles = articles[:limit]
    
    return {
        "success": True,
        "articles": articles,
        "count": len(articles)
    }


@router.post("/run")
async def run_spider(request: RunSpiderRequest):
    """运行爬虫"""
    try:
        if request.spider_name:
            # 运行单个爬虫
            result = await spider_runner.run_spider(request.spider_name, request.limit)
            return result
        else:
            # 运行所有爬虫（后台执行）
            result = spider_runner.run_in_background(request.limit)
            return result
    except Exception as e:
        return {"success": False, "message": str(e)}


@router.get("/status")
async def get_status():
    """获取爬虫运行状态"""
    from src.ai_write_x.tools.spider_runner import get_task_status
    return get_task_status()


@router.post("/run/{spider_name}")
async def run_single_spider(spider_name: str, limit: int = 10):
    """运行指定爬虫"""
    try:
        result = await spider_runner.run_spider(spider_name, limit)
        return result
    except Exception as e:
        return {"success": False, "message": str(e)}


@router.delete("/articles/{article_url}")
async def delete_article(article_url: str):
    """删除文章"""
    from src.ai_write_x.tools.spider_manager import spider_data_manager
    
    success = spider_data_manager.delete_article(article_url)
    return {"success": success}


@router.delete("/articles/by-id/{article_id}")
async def delete_article_by_id(article_id: str):
    """通过ID删除文章"""
    from src.ai_write_x.tools.spider_manager import spider_data_manager
    
    success = spider_data_manager.delete_article_by_id(article_id)
    return {"success": success}


@router.delete("/articles")
async def clear_articles():
    """清空所有文章"""
    from src.ai_write_x.tools.spider_manager import spider_data_manager
    
    success = spider_data_manager.clear_articles()
    return {"success": success}


# ========== 新增API ==========

@router.get("/failed")
async def get_failed():
    """获取失败记录"""
    from src.ai_write_x.tools.spider_manager import spider_data_manager
    
    failed = spider_data_manager.get_failed()
    return {
        "success": True,
        "failed": failed,
        "count": len(failed)
    }


@router.delete("/failed")
async def clear_failed():
    """清空失败记录"""
    from src.ai_write_x.tools.spider_manager import spider_data_manager
    
    success = spider_data_manager.clear_failed()
    return {"success": success}


@router.get("/settings")
async def get_settings():
    """获取设置"""
    from src.ai_write_x.tools.spider_manager import spider_data_manager
    
    settings = spider_data_manager.get_settings()
    return {
        "success": True,
        "settings": settings
    }


@router.post("/settings")
async def save_settings(enabled: bool = False, days: int = 7):
    """保存设置"""
    from src.ai_write_x.tools.spider_manager import spider_data_manager
    
    success = spider_data_manager.set_auto_delete(enabled, days)
    return {"success": success}


@router.get("/path")
async def get_save_path():
    """获取文章保存路径"""
    from src.ai_write_x.tools.spider_manager import spider_data_manager
    
    return {
        "success": True,
        "path": spider_data_manager.get_save_path(),
        "total_count": spider_data_manager.get_total_count()
    }


@router.get("/dates")
async def get_article_dates():
    """获取文章日期列表"""
    from src.ai_write_x.tools.spider_manager import spider_data_manager
    
    dates = spider_data_manager.get_article_dates()
    return {
        "success": True,
        "dates": dates
    }


@router.delete("/articles/by-date/{date}")
async def delete_articles_by_date(date: str):
    """删除指定日期的文章"""
    from src.ai_write_x.tools.spider_manager import spider_data_manager
    
    count = spider_data_manager.delete_articles_by_date(date)
    return {"success": True, "deleted": count}


@router.post("/auto-delete")
async def trigger_auto_delete():
    """手动触发自动删除"""
    from src.ai_write_x.tools.spider_manager import spider_data_manager
    
    count = spider_data_manager.auto_delete_old_articles()
    return {"success": True, "deleted": count}
