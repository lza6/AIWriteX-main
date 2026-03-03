"""
知识图谱API接口
"""

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel
from typing import Optional, List, Dict, Any

from src.ai_write_x.core.knowledge_graph import (
    get_semantic_analyzer,
    EntityType,
)
from src.ai_write_x.utils import log

router = APIRouter(prefix="/knowledge", tags=["knowledge"])


class AnalyzeRequest(BaseModel):
    """分析请求"""
    text: str


class SearchRequest(BaseModel):
    """搜索请求"""
    query: str


class NetworkRequest(BaseModel):
    """网络请求"""
    entity_name: str
    depth: int = 2


@router.post("/analyze")
async def analyze_text(request: AnalyzeRequest):
    """分析文本并构建知识图谱"""
    try:
        analyzer = get_semantic_analyzer()
        result = analyzer.analyze(request.text)
        
        return {
            "status": "success",
            "data": result
        }
    except Exception as e:
        log.print_log(f"知识图谱分析失败: {str(e)}", "error")
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/search")
async def search_entities(request: SearchRequest):
    """搜索实体"""
    try:
        analyzer = get_semantic_analyzer()
        results = analyzer.knowledge_graph.search(request.query)
        
        return {
            "status": "success",
            "data": {
                "query": request.query,
                "results": results,
            }
        }
    except Exception as e:
        log.print_log(f"实体搜索失败: {str(e)}", "error")
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/network")
async def get_entity_network(request: NetworkRequest):
    """获取实体关系网络"""
    try:
        analyzer = get_semantic_analyzer()
        network = analyzer.get_entity_network(request.entity_name)
        
        return {
            "status": "success",
            "data": network
        }
    except Exception as e:
        log.print_log(f"获取实体网络失败: {str(e)}", "error")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/top-entities")
async def get_top_entities(entity_type: Optional[str] = None, limit: int = 10):
    """获取热门实体"""
    try:
        analyzer = get_semantic_analyzer()
        
        et = None
        if entity_type:
            try:
                et = EntityType(entity_type)
            except ValueError:
                pass
        
        entities = analyzer.knowledge_graph.get_top_entities(et, limit)
        
        return {
            "status": "success",
            "data": entities
        }
    except Exception as e:
        log.print_log(f"获取热门实体失败: {str(e)}", "error")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/export")
async def export_knowledge_graph():
    """导出知识图谱"""
    try:
        analyzer = get_semantic_analyzer()
        graph = analyzer.knowledge_graph.export_graph()
        
        return {
            "status": "success",
            "data": graph
        }
    except Exception as e:
        log.print_log(f"导出知识图谱失败: {str(e)}", "error")
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/clear")
async def clear_knowledge_graph():
    """清空知识图谱"""
    try:
        analyzer = get_semantic_analyzer()
        analyzer.knowledge_graph.clear()
        
        return {
            "status": "success",
            "message": "知识图谱已清空"
        }
    except Exception as e:
        log.print_log(f"清空知识图谱失败: {str(e)}", "error")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/entity-types")
async def get_entity_types():
    """获取实体类型列表"""
    types = [
        {"value": t.value, "label": _get_entity_type_label(t)}
        for t in EntityType
    ]
    
    return {
        "status": "success",
        "data": types
    }


def _get_entity_type_label(entity_type: EntityType) -> str:
    """获取实体类型的中文标签"""
    labels = {
        EntityType.PERSON: "人物",
        EntityType.ORGANIZATION: "组织机构",
        EntityType.LOCATION: "地点",
        EntityType.EVENT: "事件",
        EntityType.CONCEPT: "概念",
        EntityType.TIME: "时间",
        EntityType.PRODUCT: "产品",
        EntityType.TECHNOLOGY: "技术",
        EntityType.TOPIC: "主题",
    }
    return labels.get(entity_type, entity_type.value)
