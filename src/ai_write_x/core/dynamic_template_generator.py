# -*- coding: utf-8 -*-
"""
AI动态模板生成器
根据内容主题、情感和结构自动生成匹配的HTML模板
"""

import json
import re
from typing import Dict, List, Any, Optional
from dataclasses import dataclass, field
from enum import Enum

from src.ai_write_x.utils import log


class TemplateStyle(Enum):
    """模板风格类型"""
    MINIMAL = "minimal"           # 极简风格
    TECH = "tech"                 # 科技感
    WARM = "warm"                 # 温暖人文
    BUSINESS = "business"         # 商务专业
    CREATIVE = "creative"         # 创意艺术
    ACADEMIC = "academic"         # 学术严谨
    STORY = "story"               # 故事叙述
    NEWS = "news"                 # 新闻资讯


class ColorScheme(Enum):
    """配色方案"""
    BLUE = {
        "primary": "#2563eb",
        "secondary": "#3b82f6", 
        "accent": "#60a5fa",
        "background": "#eff6ff",
        "text": "#1e3a5f",
        "light": "#dbeafe"
    }
    GREEN = {
        "primary": "#059669",
        "secondary": "#10b981",
        "accent": "#34d399", 
        "background": "#ecfdf5",
        "text": "#064e3b",
        "light": "#d1fae5"
    }
    PURPLE = {
        "primary": "#7c3aed",
        "secondary": "#8b5cf6",
        "accent": "#a78bfa",
        "background": "#f5f3ff", 
        "text": "#4c1d95",
        "light": "#ede9fe"
    }
    ORANGE = {
        "primary": "#ea580c",
        "secondary": "#f97316",
        "accent": "#fb923c",
        "background": "#fff7ed",
        "text": "#7c2d12",
        "light": "#ffedd5"
    }
    PINK = {
        "primary": "#db2777",
        "secondary": "#ec4899",
        "accent": "#f472b6",
        "background": "#fdf2f8",
        "text": "#831843",
        "light": "#fce7f3"
    }
    DARK = {
        "primary": "#1f2937",
        "secondary": "#374151",
        "accent": "#6b7280",
        "background": "#111827",
        "text": "#f9fafb",
        "light": "#374151"
    }


@dataclass
class ContentAnalysis:
    """内容分析结果"""
    title: str
    topic: str
    keywords: List[str]
    emotions: List[str]
    content_structure: Dict[str, Any]
    word_count: int
    has_numbers: bool
    has_quotes: bool
    has_list: bool
    recommended_style: TemplateStyle
    recommended_colors: ColorScheme


@dataclass
class TemplateComponent:
    """模板组件"""
    name: str
    html_template: str
    css_styles: str
    suitable_for: List[str]


class DynamicTemplateGenerator:
    """动态模板生成器"""
    
    # 预定义的组件库
    COMPONENTS = {
        "header": TemplateComponent(
            name="header",
            html_template="""
            <header style="{header_style}">
                <div style="{category_style}">{category}</div>
                <h1 style="{title_style}">{title}</h1>
                {subtitle_html}
            </header>
            """,
            css_styles="",
            suitable_for=["article", "blog", "news"]
        ),
        "section_card": TemplateComponent(
            name="section_card",
            html_template="""
            <section style="{section_style}">
                {icon_html}
                <h2 style="{heading_style}">{heading}</h2>
                {content_html}
            </section>
            """,
            css_styles="",
            suitable_for=["article", "blog"]
        ),
        "quote_block": TemplateComponent(
            name="quote_block",
            html_template="""
            <blockquote style="{quote_style}">
                <svg style="{quote_icon_style}" viewBox="0 0 24 24">
                    <path fill="currentColor" d="M6 17h3l2-4V7H5v6h3zm8 0h3l2-4V7h-6v6h3z"/>
                </svg>
                <p style="{quote_text_style}">{quote_text}</p>
                {source_html}
            </blockquote>
            """,
            css_styles="",
            suitable_for=["article", "story"]
        ),
        "highlight_box": TemplateComponent(
            name="highlight_box",
            html_template="""
            <div style="{highlight_style}">
                {icon_html}
                <p style="{highlight_text_style}">{text}</p>
            </div>
            """,
            css_styles="",
            suitable_for=["article", "tech", "news"]
        ),
        "image_placeholder": TemplateComponent(
            name="image_placeholder",
            html_template="""
            <figure style="{figure_style}">
                <img src="{image_src}" style="{image_style}" alt="{alt_text}"/>
                {caption_html}
            </figure>
            """,
            css_styles="",
            suitable_for=["article", "blog", "story"]
        ),
        "list_block": TemplateComponent(
            name="list_block",
            html_template="""
            <div style="{list_container_style}">
                {items_html}
            </div>
            """,
            css_styles="",
            suitable_for=["article", "tech", "guide"]
        ),
        "divider": TemplateComponent(
            name="divider",
            html_template="""
            <div style="{divider_style}">
                <span style="{divider_line_style}"></span>
                {icon_html}
                <span style="{divider_line_style}"></span>
            </div>
            """,
            css_styles="",
            suitable_for=["article", "story"]
        ),
        "footer": TemplateComponent(
            name="footer",
            html_template="""
            <footer style="{footer_style}">
                {content_html}
                {svg_animation}
            </footer>
            """,
            css_styles="",
            suitable_for=["article", "blog"]
        )
    }
    
    def __init__(self):
        self.style_config = self._init_style_config()
    
    def _init_style_config(self) -> Dict:
        """初始化样式配置"""
        return {
            TemplateStyle.MINIMAL: {
                "border_radius": "8px",
                "shadow": "0 2px 8px rgba(0,0,0,0.08)",
                "font_heading": "'Inter', -apple-system, sans-serif",
                "font_body": "'Inter', -apple-system, sans-serif",
                "spacing": "24px",
                "decoration": "minimal"
            },
            TemplateStyle.TECH: {
                "border_radius": "12px",
                "shadow": "0 4px 20px rgba(37, 99, 235, 0.15)",
                "font_heading": "'JetBrains Mono', 'Fira Code', monospace",
                "font_body": "'Inter', -apple-system, sans-serif",
                "spacing": "28px",
                "decoration": "geometric"
            },
            TemplateStyle.WARM: {
                "border_radius": "16px",
                "shadow": "0 4px 16px rgba(249, 115, 22, 0.12)",
                "font_heading": "'Noto Serif SC', Georgia, serif",
                "font_body": "'Noto Sans SC', -apple-system, sans-serif",
                "spacing": "32px",
                "decoration": "organic"
            },
            TemplateStyle.BUSINESS: {
                "border_radius": "6px",
                "shadow": "0 2px 12px rgba(0,0,0,0.1)",
                "font_heading": "'Inter', 'Helvetica Neue', sans-serif",
                "font_body": "'Inter', -apple-system, sans-serif",
                "spacing": "24px",
                "decoration": "professional"
            },
            TemplateStyle.CREATIVE: {
                "border_radius": "20px",
                "shadow": "0 8px 32px rgba(124, 58, 237, 0.2)",
                "font_heading": "'Playfair Display', Georgia, serif",
                "font_body": "'Inter', sans-serif",
                "spacing": "36px",
                "decoration": "artistic"
            },
            TemplateStyle.ACADEMIC: {
                "border_radius": "4px",
                "shadow": "0 1px 4px rgba(0,0,0,0.05)",
                "font_heading": "'Times New Roman', Georgia, serif",
                "font_body": "'Times New Roman', serif",
                "spacing": "20px",
                "decoration": "formal"
            },
            TemplateStyle.STORY: {
                "border_radius": "12px",
                "shadow": "0 4px 20px rgba(236, 72, 153, 0.15)",
                "font_heading": "'Noto Serif SC', Georgia, serif",
                "font_body": "'Noto Sans SC', sans-serif",
                "spacing": "28px",
                "decoration": "narrative"
            },
            TemplateStyle.NEWS: {
                "border_radius": "0px",
                "shadow": "none",
                "font_heading": "'Georgia', 'Times New Roman', serif",
                "font_body": "'Georgia', serif",
                "spacing": "20px",
                "decoration": "editorial"
            }
        }
    
    def analyze_content(self, title: str, content: str, topic: str = "") -> ContentAnalysis:
        """分析内容特征"""
        # 提取关键词
        keywords = self._extract_keywords(content)
        
        # 分析情感
        emotions = self._analyze_emotions(content)
        
        # 分析结构
        structure = self._analyze_structure(content)
        
        # 确定推荐风格
        style = self._determine_style(title, content, topic, emotions)
        
        # 确定配色
        colors = self._determine_colors(emotions, topic)
        
        return ContentAnalysis(
            title=title,
            topic=topic or self._extract_topic(title, content),
            keywords=keywords,
            emotions=emotions,
            content_structure=structure,
            word_count=len(content),
            has_numbers=bool(re.search(r'\d+', content)),
            has_quotes='"' in content or '"' in content or '"' in content,
            has_list=re.search(r'^[\s]*[\d\-\*•]', content, re.MULTILINE) is not None,
            recommended_style=style,
            recommended_colors=colors
        )
    
    def _extract_keywords(self, content: str) -> List[str]:
        """提取关键词"""
        # 简单的关键词提取（基于词频和长度）
        words = re.findall(r'[\u4e00-\u9fa5]{2,8}', content)
        word_freq = {}
        for word in words:
            if len(word) >= 2 and len(word) <= 8:
                word_freq[word] = word_freq.get(word, 0) + 1
        
        # 返回频率最高的前10个词
        sorted_words = sorted(word_freq.items(), key=lambda x: x[1], reverse=True)
        return [word for word, freq in sorted_words[:10] if freq >= 2]
    
    def _analyze_emotions(self, content: str) -> List[str]:
        """分析情感倾向"""
        emotions = []
        
        # 定义情感词库
        emotion_words = {
            "excited": ["激动", "兴奋", "惊喜", "棒极了", "太棒了", " amazing"],
            "warm": ["温暖", "感动", "温馨", "美好", "幸福", "感恩"],
            "serious": ["重要", "严峻", "关键", "必须", "严肃", "critical"],
            "tech": ["创新", "技术", "智能", "科技", "未来", "突破"],
            "sad": ["悲伤", "遗憾", "可惜", "难过", "痛苦", "struggle"],
            "professional": ["专业", "高效", "精准", "优化", "提升", "improve"]
        }
        
        for emotion, words in emotion_words.items():
            if any(word in content for word in words):
                emotions.append(emotion)
        
        return emotions if emotions else ["neutral"]
    
    def _analyze_structure(self, content: str) -> Dict[str, Any]:
        """分析内容结构"""
        structure = {
            "has_introduction": False,
            "has_conclusion": False,
            "sections": 0,
            "paragraphs": content.count('\n\n') + 1,
            "lists": len(re.findall(r'^[\s]*[\d\-\*•]', content, re.MULTILINE)),
            "quotes": content.count('"') + content.count('"') + content.count('"')
        }
        
        # 检测引言和结论
        lines = content.split('\n')
        if lines:
            first_para = lines[0]
            if any(word in first_para for word in ["引言", "前言", "介绍", "开篇"]):
                structure["has_introduction"] = True
            
            last_para = lines[-1]
            if any(word in last_para for word in ["结语", "总结", "结论", "总而言之"]):
                structure["has_conclusion"] = True
        
        # 检测章节数
        section_markers = re.findall(r'[\s]*(?:##|第[一二三四五六七八九十]+章|【.*?】)', content)
        structure["sections"] = len(section_markers)
        
        return structure
    
    def _determine_style(self, title: str, content: str, topic: str, emotions: List[str]) -> TemplateStyle:
        """确定推荐风格"""
        # 基于情感和主题判断风格
        if "tech" in emotions or any(word in title + topic for word in ["AI", "技术", "科技", "创新", "智能"]):
            return TemplateStyle.TECH
        elif "sad" in emotions or "struggle" in emotions:
            return TemplateStyle.STORY
        elif "professional" in emotions:
            return TemplateStyle.BUSINESS
        elif "warm" in emotions:
            return TemplateStyle.WARM
        elif "excited" in emotions:
            return TemplateStyle.CREATIVE
        elif "学术" in topic or "研究" in title or "论文" in title:
            return TemplateStyle.ACADEMIC
        elif "新闻" in topic or "资讯" in topic:
            return TemplateStyle.NEWS
        else:
            return TemplateStyle.MINIMAL
    
    def _determine_colors(self, emotions: List[str], topic: str) -> ColorScheme:
        """确定配色方案"""
        if "tech" in emotions or "科技" in topic:
            return ColorScheme.BLUE
        elif "环保" in topic or "健康" in topic or "生机" in emotions:
            return ColorScheme.GREEN
        elif "创意" in topic or "艺术" in topic or "excited" in emotions:
            return ColorScheme.PURPLE
        elif "美食" in topic or "温暖" in emotions:
            return ColorScheme.ORANGE
        elif "story" in emotions or "情感" in topic:
            return ColorScheme.PINK
        else:
            return ColorScheme.BLUE
    
    def _extract_topic(self, title: str, content: str) -> str:
        """提取主题"""
        # 简单的主题提取
        tech_keywords = ["AI", "技术", "科技", "软件", "硬件", "互联网"]
        life_keywords = ["生活", "美食", "旅行", "健康", "养生"]
        business_keywords = ["商业", "投资", "财经", "管理", "职场"]
        
        combined = title + content[:500]
        
        if any(kw in combined for kw in tech_keywords):
            return "科技"
        elif any(kw in combined for kw in life_keywords):
            return "生活"
        elif any(kw in combined for kw in business_keywords):
            return "商业"
        else:
            return "综合"
    
    def _generate_js_scripts(self) -> str:
        """生成JavaScript脚本 - 避免f-string冲突"""
        return """
    <script>
        // 初始化图标
        lucide.createIcons();
        
        // 阅读进度
        window.addEventListener('scroll', function() {
            var winScroll = document.body.scrollTop || document.documentElement.scrollTop;
            var height = document.documentElement.scrollHeight - document.documentElement.clientHeight;
            var scrolled = (winScroll / height) * 100;
            document.getElementById('readingProgress').style.width = scrolled + '%';
        });
        
        // 回到顶部
        function scrollToTop() {
            window.scrollTo({ top: 0, behavior: 'smooth' });
        }
        
        // 代码高亮
        document.addEventListener('DOMContentLoaded', function() {
            document.querySelectorAll('pre code').forEach(function(block) {
                hljs.highlightBlock(block);
            });
        });
        
        // 图片点击放大
        document.querySelectorAll('.content-body img').forEach(function(img) {
            img.classList.add('lazy-image');
            img.onclick = function() {
                this.classList.toggle('expanded');
            };
        });
    </script>"""
    
    def generate_template(self, analysis: ContentAnalysis) -> str:
        """生成完整模板 - 现代精美设计"""
        colors = analysis.recommended_colors.value
        style_config = self.style_config[analysis.recommended_style]
        
        # 生成各个部分
        header = self._generate_header(analysis, colors, style_config)
        body = self._generate_body(analysis, colors, style_config)
        footer = self._generate_footer(analysis, colors, style_config)
        js_scripts = self._generate_js_scripts()
        
        # 生成CSS样式
        css_styles = self._generate_css_styles(colors, style_config)
        
        # 组合完整HTML
        template_parts = [
            "<!DOCTYPE html>",
            '<html lang="zh-CN">',
            "<head>",
            '    <meta charset="UTF-8">',
            '    <meta name="viewport" content="width=device-width, initial-scale=1.0">',
            f"    <title>{analysis.title}</title>",
            '    <link href="https://fonts.googleapis.com/css2?family=Inter:wght@300;400;500;600;700&family=Noto+Sans+SC:wght@300;400;500;700;900&display=swap" rel="stylesheet">',
            '    <link rel="stylesheet" href="https://cdnjs.cloudflare.com/ajax/libs/highlight.js/11.9.0/styles/github.min.css">',
            '    <script src="https://cdnjs.cloudflare.com/ajax/libs/highlight.js/11.9.0/highlight.min.js"></script>',
            '    <script src="https://unpkg.com/lucide@latest"></script>',
            "    <style>",
            css_styles,
            "    </style>",
            "</head>",
            "<body>",
            "    <!-- 阅读进度条 -->",
            '    <div class="reading-progress-container">',
            '        <div class="reading-progress-bar" id="readingProgress"></div>',
            "    </div>",
            "    ",
            "    <!-- 背景装饰 -->",
            '    <div class="ambient-bg">',
            '        <div class="gradient-orb orb-1"></div>',
            '        <div class="gradient-orb orb-2"></div>',
            '        <div class="gradient-orb orb-3"></div>',
            "    </div>",
            "    ",
            header,
            body,
            footer,
            "    ",
            "    <!-- 悬浮操作按钮 -->",
            '    <div class="floating-actions">',
            '        <button class="fab-btn" onclick="scrollToTop()" title="回到顶部">',
            '            <i data-lucide="chevron-up"></i>',
            "        </button>",
            "    </div>",
            "    ",
            js_scripts,
            "</body>",
            "</html>"
        ]
        
        return "\n".join(template_parts)
    
    def _generate_css_styles(self, colors: Dict, style_config: Dict) -> str:
        """生成现代CSS样式 - 玻璃拟态、渐变、动画"""
        return f"""
        /* ===== 基础变量 ===== */
        :root {{
            --primary: {colors['primary']};
            --secondary: {colors['secondary']};
            --accent: {colors['accent']};
            --background: {colors['background']};
            --text: {colors['text']};
            --light: {colors['light']};
            --shadow: {style_config['shadow']};
            --radius: {style_config['border_radius']};
        }}
        
        /* ===== 重置与基础 ===== */
        * {{
            margin: 0;
            padding: 0;
            box-sizing: border-box;
        }}
        
        body {{
            font-family: {style_config['font_body']}, -apple-system, BlinkMacSystemFont, 'Segoe UI', sans-serif;
            background: linear-gradient(135deg, {colors['background']} 0%, #ffffff 50%, {colors['background']} 100%);
            color: {colors['text']};
            line-height: 1.8;
            min-height: 100vh;
            position: relative;
            overflow-x: hidden;
        }}
        
        /* ===== 阅读进度条 ===== */
        .reading-progress-container {{
            position: fixed;
            top: 0;
            left: 0;
            width: 100%;
            height: 3px;
            background: rgba(0,0,0,0.05);
            z-index: 10000;
        }}
        
        .reading-progress-bar {{
            height: 100%;
            background: linear-gradient(90deg, {colors['primary']}, {colors['secondary']}, {colors['accent']});
            width: 0%;
            transition: width 0.1s ease;
            box-shadow: 0 0 10px {colors['primary']}80;
        }}
        
        /* ===== 环境背景动画 ===== */
        .ambient-bg {{
            position: fixed;
            top: 0;
            left: 0;
            width: 100%;
            height: 100%;
            pointer-events: none;
            z-index: -1;
            overflow: hidden;
        }}
        
        .gradient-orb {{
            position: absolute;
            border-radius: 50%;
            filter: blur(80px);
            opacity: 0.4;
            animation: float 20s infinite ease-in-out;
        }}
        
        .orb-1 {{
            width: 600px;
            height: 600px;
            background: {colors['primary']};
            top: -200px;
            right: -200px;
            animation-delay: 0s;
        }}
        
        .orb-2 {{
            width: 400px;
            height: 400px;
            background: {colors['secondary']};
            bottom: 10%;
            left: -100px;
            animation-delay: -5s;
        }}
        
        .orb-3 {{
            width: 300px;
            height: 300px;
            background: {colors['accent']};
            top: 40%;
            right: 10%;
            animation-delay: -10s;
        }}
        
        @keyframes float {{
            0%, 100% {{ transform: translate(0, 0) scale(1); }}
            25% {{ transform: translate(30px, -30px) scale(1.1); }}
            50% {{ transform: translate(-20px, 20px) scale(0.9); }}
            75% {{ transform: translate(20px, 30px) scale(1.05); }}
        }}
        
        /* ===== 玻璃拟态卡片 ===== */
        .glass-card {{
            background: rgba(255, 255, 255, 0.7);
            backdrop-filter: blur(20px);
            -webkit-backdrop-filter: blur(20px);
            border: 1px solid rgba(255, 255, 255, 0.3);
            border-radius: 24px;
            box-shadow: 
                0 4px 6px -1px rgba(0, 0, 0, 0.05),
                0 10px 15px -3px rgba(0, 0, 0, 0.05),
                0 20px 25px -5px rgba(0, 0, 0, 0.03),
                inset 0 1px 0 rgba(255, 255, 255, 0.6);
        }}
        
        /* ===== 头部样式 ===== */
        .header-content {{
            position: relative;
            z-index: 1;
            max-width: 800px;
            margin: 0 auto;
            text-align: center;
            color: var(--text);
        }}
        
        .topic-badge {{
            display: inline-block;
            padding: 4px 12px;
            background: var(--light);
            border: 1px solid var(--primary);
            color: var(--primary);
            border-radius: 4px;
            font-size: 11px;
            font-weight: 600;
            letter-spacing: 1px;
            text-transform: uppercase;
            margin-bottom: 16px;
        }}
        
        .article-title {{
            font-size: 36px;
            font-weight: 800;
            line-height: 1.3;
            margin-bottom: 16px;
            color: var(--primary);
            letter-spacing: -0.01em;
        }}
        
        .article-meta {{
            display: flex;
            align-items: center;
            justify-content: center;
            gap: 20px;
            font-size: 13px;
            color: #6b7280;
        }}
        
        /* ===== 内容区域 ===== */
        .content-wrapper {{
            max-width: 800px;
            margin: 0 auto;
            padding: 0 24px 80px;
            position: relative;
            z-index: 1;
        }}
        
        .content-body {{
            padding: 48px;
        }}
        
        /* ===== 排版样式 ===== */
        .content-body h1 {{
            font-size: 32px;
            font-weight: 700;
            margin: 48px 0 24px;
            color: {colors['primary']};
            position: relative;
            padding-bottom: 16px;
        }}
        
        .content-body h1::after {{
            content: '';
            position: absolute;
            bottom: 0;
            left: 0;
            width: 60px;
            height: 4px;
            background: linear-gradient(90deg, {colors['primary']}, {colors['accent']});
            border-radius: 2px;
        }}
        
        .content-body h2 {{
            font-size: 26px;
            font-weight: 600;
            margin: 40px 0 20px;
            color: {colors['text']};
            display: flex;
            align-items: center;
            gap: 12px;
        }}
        
        .content-body h2::before {{
            content: '';
            width: 4px;
            height: 24px;
            background: linear-gradient(180deg, {colors['primary']}, {colors['secondary']});
            border-radius: 2px;
        }}
        
        .content-body h3 {{
            font-size: 22px;
            font-weight: 600;
            margin: 32px 0 16px;
            color: {colors['text']};
        }}
        
        .content-body p {{
            font-size: 17px;
            line-height: 1.9;
            margin: 20px 0;
            color: #374151;
            text-align: justify;
        }}
        
        /* ===== 段落首字下沉（已禁用，保持阅读流畅性） ===== */
        /* .content-body p:first-of-type::first-letter {{
            font-size: 56px;
            font-weight: 700;
            float: left;
            line-height: 1;
            margin-right: 12px;
            margin-top: 8px;
            color: {colors['primary']};
            text-shadow: 2px 2px 0 {colors['light']};
        }} */
        
        /* ===== 列表样式 ===== */
        .content-body ul, .content-body ol {{
            margin: 24px 0;
            padding-left: 0;
            list-style: none;
        }}
        
        .content-body li {{
            position: relative;
            padding-left: 32px;
            margin: 12px 0;
            font-size: 16px;
            line-height: 1.8;
        }}
        
        .content-body ul li::before {{
            content: '';
            position: absolute;
            left: 0;
            top: 10px;
            width: 8px;
            height: 8px;
            background: linear-gradient(135deg, {colors['primary']}, {colors['accent']});
            border-radius: 50%;
            box-shadow: 0 0 0 4px {colors['light']};
        }}
        
        .content-body ol {{
            counter-reset: item;
        }}
        
        .content-body ol li {{
            counter-increment: item;
        }}
        
        .content-body ol li::before {{
            content: counter(item);
            position: absolute;
            left: 0;
            top: 2px;
            width: 24px;
            height: 24px;
            background: linear-gradient(135deg, {colors['primary']}, {colors['secondary']});
            color: white;
            border-radius: 50%;
            font-size: 12px;
            font-weight: 600;
            display: flex;
            align-items: center;
            justify-content: center;
        }}
        
        /* ===== 引用块 ===== */
        .content-body blockquote {{
            margin: 32px 0;
            padding: 24px 32px;
            background: linear-gradient(135deg, {colors['background']}, #ffffff);
            border-left: 4px solid {colors['primary']};
            border-radius: 0 16px 16px 0;
            font-style: italic;
            position: relative;
        }}
        
        .content-body blockquote::before {{
            content: '"';
            position: absolute;
            top: -10px;
            left: 16px;
            font-size: 60px;
            color: {colors['primary']};
            opacity: 0.2;
            font-family: Georgia, serif;
        }}
        
        .content-body blockquote p {{
            margin: 0;
            font-size: 18px;
            color: #4b5563;
        }}
        
        /* ===== 表格样式 ===== */
        .content-body table {{
            width: 100%;
            border-collapse: separate;
            border-spacing: 0;
            margin: 32px 0;
            border-radius: 16px;
            overflow: hidden;
            box-shadow: 0 4px 6px -1px rgba(0, 0, 0, 0.05);
        }}
        
        .content-body th {{
            background: linear-gradient(135deg, {colors['primary']}, {colors['secondary']});
            color: white;
            padding: 16px;
            font-weight: 600;
            text-align: left;
            font-size: 14px;
            letter-spacing: 0.5px;
        }}
        
        .content-body td {{
            padding: 16px;
            border-bottom: 1px solid #e5e7eb;
            font-size: 15px;
        }}
        
        .content-body tr:nth-child(even) {{
            background: {colors['background']};
        }}
        
        .content-body tr:hover {{
            background: rgba({colors['primary'].replace('#', '')}, 0.05);
        }}
        
        /* ===== 代码块 ===== */
        .content-body pre {{
            background: #1f2937;
            border-radius: 16px;
            padding: 24px;
            margin: 24px 0;
            overflow-x: auto;
            position: relative;
        }}
        
        .content-body pre::before {{
            content: '';
            position: absolute;
            top: 12px;
            left: 16px;
            width: 12px;
            height: 12px;
            background: #ff5f56;
            border-radius: 50%;
            box-shadow: 20px 0 0 #ffbd2e, 40px 0 0 #27ca40;
        }}
        
        .content-body code {{
            font-family: 'Fira Code', 'Consolas', monospace;
            font-size: 14px;
        }}
        
        .content-body pre code {{
            display: block;
            padding-top: 20px;
            color: #e5e7eb;
            line-height: 1.6;
        }}
        
        .content-body p code {{
            background: {colors['background']};
            padding: 2px 8px;
            border-radius: 4px;
            color: {colors['primary']};
            font-size: 14px;
        }}
        
        /* ===== 图片样式 ===== */
        .content-body img {{
            max-width: 100%;
            border-radius: 16px;
            margin: 32px 0;
            box-shadow: 0 20px 25px -5px rgba(0, 0, 0, 0.1);
            transition: all 0.3s ease;
            cursor: zoom-in;
        }}
        
        .content-body img:hover {{
            transform: translateY(-4px);
            box-shadow: 0 25px 50px -12px rgba(0, 0, 0, 0.15);
        }}
        
        .content-body img.expanded {{
            position: fixed;
            top: 50%;
            left: 50%;
            transform: translate(-50%, -50%);
            max-width: 90vw;
            max-height: 90vh;
            z-index: 10000;
            cursor: zoom-out;
        }}
        
        /* ===== 强调样式 - 优化重点词显示 ===== */
        .content-body strong {{
            color: {colors['primary']};
            font-weight: 700;
            background: linear-gradient(180deg, transparent 60%, {colors['light']} 60%);
            padding: 0 4px;
            border-radius: 3px;
        }}
        
        .content-body em {{
            color: {colors['secondary']};
            font-style: italic;
        }}
        
        /* ===== 重点标记样式（可用于人物、事件、时间等） ===== */
        .content-body .highlight {{
            background: linear-gradient(135deg, {colors['light']}, #ffffff);
            border-left: 3px solid {colors['primary']};
            padding: 2px 8px;
            border-radius: 0 4px 4px 0;
            font-weight: 600;
        }}
        
        /* ===== 分隔线 ===== */
        .content-body hr {{
            border: none;
            height: 2px;
            background: linear-gradient(90deg, transparent, {colors['light']}, transparent);
            margin: 48px 0;
        }}
        
        /* ===== 底部样式 ===== */
        .article-footer {{
            text-align: center;
            padding: 48px 24px;
            background: linear-gradient(180deg, transparent, {colors['background']});
            margin-top: 60px;
        }}
        
        .footer-content {{
            max-width: 800px;
            margin: 0 auto;
        }}
        
        .footer-badge {{
            display: inline-flex;
            align-items: center;
            gap: 8px;
            padding: 12px 24px;
            background: white;
            border-radius: 50px;
            box-shadow: 0 4px 15px rgba(0,0,0,0.08);
            font-size: 14px;
            color: {colors['text']};
        }}
        
        .footer-decoration {{
            margin-top: 32px;
        }}
        
        /* ===== 悬浮按钮 ===== */
        .floating-actions {{
            position: fixed;
            bottom: 32px;
            right: 32px;
            z-index: 1000;
        }}
        
        .fab-btn {{
            width: 56px;
            height: 56px;
            border-radius: 50%;
            background: linear-gradient(135deg, {colors['primary']}, {colors['secondary']});
            border: none;
            color: white;
            cursor: pointer;
            box-shadow: 0 4px 15px rgba(0,0,0,0.2);
            transition: all 0.3s ease;
            display: flex;
            align-items: center;
            justify-content: center;
        }}
        
        .fab-btn:hover {{
            transform: translateY(-4px) scale(1.05);
            box-shadow: 0 8px 25px rgba(0,0,0,0.25);
        }}
        
        .fab-btn svg {{
            width: 24px;
            height: 24px;
        }}
        
        /* ===== 响应式 ===== */
        @media (max-width: 768px) {{
            .article-title {{
                font-size: 28px;
            }}
            
            .content-body {{
                padding: 32px 24px;
            }}
            
            .content-body h1 {{
                font-size: 24px;
            }}
            
            .content-body h2 {{
                font-size: 20px;
            }}
            
            .content-body p {{
                font-size: 16px;
            }}
            
            .floating-actions {{
                bottom: 20px;
                right: 20px;
            }}
            
            .fab-btn {{
                width: 48px;
                height: 48px;
            }}
        }}
        
        /* ===== 滚动条美化 ===== */
        ::-webkit-scrollbar {{
            width: 8px;
        }}
        
        ::-webkit-scrollbar-track {{
            background: #f1f1f1;
        }}
        
        ::-webkit-scrollbar-thumb {{
            background: linear-gradient(180deg, {colors['primary']}, {colors['secondary']});
            border-radius: 4px;
        }}
        
        ::-webkit-scrollbar-thumb:hover {{
            background: linear-gradient(180deg, {colors['secondary']}, {colors['primary']});
        }}
"""
    
    def _generate_header(self, analysis: ContentAnalysis, colors: Dict, style_config: Dict) -> str:
        """生成头部 - 极简主义设计"""
        
        # 获取当前日期
        from datetime import datetime
        current_date = datetime.now().strftime("%Y年%m月%d日")
        
        header_html = f"""
    <header class="article-header" style="padding: 60px 24px 40px; text-align: center;">
        <div class="header-content">
            <div class="topic-badge">{analysis.topic or '精选内容'}</div>
            <h1 class="article-title">{analysis.title}</h1>
            <div class="article-meta">
                <span><i data-lucide="calendar" style="width: 14px; height: 14px; vertical-align: middle; margin-right: 4px;"></i> {current_date}</span>
                <span><i data-lucide="clock" style="width: 14px; height: 14px; vertical-align: middle; margin-right: 4px;"></i> 预期阅读 {max(3, analysis.word_count // 500)} 分钟</span>
            </div>
        </div>
    </header>"""
        
        return header_html
    
    def _generate_header_svg(self, colors: Dict, decoration_type: str) -> str:
        """生成头部SVG装饰"""
        if decoration_type == 'geometric':
            return f"""
            <svg style="position: absolute; top: 10%; right: 5%; opacity: 0.15;" width="200" height="200" viewBox="0 0 200 200">
                <defs>
                    <linearGradient id="geoGrad" x1="0%" y1="0%" x2="100%" y2="100%">
                        <stop offset="0%" style="stop-color:white;stop-opacity:1" />
                        <stop offset="100%" style="stop-color:white;stop-opacity:0.5" />
                    </linearGradient>
                </defs>
                <circle cx="100" cy="100" r="80" fill="none" stroke="url(#geoGrad)" stroke-width="1">
                    <animateTransform attributeName="transform" type="rotate" from="0 100 100" to="360 100 100" dur="30s" repeatCount="indefinite"/>
                </circle>
                <circle cx="100" cy="100" r="50" fill="none" stroke="url(#geoGrad)" stroke-width="1">
                    <animateTransform attributeName="transform" type="rotate" from="360 100 100" to="0 100 100" dur="20s" repeatCount="indefinite"/>
                </circle>
                <circle cx="100" cy="100" r="20" fill="white" opacity="0.3">
                    <animate attributeName="r" values="20;25;20" dur="3s" repeatCount="indefinite"/>
                </circle>
            </svg>"""
        elif decoration_type == 'organic':
            return f"""
            <svg style="position: absolute; bottom: 0; left: 0; width: 100%; height: 80px;" viewBox="0 0 1200 80" preserveAspectRatio="none">
                <defs>
                    <linearGradient id="waveGrad" x1="0%" y1="0%" x2="0%" y2="100%">
                        <stop offset="0%" style="stop-color:white;stop-opacity:0.3" />
                        <stop offset="100%" style="stop-color:white;stop-opacity:0" />
                    </linearGradient>
                </defs>
                <path d="M0,40 Q150,80 300,40 T600,40 T900,40 T1200,40 L1200,80 L0,80 Z" fill="url(#waveGrad)">
                    <animate attributeName="d" 
                        values="M0,40 Q150,80 300,40 T600,40 T900,40 T1200,40 L1200,80 L0,80 Z;
                                M0,40 Q150,20 300,40 T600,40 T900,40 T1200,40 L1200,80 L0,80 Z;
                                M0,40 Q150,80 300,40 T600,40 T900,40 T1200,40 L1200,80 L0,80 Z"
                        dur="6s" repeatCount="indefinite"/>
                </path>
                <path d="M0,60 Q300,20 600,60 T1200,60 L1200,80 L0,80 Z" fill="url(#waveGrad)" opacity="0.5">
                    <animate attributeName="d" 
                        values="M0,60 Q300,20 600,60 T1200,60 L1200,80 L0,80 Z;
                                M0,60 Q300,80 600,60 T1200,60 L1200,80 L0,80 Z;
                                M0,60 Q300,20 600,60 T1200,60 L1200,80 L0,80 Z"
                        dur="8s" repeatCount="indefinite"/>
                </path>
            </svg>"""
        else:  # minimal
            return f"""
            <svg style="position: absolute; bottom: 0; right: 10%; opacity: 0.1;" width="300" height="150" viewBox="0 0 300 150">
                <circle cx="250" cy="50" r="100" fill="white"/>
                <circle cx="50" cy="100" r="60" fill="white"/>
            </svg>"""
    
    def _generate_body(self, analysis: ContentAnalysis, colors: Dict, style_config: Dict) -> str:
        """生成主体内容区 - 玻璃拟态设计"""
        
        # 生成关键词标签
        keyword_tags = ""
        if analysis.keywords:
            for kw in analysis.keywords[:5]:
                keyword_tags += f'<span class="keyword-tag">{kw}</span>'
        
        content_placeholder = f"""
    <main class="content-wrapper">
        <article class="glass-card content-body">
            {{content}}
        </article>
        
        <!-- 关键词标签 -->
        <div class="keywords-section" style="margin-top: 32px; padding: 0 24px;">
            <div style="display: flex; flex-wrap: wrap; gap: 10px; justify-content: center;">
                {keyword_tags}
            </div>
        </div>
    </main>"""
        
        return content_placeholder
    
    def _generate_footer(self, analysis: ContentAnalysis, colors: Dict, style_config: Dict) -> str:
        """生成底部 - 现代设计"""
        
        # 生成动态装饰SVG
        footer_animation = f"""
        <div class="footer-decoration">
            <svg width="240" height="60" viewBox="0 0 240 60" style="display: block; margin: 0 auto;">
                <defs>
                    <linearGradient id="dotGrad" x1="0%" y1="0%" x2="100%" y2="0%">
                        <stop offset="0%" style="stop-color:{colors['primary']}" />
                        <stop offset="50%" style="stop-color:{colors['secondary']}" />
                        <stop offset="100%" style="stop-color:{colors['accent']}" />
                    </linearGradient>
                </defs>
                <circle cx="30" cy="30" r="5" fill="url(#dotGrad)" opacity="0.8">
                    <animate attributeName="cy" values="30;20;30" dur="2s" repeatCount="indefinite"/>
                    <animate attributeName="opacity" values="0.8;0.4;0.8" dur="2s" repeatCount="indefinite"/>
                </circle>
                <circle cx="75" cy="30" r="5" fill="url(#dotGrad)" opacity="0.7">
                    <animate attributeName="cy" values="30;15;30" dur="2s" begin="0.2s" repeatCount="indefinite"/>
                    <animate attributeName="opacity" values="0.7;0.3;0.7" dur="2s" begin="0.2s" repeatCount="indefinite"/>
                </circle>
                <circle cx="120" cy="30" r="6" fill="url(#dotGrad)" opacity="1">
                    <animate attributeName="cy" values="30;10;30" dur="2s" begin="0.4s" repeatCount="indefinite"/>
                    <animate attributeName="r" values="6;8;6" dur="2s" begin="0.4s" repeatCount="indefinite"/>
                </circle>
                <circle cx="165" cy="30" r="5" fill="url(#dotGrad)" opacity="0.7">
                    <animate attributeName="cy" values="30;15;30" dur="2s" begin="0.6s" repeatCount="indefinite"/>
                    <animate attributeName="opacity" values="0.7;0.3;0.7" dur="2s" begin="0.6s" repeatCount="indefinite"/>
                </circle>
                <circle cx="210" cy="30" r="5" fill="url(#dotGrad)" opacity="0.8">
                    <animate attributeName="cy" values="30;20;30" dur="2s" begin="0.8s" repeatCount="indefinite"/>
                    <animate attributeName="opacity" values="0.8;0.4;0.8" dur="2s" begin="0.8s" repeatCount="indefinite"/>
                </circle>
            </svg>
        </div>"""
        
        footer_html = f"""
    <footer class="article-footer">
        <div class="footer-content">
            <div class="footer-badge">
                <i data-lucide="sparkles" style="width: 16px; height: 16px; color: {colors['primary']};"></i>
                <span>由 <strong style="color: {colors['primary']};">AIWriteX</strong> 智能生成</span>
            </div>
            {footer_animation}
        </div>
    </footer>
    
    <!-- 关键词标签样式 -->
    <style>
        .keyword-tag {{
            display: inline-block;
            padding: 6px 16px;
            background: linear-gradient(135deg, {colors['background']}, #ffffff);
            border: 1px solid {colors['light']};
            border-radius: 20px;
            font-size: 13px;
            color: {colors['text']};
            transition: all 0.3s ease;
            cursor: default;
        }}
        .keyword-tag:hover {{
            transform: translateY(-2px);
            box-shadow: 0 4px 12px rgba(0,0,0,0.1);
            border-color: {colors['primary']};
        }}
    </style>"""
        
        return footer_html
    
    def _dict_to_style(self, style_dict: Dict) -> str:
        """将字典转换为CSS样式字符串"""
        return "; ".join(f"{k.replace('_', '-')}: {v}" for k, v in style_dict.items())
    
    def generate_template_with_content(self, title: str, content: str, topic: str = "") -> str:
        """根据内容生成完整模板"""
        # 分析内容
        analysis = self.analyze_content(title, content, topic)
        
        log.print_log(f"[模板生成] 检测到风格: {analysis.recommended_style.value}, 配色: {analysis.recommended_colors.name}")
        log.print_log(f"[模板生成] 关键词: {', '.join(analysis.keywords[:5])}")
        
        # 生成模板
        template = self.generate_template(analysis)
        
        # 将内容填充到模板中
        # 这里需要将markdown内容转换为HTML并适配模板样式
        formatted_content = self._format_content_for_template(content, analysis)
        
        final_html = template.replace("{content}", formatted_content)
        
        return final_html
    
    def _format_content_for_template(self, content: str, analysis: ContentAnalysis) -> str:
        """将内容格式化为模板样式 - 智能Markdown解析"""
        colors = analysis.recommended_colors.value
        
        # 首先将标题单独成行（处理标题后直接跟内容的情况）
        content = re.sub(r'^(#{1,6}\s.+?)\n(?=[^#\n])', r'\1\n\n', content, flags=re.MULTILINE)
        
        # 处理代码块
        content = self._process_code_blocks(content)
        
        # 处理引用块
        content = self._process_blockquotes(content)
        
        # 处理表格
        content = self._process_tables(content)
        
        # 处理分隔线
        content = re.sub(r'\n---\n', '\n<hr>\n', content)
        content = re.sub(r'\n\*\*\*\n', '\n<hr>\n', content)
        
        # 处理图片
        content = self._process_images(content, colors)
        
        # 处理链接
        content = self._process_links(content, colors)
        
        # 处理加粗和斜体
        content = re.sub(r'\*\*\*(.+?)\*\*\*', r'<strong><em>\1</em></strong>', content)
        content = re.sub(r'\*\*(.+?)\*\*', r'<strong>\1</strong>', content)
        content = re.sub(r'\*(.+?)\*', r'<em>\1</em>', content)
        content = re.sub(r'_(.+?)_', r'<em>\1</em>', content)
        
        # 处理行内代码
        content = re.sub(r'`([^`]+)`', r'<code>\1</code>', content)
        
        # 按段落处理
        paragraphs = content.split('\n\n')
        formatted_paragraphs = []
        in_list = False
        list_items = []
        list_type = 'ul'
        
        for para in paragraphs:
            para = para.strip()
            if not para:
                continue
            
            # 检测标题（多行标题只取第一行）
            if para.startswith('#'):
                # 先结束任何未结束的列表
                if in_list:
                    formatted_paragraphs.append(self._close_list(list_items, list_type))
                    in_list = False
                    list_items = []
                
                # 分割标题和后面的内容
                lines = para.split('\n', 1)
                header_line = lines[0]
                level = len(header_line) - len(header_line.lstrip('#'))
                text = header_line.lstrip('#').strip()
                
                # 修复 Markdown 泄漏: 移除标题内部的 ** 或 * 语法
                # 同时也移除可能已经被替换的 HTML 标签，确保标题纯净
                text = re.sub(r'</?strong>', '', text)
                text = re.sub(r'</?em>', '', text)
                text = text.replace('**', '').replace('*', '').replace('_', '')
                
                formatted_paragraphs.append(f'<h{level}>{text}</h{level}>')
                
                # 如果标题后有内容，作为段落处理
                if len(lines) > 1 and lines[1].strip():
                    remaining = lines[1].strip()
                    formatted_paragraphs.append(f'<p>{remaining}</p>')
            
            # 检测无序列表
            elif re.match(r'^[\s]*[-\*•]\s', para):
                if not in_list:
                    in_list = True
                    list_type = 'ul'
                    list_items = []
                
                # 处理列表项，可能包含多行
                items = re.split(r'\n(?=[\s]*[-\*•]\s)', para)
                for item in items:
                    match = re.match(r'^[\s]*[-\*•]\s+(.*)', item, re.DOTALL)
                    if match:
                        item_text = match.group(1).replace('\n', '<br>')
                        list_items.append(item_text)
            
            # 检测有序列表
            elif re.match(r'^[\s]*\d+[.\)]\s', para):
                if not in_list or list_type != 'ol':
                    if in_list:
                        formatted_paragraphs.append(self._close_list(list_items, list_type))
                    in_list = True
                    list_type = 'ol'
                    list_items = []
                
                items = re.split(r'\n(?=[\s]*\d+[.\)]\s)', para)
                for item in items:
                    match = re.match(r'^[\s]*\d+[.\)]\s+(.*)', item, re.DOTALL)
                    if match:
                        item_text = match.group(1).replace('\n', '<br>')
                        list_items.append(item_text)
            
            # 已经处理过的HTML块
            elif para.startswith('<') and not para.startswith('<p'):
                if in_list:
                    formatted_paragraphs.append(self._close_list(list_items, list_type))
                    in_list = False
                    list_items = []
                formatted_paragraphs.append(para)
            
            # 普通段落
            else:
                if in_list:
                    formatted_paragraphs.append(self._close_list(list_items, list_type))
                    in_list = False
                    list_items = []
                
                # 处理段落中的换行
                para = para.replace('\n', '<br>')
                formatted_paragraphs.append(f'<p>{para}</p>')
        
        # 关闭任何未结束的列表
        if in_list:
            formatted_paragraphs.append(self._close_list(list_items, list_type))
        
        return '\n'.join(formatted_paragraphs)
    
    def _close_list(self, items: list, list_type: str) -> str:
        """关闭列表"""
        list_html = ''.join(f'<li>{item}</li>' for item in items)
        return f'<{list_type}>{list_html}</{list_type}>'
    
    def _process_code_blocks(self, content: str) -> str:
        """处理代码块"""
        pattern = r'```(\w+)?\n(.*?)```'
        
        def replace_code_block(match):
            lang = match.group(1) or 'plaintext'
            code = match.group(2).strip()
            # HTML转义
            code = code.replace('&', '&amp;').replace('<', '&lt;').replace('>', '&gt;')
            return f'\n<pre><code class="language-{lang}">{code}</code></pre>\n'
        
        return re.sub(pattern, replace_code_block, content, flags=re.DOTALL)
    
    def _process_blockquotes(self, content: str) -> str:
        """处理引用块"""
        pattern = r'(^>.*$\n?)+'
        
        def replace_blockquote(match):
            quote_text = match.group(0)
            # 移除开头的>和空格
            lines = [line[1:].strip() if line.startswith('>') else line for line in quote_text.split('\n')]
            text = '\n'.join(lines).strip()
            return f'\n<blockquote><p>{text}</p></blockquote>\n'
        
        return re.sub(pattern, replace_blockquote, content, flags=re.MULTILINE)
    
    def _process_tables(self, content: str) -> str:
        """处理表格"""
        pattern = r'\|(.+)\|\n\|[-:\s|]+\|\n((?:\|.+\|\n?)+)'
        
        def replace_table(match):
            header_row = match.group(1)
            body_rows = match.group(2).strip().split('\n')
            
            # 解析表头
            headers = [cell.strip() for cell in header_row.split('|') if cell.strip()]
            header_html = ''.join(f'<th>{h}</th>' for h in headers)
            
            # 解析表体
            rows_html = ''
            for row in body_rows:
                cells = [cell.strip() for cell in row.split('|')[1:-1]]
                row_html = ''.join(f'<td>{c}</td>' for c in cells)
                rows_html += f'<tr>{row_html}</tr>'
            
            return f'\n<table><thead><tr>{header_html}</tr></thead><tbody>{rows_html}</tbody></table>\n'
        
        return re.sub(pattern, replace_table, content)
    
    def _process_images(self, content: str, colors: Dict) -> str:
        """处理图片"""
        # Markdown图片: ![alt](url)
        content = re.sub(
            r'!\[([^\]]*)\]\(([^)]+)\)',
            r'<img src="\2" alt="\1" loading="lazy">',
            content
        )
        return content
    
    def _process_links(self, content: str, colors: Dict) -> str:
        """处理链接"""
        content = re.sub(
            r'\[([^\]]+)\]\(([^)]+)\)',
            r'<a href="\2" target="_blank" rel="noopener noreferrer">\1</a>',
            content
        )
        return content


# 便捷函数
def generate_dynamic_template(title: str, content: str, topic: str = "") -> str:
    """便捷函数：根据内容生成动态模板"""
    generator = DynamicTemplateGenerator()
    return generator.generate_template_with_content(title, content, topic)
