from src.ai_write_x.core.tool_registry import GlobalToolRegistry
from src.ai_write_x.tools.custom_tool import ReadTemplateTool
from src.ai_write_x.tools.dynamic_template_tool import DynamicTemplateTool
from src.ai_write_x.news_aggregator.mcp_tools import NEWSHUB_TOOLS
from src.ai_write_x.core.unified_workflow import UnifiedContentWorkflow

from src.ai_write_x.core.platform_adapters import (
    WeChatAdapter,
    XiaohongshuAdapter,
    DouyinAdapter,
    ZhihuAdapter,
    ToutiaoAdapter,
    BaijiahaoAdapter,
    DoubanAdapter,
)
from src.ai_write_x.core.platform_adapters import PlatformType


def initialize_global_tools():
    """初始化全局工具注册表"""
    registry = GlobalToolRegistry.get_instance()

    # 注册所有可用工具
    registry.register_tool("ReadTemplateTool", ReadTemplateTool)
    registry.register_tool("DynamicTemplateTool", DynamicTemplateTool)
    
    # 注册NewsHub MCP工具
    for tool in NEWSHUB_TOOLS:
        registry.register_tool(tool.name, tool)

    return registry


def get_platform_adapter(platform_name: str):
    """获取指定平台的适配器"""

    # 创建临时工作流实例来获取适配器
    workflow = UnifiedContentWorkflow()
    return workflow.platform_adapters.get(platform_name)


# 在应用启动时调用
def setup_aiwritex():
    """完整的系统初始化"""
    # 1. 初始化工具注册表
    initialize_global_tools()

    # 2. 创建统一工作流
    workflow = UnifiedContentWorkflow()

    # 3. 注册所有平台适配器
    workflow.register_platform_adapter(PlatformType.WECHAT.value, WeChatAdapter())
    workflow.register_platform_adapter(PlatformType.XIAOHONGSHU.value, XiaohongshuAdapter())
    workflow.register_platform_adapter(PlatformType.DOUYIN.value, DouyinAdapter())
    workflow.register_platform_adapter(PlatformType.ZHIHU.value, ZhihuAdapter())
    workflow.register_platform_adapter(PlatformType.TOUTIAO.value, ToutiaoAdapter())
    workflow.register_platform_adapter(PlatformType.BAIJIAHAO.value, BaijiahaoAdapter())
    workflow.register_platform_adapter(PlatformType.DOUBAN.value, DoubanAdapter())

    return workflow
