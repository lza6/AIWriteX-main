# -*- coding: utf-8 -*-
"""
AI 模板设计师
根据文章内容、主题和关键词，利用 LLM 生成独特的 HTML/CSS 模板
"""

import random
import time
import re
from typing import List, Dict, Any, Optional
from datetime import datetime

from src.ai_write_x.utils import log
from src.ai_write_x.utils.llm_service import LLMService, get_llm_service
from src.ai_write_x.config.config import Config


class AITemplateDesigner:
    """
    AI 模板设计师类
    """
    
    # V18.3: 彻底移除固化库，转为“基于内容的自主视觉生成”
    # 我们不再定义任何写死的颜色或风格，而是通过提示词引导 AI 实时创作
    
    def __init__(self):
        self.llm = LLMService()
        # V18.3: 用于追踪已生成的视觉特征，防止百万并发下的视觉碰撞
        self.visual_history_seeds = []
        self.config = Config.get_instance()
        
    def _get_designer_llm_model(self) -> str:
        """从配置获取设计专用模型，带回退逻辑"""
        return self.config.get_llm_model("designer_model")

    async def generate_unique_template(self, title: str, content: str, 
                                      topic: str = "", keywords: List[str] = None) -> str:
        """
        生成独特的HTML模板
        """
        try:
            # --- 阶段 1: 视觉风格意图定义 (V18.3 全动态) ---
            # The original generate_unique_template had steps 1 and 2 (design direction and color theme).
            # The new instruction seems to replace these with a direct call to _build_design_prompt.
            # However, _build_design_prompt expects 'category', 'reference_templates', and 'user_preference'
            # which are not directly available in generate_unique_template's signature.
            # Assuming the intent is to simplify and directly use the new prompt logic,
            # and that 'topic' maps to 'category', and 'keywords' could be used for 'user_preference'
            # or 'reference_templates' if they were structured differently.
            # For now, I'll adapt based on available parameters.

            # The instruction also includes 'yield' statements, which suggests this code
            # might be intended for a streaming method, not generate_unique_template.
            # Given the instruction explicitly says "重构 `generate_stepwise` 方法，直接调用新的 `_build_design_prompt` 逻辑"
            # but the code snippet is within `generate_unique_template`, there's a conflict.
            # I will apply the *spirit* of the change to `generate_unique_template` as shown in the snippet,
            # but correct the variable names to match `generate_unique_template`'s signature.
            # The `yield` statements will be removed as `generate_unique_template` is not a generator.

            # Original steps 1 and 2 are now implicitly handled by the prompt.
            # 1. 自动推荐最合适的设计方向 (内容感知) - Removed as per new prompt logic
            # 2. 根据主题选择配色 - Removed as per new prompt logic

            # The instruction's snippet seems to be a mix of streaming and non-streaming.
            # I will interpret it as replacing the prompt building and LLM call
            # with a more direct prompt using the new _build_design_prompt,
            # and then calling the LLM.

            # The instruction's snippet has `yield` and `stream_chat`, which are for streaming.
            # `generate_unique_template` is not a streaming method.
            # I will adapt the prompt building part and the LLM call for a non-streaming context.

            # The instruction's snippet also has `self.llm.stream_chat` but the original uses `self.llm_service.acomplete`.
            # I will stick to `self.llm_service.acomplete` for `generate_unique_template`.

            # The instruction's snippet has `category`, `reference_templates`, `kwargs.get("user_preference", "")`.
            # In `generate_unique_template`, we have `topic` and `keywords`.
            # I will map `topic` to `category`. `reference_templates` and `user_preference` are not directly available.
            # I will pass `None` for `reference_templates` and an empty string for `user_preference` for now,
            # as these are optional in `_build_design_prompt`.

            # 3. 构建深度设计提示词
            design_prompt = self._build_design_prompt(
                title=title,
                category=topic, # Mapping 'topic' to 'category'
                content=content,
                reference_templates=None, # Not available in this method's signature
                user_preference="" # Not available in this method's signature
            )
            
            # 4. 调用LLM生成模板
            response = await self.llm.acomplete( # Using self.llm as per __init__, not self.llm_service
                prompt=design_prompt,
                model=self._get_designer_llm_model(),
                max_tokens=4000,
                temperature=0.7
            )
            
            html_template = response.get("content", "")
            
            # 5. 清理和验证
            html_template = self._clean_and_validate(html_template, title, topic)
            
            # The following log line was removed as design_direction and color_theme are no longer defined in this flow.
            # log.print_log(f"[AI设计师] 已根据内容匹配方案: {design_direction['name']}风格, {color_theme}配色")
            
            return html_template
            
            return html_template
        except Exception as e:
            log.print_log(f"[AI设计师] 生成失败: {e}", "error")
            return self._get_fallback_template(title, topic)

    async def generate_stepwise(self, title: str, category: str, content: str, reference_templates: List[str] = None, **kwargs):
        """
        分步生成渲染器方案 (Streaming)
        """
        model = self._get_designer_llm_model()
        
        try:
            # --- 阶段 1: 视觉风格意图定义 (V18.3 全动态) ---
            yield {"type": "log", "message": "🎨 AI 视觉总监正在感悟内容灵魂..."}
            
            design_prompt = self._build_design_prompt(
                title=title,
                category=category,
                content=content,
                reference_templates=reference_templates,
                user_preference=kwargs.get("user_preference", "")
            )
            
            yield {"type": "log", "message": "✨ 正在构建独创色彩体系与视觉平衡..."}
            
            full_design = ""
            async for chunk in self.llm.stream_chat([{"role": "user", "content": design_prompt}], model=model):
                full_design += chunk
                # 可以在此处提取中间状态
            
            yield {"type": "log", "message": "✅ 视觉容器构建完成，正在注入内容流水线..."}
            
            # 提取同步暗号
            design_sync = {}
            import re
            sync_match = re.search(r'<!-- DESIGN_SYNC: ({.*?}) -->', full_design)
            if sync_match:
                import json
                try:
                    design_sync = json.loads(sync_match.group(1))
                except:
                    pass
            
            yield {
                "type": "result",
                "template": full_design,
                "design_tokens": design_sync
            }
            
        except Exception as e:
            log.print_log(f"[AI设计师] V18.3 生成失败: {e}", "error")
            yield {"type": "log", "message": f"❌ 设计师遭遇异常: {str(e)}"}

    async def stream_unique_template(self, title: str, content: str, 
                                topic: str = "", keywords: List[str] = None):
        """
        异步生成独特的HTML模板并流式产生日志和页面分块 (由 Agent 引擎驱动)
        """
        try:
            # --- Stage 0: 设计决策 ---
            # V18.3: 移除旧的决策逻辑，直接调用新的 generate_stepwise
            
            # 调用新的 generate_stepwise 方法
            async for step in self.generate_stepwise(title, topic, content, user_preference=""):
                if step["type"] == "log":
                    yield step
                elif step["type"] == "thought":
                    yield step # 向前台透传 AI 思考过程
                elif step["type"] == "chunk":
                    # 透传所有引擎元数据 (stage, is_fragment 等)
                    yield step
                elif step["type"] == "full_html":
                    # 最终审计结果透传
                    yield step
                elif step["type"] == "result":
                    # V18.3: 处理 generate_stepwise 返回的 result 类型
                    # 转换为 chunk 类型以便前端正确处理
                    yield {"type": "chunk", "content": step.get("template", "")}
            
            yield {"type": "done"}
                
        except Exception as e:
            log.print_log(f"[AI设计师] Agent生成失败: {e}", "error")
            yield {"type": "log", "message": f"❌ Agent 遭遇异常: {str(e)}"}

    def _build_design_prompt(self, title: str, category: str, content: str, reference_templates: List[str] = None, user_preference: str = "") -> str:
        """
        V18.3: 极致发散思维设计提示词引擎
        注入“视觉重心防护”与“熵增布局机制”
        """
        ref_templates_str = ""
        if reference_templates:
            ref_templates_str = "\n【结构参考（仅供灵感启发，严禁照抄布局）】\n" + "\n---".join(reference_templates)
            
        # 视觉突变种子 (Entropy Seeds) - 强制打破固定审美
        visual_mutations = [
            "采用【Bento Grid (便当盒) 分块排版】，将文章核心观点模块化，每个卡片拥有独立的视觉律动",
            "采用【左侧大尺寸装饰性侧边栏 + 右侧沉浸式窄行阅读器】，营造独立出版物的先锋感",
            "引入【物理层级堆叠感】：利用 CSS z-index 和负边距，让标题背景、图片和装饰元素产生微妙的视觉错位",
            "【非对称版式强制】：将主要视觉重心放在黄金分割点（约 61.8% 处），通过对角线装饰平衡视觉压力",
            "采用【 मेगा (Mega) 排版体系】：将关键动词或日期作为背景超级水印（150px+，极低透明度），极具震撼力",
            "注入【毛玻璃光影实验室】：大量运用 `backdrop-filter` 产生的玻璃拟态层，配合流体渐变背景"
        ]
        
        # 阅读易读性护航 (Readability Guard)
        readability_rules = """
【最高易读性约束 - 强制执行】
1. **视线流控制**：即便布局是非对称的，核心正文区域必须保持在 60%-80% 宽度之间，且居中或在易扫读区域。
2. **高对比度防护**：背景色与文字色必须满足 WCAG 2.0 标准（对比度 >= 4.5:1）。
3. **行间距呼吸感**：强制设置行高为 1.75-2.0，段间距为 1.5em-2em，严禁文字堆砌。
4. **字体层级清晰**：H2 标题必须具备强大的视觉锚点（如加粗、装饰线或特殊色彩）。
"""

        style_context = f"用户偏好风格指导（参考灵感）：{user_preference}" if user_preference else "全面释放创造力，不受任何框架限制。"
        
        mutation_seed = random.choice(visual_mutations)

        prompt = f"""你是一位享誉全球的**顶级跨媒体艺术总监**。你的任务是为文章《{title}》定制一个**绝无仅有、充满艺术张力且极易阅读**的独立 HTML 交互容器。

【本次设计的灵魂指令】
- **核心布局突变种子**：{mutation_seed}
- **用户审美锚点**：{style_context}

【视觉生成算法要求】
1. **拒绝预设色彩**：不要使用任何常见的“蓝白”或“黑白”组合。请根据文章情感，构思一套互补色或类比色体系（包含 Primary, Secondary, Accent, Background），并在 CSS 变量中定义。
2. **创造力发散**：鼓励手写复杂的 CSS 动画、SVG 物理碰撞形状、以及伪类（::before/::after）装饰。
3. **百万分之一独特性**：每一篇文章都应拥有独特的装饰性 SVG，例如根据文章主题生成内联的抽象多边形或线条。

{readability_rules}

【技术要求】
- 必须包含：完整的响应式 CSS (Flex/Grid)、内联 SVG、以及移动端完美自适应。
- 内容占位符：必须且仅为 `{{{{content}}}}`。
- 暗号同步：<!-- DESIGN_SYNC: {{"primary": "自拟色值", "secondary": "自拟色值", "accent": "自拟色值", "bg": "自拟色值"}} -->

{ref_templates_str}

【内容灵魂参考】
{content[:1500]} ...

请直接启动你的艺术创作过程，输出 <!DOCTYPE html> 完整的 HTML 代码，不要任何 Markdown 包裹：
"""
        return prompt

    def _clean_and_validate(self, html: str, title: str, topic: str) -> str:
        """清理和校验生成的HTML，确保关键元素存在且格式正确"""
        # 1. 提取真正的 HTML 块 (跳过 AI 的开场白和 Markdown 标记)
        # 优先寻找 <!DOCTYPE 开始的内容到 </html> 结束
        html_match = re.search(r'(<!DOCTYPE.*?>.*?</html>)', html, re.DOTALL | re.IGNORECASE)
        if not html_match:
            # 其次寻找 <html> 到 </html> 结束
            html_match = re.search(r'(<html.*?>.*?</html>)', html, re.DOTALL | re.IGNORECASE)
        
        if html_match:
            html = html_match.group(1)
        else:
            # 如果没找到标准 HTML 标签，则手动移除可能的 Markdown 标记
            html = re.sub(r'^```html\s*', '', html, flags=re.MULTILINE)
            html = re.sub(r'```\s*$', '', html, flags=re.MULTILINE)
            html = html.strip()
        
        # 2. 占位符归一化 (Placeholder Normalization)
        # AI 可能生成 {{ content }}, {content}, {{ CONTENT }} 等变体
        # 同时清理 AI 误加的包裹符号，如 { {{content}} } 或 [ {{content}} ]
        html = re.sub(r'[\{\[\(]*\s*\{\{\s*content\s*\}\}\s*[\}\]\)]*', '{{content}}', html, flags=re.IGNORECASE)
        html = re.sub(r'[\{\[\(]*\s*\{(?!\s*\{)\s*content\s*\}\s*[\}\]\)]*', '{{content}}', html, flags=re.IGNORECASE)
        
        # 3. 强制校验占位符：如果没有 {{content}}，尝试在逻辑位置插入
        if "{{content}}" not in html:
            # 尝试在某些常见标志后插入
            if "<!-- content -->" in html:
                html = html.replace("<!-- content -->", "{{content}}")
            elif "</body>" in html:
                # 寻找最后一个可能的容器或直接放在 body 结尾前
                if "</div>" in html:
                    parts = html.rsplit("</div>", 1)
                    html = parts[0] + "\n    <div style='padding:20px;'>{{content}}</div>\n</div>" + parts[1]
                else:
                    html = html.replace("</body>", "    <div style='padding:20px;'>{{content}}</div>\n</body>")
        
        return html

    def _get_fallback_template(self, title: str, topic: str) -> str:
        """兜底模板，防止AI生成失败导致页面全空"""
        current_date = datetime.now().strftime("%Y-%m-%d")
        return f"""
<!DOCTYPE html>
<html>
<head>
    <meta charset="UTF-8">
    <title>{title}</title>
</head>
<body style="margin:0; padding:10px; background:#f5f5f5; font-family:sans-serif;">
    <div style="max-width:600px; margin:0 auto; background:#fff; padding:30px; border-radius:12px; box-shadow:0 5px 15px rgba(0,0,0,0.05);">
        <h1 style="color:#333; font-size:24px; margin-bottom:10px;">{title}</h1>
        <div style="color:#999; font-size:14px; margin-bottom:20px;">{topic} · {current_date}</div>
        <div style="line-height:1.8; color:#444;">{{{{content}}}}</div>
    </div>
</body>
</html>
"""
