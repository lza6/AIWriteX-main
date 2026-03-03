"""
内容质量检测API接口
"""

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel
from typing import Optional, List, Dict, Any
import asyncio

from src.ai_write_x.core.quality_engine import (
    ContentQualityEngine,
    AutoOptimizer,
    ContentAnalysisResult,
)
from src.ai_write_x.utils import log

router = APIRouter(prefix="/api/quality", tags=["quality"])


class AnalyzeRequest(BaseModel):
    """分析请求"""
    content: str


class OptimizeRequest(BaseModel):
    """优化请求"""
    content: str
    target_originality: float = 75.0
    max_ai_likelihood: float = 30.0
    max_iterations: int = 5


class CompareRequest(BaseModel):
    """对比请求"""
    original: str
    optimized: str


class OptimizeWithSuggestionsRequest(BaseModel):
    """基于建议的优化请求"""
    content: str
    suggestions: List[str]
    mode: str = "agent"  # agent 或 simple


class AnalyzeResponse(BaseModel):
    """分析响应"""
    status: str
    data: Dict[str, Any]


@router.post("/analyze")
async def analyze_content(request: AnalyzeRequest):
    """分析内容质量"""
    try:
        engine = ContentQualityEngine()
        result = engine.analyze_content(request.content)
        
        # 转换为可序列化的字典
        scores_dict = {}
        for metric, score in result.quality_scores.items():
            scores_dict[metric] = {
                "score": score.score,
                "details": score.details,
                "suggestions": score.suggestions,
            }
        
        # 调用AI生成个性化优化建议
        suggestions = await engine.generate_optimization_suggestions(result)
        
        return {
            "status": "success",
            "data": {
                "overall_score": result.overall_score,
                "ai_detection_score": result.ai_detection_score,
                "originality_score": result.originality_score,
                "quality_scores": scores_dict,
                "suggestions": suggestions,
            }
        }
    except Exception as e:
        log.print_log(f"内容分析失败: {str(e)}", "error")
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/compare")
async def compare_contents(request: CompareRequest):
    """对比原文和优化后的内容"""
    try:
        engine = ContentQualityEngine()
        comparison = engine.compare_contents(request.original, request.optimized)
        
        return {
            "status": "success",
            "data": comparison
        }
    except Exception as e:
        log.print_log(f"内容对比失败: {str(e)}", "error")
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/optimize-suggestions")
async def get_optimization_suggestions(request: AnalyzeRequest):
    """获取优化建议"""
    try:
        engine = ContentQualityEngine()
        result = engine.analyze_content(request.content)
        # 调用AI生成个性化优化建议
        suggestions = await engine.generate_optimization_suggestions(result)
        
        return {
            "status": "success",
            "data": {
                "suggestions": suggestions,
                "ai_detection_score": result.ai_detection_score,
                "originality_score": result.originality_score,
                "overall_score": result.overall_score,
            }
        }
    except Exception as e:
        log.print_log(f"获取优化建议失败: {str(e)}", "error")
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/auto-optimize")
async def auto_optimize_content(request: OptimizeRequest):
    """自动优化内容 (返回优化计划，实际优化由前端调用AI完成)"""
    try:
        engine = ContentQualityEngine()
        optimizer = AutoOptimizer(engine)
        
        # 初始分析
        initial_result = engine.analyze_content(request.content)
        
        # 检查是否需要优化
        needs_optimization = (
            initial_result.originality_score < request.target_originality or
            initial_result.ai_detection_score > request.max_ai_likelihood
        )
        
        if not needs_optimization:
            return {
                "status": "success",
                "data": {
                    "needs_optimization": False,
                    "message": "内容已达标，无需优化",
                    "current_scores": {
                        "overall": initial_result.overall_score,
                        "originality": initial_result.originality_score,
                        "ai_likelihood": initial_result.ai_detection_score,
                    },
                    "target_scores": {
                        "originality": request.target_originality,
                        "ai_likelihood": request.max_ai_likelihood,
                    }
                }
            }
        
        # 生成优化计划（调用AI生成个性化建议）
        suggestions = await engine.generate_optimization_suggestions(initial_result)
        
        return {
            "status": "success",
            "data": {
                "needs_optimization": True,
                "current_scores": {
                    "overall": initial_result.overall_score,
                    "originality": initial_result.originality_score,
                    "ai_likelihood": initial_result.ai_detection_score,
                    "readability": initial_result.quality_scores.get("readability", {}).score if "readability" in initial_result.quality_scores else 0,
                    "coherence": initial_result.quality_scores.get("coherence", {}).score if "coherence" in initial_result.quality_scores else 0,
                },
                "target_scores": {
                    "originality": request.target_originality,
                    "ai_likelihood": request.max_ai_likelihood,
                },
                "suggestions": suggestions,
                "max_iterations": request.max_iterations,
                "quality_scores_detail": {
                    metric: {
                        "score": score.score,
                        "details": score.details,
                    }
                    for metric, score in initial_result.quality_scores.items()
                }
            }
        }
    except Exception as e:
        log.print_log(f"自动优化失败: {str(e)}", "error")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/metrics")
async def get_quality_metrics():
    """获取质量指标说明"""
    from src.ai_write_x.core.quality_engine import QualityMetric
    
    metrics_info = {
        QualityMetric.ORIGINALITY.value: {
            "name": "原创性",
            "description": "评估内容的独特性和原创程度",
            "weight": 0.20,
            "target": ">= 75分",
        },
        QualityMetric.READABILITY.value: {
            "name": "可读性",
            "description": "评估内容的阅读体验和流畅度",
            "weight": 0.15,
            "target": ">= 70分",
        },
        QualityMetric.COHERENCE.value: {
            "name": "连贯性",
            "description": "评估内容的逻辑连贯和过渡自然程度",
            "weight": 0.15,
            "target": ">= 70分",
        },
        QualityMetric.VOCABULARY_RICHNESS.value: {
            "name": "词汇丰富度",
            "description": "评估内容使用的词汇多样性",
            "weight": 0.10,
            "target": ">= 65分",
        },
        QualityMetric.SENTENCE_VARIETY.value: {
            "name": "句式多样性",
            "description": "评估句子结构和长度的变化程度",
            "weight": 0.10,
            "target": ">= 65分",
        },
        QualityMetric.AI_LIKELIHOOD.value: {
            "name": "AI检测概率",
            "description": "评估内容被AI检测工具识别的概率",
            "weight": 0.20,
            "target": "<= 30分 (越低越好)",
        },
        QualityMetric.SEMANTIC_DEPTH.value: {
            "name": "语义深度",
            "description": "评估内容的观点深度和论证强度",
            "weight": 0.10,
            "target": ">= 70分",
        },
    }
    
    return {
        "status": "success",
        "data": metrics_info
    }


@router.post("/optimize-with-suggestions")
async def optimize_with_suggestions(request: OptimizeWithSuggestionsRequest):
    """基于选定建议优化内容 - Agent智能优化"""
    import traceback
    
    try:
        from src.ai_write_x.llm import LiteLLMClient
        
        log.print_log(f"[Quality] 开始基于建议优化，选中 {len(request.suggestions)} 个建议")
        log.print_log(f"[Quality] 原文长度: {len(request.content)} 字")
        
        # 构建优化提示词
        suggestions_text = "\n".join([f"{i+1}. {s}" for i, s in enumerate(request.suggestions)])
        
        prompt = f"""你是一位专业的内容编辑和写作专家。请根据以下优化建议对原文进行改进。

## 优化建议：
{suggestions_text}

## 原文：
{request.content}

## 优化要求：
1. 针对每条建议进行相应的改进
2. 保持文章的核心观点和主要信息不变
3. 确保语言流畅、自然
4. 直接输出优化后的完整文章，不要添加解释或说明

## 优化后的文章："""

        log.print_log(f"[Quality] 调用LLM进行优化...")
        
        # 调用LLM进行优化
        llm = LiteLLMClient()
        response = await llm.acomplete(
            prompt=prompt,
            temperature=0.7,
            max_tokens=4000
        )
        
        optimized_content = response.strip()
        log.print_log(f"[Quality] LLM返回内容长度: {len(optimized_content)} 字")
        
        # 如果返回的内容为空或太短，返回原文
        if len(optimized_content) < len(request.content) * 0.5:
            log.print_log("[Quality] 优化结果异常，使用原文", "warning")
            optimized_content = request.content
        
        log.print_log(f"[Quality] 优化完成，原文 {len(request.content)} 字 -> 优化后 {len(optimized_content)} 字")
        
        return {
            "status": "success",
            "data": {
                "optimized_content": optimized_content,
                "original_content": request.content,
                "changes": request.suggestions,
                "word_count": {
                    "original": len(request.content),
                    "optimized": len(optimized_content)
                }
            }
        }
    except Exception as e:
        error_msg = f"基于建议优化失败: {str(e)}"
        log.print_log(error_msg, "error")
        log.print_log(traceback.format_exc(), "error")
        raise HTTPException(status_code=500, detail=error_msg)


class TitleOptimizeRequest(BaseModel):
    """标题优化请求"""
    title: str
    content: str
    platform: str = ""  # 目标平台：微信公众号、今日头条、知乎等


@router.post("/optimize-title")
async def optimize_title(request: TitleOptimizeRequest):
    """使用AI优化文章标题"""
    try:
        from src.ai_write_x.core.quality_engine import TitleOptimizer
        
        log.print_log(f"[TitleOptimizer] 开始优化标题: {request.title[:30]}...")
        
        result = await TitleOptimizer.optimize_title(
            title=request.title,
            content=request.content,
            platform=request.platform
        )
        
        log.print_log(f"[TitleOptimizer] 生成 {len(result.get('optimized_titles', []))} 个备选标题")
        
        return {
            "status": "success",
            "data": result
        }
    except Exception as e:
        error_msg = f"标题优化失败: {str(e)}"
        log.print_log(error_msg, "error")
        log.print_log(traceback.format_exc(), "error")
        raise HTTPException(status_code=500, detail=error_msg)
