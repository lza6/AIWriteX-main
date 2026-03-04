# -*- coding: utf-8 -*-
"""
MCP工具适配器
将MCP服务提供的工具适配为CrewAI可用的工具
"""

import json
import asyncio
from typing import Dict, Any, Optional, List, Type
from pydantic import BaseModel, Field

from crewai.tools import BaseTool
from src.ai_write_x.utils import log
from src.ai_write_x.tools.mcp_manager import MCPManager, MCPServiceStatus


class MCPToolInput(BaseModel):
    """MCP工具通用输入"""
    query: str = Field(..., description="查询内容或URL")


class MCPFetchToolInput(BaseModel):
    """Fetch工具输入参数"""
    url: str = Field(..., description="要抓取的URL")
    max_length: int = Field(default=5000, description="返回的最大字符数")
    start_index: int = Field(default=0, description="从该字符索引开始提取内容")
    raw: bool = Field(default=False, description="获取未经markdown转换的原始内容")


class MCPWebFetchTool(BaseTool):
    """
    MCP网页抓取工具
    通过mcp-server-fetch服务抓取网页内容并转换为Markdown
    """
    
    name: str = "mcp_web_fetch"
    description: str = (
        "从互联网抓取URL并将其内容提取为Markdown格式。"
        "适用于获取网页的纯文本内容，支持分块读取长网页。"
    )
    args_schema: Type[BaseModel] = MCPFetchToolInput
    
    def _run(self, url: str, max_length: int = 5000, start_index: int = 0, raw: bool = False) -> str:
        """执行网页抓取"""
        manager = MCPManager.get_instance()
        
        # 检查fetch服务状态
        service = manager.services.get("fetch")
        if not service or service.status != MCPServiceStatus.RUNNING:
            # 尝试启动服务
            if service and service.config.enabled:
                log.print_log("正在启动MCP Fetch服务...")
                manager.start_service("fetch")
            else:
                return "错误: MCP Fetch服务未启用或不可用"
        
        try:
            # 使用requests直接抓取（简化版本，实际MCP需要JSON-RPC通信）
            import requests
            from bs4 import BeautifulSoup
            
            headers = {
                "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36"
            }
            
            response = requests.get(url, headers=headers, timeout=30)
            response.raise_for_status()
            
            # 解析HTML
            soup = BeautifulSoup(response.text, 'html.parser')
            
            # 移除脚本和样式
            for script in soup(["script", "style", "nav", "footer", "header"]):
                script.decompose()
            
            # 获取文本
            text = soup.get_text(separator='\n', strip=True)
            
            # 清理多余空行
            lines = [line.strip() for line in text.splitlines() if line.strip()]
            content = '\n'.join(lines)
            
            # 截取内容
            if start_index > 0:
                content = content[start_index:]
            if len(content) > max_length:
                content = content[:max_length] + "\n... [内容已截断]"
            
            log.print_log(f"成功抓取网页内容: {url}")
            return f"URL: {url}\n\n{content}"
            
        except requests.exceptions.RequestException as e:
            return f"抓取失败: {str(e)}"
        except Exception as e:
            log.print_traceback("MCP网页抓取错误", e)
            return f"处理失败: {str(e)}"


class MCPMemoryToolInput(BaseModel):
    """Memory工具输入参数"""
    action: str = Field(..., description="操作类型: create_entities, create_relations, search_nodes, read_graph")
    data: Dict[str, Any] = Field(default={}, description="操作数据")


class MCPMemoryTool(BaseTool):
    """
    MCP知识图谱内存工具
    通过memory服务存储和检索知识
    """
    
    name: str = "mcp_memory"
    description: str = (
        "知识图谱内存工具，支持存储实体、关系和观察。"
        "操作类型: create_entities(创建实体), create_relations(创建关系), "
        "search_nodes(搜索节点), read_graph(读取整个图谱)"
    )
    args_schema: Type[BaseModel] = MCPMemoryToolInput
    
    # 内存存储（简化版本，实际应该通过MCP服务）
    _memory_store: Dict[str, Any] = {"entities": {}, "relations": []}
    
    def _run(self, action: str, data: Dict[str, Any] = None) -> str:
        """执行内存操作"""
        data = data or {}
        
        if action == "create_entities":
            return self._create_entities(data.get("entities", []))
        elif action == "create_relations":
            return self._create_relations(data.get("relations", []))
        elif action == "search_nodes":
            return self._search_nodes(data.get("query", ""))
        elif action == "read_graph":
            return self._read_graph()
        else:
            return f"未知操作: {action}"
    
    def _create_entities(self, entities: List[Dict]) -> str:
        """创建实体"""
        created = []
        for entity in entities:
            name = entity.get("name")
            if name:
                self._memory_store["entities"][name] = {
                    "entityType": entity.get("entityType", "unknown"),
                    "observations": entity.get("observations", [])
                }
                created.append(name)
        return f"已创建实体: {', '.join(created)}"
    
    def _create_relations(self, relations: List[Dict]) -> str:
        """创建关系"""
        for rel in relations:
            self._memory_store["relations"].append(rel)
        return f"已创建 {len(relations)} 个关系"
    
    def _search_nodes(self, query: str) -> str:
        """搜索节点"""
        results = []
        query_lower = query.lower()
        
        for name, entity in self._memory_store["entities"].items():
            if query_lower in name.lower():
                results.append({"name": name, **entity})
            else:
                for obs in entity.get("observations", []):
                    if query_lower in obs.lower():
                        results.append({"name": name, **entity})
                        break
        
        if results:
            return json.dumps(results, ensure_ascii=False, indent=2)
        return f"未找到匹配 '{query}' 的节点"
    
    def _read_graph(self) -> str:
        """读取整个图谱"""
        return json.dumps(self._memory_store, ensure_ascii=False, indent=2)


class MCPBrowserToolInput(BaseModel):
    """浏览器工具输入参数"""
    action: str = Field(..., description="操作类型: navigate, snapshot, screenshot, click, type")
    data: Dict[str, Any] = Field(default={}, description="操作数据")


class MCPBrowserTool(BaseTool):
    """
    MCP浏览器自动化工具
    通过Playwright服务进行网页自动化
    """
    
    name: str = "mcp_browser"
    description: str = (
        "浏览器自动化工具，支持网页导航、截图、点击、输入等操作。"
        "操作类型: navigate(导航), snapshot(快照), screenshot(截图), "
        "click(点击), type(输入)"
    )
    args_schema: Type[BaseModel] = MCPBrowserToolInput
    
    def _run(self, action: str, data: Dict[str, Any] = None) -> str:
        """执行浏览器操作"""
        data = data or {}
        
        # 检查Playwright服务
        manager = MCPManager.get_instance()
        service = manager.services.get("playwright")
        
        if not service or service.status != MCPServiceStatus.RUNNING:
            if service and service.config.enabled:
                log.print_log("正在启动MCP Playwright服务...")
                manager.start_service("playwright")
            else:
                return "错误: MCP Playwright服务未启用或不可用"
        
        # 这里是简化版本，实际需要通过MCP协议与Playwright服务通信
        if action == "navigate":
            url = data.get("url", "")
            return f"已导航到: {url} (模拟操作)"
        elif action == "snapshot":
            return "页面快照已获取 (模拟操作)"
        elif action == "screenshot":
            return "截图已保存 (模拟操作)"
        else:
            return f"浏览器操作 '{action}' 已执行 (模拟操作)"


def get_mcp_tools() -> List[BaseTool]:
    """获取所有可用的MCP工具"""
    tools = []
    
    manager = MCPManager.get_instance()
    
    # 检查哪些服务已启用并运行
    for name, instance in manager.services.items():
        if instance.config.enabled:
            if name == "fetch":
                tools.append(MCPWebFetchTool())
            elif name == "memory":
                tools.append(MCPMemoryTool())
            elif name == "playwright":
                tools.append(MCPBrowserTool())
    
    return tools


def is_mcp_tool_available(tool_name: str) -> bool:
    """检查指定的MCP工具是否可用"""
    manager = MCPManager.get_instance()
    
    tool_service_map = {
        "mcp_web_fetch": "fetch",
        "mcp_memory": "memory",
        "mcp_browser": "playwright",
    }
    
    service_name = tool_service_map.get(tool_name)
    if not service_name:
        return False
    
    service = manager.services.get(service_name)
    return service is not None and service.config.enabled
