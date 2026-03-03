# -*- coding: utf-8 -*-
import re
import random

class AntiAIEngine:
    """
    反AI味引擎 (Anti-AI-Flavor Engine)
    用于破坏传统的AI生成特征（高度对称的段落、工整的列表、机械的连接词），
    从而降低被如朱雀等AI检测器识别的概率。
    """

    @classmethod
    def pulverize(cls, text: str) -> str:
        """结构粉碎：打散列表，随机化段落长度"""
        if not text:
            return text
            
        text = cls._flatten_lists(text)
        text = cls._randomize_paragraphs(text)
        text = cls._inject_human_transitions(text)
        
        return text

    @classmethod
    def _flatten_lists(cls, text: str) -> str:
        """将过于工整的Markdown列表扁平化处理为长句"""
        # 寻找连续的列表项
        lines = text.split('\n')
        out_lines = []
        
        list_buffer = []
        for line in lines:
            if re.match(r'^[\-\*\•]\s+(.*)', line.strip()) or re.match(r'^\d+\.\s+(.*)', line.strip()):
                # 提取列表文字
                content = re.sub(r'^[\-\*\•]\s+', '', line.strip())
                content = re.sub(r'^\d+\.\s+', '', content)
                list_buffer.append(content)
            else:
                if list_buffer:
                    # 将列表内容打平并用不同的标点连接
                    if random.random() > 0.5:
                        flattened = "，此外，" + "；同时".join(list_buffer) + "。"
                    else:
                        flattened = "具体来说包括：" + "，".join(list_buffer)[:-1] + "等。"
                    out_lines.append(flattened)
                    list_buffer = []
                out_lines.append(line)
        
        if list_buffer:
            flattened = "，此外，" + "；同时".join(list_buffer) + "。"
            out_lines.append(flattened)
            
        return '\n'.join(out_lines)

    @classmethod
    def _randomize_paragraphs(cls, text: str) -> str:
        """随机合并/拆分段落，打破AI 200字/段的魔咒"""
        paragraphs = [p for p in text.split('\n\n') if p.strip()]
        new_paragraphs = []
        
        i = 0
        while i < len(paragraphs):
            p = paragraphs[i]
            # 如果段落太短且不是标题，有一定概率与下一个段落合并
            if not p.startswith('#') and len(p) < 80 and i + 1 < len(paragraphs) and not paragraphs[i+1].startswith('#'):
                if random.random() > 0.4:
                    p = p.strip() + " 而且，" + paragraphs[i+1].strip()
                    i += 1
            new_paragraphs.append(p)
            i += 1
            
        return '\n\n'.join(new_paragraphs)

    @classmethod
    def _inject_human_transitions(cls, text: str) -> str:
        """随机替换机械过渡词为人类高频口语词/强情感词"""
        replacements = [
            (r'首先，', ['其实第一点就是，', '最直白地说，', '先不说别的，']),
            (r'其次，', ['退一步讲，', '另外呢，', '更有意思的是，']),
            (r'最后，', ['说到底，', '归根结底，', '最让我感慨的是，']),
            (r'总之，', ['总而言之，', '说句掏心窝子的话，', '说实话，']),
        ]
        
        for old, new_list in replacements:
            if random.random() > 0.5: # 50%概率替换
                text = re.sub(old, lambda m: random.choice(new_list), text, count=1)
                
        return text

    @classmethod
    def get_style_mimicry_prompt(cls) -> str:
        """获取强制风格注入提示词"""
        return (
            "【去AI味强制指令】：禁止使用高度对称的排比句、'首先/其次/最后'等机械结构。请使用长短句交错的行文，"
            "允许使用带有些许主观色彩的反问句，使用自然过渡。行文必须像真人专家在直接向读者对话，而非AI在背诵条目。"
            "(注意：如果系统要求你输出 JSON格式、工具参数调用、或是包含 Thought: / Action: 等流程控制的格式，"
            "请你必须严格遵守特定的格式要求，仅在正文内容本身应用上述去AI味风格。千万不要破坏系统要求的语法格式！)"
        )
