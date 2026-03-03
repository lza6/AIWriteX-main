# -*- coding: utf-8 -*-
"""
自适应模板引擎
根据内容特征动态构建模块化、组件化的HTML模板
"""

import re
import random
import asyncio
from typing import List, Dict, Any, Optional, Tuple
from dataclasses import dataclass, field
from enum import Enum

from src.ai_write_x.utils import log
from src.ai_write_x.utils.llm_service import LLMService


class ComponentType(Enum):
    """组件类型"""
    HERO = "hero"                    # 顶部大图/标题区
    INTRO_CARD = "intro_card"        # 导语卡片（左边框强调）
    CONTENT_SECTION = "content_section"  # 标准内容区块
    QUOTE_CARD = "quote_card"        # 引用卡片（渐变背景）
    DATA_VISUAL = "data_visual"      # 数据可视化
    FEATURE_LIST = "feature_list"    # 特性列表（带图标）
    TIMELINE = "timeline"            # 时间线
    COMPARISON = "comparison"        # 对比卡片
    IMAGE_SECTION = "image_section"  # 图文区域
    STATS_GRID = "stats_grid"        # 统计数据网格
    DIVIDER = "divider"              # 分隔装饰


@dataclass
class ContentBlock:
    """内容块"""
    type: str                          # 类型：heading, paragraph, list, quote, etc.
    content: str                       # 原始内容
    level: int = 0                     # 标题级别
    items: List[str] = field(default_factory=list)  # 列表项
    metadata: Dict[str, Any] = field(default_factory=dict)  # 额外信息


@dataclass
class DesignScheme:
    """设计方案"""
    name: str                          # 方案名称
    primary_color: str                 # 主色
    secondary_color: str               # 辅助色
    accent_color: str                  # 强调色
    bg_color: str                      # 背景色
    text_color: str                    # 文字色
    style_features: List[str] = field(default_factory=list)  # 风格特征


class ContentAnalyzer:
    """内容分析器 - 识别内容特征和适合的组件"""
    
    def analyze(self, content: str) -> List[ContentBlock]:
        """分析内容，提取内容块"""
        blocks = []
        lines = content.split('\n')
        i = 0
        
        while i < len(lines):
            line = lines[i].strip()
            
            # 标题
            if line.startswith('#'):
                level = len(line) - len(line.lstrip('#'))
                text = line.lstrip('#').strip()
                blocks.append(ContentBlock(
                    type='heading',
                    content=text,
                    level=level
                ))
                i += 1
                continue
            
            # 引用块
            if line.startswith('>'):
                quote_lines = []
                while i < len(lines) and lines[i].strip().startswith('>'):
                    quote_lines.append(lines[i].strip()[1:].strip())
                    i += 1
                blocks.append(ContentBlock(
                    type='quote',
                    content='\n'.join(quote_lines)
                ))
                continue
            
            # 无序列表
            if re.match(r'^[-\*•]\s', line):
                items = []
                while i < len(lines) and re.match(r'^[-\*•]\s', lines[i].strip()):
                    items.append(re.sub(r'^[-\*•]\s', '', lines[i].strip()))
                    i += 1
                blocks.append(ContentBlock(
                    type='unordered_list',
                    content='',
                    items=items
                ))
                continue
            
            # 有序列表
            if re.match(r'^\d+[.\)]\s', line):
                items = []
                while i < len(lines) and re.match(r'^\d+[.\)]\s', lines[i].strip()):
                    items.append(re.sub(r'^\d+[.\)]\s', '', lines[i].strip()))
                    i += 1
                blocks.append(ContentBlock(
                    type='ordered_list',
                    content='',
                    items=items
                ))
                continue
            
            # 空行
            if not line:
                i += 1
                continue
            
            # 普通段落（可能包含多行）
            para_lines = [line]
            i += 1
            while i < len(lines) and lines[i].strip() and not lines[i].strip().startswith(('#', '>', '-', '*', '•')):
                para_lines.append(lines[i].strip())
                i += 1
            
            para_text = ' '.join(para_lines)
            if para_text:
                # 检查特殊图像提示标记 (支持 [[V-SCENE:]], [IMG_PROMPT:] 和 [图片解析[:：]])
                img_prompt_match = re.search(r'(?:\[\[V-SCENE:|\[(?:IMG_PROMPT|图片解析)[:：])\s*(.+?)\s*(?:\|\s*([\d\.:]+))?\s*(?:\]\]|\])', para_text)
                img_metadata = {}
                if img_prompt_match:
                    img_metadata['img_prompt'] = img_prompt_match.group(1).strip()
                    img_metadata['aspect_ratio'] = img_prompt_match.group(2).strip() if img_prompt_match.group(2) else "16:9"
                    # 从文本中移除该标记
                    para_text = re.sub(r'(?:\[\[V-SCENE:|\[(?:IMG_PROMPT|图片解析)[:：]).*?(?:\]\]|\])', '', para_text).strip()

                if para_text:
                    # 分析段落特征
                    metadata = self._analyze_paragraph(para_text)
                    metadata.update(img_metadata)
                    blocks.append(ContentBlock(
                        type='paragraph',
                        content=para_text,
                        metadata=metadata
                    ))
                elif img_metadata and blocks:
                    # 如果这行只有标记，则将提示词附着到上一个内容块
                    blocks[-1].metadata.update(img_metadata)
        
        return blocks
    
    def _analyze_paragraph(self, text: str) -> Dict[str, Any]:
        """分析段落特征"""
        metadata = {}
        
        # 是否包含数据/数字
        if re.search(r'\d+[%％亿万千美元元]', text):
            metadata['has_data'] = True
        
        # 是否包含年份/时间
        if re.search(r'20\d{2}年|19\d{2}年|\d{4}[-/]\d{2}', text):
            metadata['has_time'] = True
        
        # 是否包含人名（简单判断）
        if re.search(r'[\u4e00-\u9fa5]{2,4}(?:表示|说|指出|认为)', text):
            metadata['has_quote'] = True
        
        # 段落长度
        metadata['length'] = len(text)
        metadata['is_long'] = len(text) > 100
        
        return metadata
    
    def suggest_components(self, blocks: List[ContentBlock]) -> List[Tuple[ComponentType, ContentBlock]]:
        """为内容块建议组件类型"""
        components = []
        
        # 布局池，用于循环分配不同的排版风格，增加灵活性
        layout_pool = ['card', 'accent', 'glass', 'clean']
        layout_idx = 0
        
        for i, block in enumerate(blocks):
            # 强化逻辑：防止正文第一行重复渲染 HERO (如果它是 H1 且可能又是标题)
            if i == 0 and block.type == 'heading' and block.level == 1:
                # 只有当正文真的需要一个大封面且这个 H1 不是重复的标题时才作为 HERO
                # 在 UnifiedWorkflow 优化后，理论上不该出现，这里做保险
                continue
            
            # 为段落分配随机/循环布局
            if block.type == 'paragraph':
                block.metadata['layout_style'] = layout_pool[layout_idx % len(layout_pool)]
                layout_idx += 1
            
            # 第二个h1或第一个h2作为INTRO_CARD
            if (block.type == 'heading' and block.level <= 2 and i < 3 and 
                not any(c[0] == ComponentType.INTRO_CARD for c in components)):
                components.append((ComponentType.INTRO_CARD, block))
                continue
            
            # 引用块 → 引用卡片
            if block.type == 'quote':
                components.append((ComponentType.QUOTE_CARD, block))
                continue
            
            # 包含数据的段落
            if block.type == 'paragraph' and block.metadata.get('has_data'):
                if block.metadata.get('is_long'):
                    components.append((ComponentType.CONTENT_SECTION, block))
                else:
                    components.append((ComponentType.STATS_GRID, block))
                continue
            
            # 长段落 → 内容区块
            if block.type == 'paragraph' and block.metadata.get('is_long'):
                components.append((ComponentType.CONTENT_SECTION, block))
                continue
            
            # 列表 → 特性列表
            if block.type in ['unordered_list', 'ordered_list']:
                if len(block.items) <= 4:
                    components.append((ComponentType.FEATURE_LIST, block))
                else:
                    components.append((ComponentType.TIMELINE, block))
                continue
            
            # 其他标题 → 内容区块
            if block.type == 'heading':
                components.append((ComponentType.CONTENT_SECTION, block))
                continue
            
            # 默认
            components.append((ComponentType.CONTENT_SECTION, block))
        
        return components


class ModularTemplateBuilder:
    """模块化模板构建器"""
    
    def __init__(self):
        self.design_scheme = self._generate_random_scheme()
        self.design_tokens = {
            "primary": self.design_scheme.primary_color,
            "secondary": self.design_scheme.secondary_color,
            "accent": self.design_scheme.accent_color,
            "bg": self.design_scheme.bg_color,
            "text_color": self.design_scheme.text_color
        }
        self.stage = 1  # 初始 Agent 阶段
    
    def set_design_scheme(self, scheme: DesignScheme):
        """设置设计方案并同步 Tokens"""
        self.design_scheme = scheme
        self.design_tokens = {
            "primary": scheme.primary_color,
            "secondary": scheme.secondary_color,
            "accent": scheme.accent_color,
            "bg": scheme.bg_color,
            "text_color": scheme.text_color
        }
    
    def build_template(self, title: str, components: List[Tuple[ComponentType, ContentBlock]]) -> str:
        """构建完整模板"""
        if not self.design_scheme:
            self.design_scheme = self._generate_random_scheme()
        
        html_parts = []
        
        # HTML头部
        html_parts.append(self._build_head(title))
        
        # 开始body
        html_parts.append(self._build_body_start())
        
        in_timeline = False
        
        # 构建每个组件
        for comp_type, block in components:
            if comp_type == ComponentType.CONTENT_SECTION and not in_timeline:
                html_parts.append('<div class="timeline-container">')
                in_timeline = True
            elif comp_type in [ComponentType.HERO, ComponentType.INTRO_CARD]:
                if in_timeline:
                    html_parts.append('</div>')
                    in_timeline = False
                    
            component_html = self._build_component(comp_type, block)
            html_parts.append(component_html)
            
        if in_timeline:
            html_parts.append('</div>')
            
        # 结尾的footer是特殊的，通常附着在最后一个内容块后面或单独作为一个ContentBlock
        # 这里为了保持结构，由AdaptiveTemplateEngine调度，或者我们在这里寻找footer类型的block
        
        # 结束body和html
        html_parts.append(self._build_body_end())
        
        return '\n'.join(html_parts)
    
    def _generate_random_scheme(self) -> DesignScheme:
        """生成随机设计方案"""
        schemes = [
            DesignScheme("深海蓝", "#3b82f6", "#1e3a8a", "#f59e0b", "#eff6ff", "#334155", ["现代", "交互"]),
            DesignScheme("翠柏绿", "#10b981", "#064e3b", "#f59e0b", "#ecfdf5", "#334155", ["自然", "交互"]),
            DesignScheme("活力橙", "#f97316", "#7c2d12", "#3b82f6", "#fff7ed", "#334155", ["活力", "现代"]),
            DesignScheme("紫水晶", "#8b5cf6", "#4c1d95", "#f59e0b", "#f5f3ff", "#334155", ["优雅", "科技"]),
            DesignScheme("高级灰", "#64748b", "#0f172a", "#3b82f6", "#f8fafc", "#334155", ["商务", "极简"]),
        ]
        return random.choice(schemes)
    
    def _build_head(self, title: str) -> str:
        """构建 HTML 头部和 CSS (核心样式已转为内联)"""
        return f'''<!DOCTYPE html>
<html lang="zh-CN">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>{title}</title>
    <style>
        :root {{
            --primary: {self.design_tokens.get("primary", "#4F46E5")};
            --primary-dark: {self.design_tokens.get("secondary", "#4338CA")};
            --primary-light: {self.design_tokens.get("bg", "#F8FAFC")};
            --accent: {self.design_tokens.get("accent", "#8B5CF6")};
            --text-main: {self.design_tokens.get("text_color", "#334155")};
        }}
        * {{ margin: 0; padding: 0; box-sizing: border-box; }}
        body {{
            font-family: -apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, "Helvetica Neue", Arial, "Noto Sans SC", sans-serif;
            background: #FAFAFA;
            color: var(--text-main);
            line-height: 1.8;
        }}
        .event-card img {{ max-width: 100%; height: auto; border-radius: 8px; margin: 16px 0; }}
        blockquote {{ margin: 20px 0; padding: 15px 20px; background: #f8fafc; border-left: 4px solid var(--primary); color: #475569; }}
    </style>
</head>'''

    def _build_footer(self, block: ContentBlock) -> str:
        """构建底部卡片"""
        icon_svg = self._get_svg_icon("book-open", 24, self.design_scheme.primary_color)
        return f'''
    <!-- 结语卡片 -->
    <footer class="footer-card" style="background: linear-gradient(to right, #ffffff, {self.design_scheme.bg_color}); border-radius: 16px; padding: 35px; margin-top: 50px; text-align: center; box-shadow: 0 10px 25px rgba(0,0,0,0.04); border-left: 5px solid {self.design_scheme.primary_color}; border: 1px solid rgba(255,255,255,0.5);">
        <h3 style="color: {self.design_scheme.secondary_color}; margin-bottom: 15px; display: flex; align-items: center; justify-content: center; gap: 10px;">{icon_svg} 探索与启示</h3>
        <p style="color: {self.design_scheme.text_color}; line-height: 1.8;">{self._format_inline_styles(block.content)}</p>
    </footer>'''
    
    def _build_body_start(self) -> str:
        """构建body开始"""
        return '<body>'
    
    def _build_body_end(self) -> str:
        """构建body结束"""
        return '</body>\n</html>'
    
    def _build_component(self, comp_type: ComponentType, block: ContentBlock) -> str:
        """构建单个组件"""
        builders = {
            ComponentType.HERO: self._build_hero,
            ComponentType.INTRO_CARD: self._build_intro_card,
            ComponentType.CONTENT_SECTION: self._build_content_section,
            ComponentType.QUOTE_CARD: self._build_quote_card,
            ComponentType.FEATURE_LIST: self._build_feature_list,
            ComponentType.TIMELINE: self._build_content_section,
            ComponentType.STATS_GRID: self._build_content_section,
        }
        
        builder = builders.get(comp_type, self._build_content_section)
        return builder(block)
    
    def _get_background_ornament(self, ornament_type: str = "dots") -> str:
        """获取背景装饰 SVG"""
        if ornament_type == "dots":
            return f'''<svg width="100" height="100" viewBox="0 0 100 100" style="position: absolute; top: 0; right: 0; opacity: 0.1; pointer-events: none;"><defs><pattern id="dots" x="0" y="0" width="20" height="20" patternUnits="userSpaceOnUse"><circle cx="2" cy="2" r="1" fill="white" /></pattern></defs><rect width="100" height="100" fill="url(#dots)" /></svg>'''
        elif ornament_type == "waves":
            return f'''<svg width="100%" height="60" viewBox="0 0 1000 60" preserveAspectRatio="none" style="position: absolute; bottom: 0; left: 0; opacity: 0.15; pointer-events: none;"><path d="M0,30 C150,60 350,0 500,30 C650,60 850,0 1000,30 L1000,60 L0,60 Z" fill="white"></path></svg>'''
        elif ornament_type == "circles":
            return f'''<svg width="200" height="200" viewBox="0 0 200 200" style="position: absolute; top: -50px; left: -50px; opacity: 0.05; pointer-events: none;"><circle cx="100" cy="100" r="80" stroke="white" stroke-width="20" fill="none" /><circle cx="100" cy="100" r="40" stroke="white" stroke-width="10" fill="none" /></svg>'''
        return ""

    def _get_svg_icon(self, icon_name: str, size: int = 24, color: str = "currentColor") -> str:
        """获取原生 SVG 图标代码 (扩展版)"""
        icons = {
            "terminal": f'<svg width="{size}" height="{size}" viewBox="0 0 24 24" fill="none" stroke="{color}" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><polyline points="4 17 10 11 4 5"/><line x1="12" y1="19" x2="20" y2="19"/></svg>',
            "brush": f'<svg width="{size}" height="{size}" viewBox="0 0 24 24" fill="none" stroke="{color}" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><path d="m9.06 11.9 8.07-8.06a2.85 2.85 0 1 1 4.03 4.03l-8.06 8.08"></path><path d="M7.07 14.94c-1.66 0-3 1.35-3 3.02 0 1.33-2.5 1.52-2 3.5a4.5 4.5 0 0 0 9 0c0-1.66-1.34-3-3-3.02Z"></path></svg>',
            "globe": f'<svg width="{size}" height="{size}" viewBox="0 0 24 24" fill="none" stroke="{color}" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><circle cx="12" cy="12" r="10"></circle><line x1="2" y1="12" x2="22" y2="12"></line><path d="M12 2a15.3 15.3 0 0 1 4 10 15.3 15.3 0 0 1-4 10 15.3 15.3 0 0 1-4-10 15.3 15.3 0 0 1 4-10z"></path></svg>',
            "chip": f'<svg width="{size}" height="{size}" viewBox="0 0 24 24" fill="none" stroke="{color}" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><rect x="4" y="4" width="16" height="16" rx="2"/><path d="M9 9h6v6H9z"/><path d="M15 2v2"/><path d="M15 20v2"/><path d="M9 2v2"/><path d="M9 20v2"/><path d="M22 15h-2"/><path d="M4 15H2"/><path d="M22 9h-2"/><path d="M4 9H2"/></svg>',
            "leaf": f'<svg width="{size}" height="{size}" viewBox="0 0 24 24" fill="none" stroke="{color}" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><path d="M11 20A7 7 0 0 1 9.8 6.1C15.5 5 17 4.48 19 2c1 2 2 4.18 2 8 0 5.5-4.78 10-10 10Z"></path><path d="M2 21c0-3 1.85-5.36 5.08-6C9.5 14.52 12 13 13 12"></path></svg>',
            "sparkles": f'<svg width="{size}" height="{size}" viewBox="0 0 24 24" fill="none" stroke="{color}" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><path d="m12 3-1.912 5.813a2 2 0 0 1-1.275 1.275L3 12l5.813 1.912a2 2 0 0 1 1.275 1.275L12 21l1.912-5.813a2 2 0 0 1 1.275-1.275L21 12l-5.813-1.912a2 2 0 0 1-1.275-1.275L12 3Z"></path><path d="M5 3v4"></path><path d="M19 17v4"></path><path d="M3 5h4"></path><path d="M17 19h4"></path></svg>',
            "compass": f'<svg width="{size}" height="{size}" viewBox="0 0 24 24" fill="none" stroke="{color}" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><circle cx="12" cy="12" r="10"/><polygon points="16.24 7.76 14.12 14.12 7.76 16.24 9.88 9.88 16.24 7.76"/></svg>',
            "rocket": f'<svg width="{size}" height="{size}" viewBox="0 0 24 24" fill="none" stroke="{color}" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><path d="M4.5 16.5c-1.5 1.26-2 5-2 5s3.74-.5 5-2c.71-.84.7-2.13-.09-2.91a2.18 2.18 0 0 0-2.91-.09z"/><path d="m12 15-3-3a22 22 0 0 1 2-3.95A12.88 12.88 0 0 1 22 2c0 2.72-.78 7.5-6 11a22.35 22.35 0 0 1-4 2z"/></svg>',
            "landmark": f'<svg width="{size}" height="{size}" viewBox="0 0 24 24" fill="none" stroke="{color}" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><line x1="3" y1="22" x2="21" y2="22"/><line x1="6" y1="18" x2="6" y2="11"/><line x1="10" y1="18" x2="10" y2="11"/><line x1="14" y1="18" x2="14" y2="11"/><line x1="18" y1="18" x2="18" y2="11"/><polygon points="12 2 20 7 4 7 12 2"/></svg>',
            "users": f'<svg width="{size}" height="{size}" viewBox="0 0 24 24" fill="none" stroke="{color}" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><path d="M16 21v-2a4 4 0 0 0-4-4H6a4 4 0 0 0-4 4v2"/><circle cx="9" cy="7" r="4"/><path d="M22 21v-2a4 4 0 0 0-3-3.87"/><path d="M16 3.13a4 4 0 0 1 0 7.75"/></svg>',
            "star": f'<svg width="{size}" height="{size}" viewBox="0 0 24 24" fill="none" stroke="{color}" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><polygon points="12 2 15.09 8.26 22 9.27 17 14.14 18.18 21.02 12 17.77 5.82 21.02 7 14.14 2 9.27 8.91 8.26 12 2"/></svg>',
            "image": f'<svg width="{size}" height="{size}" viewBox="0 0 24 24" fill="none" stroke="{color}" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><rect x="3" y="3" width="18" height="18" rx="2" ry="2"/><circle cx="8.5" cy="8.5" r="1.5"/><polyline points="21 15 16 10 5 21"/></svg>',
            "book": f'<svg width="{size}" height="{size}" viewBox="0 0 24 24" fill="none" stroke="{color}" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><path d="M4 19.5A2.5 2.5 0 0 1 6.5 17H20"/><path d="M6.5 2H20v20H6.5A2.5 2.5 0 0 1 4 19.5v-15A2.5 2.5 0 0 1 6.5 2z"/></svg>',
            "lantern": f'<svg width="{size}" height="{size}" viewBox="0 0 24 24" fill="none" stroke="{color}" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><path d="M12 2v2"/><path d="M7 22h10"/><path d="M9 4h6a2 2 0 0 1 2 2v12a2 2 0 0 1-2 2H9a2 2 0 0 1-2-2V6a2 2 0 0 1 2-2z"/><path d="M12 10v4"/><path d="M8 7h8"/><path d="M8 17h8"/></svg>',
            "calendar": f'<svg width="{size}" height="{size}" viewBox="0 0 24 24" fill="none" stroke="{color}" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><rect x="3" y="4" width="18" height="18" rx="2" ry="2"/><line x1="16" y1="2" x2="16" y2="6"/><line x1="8" y1="2" x2="8" y2="6"/><line x1="3" y1="10" x2="21" y2="10"/></svg>',
            "quote": f'<svg width="{size}" height="{size}" viewBox="0 0 24 24" fill="none" stroke="{color}" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><path d="M3 21c3 0 7-1 7-8V5c0-1.25-.756-2.017-2-2H4c-1.25 0-2 .75-2 1.972V11c0 1.25.75 2 2 2 1 0 1 0 1 1v1c0 2.5 1 4.066 2 5V21zm14 0c3 0 7-1 7-8V5c0-1.25-.756-2.017-2-2h-4c-1.25 0-2 .75-2 1.972V11c0 1.25.75 2 2 2 1 0 1 0 1 1v1c0 2.5 1 4.066 2 5V21z"/></svg>',
            "book-open": f'<svg width="{size}" height="{size}" viewBox="0 0 24 24" fill="none" stroke="{color}" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><path d="M2 3h6a4 4 0 0 1 4 4v14a3 3 0 0 0-3-3H2z"/><path d="M22 3h-6a4 4 0 0 0-4 4v14a3 3 0 0 1 3-3h7z"/></svg>'
        }
        return icons.get(icon_name, icons.get("sparkles"))

    def _get_icon_for_heading(self, text: str) -> str:
        text = text.lower()
        if any(w in text for w in ['元宵', '灯', '节', '习俗', '传统']):
            return "lantern"
        if any(w in text for w in ['政治', '国际', '版图', '历史']):
            return "globe"
        if any(w in text for w in ['科技', '探索', '技术', '突破']):
            return "rocket"
        if any(w in text for w in ['文化', '艺术', '文明', '瑰宝']):
            return "landmark"
        if any(w in text for w in ['社会', '民生', '人类', '发展']):
            return "users"
        if any(w in text for w in ['自然', '灾难', '环境', '树']):
            return "leaf"
        icons = ["globe", "rocket", "landmark", "users", "chip", "star", "image", "compass", "book", "terminal"]
        return random.choice(icons)

    def _build_hero(self, block: ContentBlock) -> str:
        """构建顶部英雄区"""
        icon_svg = self._get_svg_icon("compass", 32, "white")
        ornament = self._get_background_ornament("circles")
        return f'''
    <!-- 顶层 Header 区 -->
    <header class="header-section" style="background: linear-gradient(135deg, {self.design_tokens.get("secondary", "#4338CA")} 0%, {self.design_tokens.get("primary", "#4F46E5")} 100%); border-radius: 20px; padding: 40px; color: white; box-shadow: 0 15px 35px rgba(0,0,0,0.04); margin-bottom: 40px; position: relative; overflow: hidden; border: 1px solid rgba(255,255,255,0.1);">
        {ornament}
        <h1 style="font-size: 2.2em; font-weight: 800; margin-bottom: 15px; display: flex; align-items: center; gap: 12px; position: relative; color: white;">{icon_svg} {self._format_inline_styles(block.content)}</h1>
    </header>'''
    
    def _build_intro_card(self, block: ContentBlock) -> str:
        """构建导语卡片"""
        icon_svg = self._get_svg_icon("quote", 40, self.design_tokens.get("accent", "#EAB308"))
        return f'''
    <!-- 核心引用区 -->
    <div class="quote-block" style="background: #ffffff; border-left: 5px solid {self.design_tokens.get("accent", "#EAB308")}; padding: 25px 30px; margin: 40px 0; border-radius: 0 12px 12px 0; box-shadow: 0 8px 20px rgba(0,0,0,0.04); font-size: 1.15em; color: {self.design_tokens.get("text_color", "#334155")}; position: relative; border: 1px solid rgba(0,0,0,0.05);">
        <div style="position: absolute; top: 20px; right: 25px; opacity: 0.15;">{icon_svg}</div>
        {self._format_inline_styles(block.content)}
    </div>'''
    
    def _extract_date_from_text(self, text: str) -> str:
        match = re.search(r'(20\d{2}年|19\d{2}年(?:\d{1,2}月\d{1,2}日)?|18\d{2}年(?:\d{1,2}月\d{1,2}日)?|\d{4}年\d{1,2}月\d{1,2}日|.*?月.*?日)', text)
        if match:
            part = match.group(1)
            # 如果整段是以日期开头，提取更准确
            if text.startswith(part):
                return part
            return match.group(1)
        return ""

    def _build_content_section(self, block: ContentBlock) -> str:
        """构建内容区块/事件卡片"""
        # 深拷贝内容，用于由于图片冲突而进行的清理
        cleaned_content = block.content
        
        if block.type == 'heading':
            icon_name = self._get_icon_for_heading(block.content)
            icon_svg = self._get_svg_icon(icon_name, 24, self.design_tokens["primary"])
            return f'''
        <!-- 章节标题 -->
        <div class="section-title" style="position: relative; margin: 50px 0 25px 0; display: flex; align-items: center; color: {self.design_tokens["secondary"]};">
            <div class="section-icon" style="background: white; padding: 8px; border-radius: 50%; box-shadow: 0 4px 10px rgba(0,0,0,0.1); color: {self.design_tokens["primary"]}; z-index: 2; margin-right: 15px; border: 3px solid {self.design_tokens["bg"]}; display: flex; align-items: center; justify-content: center;">{icon_svg}</div>
            <h2 style="font-size: 1.5em; font-weight: 700;">{block.content}</h2>
        </div>'''
        else:
            date_str = self._extract_date_from_text(block.content)
            cal_svg = self._get_svg_icon("calendar", 16, self.design_tokens["secondary"])
            date_html = f'<div class="date-badge" style="display: inline-flex; align-items: center; gap: 6px; background: {self.design_tokens["bg"]}; color: {self.design_tokens["secondary"]}; padding: 6px 14px; border-radius: 20px; font-weight: 700; font-size: 0.9em; margin-bottom: 12px; letter-spacing: 0.5px;">{cal_svg} {date_str}</div>' if date_str else ''
            
            img_html = ""
            # 检查正文中是否已经包含图片（HTML img 标签、Markdown 图片语法、或图片占位符）
            # 检查正文中是否已经包含图片（HTML img 标签、Markdown 图片语法、或图片占位符）
            has_existing_img = re.search(r'<img\s+[^>]*src=|\!\[.*?\]\(.*?\)|\[(?:IMG_PROMPT|图片解析)[:：]', block.content)
            
            # 如果元数据中显式定义了图片描述，且正文里还没塞图
            if block.metadata.get('img_prompt') and not has_existing_img:
                prompt = block.metadata.get('img_prompt', '').replace('"', "'")
                aspect_ratio = block.metadata.get('aspect_ratio', '16:9')
                padding_top = "56.25%" if aspect_ratio == "16:9" else "75%" if aspect_ratio == "4:3" else "133.3%" if aspect_ratio == "3:4" else "42.5%" if aspect_ratio == "2.35:1" else "56.25%"
                img_svg = self._get_svg_icon("image", 40, self.design_tokens["primary"])
                
                padding_top = "56.25%" if aspect_ratio == "16:9" else "75%" if aspect_ratio == "4:3" else "133.3%" if aspect_ratio == "3:4" else "42.5%" if aspect_ratio == "2.35:1" else "56.25%"
                img_svg = self._get_svg_icon("image", 40, self.design_tokens["primary"])
                
                img_html = f'''
            <div class="img-placeholder" data-img-prompt="{prompt}" data-aspect-ratio="{aspect_ratio}" style="padding-top: {padding_top}; width: calc(100% + 50px); margin-left: -25px; margin-top: -25px; position: relative; overflow: hidden; background: linear-gradient(135deg, {self.design_tokens["bg"]} 0%, {self.design_tokens["bg"]}99 100%); border-bottom: 2px dashed {self.design_tokens["primary"]}22; border-radius: 16px 16px 0 0; margin-bottom: 20px;">
                <div style="position: absolute; top: 0; left: 0; width: 100%; height: 100%; display: flex; flex-direction: column; align-items: center; justify-content: center; padding: 30px;">
                    <div style="position: absolute; top: 15px; right: 15px; background: {self.design_tokens["primary"]}; color: white; padding: 4px 12px; border-radius: 20px; font-size: 11px; font-weight: 700; box-shadow: 0 4px 10px {self.design_tokens["primary"]}44; display: flex; align-items: center; gap: 4px;">
                        <span style="width: 6px; height: 6px; background: white; border-radius: 50%; display: inline-block;"></span>
                        高品质自动配图中
                    </div>
                    <div style="animation: float 3s ease-in-out infinite;">{img_svg}</div>
                    <span style="margin-top: 15px; font-weight: 700; color: {self.design_tokens["secondary"]}; letter-spacing: 1px; font-size: 1.1em;">🎨 AI 视觉引擎正在深度构图...</span>
                    <span style="font-size: 0.8em; color: {self.design_tokens["text_color"]}cc; max-width: 80%; text-align: center; margin-top: 10px; font-style: italic; line-height: 1.5; background: white; padding: 6px 15px; border-radius: 12px; box-shadow: 0 4px 12px rgba(0,0,0,0.03);">
                        <strong>视觉倾向:</strong> {prompt}
                    </span>
                    <div style="margin-top: 15px; display: flex; gap: 6px;">
                        <div style="width: 5px; height: 5px; border-radius: 50%; background: {self.design_tokens["primary"]}; animation: flicker 1s infinite;"></div>
                        <div style="width: 5px; height: 5px; border-radius: 50%; background: {self.design_tokens["primary"]}; animation: flicker 1s infinite 0.2s;"></div>
                        <div style="width: 5px; height: 5px; border-radius: 50%; background: {self.design_tokens["primary"]}; animation: flicker 1s infinite 0.4s;"></div>
                    </div>
                </div>
            </div>'''
            
            # 重要：如果已经生成了卡片顶部的图片(img_html)，则必须从正文中剔除重复的图片标签，防止双倍图像
            if img_html:
                # 剔除 HTML img 标签
                cleaned_content = re.sub(r'<img\s+[^>]*>', '', cleaned_content)
                # 剔除 Markdown 图片语法
                cleaned_content = re.sub(r'\!\[.*?\]\(.*?\)', '', cleaned_content)
                # 剔除系统占位符
                # 剔除系统占位符
                cleaned_content = re.sub(r'\[(?:IMG_PROMPT|图片解析)[:：].*?\]', '', cleaned_content)
            
            # 布局随机化逻辑
            layout_style = block.metadata.get('layout_style', 'card')
            
            if layout_style == 'accent':
                # 风格2: 带侧边强调线的轻量卡片
                return f'''
        <div class="event-accent-box" style="background: {self.design_tokens.get("bg", "#F8FAFC")}33; border-left: 4px solid {self.design_tokens.get("primary", "#4F46E5")}; padding: 20px 25px; margin-bottom: 30px; border-radius: 4px 12px 12px 4px; position: relative;">
            {date_html}
            <div style="font-size: 1.05em; line-height: 1.8; color: {self.design_tokens.get("text_color", "#334155")}; text-align: justify;">{self._format_inline_styles(cleaned_content)}</div>
        </div>'''
            
            elif layout_style == 'glass':
                # 风格3: 极简磨砂质感 (带极细边框)
                return f'''
        <div class="event-glass-card" style="background: rgba(255,255,255,0.7); backdrop-filter: blur(10px); -webkit-backdrop-filter: blur(10px); border: 1px solid rgba(0,0,0,0.05); border-radius: 12px; padding: 25px; margin-bottom: 30px; box-shadow: 0 4px 15px rgba(0,0,0,0.02);">
            {date_html}
            <div style="font-size: 1.05em; line-height: 1.8; color: {self.design_tokens.get("text_color", "#334155")}; text-align: justify;">{self._format_inline_styles(cleaned_content)}</div>
        </div>'''

            elif layout_style == 'clean':
                # 风格4: 纯净文本流 (带图标符号)
                symbol_svg = self._get_svg_icon("sparkles", 14, self.design_tokens.get("primary", "#4F46E5"))
                return f'''
        <div class="event-clean-flow" style="padding: 10px 0; margin-bottom: 30px; position: relative;">
            <div style="display: flex; align-items: center; gap: 8px; margin-bottom: 12px;">{symbol_svg} {date_html}</div>
            <div style="font-size: 1.1em; line-height: 1.9; color: {self.design_tokens.get("text_color", "#334155")}; text-align: justify;">{self._format_inline_styles(cleaned_content)}</div>
        </div>'''

            # 默认风格1: 标准高质感卡片
            return f'''
        <!-- 事件卡片 -->
        <div class="event-card" style="background: white; border-radius: 16px; padding: 25px; margin-bottom: 30px; box-shadow: 0 10px 30px rgba(0,0,0,0.03); border: 1px solid rgba(0,0,0,0.02); position: relative; overflow: hidden;">
            {img_html}
            {date_html}
            <div style="font-size: 1.05em; line-height: 1.8; color: {self.design_tokens.get("text_color", "#334155")}; text-align: justify;">{self._format_inline_styles(cleaned_content)}</div>
        </div>'''

    def _build_quote_card(self, block: ContentBlock) -> str:
        """构建引用卡片（使用quote-block）"""
        return self._build_intro_card(block)
    
    def _build_feature_list(self, block: ContentBlock) -> str:
        """构建特性/列表区块"""
        items_html = ""
        for item in block.items:
            icon_svg = self._get_svg_icon("star", 18, self.design_tokens["primary"])
            items_html += f'''
        <div style="background: #ffffff; border-radius: 12px; padding: 15px 20px; margin-bottom: 15px; box-shadow: 0 2px 8px rgba(0,0,0,0.03); border: 1px solid {self.design_tokens["bg"]}; display: flex; align-items: flex-start; gap: 12px;">
            <div style="margin-top: 4px; flex-shrink: 0;">{icon_svg}</div>
            <div style="font-size: 1.05em; color: {self.design_tokens["text_color"]};">{self._format_inline_styles(item)}</div>
        </div>'''
        return items_html
    
    def _format_inline_styles(self, content: str) -> str:
        """
        增强版行内样式转换 - 根据 self.stage 分阶段处理
        """
        text = content
        stage = getattr(self, 'stage', 1)
        
        # 阶段 1: 基础格式化 (Markdown 转 HTML)
        if stage >= 1:
            # 图片转换
            text = re.sub(r'\!\[(.*?)\]\((.*?)\)', 
                         lambda m: f'<img src="{m.group(2)}" alt="{m.group(1)}" style="max-width: 100%; height: auto; border-radius: 12px; margin: 20px 0; display: block; box-shadow: 0 6px 20px rgba(0,0,0,0.07);">', 
                         text)
            # 基础加粗
            text = re.sub(r'\*\*(.+?)\*\*', r'<strong>\1</strong>', text)
            # 基础斜体
            text = re.sub(r'(?<!\*)\*([^\*]+?)\*(?!\*)', r'<em>\1</em>', text)
            
            # 兼容性高亮处理 (阻止 [KEY:] [HL:] 在 Stage 1/2 以源码形式露脸)
            text = re.sub(r'\[(HL|KEY):\s*(.+?)\s*\]', 
                         lambda m: f'<mark style="background: rgba(255, 230, 0, 0.2); border-radius: 2px; padding: 0 2px;">{m.group(2)}</mark>', 
                         text)

        # 阶段 2: AI 驱动的元素智能注入 Agent
        if stage >= 2:
            # 高级语义映射 (取代单纯的关键词匹配)
            semantic_elements = {
                "核心提示": "�", "重要结论": "🎯", "独家策略": "⚡", "实战技巧": "🛠️",
                "未来趋势": "🔮", "深度分析": "�", "警告/注意事项": "⚠️", "精彩总结": "�",
                "数字/数据": "�", "全球视野": "🌍", "时间/历史": "⏳", "人文学科": "�",
                "元宵/传统": "�", "节日/喜庆": "�", "团圆/亲情": "�‍👩‍👧‍👦", "浪漫/爱情": "🌹"
            }
            
            # 使用更智能的正则，避免在 HTML 标签内部注入，且避免重复注入
            for kw, symbol in semantic_elements.items():
                # 校验是否已经注入过该符号
                if f'>{symbol}</span>' in text:
                    continue
                # 匹配关键词，且确保不在 <> 或 [] 内部
                pattern = rf'(?<![<\[])({kw})(?![>\]])'
                text = re.sub(pattern, f'<span style="margin-right:4px;">{symbol}</span>\\1', text)
            
            # 自动探测句末情绪并追加符号 (简单启发式)
            if "！" in text or "!" in text:
                text = text.replace("！", "！✨").replace("!", "!✨")

        # 阶段 3: 专业级标注 Agent (关键字高亮与深度格式化)
        if stage >= 3:
            primary = self.design_tokens["primary"]
            secondary = self.design_tokens["secondary"]
            accent = self.design_tokens["accent"]
            bg = self.design_tokens["bg"]
            
            # 使用“荧光笔”效果的高级标注 (带有微妙的旋转和阴影，但保持专业)
            text = re.sub(r'<strong>(.+?)</strong>', 
                         lambda m: f'<strong style="color: {secondary}; font-weight: 800; background: linear-gradient(120deg, {primary}22 0%, {primary}44 100%); padding: 2px 6px; border-radius: 4px; box-shadow: 0 1px 3px rgba(0,0,0,0.1);">{m.group(1)}</strong>', 
                         text)
            
            # 高级高亮标记 [HL: text] -> 丝滑弥散阴影高亮 (覆盖 Stage 1 的简易处理)
            text = re.sub(r'\[(HL|KEY):\s*(.+?)\s*\]', 
                         lambda m: f'<mark style="background: {accent}22; border: 1px solid {accent}44; color: {secondary}; padding: 2px 6px; border-radius: 6px; font-weight: bold; box-shadow: 0 2px 10px {accent}11;">{m.group(2)}</mark>', 
                         text)
            
            # 自动识别核心短语并增强 (启发式)
            phrases = ["核心底层", "关键路径", "绝对原则", "深度解构"]
            for p in phrases:
                text = text.replace(p, f'<span style="font-weight: 600; color: {primary};">{p}</span>')

        return text
    


class AdaptiveTemplateEngine:
    """
    自适应模板引擎
    整合内容分析和模板构建
    """
    
    def __init__(self):
        self.analyzer = ContentAnalyzer()
        self.builder = ModularTemplateBuilder()
        self.llm_service = LLMService()

    def _clean_llm_response(self, text: str) -> str:
        """清洗 LLM 响应，去除 Markdown 代码块包裹和多余的反引号"""
        if not text:
            return ""
        # 去除 ```html ... ``` 或 ```markdown ... ```
        text = re.sub(r'^```(?:html|markdown|md)?\s*', '', text, flags=re.MULTILINE)
        text = re.sub(r'```\s*$', '', text, flags=re.MULTILINE)
        # 去除开头和结尾可能残余的单个反引号
        text = text.strip('`').strip()
        return text

    def _format_inline_styles(self, content: str) -> str:
        """代理调用 Builder 的行内样式处理"""
        return self.builder._format_inline_styles(content)

    async def _apply_semantic_refinement(self, content: str, design_tokens: Dict):
        """Stage 2: 语义元素 Agent - 支持流式输出 Thought 和最终结果"""
        try:
            prompt = f"""
你是一位资深新媒体排版专家。请分析以下内容，识别出 1-2 个真正关键的“灵魂锚点”。
【指令】：
1. 仅在最重要的短语前添加图标，包裹在 <span style="margin-right:4px;">图标</span> 中。
2. 严禁重构、虚构或过度修饰。仅在原文本基础上注入 1-2 个图标。
3. 保持原有的 HTML 结构。
4. 如果内容已足够好，不要添加任何图标。
5. **禁令**：严禁输出类似“(保持原样输出)”、“(内容不变)”等任何形式的元说明、括号注释或英文提示。
6. **语言**：所有 Thought 和输出内容必须使用 **中文**。

【内容】：
{content[:2000]}

在你输出最终 HTML 之前，请先输出一行 `Thought: [你的分析简述]`。
"""
            full_response = ""
            html_started = False
            
            async for chunk in self.llm_service.astream(
                prompt=prompt,
                model="deepseek-v3",
                temperature=0.2
            ):
                full_response += chunk
                if "Thought:" in full_response and not html_started:
                    # 尝试提取 Thought 部分并 yield
                    thought_match = re.search(r'Thought:(.*?)(?:\n|<|$)', full_response, re.S)
                    if thought_match:
                        yield {"type": "thought", "content": thought_match.group(1).strip()}
                
                if "<" in chunk or html_started:
                    html_started = True

            # 提取最终 HTML (过滤掉 Thought 部分)
            final_html = full_response
            if "Thought:" in final_html:
                parts = re.split(r'Thought:.*?\n', final_html, flags=re.S)
                final_html = parts[-1].strip() if parts else final_html
            
            # 清洗结果
            final_html = self._clean_llm_response(final_html)
            yield {"type": "result", "content": final_html if final_html else content}
            
        except Exception as e:
            log.print_log(f"语义细化流式解析失败: {e}", "warning")
            yield {"type": "result", "content": content}

    async def _apply_professional_annotation(self, content: str, design_tokens: Dict):
        """Stage 3: 专业标注 Agent - 支持流式 Thought"""
        try:
            primary = design_tokens.get("primary", "#4F46E5")
            accent = design_tokens.get("accent", "#8B5CF6")
            
            prompt = f"""
你是一位资深美编。请找出 1 处真正值得划重点的“黄金句子”，用 <span class="pro-highlight">句子内容</span> 包裹。
【准则】：
- 仅标注真正深刻的句子。严禁改变原内容。
- **禁令**：严禁在输出结果中包含类如“(保持原样)”、“(No changes)”等元说明或任何非内容的括号提示。
- **语言**：所有 Thought 和输出内容必须使用 **中文**。
- 在输出 HTML 前，先输出一行 `Thought: [为什么选择这一句]`。

【内容】：
{content[:2000]}
"""
            full_response = ""
            async for chunk in self.llm_service.astream(
                prompt=prompt,
                model="deepseek-v3",
                temperature=0.2
            ):
                full_response += chunk
                if "Thought:" in full_response and "<" not in full_response:
                    thought_match = re.search(r'Thought:(.*?)(?:\n|<|$)', full_response, re.S)
                    if thought_match:
                        yield {"type": "thought", "content": thought_match.group(1).strip()}

            refined = full_response
            if "Thought:" in refined:
                refined = re.split(r'Thought:.*?\n', refined, flags=re.S)[-1].strip()
            
            # 清洗结果
            refined = self._clean_llm_response(refined)
            refined = refined.replace('class="pro-highlight"', f'style="background: {accent}11; color: {primary}; padding: 2px 4px; border-radius: 4px; font-weight: 600;"')
            yield {"type": "result", "content": refined if refined else content}
            
        except Exception as e:
            log.print_log(f"专业标注流式解析失败: {e}", "warning")
            yield {"type": "result", "content": content}

    async def _apply_global_audit(self, html: str) -> str:
        """Stage 5: 全局终审 Agent - 优化一致性与细节，清理所有英文提示词"""
        try:
            from bs4 import BeautifulSoup
            
            # 简单清理：移除多余空行
            html = re.sub(r'\n\s*\n', '\n', html)
            
            # --- 使用 BeautifulSoup 深度清理英文 ComfyUI 提示词 ---
            soup = BeautifulSoup(html, 'html.parser')
            
            # 1. 清理所有 <img> alt 属性中的英文提示词
            for img in soup.find_all('img'):
                alt_val = img.get('alt', '')
                english_words = re.findall(r'[A-Za-z]{3,}', alt_val)
                if len(english_words) >= 3:
                    img['alt'] = '配图'
            
            # 2. 清理包含英文 prompt 的高亮 span（含嵌套 emoji span）
            #    例: <span style="background:...;">A close-up shot of a <span>🐇</span>traditional...</span>
            comfyui_phrases = [
                'close-up', 'Close-up', 'A close', 'A majestic', 'A glowing',
                'A young', 'A dynamic', 'Ancient Chinese', 'Traditional',
                'Delicate silk', 'wide-angle', 'panoramic', 'shot of',
                'scene of', 'depicting', 'procession', 'lantern', 'glutinous',
            ]
            for span in soup.find_all('span'):
                # 获取 span 的完整文本（包括嵌套子元素的文本）
                full_text = span.get_text()
                # 跳过仅包含 emoji 或中文的 span
                english_words = re.findall(r'[A-Za-z]{3,}', full_text)
                chinese_chars = re.findall(r'[\u4e00-\u9fa5]', full_text)
                
                # 检查是否是 ComfyUI prompt
                is_prompt = False
                if len(english_words) >= 3 and len(chinese_chars) < 5:
                    is_prompt = True
                # 检查已知 ComfyUI 短语
                for phrase in comfyui_phrases:
                    if phrase in full_text:
                        if len(english_words) >= 2:
                            is_prompt = True
                            break
                
                if is_prompt:
                    # 检查 span 内是否有 <img> 标签，如果有则保留图片
                    imgs = span.find_all('img')
                    if imgs:
                        # 保留图片，移除 span 包裹和文本
                        for img in imgs:
                            span.insert_before(img.extract())
                    span.decompose()
            
            # 3. 清理 "深度解析与全景展示" 被当作正文内容的残留以及顽固占位符
            for div in soup.find_all('div'):
                text = div.get_text(strip=True)
                if text == '深度解析与全景展示' and not div.find(['h1', 'h2', 'h3', 'img']):
                    # 移除仅包含此副标题文本的 div
                    div.decompose()
            
            # 4. 彻底剥离所有可能的顽固占位符和 AI 解析文本 (增强型)
            raw_html = str(soup)
            cleaned_html = re.sub(r'\[(?:IMG_PROMPT|图片解析)[:：].*?\]', '', raw_html)
            
            # 5. 最终文本纯净化 (去除代码块包装、反引号)
            cleaned_html = self._clean_llm_response(cleaned_html)
            
            return cleaned_html
            
            # 4. 清理 broken Markdown 图片语法: !✨[📜 等
            #    这些可能出现在 span 或 div 的文本中 (此段逻辑已被 cleaned_html 覆盖，但保留 Soup 处理作为双保险)
            for el in soup.find_all(['span', 'div', 'p']):
                text = el.get_text(strip=True)
                if text and re.match(r'^!?[✨🎯⚡💡🌟]*\[?[\U0001f300-\U0001f9ff\u2600-\u26ff]*\]?$', text):
                    el.decompose()
            
            # 5. 清理「探索与启示」等 AI 生成的通用尾部段落（非原文内容）
            for div in soup.find_all('div'):
                text = div.get_text(strip=True)
                if text == '每一个当下都将成为历史，我们在纵览这些改变世界轨迹的关键节点时，也能从中汲取前行的智慧。':
                    parent = div.parent
                    div.decompose()
            
            html = str(soup)
            
            # 6. 最后一轮用 regex 清理漏网之鱼
            # 清理 >纯英文文本< 模式
            def _clean_bare_prompt(m):
                text = m.group(1)
                eng = re.findall(r'[A-Za-z]{3,}', text)
                chs = re.findall(r'[\u4e00-\u9fa5]', text)
                if len(eng) >= 5 and len(chs) < 3:
                    return '>'
                return m.group(0)
            html = re.sub(r'>([^<]{15,})', _clean_bare_prompt, html)
            
            # 清理残留的 broken Markdown
            html = re.sub(r'!✨?\[[^\]]*\]', '', html)
            # 清理 !✨[<span> 这种混合形式
            html = re.sub(r'!✨?\[<span[^>]*>.*?</span>\s*', '', html)
            
            return html.strip()
        except Exception:
            return html
    
    async def generate_stepwise(self, title: str, content: str, topic: str = "", 
                                fixed_direction: dict = None, fixed_color_key: str = None):
        """
        生成自适应模板 - 真正 AI 驱动的 5阶 Agent 工作流
        """
        # --- Stage 0: 设计决策 ---
        yield {"type": "log", "message": "🤖 Agent 启动: 正在深入理解文章结构并制定设计蓝图..."}
        blocks = self.analyzer.analyze(content)
        components = self.analyzer.suggest_components(blocks)
        
        from src.ai_write_x.core.ai_template_designer import AITemplateDesigner
        designer = AITemplateDesigner()
        
        try:
            # 优先使用固定的设计决策，避免重复 LLM 调用导致的 logs 与渲染不一致
            if fixed_direction and fixed_color_key:
                design_direction = fixed_direction
                color_scheme_key = fixed_color_key
            else:
                design_direction = await designer._get_recommended_direction(title, content, topic)
                color_scheme_key = await designer._select_color_theme(topic, content)
            
            colors = designer.COLOR_PALETTES.get(color_scheme_key, designer.COLOR_PALETTES["minimal"])
            
            design_tokens = {
                "primary": colors[0], "secondary": colors[1], "accent": colors[2],
                "bg": colors[3] if len(colors) > 3 else "#F8FAFC",
                "text_color": "#334155", "concept": design_direction["name"],
                "style_hint": design_direction["style"]
            }
            if design_tokens["bg"].lower() in ["#000000", "#121212", "#1a1a1a"]:
                design_tokens["bg"] = "#F8FAFC"
        except:
            design_tokens = {"primary": "#4F46E5", "secondary": "#6366F1", "accent": "#8B5CF6", "bg": "#F8FAFC", "text_color": "#334155", "concept": "极简", "style_hint": ""}

        self.builder = ModularTemplateBuilder()
        self.builder.design_tokens = design_tokens
        
        # --- Stage 1: 布局 Agent ---
        yield {"type": "log", "message": f"🎨 Agent Stage 1: 注入视觉灵魂【{design_tokens['concept']}】，构建排版架构..."}
        self.builder.stage = 1
        html_v1 = self.builder.build_template(title, components)
        # 初始布局预览
        yield {"type": "chunk", "content": html_v1, "stage": 1}
        
        # --- Stage 2: 语义 Agent (Real AI) ---
        yield {"type": "log", "message": "✨ Agent Stage 2: 正在利用 LLM 挖掘内容深处的语义锚点并匹配视觉符号..."}
        self.builder.stage = 2
        refined_components = []
        total_blocks = len([b for _, b in components if b.type == 'paragraph' and len(b.content) > 50])
        processed_blocks = 0
        
        for c_type, block in components:
            if block.type == 'paragraph' and len(block.content) > 50:
                processed_blocks += 1
                msg = f"🧬 正在流式解析第 {processed_blocks}/{total_blocks} 段语义..."
                yield {"type": "log", "message": msg}
                log.print_log(msg, "info") # 同时输出到 CMD 日志
                async for event in self._apply_semantic_refinement(block.content, design_tokens):
                    if event["type"] == "thought":
                        yield event
                    elif event["type"] == "result":
                        block.content = event["content"]
                        # 实时向 UI 投递 *全量* 结果 (而非片段)，确保预览不缩水
                        current_html = self.builder.build_template(title, components)
                        yield {"type": "chunk", "content": current_html, "stage": 2, "is_fragment": True}
                
            # 无需再 append 到 refined_components，直接全量操作 components
            pass
        
        # --- Stage 3: 标注 Agent (Real AI) ---
        yield {"type": "log", "message": "🔍 Agent Stage 3: 正在通过深度学习识别文章“金句”，应用专业化视觉标注..."}
        self.builder.stage = 3
        total_anno_blocks = len([b for _, b in components if b.type == 'paragraph' and len(b.content) > 100])
        processed_anno_blocks = 0
        
        for c_type, block in components:
            if block.type == 'paragraph' and len(block.content) > 100:
                processed_anno_blocks += 1
                msg = f"🖋️ 正在标注第 {processed_anno_blocks}/{total_anno_blocks} 段黄金金句..."
                yield {"type": "log", "message": msg}
                log.print_log(msg, "info")
                async for event in self._apply_professional_annotation(block.content, design_tokens):
                    if event["type"] == "thought":
                        yield event
                    elif event["type"] == "result":
                        block.content = event["content"]
                        # 实时投递全量标注后的结果
                        current_html = self.builder.build_template(title, components)
                        yield {"type": "chunk", "content": current_html, "stage": 3, "is_fragment": True}
        
        # --- Stage 4: 图像 Agent ---
        yield {"type": "log", "message": "🛡️ Agent Stage 4: 正在核查图像资产完整性，优化视觉缺位..."}
        self.builder.stage = 4
        html_v4 = self.builder.build_template(title, components)
        if "img-placeholder" in html_v4:
             yield {"type": "log", "message": "📸 发现待生成视觉资源，已标记由视觉引擎异步托管..."}
        yield {"type": "chunk", "content": html_v4, "stage": 4}
        
        # --- Stage 5: 终审 Agent ---
        yield {"type": "log", "message": "🚀 Agent Stage 5: 发起全局设计审计，移除冗余，确保视觉链路一致性..."}
        self.builder.stage = 5
        # 此时 components 应当是负载了所有 AI 强化的内容
        final_html = self.builder.build_template(title, components)
        final_html = await self._apply_global_audit(final_html)
        yield {"type": "chunk", "content": final_html, "stage": 5}
        yield {"type": "full_html", "content": final_html, "stage": 5}
        
        log.print_log(f"[Agent 工作流] 5阶设计完成: {design_tokens['concept']}")

    async def generate(self, title: str, content: str, topic: str = "") -> str:
        """兼容旧版 generate 方法，直接返回最终结果"""
        final_result = None
        async for step in self.generate_stepwise(title, content, topic):
            if step["type"] == "full_html":
                final_result = step["content"]
        return final_result or ""
    
    def _select_scheme(self, topic: str) -> DesignScheme:
        """根据主题选择配色方案"""
        topic = topic.lower()
        
        if any(k in topic for k in ['科技', 'tech', 'ai', '数字']):
            return DesignScheme("科技蓝", "#0066cc", "#0099ff", "#00ccff", "#f0f7ff", "#1e3a5f", ["科技", "现代"])
        elif any(k in topic for k in ['自然', '环保', '绿色', 'nature']):
            return DesignScheme("自然绿", "#2d5016", "#5a8c3a", "#8fbc8f", "#f5f9f0", "#1a2e1a", ["自然", "清新"])
        elif any(k in topic for k in ['财经', '商业', 'finance', 'business']):
            return DesignScheme("商务灰", "#1f2937", "#4b5563", "#6b7280", "#f9fafb", "#111827", ["商务", "专业"])
        elif any(k in topic for k in ['美食', '生活', 'food', 'life']):
            return DesignScheme("温暖橙", "#c2410c", "#ea580c", "#fb923c", "#fff7ed", "#431407", ["温暖", "活力"])
        elif any(k in topic for k in ['新闻', 'news']):
            return DesignScheme("新闻蓝", "#1e3a5f", "#3d6b9c", "#60a5fa", "#f0f7ff", "#0f172a", ["新闻", "严肃"])
        else:
            # 随机选择
            schemes = [
                DesignScheme("深海蓝", "#1e3a5f", "#3d6b9c", "#60a5fa", "#f0f7ff", "#1e293b", ["渐变", "阴影"]),
                DesignScheme("森林绿", "#2d5016", "#5a8c3a", "#8fbc8f", "#f5f9f0", "#1a2e1a", ["自然", "柔和"]),
                DesignScheme("日落橙", "#c2410c", "#ea580c", "#fb923c", "#fff7ed", "#431407", ["温暖", "活力"]),
                DesignScheme("紫罗兰", "#5b21b6", "#7c3aed", "#a78bfa", "#faf5ff", "#2e1065", ["优雅", "现代"]),
            ]
            return random.choice(schemes)


async def generate_adaptive_template(title: str, content: str, topic: str = "") -> str:
    """便捷函数：生成自适应模板"""
    engine = AdaptiveTemplateEngine()
    return await engine.generate(title, content, topic)
