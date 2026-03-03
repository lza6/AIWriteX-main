# -*- coding: utf-8 -*-
"""
模板设计师 Agent
根据内容特征生成自适应的HTML模板
"""

from typing import Dict, Any, Optional
from src.ai_write_x.core.base_framework import AgentConfig
from crewai import Agent
from src.ai_write_x.utils import log


class TemplateDesignerAgent(Agent):
    """
    模板设计师 Agent
    负责根据文章内容生成独特的视觉模板
    """
    
    def __init__(self, config: Optional[AgentConfig] = None):
        super().__init__(config)
        self.agent_role = "template_designer"
        self.system_prompt = self._get_system_prompt()
    
    def _get_system_prompt(self) -> str:
        """获取系统提示词"""
        return """你是一位专业的视觉设计师和前端开发专家。
你的任务是根据文章的主题、情感和结构，设计并生成独特的HTML模板。

设计原则：
1. 主题适配 - 模板风格必须贴合文章主题（科技、生活、商业、艺术等）
2. 情感共鸣 - 通过配色和排版传达文章的情感基调
3. 结构优化 - 根据内容结构选择合适的布局方式
4. 视觉层次 - 使用字体大小、颜色、间距创造清晰的视觉层次
5. 现代美学 - 运用渐变、阴影、圆角等现代设计元素

技术要求：
- 使用内联CSS样式（style属性）
- 确保响应式设计（适配移动端）
- 使用Google Fonts字体
- 添加适当的SVG装饰元素
- 保持代码简洁高效

输出要求：
- 只输出完整的HTML代码
- 不要包含任何解释文字
- 使用占位符 {{content}} 标记内容插入位置
"""
    
    def get_task_prompt(self, title: str, content: str, topic: str = "", 
                       emotions: list = None, keywords: list = None) -> str:
        """生成任务提示词"""
        emotions_str = ", ".join(emotions) if emotions else "待分析"
        keywords_str = ", ".join(keywords[:8]) if keywords else "待提取"
        
        # 分析内容特征
        content_length = len(content)
        has_sections = "##" in content or "第" in content[:100]
        has_lists = "- " in content or "1." in content
        has_quotes = '"' in content
        
        return f"""请为以下文章设计一个独特的HTML模板：

【文章标题】
{title}

【主题分类】
{topic or "自动识别"}

【情感基调】
{emotions_str}

【关键词】
{keywords_str}

【内容特征】
- 字数：约{content_length}字
- 包含章节：{'是' if has_sections else '否'}
- 包含列表：{'是' if has_lists else '否'}
- 包含引用：{'是' if has_quotes else '否'}

【内容预览】
{content[:500]}...

【设计要求】
1. 根据主题选择配色方案（科技-蓝/紫、生活-橙/粉、商业-蓝/灰、自然-绿）
2. 设计吸引人的头部区域，包含标题和主题标签
3. 内容区域需要良好的阅读体验（适当的行高、段落间距）
4. 添加与主题相关的SVG装饰元素
5. 设计简洁的页脚
6. 使用 {{content}} 作为内容占位符

请生成完整的HTML代码（包含DOCTYPE、html、head、body），使用内联样式。
"""
    
    async def design_template(self, title: str, content: str, topic: str = "",
                             emotions: list = None, keywords: list = None) -> str:
        """
        设计模板
        
        Args:
            title: 文章标题
            content: 文章内容
            topic: 主题分类
            emotions: 情感列表
            keywords: 关键词列表
            
        Returns:
            HTML模板字符串
        """
        task_prompt = self.get_task_prompt(title, content, topic, emotions, keywords)
        
        try:
            # 调用LLM生成模板
            response = await self.llm.acomplete(
                system_prompt=self.system_prompt,
                prompt=task_prompt,
                max_tokens=4096,
                temperature=0.7
            )
            
            html_template = response.text if hasattr(response, 'text') else str(response)
            
            # 清理输出
            html_template = self._clean_template(html_template)
            
            log.print_log(f"[TemplateDesigner] 模板生成成功，长度: {len(html_template)}")
            
            return html_template
            
        except Exception as e:
            log.print_log(f"[TemplateDesigner] 模板生成失败: {e}", "error")
            # 返回一个默认模板
            return self._get_default_template(title, topic)
    
    def _clean_template(self, template: str) -> str:
        """清理模板代码"""
        # 移除markdown代码块标记
        if "```html" in template:
            template = template.split("```html")[1].split("```")[0]
        elif "```" in template:
            template = template.split("```")[1].split("```")[0]
        
        # 确保包含基本结构
        if "<!DOCTYPE" not in template and "<html" not in template:
            template = f"""<!DOCTYPE html>
<html lang="zh-CN">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>Article</title>
</head>
<body style="margin: 0; padding: 0; font-family: system-ui, -apple-system, sans-serif;">
    {template}
</body>
</html>"""
        
        return template.strip()
    
    def _get_default_template(self, title: str, topic: str) -> str:
        """获取默认模板（备用）"""
        return f"""<!DOCTYPE html>
<html lang="zh-CN">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>{title}</title>
    <link href="https://fonts.googleapis.com/css2?family=Noto+Sans+SC:wght@400;500;700&display=swap" rel="stylesheet">
</head>
<body style="margin: 0; padding: 0; font-family: 'Noto Sans SC', sans-serif; background: #f8fafc; color: #1e293b; line-height: 1.7;">
    <header style="background: linear-gradient(135deg, #667eea 0%, #764ba2 100%); color: white; padding: 48px 24px; text-align: center;">
        <div style="font-size: 14px; opacity: 0.9; margin-bottom: 12px; text-transform: uppercase; letter-spacing: 2px;">{topic or '文章'}</div>
        <h1 style="font-size: 32px; font-weight: 700; margin: 0; line-height: 1.3;">{title}</h1>
    </header>
    <main style="max-width: 800px; margin: 0 auto; padding: 32px 24px;">
        <div style="background: white; padding: 32px; border-radius: 16px; box-shadow: 0 4px 20px rgba(0,0,0,0.08);">
            {{{{content}}}}
        </div>
    </main>
    <footer style="text-align: center; padding: 32px; color: #64748b; font-size: 14px;">
        由 AIWriteX 智能生成
    </footer>
</body>
</html>"""


# 便捷函数
async def generate_template_by_ai(title: str, content: str, topic: str = "",
                                  emotions: list = None, keywords: list = None) -> str:
    """便捷函数：使用AI生成模板"""
    agent = TemplateDesignerAgent()
    return await agent.design_template(title, content, topic, emotions, keywords)
