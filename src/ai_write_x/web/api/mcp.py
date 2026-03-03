#!/usr/bin/env python
# -*- coding: UTF-8 -*-
"""
MCP服务管理API
提供MCP服务的添加、删除、启动、停止、状态查询等接口
"""

from typing import Dict, Any, List, Optional
from fastapi import APIRouter, HTTPException
from pydantic import BaseModel

from src.ai_write_x.utils import log
from src.ai_write_x.tools.mcp_manager import MCPManager, MCPServiceStatus


router = APIRouter(prefix="/api/mcp", tags=["mcp"])


# 请求模型
class MCPServerConfig(BaseModel):
    """MCP服务配置请求"""
    name: str
    command: str
    args: List[str] = []
    env: Dict[str, str] = {}
    enabled: bool = True
    auto_start: bool = False
    description: str = ""
    tools: List[str] = []


class MCPServiceUpdate(BaseModel):
    """MCP服务更新请求"""
    args: Optional[List[str]] = None
    env: Optional[Dict[str, str]] = None
    enabled: Optional[bool] = None
    auto_start: Optional[bool] = None
    description: Optional[str] = None
    tools: Optional[List[str]] = None


# API端点
@router.get("/")
async def get_all_services():
    """获取所有MCP服务列表"""
    try:
        manager = MCPManager.get_instance()
        services = manager.get_all_services()
        summary = manager.get_status_summary()
        
        return {
            "status": "success",
            "data": {
                "services": services,
                "summary": summary
            }
        }
    except Exception as e:
        log.print_log(f"获取MCP服务列表失败: {str(e)}", "error")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/summary")
async def get_status_summary():
    """获取MCP服务状态摘要"""
    try:
        manager = MCPManager.get_instance()
        summary = manager.get_status_summary()
        
        return {
            "status": "success",
            "data": summary
        }
    except Exception as e:
        log.print_log(f"获取MCP状态摘要失败: {str(e)}", "error")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/tools")
async def get_available_tools():
    """获取所有可用的MCP工具"""
    try:
        manager = MCPManager.get_instance()
        tools = manager.get_available_tools()
        
        return {
            "status": "success",
            "data": tools
        }
    except Exception as e:
        log.print_log(f"获取MCP工具列表失败: {str(e)}", "error")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/dependencies")
async def check_dependencies():
    """检查MCP服务依赖"""
    try:
        manager = MCPManager.get_instance()
        deps = manager.check_dependencies()
        
        return {
            "status": "success",
            "data": deps
        }
    except Exception as e:
        log.print_log(f"检查MCP依赖失败: {str(e)}", "error")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/{service_name}")
async def get_service(service_name: str):
    """获取单个MCP服务详情"""
    try:
        manager = MCPManager.get_instance()
        service = manager.get_service(service_name)
        
        if service is None:
            raise HTTPException(status_code=404, detail=f"服务 {service_name} 不存在")
        
        return {
            "status": "success",
            "data": service
        }
    except HTTPException:
        raise
    except Exception as e:
        log.print_log(f"获取MCP服务详情失败: {str(e)}", "error")
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/")
async def add_service(config: MCPServerConfig):
    """添加新的MCP服务"""
    try:
        manager = MCPManager.get_instance()
        
        success = manager.add_service(config.dict())
        
        if success:
            return {
                "status": "success",
                "message": f"服务 {config.name} 添加成功"
            }
        else:
            raise HTTPException(status_code=400, detail="添加服务失败")
            
    except HTTPException:
        raise
    except Exception as e:
        log.print_log(f"添加MCP服务失败: {str(e)}", "error")
        raise HTTPException(status_code=500, detail=str(e))


@router.patch("/{service_name}")
async def update_service(service_name: str, update: MCPServiceUpdate):
    """更新MCP服务配置"""
    try:
        manager = MCPManager.get_instance()
        
        # 过滤掉None值
        update_data = {k: v for k, v in update.dict().items() if v is not None}
        
        success = manager.update_service(service_name, update_data)
        
        if success:
            return {
                "status": "success",
                "message": f"服务 {service_name} 更新成功"
            }
        else:
            raise HTTPException(status_code=404, detail=f"服务 {service_name} 不存在")
            
    except HTTPException:
        raise
    except Exception as e:
        log.print_log(f"更新MCP服务失败: {str(e)}", "error")
        raise HTTPException(status_code=500, detail=str(e))


@router.delete("/{service_name}")
async def remove_service(service_name: str):
    """删除MCP服务"""
    try:
        manager = MCPManager.get_instance()
        
        success = manager.remove_service(service_name)
        
        if success:
            return {
                "status": "success",
                "message": f"服务 {service_name} 已删除"
            }
        else:
            raise HTTPException(status_code=404, detail=f"服务 {service_name} 不存在")
            
    except HTTPException:
        raise
    except Exception as e:
        log.print_log(f"删除MCP服务失败: {str(e)}", "error")
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/{service_name}/enable")
async def enable_service(service_name: str):
    """启用MCP服务"""
    try:
        manager = MCPManager.get_instance()
        
        success = manager.enable_service(service_name)
        
        if success:
            return {
                "status": "success",
                "message": f"服务 {service_name} 已启用"
            }
        else:
            raise HTTPException(status_code=404, detail=f"服务 {service_name} 不存在")
            
    except HTTPException:
        raise
    except Exception as e:
        log.print_log(f"启用MCP服务失败: {str(e)}", "error")
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/{service_name}/disable")
async def disable_service(service_name: str):
    """禁用MCP服务"""
    try:
        manager = MCPManager.get_instance()
        
        success = manager.disable_service(service_name)
        
        if success:
            return {
                "status": "success",
                "message": f"服务 {service_name} 已禁用"
            }
        else:
            raise HTTPException(status_code=404, detail=f"服务 {service_name} 不存在")
            
    except HTTPException:
        raise
    except Exception as e:
        log.print_log(f"禁用MCP服务失败: {str(e)}", "error")
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/{service_name}/start")
async def start_service(service_name: str):
    """启动MCP服务"""
    try:
        manager = MCPManager.get_instance()
        
        success = manager.start_service(service_name)
        
        if success:
            return {
                "status": "success",
                "message": f"服务 {service_name} 启动成功"
            }
        else:
            service = manager.get_service(service_name)
            error_msg = service.get("error_message", "启动失败") if service else "启动失败"
            raise HTTPException(status_code=400, detail=error_msg)
            
    except HTTPException:
        raise
    except Exception as e:
        log.print_log(f"启动MCP服务失败: {str(e)}", "error")
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/{service_name}/stop")
async def stop_service(service_name: str):
    """停止MCP服务"""
    try:
        manager = MCPManager.get_instance()
        
        success = manager.stop_service(service_name)
        
        if success:
            return {
                "status": "success",
                "message": f"服务 {service_name} 已停止"
            }
        else:
            raise HTTPException(status_code=404, detail=f"服务 {service_name} 不存在")
            
    except HTTPException:
        raise
    except Exception as e:
        log.print_log(f"停止MCP服务失败: {str(e)}", "error")
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/{service_name}/restart")
async def restart_service(service_name: str):
    """重启MCP服务"""
    try:
        manager = MCPManager.get_instance()
        
        success = manager.restart_service(service_name)
        
        if success:
            return {
                "status": "success",
                "message": f"服务 {service_name} 重启成功"
            }
        else:
            service = manager.get_service(service_name)
            error_msg = service.get("error_message", "重启失败") if service else "重启失败"
            raise HTTPException(status_code=400, detail=error_msg)
            
    except HTTPException:
        raise
    except Exception as e:
        log.print_log(f"重启MCP服务失败: {str(e)}", "error")
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/start-all")
async def start_all_enabled():
    """启动所有已启用且自动启动的服务"""
    try:
        manager = MCPManager.get_instance()
        results = manager.start_all_enabled()
        
        success_count = sum(1 for v in results.values() if v)
        failed_count = len(results) - success_count
        
        return {
            "status": "success",
            "message": f"已启动 {success_count} 个服务，失败 {failed_count} 个",
            "data": results
        }
    except Exception as e:
        log.print_log(f"启动所有MCP服务失败: {str(e)}", "error")
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/stop-all")
async def stop_all():
    """停止所有运行中的服务"""
    try:
        manager = MCPManager.get_instance()
        results = manager.stop_all()
        
        return {
            "status": "success",
            "message": f"已停止 {len(results)} 个服务",
            "data": results
        }
    except Exception as e:
        log.print_log(f"停止所有MCP服务失败: {str(e)}", "error")
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/install-dependency/{dep_name}")
async def install_dependency(dep_name: str):
    """
    安装MCP依赖
    
    Args:
        dep_name: 依赖名称 (npx/nodejs 或 uvx/uv)
    """
    try:
        manager = MCPManager.get_instance()
        result = manager.install_dependency(dep_name)
        
        return {
            "status": "success" if result.get("success") else "info",
            "data": result
        }
    except Exception as e:
        log.print_log(f"安装MCP依赖失败: {str(e)}", "error")
        raise HTTPException(status_code=500, detail=str(e))
