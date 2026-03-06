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
    
    # 丰富的设计方向：侧重浅色、呼吸感、现代感
    DESIGN_DIRECTIONS = [
        {
            "name": "极简果粉风",
            "style": "大面积留白、SF Pro 字体感、极细边框、浅灰色调、高精密感",
            "colors": "#000000, #8E8E93, #F2F2F7, #FFFFFF",
            "typography": "高端非衬线体, 增大字间距"
        },
        {
            "name": "诺德森冷色",
            "style": "冰岛蓝、深林绿点缀、半透明磨砂玻璃、冷静而高级",
            "colors": "#2E3440, #5E81AC, #ECEFF4, #D8DEE9",
            "typography": "干净、几何感"
        },
        {
            "name": "人文艺术志",
            "style": "衬线体大标题、米白底色、纸张质感、古典优雅",
            "colors": "#1A1A1A, #C2A679, #F5F2ED, #E8E4DB",
            "typography": "宋体/衬线体, 垂直行高, 宁静"
        },
        {
            "name": "奢侈品画册",
            "style": "大幅留白、极细线条装饰、不对称布局、金色勾边、尊贵优雅",
            "colors": "#111111, #D4AF37, #FAFAFA, #FFFFFF",
            "typography": "高对比衬线体 (Didot/Bodoni感)"
        },
        {
            "name": "未来赛博感",
            "style": "极窄边框、霓虹色线条点缀、悬浮阴影、数字化网格装饰",
            "colors": "#6366F1, #A855F7, #F8FAFC, #FFFFFF",
            "typography": "现代等宽字体 (JetBrains Mono感)"
        },
        {
            "name": "大地有机风",
            "style": "圆润边角、自然纹理装饰、温暖土色系、极佳的呼吸感",
            "colors": "#4B2C20, #8C6239, #FDF8F5, #FFFFFF",
            "typography": "温润非衬线体"
        },
        {
            "name": "瑞士国际风",
            "style": "严谨网格、红黑白经典配色、极致整洁、高度专业化",
            "colors": "#E63946, #1D3557, #F1FAEE, #FFFFFF",
            "typography": "经典黑体, 比例严谨"
        },
        {
            "name": "新粗野主义",
            "style": "粗大黑体、高对比色彩撞击、硬核工业感、装饰性大字报、厚重阴影",
            "colors": "#000000, #FFE600, #FF3D00, #FFFFFF",
            "typography": "重型黑体, 倾斜加粗"
        },
        {
            "name": "极客碳感",
            "style": "深灰色磨砂碳纤维感、悬浮控制台、青色氛围光、程序员美学、逻辑感强",
            "colors": "#121212, #00FFD1, #1E1E1E, #FFFFFF",
            "typography": "等宽字体, 现代科技感"
        },
        {
            "name": "浮世绘卷",
            "style": "淡雅和纸色纹理、传统扇面布局、墨迹晕染、清逸空灵、东方韵味",
            "colors": "#333333, #C85A5A, #F5F1E9, #FFFDF5",
            "typography": "衬线楷体感, 留白意境"
        }
    ]
    
    # 色彩调色盘映射
    COLOR_PALETTES = {
        "tech": ["#4F46E5", "#06B6D4", "#6366F1", "#ECFDF5"],
        "nature": ["#059669", "#10B981", "#34D399", "#F0FDF4"],
        "elegant": ["#111827", "#374151", "#C2A679", "#F9FAFB"],
        "vibrant": ["#EC4899", "#8B5CF6", "#F59E0B", "#FFF7ED"],
        "minimal": ["#1F2937", "#6B7280", "#9CA3AF", "#F3F4F6"],
        "warm": ["#D97706", "#B45309", "#F59E0B", "#FFFBEB"],
        "retro": ["#7C2D12", "#9A3412", "#C2410C", "#FFF7ED"]
    }

    def __init__(self):
        self.llm_service = get_llm_service()
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
            # 1. 自动推荐最合适的设计方向 (内容感知)
            design_direction = await self._get_recommended_direction(title, content, topic)
            
            # 2. 根据主题选择配色
            color_theme = await self._select_color_theme(topic, content)
            
            # 3. 构建深度设计提示词
            prompt = self._build_design_prompt(
                title, content, topic, keywords,
                design_direction, color_theme
            )
            
            # 4. 调用LLM生成模板
            response = await self.llm_service.acomplete(
                prompt=prompt,
                model=self._get_designer_llm_model(),
                max_tokens=4000,
                temperature=0.7
            )
            
            html_template = response.get("content", "")
            
            # 5. 清理和验证
            html_template = self._clean_and_validate(html_template, title, topic)
            
            log.print_log(f"[AI设计师] 已根据内容匹配方案: {design_direction['name']}风格, {color_theme}配色")
            
            return html_template
            
        except Exception as e:
            log.print_log(f"[AI设计师] 生成失败: {e}", "error")
            return self._get_fallback_template(title, topic)
    
    async def _get_recommended_direction(self, title: str, content: str, topic: str) -> Dict:
        """根据内容同步推荐最合适的设计方向"""
        try:
            directions_summary = "\n".join([f"- {d['name']}: {d['style']}" for d in self.DESIGN_DIRECTIONS])
            
            recommend_prompt = f"""
你是一位资深新媒体视觉总监。请根据以下文章信息，从提供的设计方向列表中，选出一个最能体现文章气质、最能吸引读者沉浸阅读的方向。

【文章标题】：{title}
【所属主题】：{topic}
【内容片段】：{content[:500]}

【备选设计方向】：
{directions_summary}

请直接返回你认为最合适的方案【名称】，不要解释原因，不要输出其他任何文字。
"""
            # 使用异步 acomplete 方法
            response = await self.llm_service.acomplete(
                prompt=recommend_prompt,
                model=self._get_designer_llm_model(),
                max_tokens=50,
                temperature=0.3
            )
            
            recommendation = response.get("content", "").strip()
            for d in self.DESIGN_DIRECTIONS:
                if d['name'] in recommendation:
                    return d
                    
            return random.choice(self.DESIGN_DIRECTIONS)
        except:
            return random.choice(self.DESIGN_DIRECTIONS)

    async def _select_color_theme(self, topic: str, content: str) -> str:
        """根据内容意图自动挑选配色方案"""
        try:
            color_prompt = f"""
请根据以下文章主题和内容核心，从提供的视觉风格中选出最匹配的一种：
- tech (科技感: 深邃蓝/青)
- nature (自然感: 清爽绿)
- elegant (商务/金融: 高亮金/深蓝)
- warm (生活/美食: 暖橙/木色)
- minimal (通用新闻: 极简灰/白)
- vibrant (创意艺术: 鲜艳对比色)
- retro (人文怀旧: 复古色调)

【文章标题】：{topic}
【内容片段】：{content[:500]}

请仅返回标识符单词（如 tech, vibrant 等），不要输出其他任何文字。
"""
            response = await self.llm_service.acomplete(
                prompt=color_prompt,
                model=self._get_designer_llm_model(),
                max_tokens=2000,
                temperature=0.3
            )
            theme = response.get("content", "").lower().strip()
            
            # 校验返回值是否在有效范围
            if theme in self.COLOR_PALETTES:
                return theme
            
            # 如果 AI 回答中有关键词
            for k in self.COLOR_PALETTES.keys():
                if k in theme: return k
                
            return "minimal"
        except:
            return "minimal"

    async def stream_unique_template(self, title: str, content: str, 
                                topic: str = "", keywords: List[str] = None):
        """
        异步生成独特的HTML模板并流式产生日志和页面分块 (由 Agent 引擎驱动)
        """
        try:
            from src.ai_write_x.core.adaptive_template_engine import AdaptiveTemplateEngine
            engine = AdaptiveTemplateEngine()
            
            # --- Stage 0: 设计决策 ---
            design_direction = await self._get_recommended_direction(title, content, topic)
            color_scheme_key = await self._select_color_theme(topic, content)
            
            yield {"type": "log", "message": f"🤖 AI 设计师已感知内容气质: 推荐使用【{design_direction.get('name', '默认')}】风格"}
            yield {"type": "log", "message": f"🎨 核心视觉规则: {design_direction.get('style', '自适应布局')}"}
            
            # --- 调用 Agent 引擎进行 5 阶逐步强化 ---
            # 传入固定决策，确保渲染结果与 Log 一致
            async for step in engine.generate_stepwise(title, content, topic, 
                                                     fixed_direction=design_direction,
                                                     fixed_color_key=color_scheme_key):
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
            
            yield {"type": "done"}
                
        except Exception as e:
            log.print_log(f"[AI设计师] Agent生成失败: {e}", "error")
            yield {"type": "log", "message": f"❌ Agent 遭遇异常: {str(e)}"}
                
        except Exception as e:
            log.print_log(f"[AI设计师] 流式生成失败: {e}", "error")
            yield {"type": "log", "message": f"❌ 设计师遭遇异常: {str(e)}"}

    def _build_design_prompt(self, title: str, content: str, topic: str, 
                            keywords: List[str], design_direction: Dict, 
                            color_theme: str, reference_templates: List[str] = None) -> str:
        """构建详细的设计提示词"""
        colors = self.COLOR_PALETTES.get(color_theme, self.COLOR_PALETTES["minimal"])
        current_date = datetime.now().strftime("%Y-%m-%d")
        
        ref_templates_str = ""
        if reference_templates:
            ref_templates_str = "\n【结构参考（学习其容器布局而非文本内容）】\n" + "\n---\n".join(reference_templates)
            
        # 布局突变变量 (Layout Mutation Variables) - 强制打破固定审美
        layout_mutations = [
            "采用【左侧宽视觉留白 + 右侧内容对齐】的非对称结构，营造高级呼吸感",
            "主体容器使用【微圆角 + 多层柔和弥散阴影】产生悬浮感，模仿物理杂志层级",
            "在标题区域使用【巨大的装饰性水印字母/汉字】局部透出底层背景，增加视觉锚点",
            "引用块采用【全屏宽度或溢出容器】的设计，产生杂志跨页感，打断阅读疲劳",
            "使用【精美的内联 SVG 几何图形】作为段落间的流动点缀，引导视线向下",
            "正文背景融入【细微的纸张/碳纤维纹理】内联图片或 CSS 渐变，增强触觉暗示",
            "采用【Bento Grid (便当盒) 风格】的局部色块封装核心结论，使重点一目了然",
            "设计一个【沉浸式侧边进度装饰】，随滚动产生微妙的视觉位移变化"
        ]
        
        # 创意灵魂钩子 (Creative Soul Hooks) - 赋予AI“思想”和“感觉”
        experience_concepts = [
            "数字花园 (Digital Garden)：设计中充满自然生长的线条和有机形状，强调生长感",
            "未来考古 (Future Archeology)：利用怀旧的线条与极现代的模糊滤镜(Blur)结合，产生时空错位感",
            "极简留白意识：将 60% 的视觉注意力留给空白，让文字在呼吸中跳动",
            "电影蒙太奇：通过强烈的明暗对比和局部的“聚光灯”效果设计，让阅读像看电影",
            "动态韵律：段落间宽窄不一，通过 CSS 变量营造一种“音阶”般的节奏感"
        ]
        
        mutation_hook = random.choice(layout_mutations)
        creative_concept = random.choice(experience_concepts)
        
        prompt = f"""你是一位享誉全球、拥有深厚人文底蕴的**顶级视觉体验顾问**。你的目标不再是简单的“套模板”，而是根据文章主题，为读者构建一个**极其丝滑、富有节奏感、且能产生情感共鸣的深度阅读场域**。

你的终极指标是：**大幅提升读者的阅读愉悦度与页面停留时间 (Dwell Time)**。

【本次设计的“灵魂思想”】
- **核心理念**：{creative_concept}。
- **布局钩子**：{mutation_hook}。

【视觉引导心理学】
1. **视觉锚点 (Visual Anchors)**：在标题、开篇处利用强大的 SVG 装饰或大号字体强制吸引注意。
2. **阅读节奏 (Reading Rhythm)**：正文不要一成不变。利用间距的变化、局部的色块、精美的图标点缀，让读者的眼睛“不累”。
3. **沉浸式氛围**：主色彩点缀（{colors[0]}）不仅仅是线条，它可以是背景的微弱光晕、渐变的引导。

【强制美学规则】
- **留白即生命**：严禁内容堆砌，四周必须预留充足的“呼吸空间”。
- **跨屏一致性**：必须适配移动端，使用自适应逻辑确保在不同屏幕上都像一张完美的艺术海报。
- **自定义富文本组件**：
    - `<strong>`：设计为具有【呼吸感】的下划线或艺术底纹，不能只是加粗。
    - `[KEY/HL/TIPS]` 等标签：必须与【{creative_concept}】的灵魂完全融合，例如：如果风格是“数字花园”，标签应像叶片般圆润。

【技术约束：内联艺术】
- 100% 内联化：所有 SVG 路径必须原生手写，所有交互通过简单的内联 CSS 变体模拟。
- **自由意志**：如果文章充满科技感，你甚至可以尝试打破“容器”概念，让文字像在真空中漂浮。如果是历史题材，让文字像写在陈旧的绢帛上。

【内容占位符 `{{{{content}}}}`】
- **严禁符号包裹**：只需输出 `{{{{content}}}}`。
- **样式穿透**：通过在父容器定义样式，确保生成的 `<h2>`, `<p>`, `<ul>`, `<img>` 等具有统一且极其高级的排版属性。

【输出结构】
1. 覆盖全屏的沉浸背景。
2. 具有强大视觉冲击力的头部 (Title: {title})。
3. 承载 `{{{{content}}}}` 的核心场域。
4. 页脚处的艺术化收尾。

【色彩同步暗号】
在 HTML 的最后，包含：<!-- DESIGN_SYNC: {{"primary": "{colors[0]}", "secondary": "{colors[1]}", "accent": "{colors[2]}", "bg": "{colors[3] if len(colors)>3 else '#F8FAFC'}"}} -->
{ref_templates_str}

【原文气氛参考】
{content[:2000]} ...

请直接输出整个 HTML (<!DOCTYPE html> 开始)，不要 Markdown 包裹，不要有任何 [占位图] 字样。
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
