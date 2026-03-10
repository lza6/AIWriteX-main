# -*- coding: utf-8 -*-
import json
import random
import re
from typing import Dict, Any, List, Optional
from src.ai_write_x.utils.path_manager import PathManager
import src.ai_write_x.utils.log as lg

class DynamicDesignEngine:
    """动态设计引擎 - 积木化排版系统"""
    
    _instance = None
    
    @classmethod
    def get_instance(cls):
        if cls._instance is None:
            cls._instance = cls()
        return cls._instance

    def __init__(self):
        self.design_elements = {}
        self.color_system = {}
        self.load_config()

    def load_config(self):
        """加载设计元素和色彩系统配置"""
        try:
            design_path = PathManager.get_root_dir() / "config" / "design_elements.json"
            color_path = PathManager.get_root_dir() / "config" / "color_system.json"
            
            if design_path.exists():
                with open(design_path, "r", encoding="utf-8") as f:
                    self.design_elements = json.load(f)
            
            if color_path.exists():
                with open(color_path, "r", encoding="utf-8") as f:
                    self.color_system = json.load(f)
                    
            lg.print_log("DynamicDesignEngine config loaded successfully", "success")
        except Exception as e:
            lg.print_log(f"DynamicDesignEngine config load failed: {e}", "error")

    def select_palette(self, content: str, topic: str = "") -> Dict[str, str]:
        """根据内容和话题选择最佳色彩方案"""
        if not self.color_system:
            return {}
            
        palettes = self.color_system.get("color_palettes", {})
        rules = self.color_system.get("selection_rules", {})
        mapping = rules.get("keyword_mapping", {})
        fallback = rules.get("fallback", "news")
        
        # 1. 关键词特征提取
        text_to_scan = (topic + " " + content[:1000]).lower()
        
        selected_key = None
        for keywords, palette_name in mapping.items():
            keyword_list = keywords.split("/")
            if any(kw.lower() in text_to_scan for kw in keyword_list):
                selected_key = palette_name
                break
        
        # 2. 随机化因子 (如果有的话)
        if random.random() < rules.get("randomization_factor", 0.0):
            selected_key = random.choice(list(palettes.keys()))
            
        # 3. 兜底
        if not selected_key or selected_key not in palettes:
            selected_key = fallback
            
        return palettes.get(selected_key, palettes.get(fallback, {}))

    def get_wechat_system_template(self, content: str, topic: str = "") -> str:
        """生成微信公众号专用的系统提示词"""
        palette = self.select_palette(content, topic)
        
        # 提取颜色变量
        p_color = palette.get("primary", "#4a5568")
        a_color = palette.get("accent", "#718096")
        b_color = palette.get("background", "#f7fafc")
        t_color = palette.get("text", "#2d3748")
        
        # 将 RGB 转换
        def hex_to_rgb_str(hex_color):
            hex_color = hex_color.lstrip('#')
            if len(hex_color) == 6:
                r, g, b = struct.unpack('BBB', bytes.fromhex(hex_color))
                return f"{r}, {g}, {b}"
            return "74, 85, 104"

        import struct
        p_rgb = hex_to_rgb_str(p_color)

        # 构建元素库描述
        elements_desc = ""
        for category, items in self.design_elements.items():
            elements_desc += f"\n### {category.upper()}\n"
            if isinstance(items, dict):
                for name, info in items.items():
                    html = info.get("html", info) if isinstance(info, dict) else info
                    desc = info.get("description", "") if isinstance(info, dict) else ""
                    # 替换基础占位符
                    html_preview = html.replace("{{primary_color}}", p_color)\
                                       .replace("{{accent_color}}", a_color)\
                                       .replace("{{bg_color}}", b_color)\
                                       .replace("{{primary_rgb}}", p_rgb)
                    elements_desc += f"- **{name}**: `{html_preview}` ({desc})\n"

        template = f"""<|start_header_id|>system<|end_header_id|>
# 微信公众号动态排版设计规范 - 元素积木系统 (V19.6 V-TEMPLATE)

## 【核心任务】
你是一位顶级视觉艺术总监。你的任务是将文章内容转换为**可直接发布**的精美 HTML。
本次任务核心：**基底 DNA 继承与视觉突变**。

## 【本次选定的色彩方案】
- **主色调 (Primary)**: `{p_color}`
- **强调色 (Accent)**: `{a_color}`
- **背景底色 (Background)**: `{b_color}`
- **文字主色 (Text)**: `{t_color}`

## 【设计元素库】
重点参考 `STRUCTURAL_DNA` 类别的组件，将其作为整篇文章的母体框架：
{elements_desc}

## 【排版逻辑与突变指令 (V20.2 绝不越界)】
1. **DNA 继承与多样化**：
   - 严肃/财经话题：优先使用 `gold_price_v1`。
   - 情感/爆款话题：**必须使用** `golden_intro_v2`。
   - 文艺/生活话题：尝试 `magazine_style`。
2. **黄金开头极致前置 (绝对命令)**：
   - **正文第一行必须是纯文本金句**。
   - **严禁在第一段文字前放置任何 `<img>`、`div.img-placeholder` 或 `V-SCENE` 占位符**。
   - 即使是 `gold_price_v1` 的头部下方，也必须先出文字金句，再出第一张配图。
3. **视觉布局严禁重叠**：
   - **严禁使用负数 margin (如 `margin-top: -20px`)**，这会导致文字覆盖在图片上，造成阅读障碍。
   - 所有元素必须保持正常的文档流（Block 流），确保文字在图片下方清晰排版。
4. **色彩与对比度优先**：
   - 除非背景是深色，否则文字必须使用 `#333333` 或 `#000000`。
   - 严禁在浅色背景上使用白色文字。
5. **视觉节奏 (Rhythm)**：
   - 每 300-500 字必须使用一次 `<h2>` 标题装饰。
   - 关键金句必须使用 `quote_highlight` 或 `quote_box` 容器。

## 【强制规范】
- **100% 内联样式**：严禁使用 `class` 或 `<style>` 标签。
- **严禁 Markdown**：禁止输出 `**`、`##` 等符号，必须完全使用纯净的 HTML 标签进行排版。
- **图像占位符强制规范**：必须使用 `<div class="img-placeholder" data-img-prompt="..." data-aspect-ratio="16:9"></div>`。
- **输出格式**：仅输出 ```html ``` 代码块。直接从最外层容器开始输出。

现在请开始处理：
<|eot_id|>"""
        return template
