# -*- coding: utf-8 -*-
"""
动态模板工具
用于 CrewAI 工具调用
"""

from crewai.tools import BaseTool
from pydantic import BaseModel, Field, PrivateAttr
from typing import Type, Optional
import asyncio

from src.ai_write_x.core.dynamic_template_generator import (
    DynamicTemplateGenerator,
    generate_dynamic_template
)
from src.ai_write_x.core.adaptive_template_engine import (
    AdaptiveTemplateEngine,
    generate_adaptive_template
)
from src.ai_write_x.core.ai_template_designer import AITemplateDesigner
from src.ai_write_x.utils import log


class DynamicTemplateInput(BaseModel):
    """动态模板生成输入"""
    title: str = Field(..., description="文章标题")
    content: str = Field(..., description="文章内容")
    topic: str = Field(default="", description="文章主题分类")
    use_ai_designer: bool = Field(default=True, description="是否使用AI设计师生成独特模板（默认是）")
    use_adaptive_engine: bool = Field(default=True, description="是否使用自适应模板引擎（推荐，模块化组件化设计）")


class DynamicTemplateTool(BaseTool):
    """
    动态模板生成工具
    根据文章内容自动生成独特的HTML模板
    
    特点：
    - 每次生成不同风格的模板（8种设计方向随机选择）
    - AI根据内容特点定制CSS样式
    - 支持重点词高亮、人物突出显示
    - 玻璃拟态、新粗野主义、有机现代等多种风格
    """
    name: str = "dynamic_template_tool"
    description: str = """根据文章主题、情感和结构自动生成独特的HTML模板。
    
    这个工具会：
    1. 随机选择设计风格（极简、玻璃拟态、新粗野主义、有机现代等8种）
    2. AI根据内容生成定制化CSS样式
    3. 优化重点词、人物名、时间的显示效果
    4. 生成与内容完美匹配的HTML模板
    
    每次调用都会生成不同风格的模板，避免审美疲劳！
    
    输入参数：
    - title: 文章标题
    - content: 文章内容
    - topic: 主题分类（可选）
    - use_ai_designer: 是否使用AI深度设计（默认是，推荐）
    """
    args_schema: Type[BaseModel] = DynamicTemplateInput
    
    # 使用 PrivateAttr 来定义非 Pydantic 模型字段
    _generator: DynamicTemplateGenerator = PrivateAttr(default=None)
    _ai_designer: Optional[AITemplateDesigner] = PrivateAttr(default=None)
    
    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        self._generator = DynamicTemplateGenerator()
        self._ai_designer = None
    
    def _run(self, title: str, content: str, topic: str = "", 
             use_ai_designer: bool = True, use_adaptive_engine: bool = True) -> str:
        """
        生成动态模板（同步入口）
        """
        try:
            log.print_log(f"[DynamicTemplate] 开始生成模板: {title[:30]}...")
            
            # 优先使用自适应引擎（模块化组件化设计）
            if use_adaptive_engine:
                log.print_log(f"[DynamicTemplate] 使用自适应模板引擎")
                try:
                    engine = AdaptiveTemplateEngine()
                    # 使用asyncio运行异步的 engine.generate
                    loop = asyncio.new_event_loop()
                    asyncio.set_event_loop(loop)
                    try:
                        template = loop.run_until_complete(
                            engine.generate(title, content, topic)
                        )
                    finally:
                        loop.close()
                    
                    # 将内容填充到模板
                    analysis = self._generator.analyze_content(title, content, topic)
                    formatted_content = self._generator._format_content_for_template(
                        content, analysis
                    )
                    final_html = template.replace("{content}", formatted_content)
                    final_html = final_html.replace("{{content}}", formatted_content)
                    
                    log.print_log(f"[DynamicTemplate] 自适应模板生成成功")
                    return final_html
                except Exception as ae:
                    log.print_log(f"[DynamicTemplate] 自适应引擎失败: {ae}", "warning")
                    # 回退到AI设计师
                    return self._generate_with_ai_designer(title, content, topic)
            
            elif use_ai_designer:
                # 使用AI设计师（每次生成独特风格）
                return self._generate_with_ai_designer(title, content, topic)
            else:
                # 使用快速生成器（固定风格）
                template = self._generator.generate_template_with_content(
                    title=title,
                    content=content,
                    topic=topic
                )
                log.print_log(f"[DynamicTemplate] 模板生成成功（快速模式）")
                return template
                
        except Exception as e:
            log.print_log(f"[DynamicTemplate] 模板生成失败: {e}", "error")
            # 返回备用模板
            return self._get_fallback_template(title, topic)
    
    def _generate_with_ai_designer(self, title: str, content: str, topic: str) -> str:
        """使用AI设计师生成独特模板"""
        try:
            # 初始化AI设计师
            if self._ai_designer is None:
                self._ai_designer = AITemplateDesigner()
            
            # 提取关键词
            analysis = self._generator.analyze_content(title, content, topic)
            
            # 使用asyncio运行异步方法
            loop = asyncio.new_event_loop()
            asyncio.set_event_loop(loop)
            try:
                template_html = loop.run_until_complete(
                    self._ai_designer.generate_unique_template(
                        title=title,
                        content=content,
                        topic=topic,
                        keywords=analysis.keywords
                    )
                )
            finally:
                loop.close()
            
            # 将内容填充到模板（使用正确的占位符）
            formatted_content = self._generator._format_content_for_template(
                content, analysis
            )
            
            # 支持两种占位符格式
            final_html = template_html.replace("{{content}}", formatted_content)
            final_html = final_html.replace("{content}", formatted_content)
            
            log.print_log(f"[DynamicTemplate] AI模板生成成功")
            return final_html
            
        except Exception as e:
            log.print_log(f"[DynamicTemplate] AI设计失败，回退到快速生成: {e}", "warning")
            return self._generator.generate_template_with_content(title, content, topic)
    
    def _get_fallback_template(self, title: str, topic: str) -> str:
        """备用模板"""
        return f"""<!DOCTYPE html>
<html lang="zh-CN">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>{title}</title>
</head>
<body style="margin: 0; padding: 0; font-family: system-ui, -apple-system, sans-serif; background: #f8fafc;">
    <header style="background: linear-gradient(135deg, #667eea 0%, #764ba2 100%); color: white; padding: 40px 20px; text-align: center;">
        <h1 style="margin: 0; font-size: 28px;">{title}</h1>
        <p style="margin: 10px 0 0; opacity: 0.9;">{topic}</p>
    </header>
    <main style="max-width: 800px; margin: 0 auto; padding: 30px 20px;">
        <article style="background: white; padding: 30px; border-radius: 12px; box-shadow: 0 2px 10px rgba(0,0,0,0.1); line-height: 1.8; color: #333;">
            {{{{content}}}}
        </article>
    </main>
</body>
</html>"""
    
    async def _arun(self, title: str, content: str, topic: str = "",
                    use_ai_designer: bool = False) -> str:
        """异步入口"""
        return self._run(title, content, topic, use_ai_designer)


# 便捷函数
def generate_template(title: str, content: str, topic: str = "",
                     use_ai: bool = False) -> str:
    """
    便捷函数：生成动态模板
    
    Args:
        title: 文章标题
        content: 文章内容
        topic: 主题分类
        use_ai: 是否使用AI深度设计
        
    Returns:
        HTML模板字符串
    """
    tool = DynamicTemplateTool()
    return tool._run(title, content, topic, use_ai)
