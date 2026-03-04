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
        """结构粉碎：打散列表，随机化段落长度，破坏AI对称特征"""
        if not text:
            return text
            
        text = cls._flatten_lists(text)
        text = cls._randomize_paragraphs(text)
        text = cls._inject_human_transitions(text)
        text = cls._break_sentence_symmetry(text)
        text = cls._inject_filler_words(text)
        text = cls._vary_punctuation(text)
        
        return text

    @classmethod
    def _flatten_lists(cls, text: str) -> str:
        """将过于工整的Markdown列表扁平化处理为长句
        
        注意：仅打散纯文字列表，保留包含重要数据（数字、百分比、金额）的列表。
        """
        lines = text.split('\n')
        out_lines = []
        
        list_buffer = []
        for line in lines:
            if re.match(r'^[\-\*\•]\s+(.*)', line.strip()) or re.match(r'^\d+\.\s+(.*)', line.strip()):
                content = re.sub(r'^[\-\*\•]\s+', '', line.strip())
                content = re.sub(r'^\d+\.\s+', '', content)
                list_buffer.append(content)
            else:
                if list_buffer:
                    # 如果列表项包含数据（数字+%、金额等），保留列表格式不打散
                    has_data = any(re.search(r'\d+[\.\d]*[%％亿万元]', item) for item in list_buffer)
                    if has_data or len(list_buffer) > 6:
                        # 数据密集型列表 — 保持原样，因为这正是读者需要的格式
                        for item in list_buffer:
                            out_lines.append(f"- {item}")
                    elif random.random() > 0.5:
                        flattened = "，此外，" + "；同时".join(list_buffer) + "。"
                        out_lines.append(flattened)
                    else:
                        flattened = "具体来说包括：" + "，".join(list_buffer)[:-1] + "等。"
                        out_lines.append(flattened)
                    list_buffer = []
                out_lines.append(line)
        
        if list_buffer:
            has_data = any(re.search(r'\d+[\.\d]*[%％亿万元]', item) for item in list_buffer)
            if has_data:
                for item in list_buffer:
                    out_lines.append(f"- {item}")
            else:
                flattened = "，此外，" + "；同时".join(list_buffer) + "。"
                out_lines.append(flattened)
            
        return '\n'.join(out_lines)

    @classmethod
    def _randomize_paragraphs(cls, text: str) -> str:
        """随机合并/拆分段落，打破AI 200字/段的魔咒"""
        paragraphs = [p for p in text.split('\n\n') if p.strip()]
        new_paragraphs = []
        
        # 多样化连接词池，避免单一"而且"泛滥
        connectors = [
            "——", "。\n\n", "，与此同时，", "。换个角度看，",
            "。说白了，", "。不止于此，", "。值得注意的是，",
            "。有意思的是，", "。更关键的是，", "，同时，",
            "。事实上，", "。简单来说，",
        ]
        
        i = 0
        while i < len(paragraphs):
            p = paragraphs[i]
            # 降低合并概率（35%），且仅对非标题、非图片占位符的短段落生效
            if (not p.startswith('#') 
                and len(p) < 60 
                and i + 1 < len(paragraphs) 
                and not paragraphs[i+1].startswith('#')
                and '[[V-SCENE' not in p
                and '[[V-SCENE' not in paragraphs[i+1]
                and '[图片解析' not in p
                and '>' not in p):  # 不合并引用块
                if random.random() > 0.65:
                    connector = random.choice(connectors)
                    p = p.strip() + connector + paragraphs[i+1].strip()
                    i += 1
            new_paragraphs.append(p)
            i += 1
            
        return '\n\n'.join(new_paragraphs)

    @classmethod
    def _inject_human_transitions(cls, text: str) -> str:
        """随机替换机械过渡词为人类高频口语词/强情感词"""
        replacements = [
            (r'首先，', ['其实第一点就是，', '最直白地说，', '先不说别的，', '开门见山来讲，']),
            (r'其次，', ['退一步讲，', '另外呢，', '更有意思的是，', '再来看看，', '还有个细节是，']),
            (r'最后，', ['说到底，', '归根结底，', '最让我感慨的是，', '最值得聊的是，']),
            (r'总之，', ['总而言之，', '说句掏心窝子的话，', '说实话，', '一句话总结：']),
            (r'此外，', ['顺带一提，', '对了还有，', '另一个值得注意的点是，']),
            (r'因此，', ['所以呢，', '这就意味着，', '结果就是，']),
            (r'然而，', ['但话说回来，', '不过转念一想，', '可事情远没这么简单，']),
        ]
        
        for old, new_list in replacements:
            if random.random() > 0.5:
                text = re.sub(old, lambda m: random.choice(new_list), text, count=1)
                
        return text

    @classmethod
    def _break_sentence_symmetry(cls, text: str) -> str:
        """打破AI常见的前后对称排比句式（如"A是X，B是Y，C是Z"的平行结构）"""
        lines = text.split('\n')
        result_lines = []
        
        for i, line in enumerate(lines):
            if i >= 2 and random.random() > 0.6:
                prev2 = lines[i-2].strip() if i >= 2 else ""
                prev1 = lines[i-1].strip() if i >= 1 else ""
                curr = line.strip()
                common_starts = ['不仅', '不但', '一方面', '与此同时', '同样']
                for s in common_starts:
                    if prev2.startswith(s) and prev1.startswith(s) and curr.startswith(s):
                        replacements = ['说到这个，', '换个思路看，', '有趣的是，']
                        line = random.choice(replacements) + curr[len(s):]
                        break
            result_lines.append(line)
        
        return '\n'.join(result_lines)

    @classmethod
    def _inject_filler_words(cls, text: str) -> str:
        """随机在少量段落开头插入口语化填充词，增添真人感"""
        fillers = [
            "说实话，", "怎么说呢，", "不得不说，",
            "坦白讲，", "你可能没想到，", "有一说一，",
        ]
        
        paragraphs = text.split('\n\n')
        inject_count = 0
        max_injects = 2
        
        for i in range(len(paragraphs)):
            p = paragraphs[i].strip()
            # 仅对非标题、非引用、非占位符的普通段落注入
            if (inject_count < max_injects 
                and p and not p.startswith('#') 
                and not p.startswith('>') 
                and not p.startswith('[[')
                and not p.startswith('**')
                and not p.startswith('[图片')
                and len(p) > 40
                and random.random() > 0.75):
                # 直接拼接，不要修改原文第一个字的大小写
                paragraphs[i] = random.choice(fillers) + p
                inject_count += 1
        
        return '\n\n'.join(paragraphs)

    @classmethod
    def _vary_punctuation(cls, text: str) -> str:
        """随机替换部分句尾标点，打破AI全篇统一句号的机械感"""
        # 用省略号或感叹号替换少量句号（最多3处）
        sentences = text.split('。')
        if len(sentences) < 5:
            return text
        
        # 重新组装，确保每个句子后面都有标点
        result_parts = []
        replace_count = 0
        max_replace = min(3, len(sentences) // 5)
        
        for i in range(len(sentences)):
            part = sentences[i]
            # 最后一段不需要加句号（它本身可能没有句号结尾）
            if i == len(sentences) - 1:
                result_parts.append(part)
                break
            
            # 避免替换标题行或占位符附近的标点
            if (replace_count < max_replace
                and random.random() > 0.85 
                and not part.strip().startswith('#')
                and '[[' not in part
                and '[图片' not in part
                and len(part.strip()) > 15):
                choice = random.choice(['……', '！'])
                result_parts.append(part + choice)
                replace_count += 1
            else:
                result_parts.append(part + '。')
        
        return ''.join(result_parts)

    @classmethod
    def get_style_mimicry_prompt(cls) -> str:
        """获取强制风格注入提示词"""
        return (
            "【去AI味强制指令】：禁止使用高度对称的排比句、'首先/其次/最后'等机械结构。请使用长短句交错的行文，"
            "允许使用带有些许主观色彩的反问句，使用自然过渡。行文必须像真人专家在直接向读者对话，而非AI在背诵条目。"
            "(注意：如果系统要求你输出 JSON格式、工具参数调用、或是包含 Thought: / Action: 等流程控制的格式，"
            "请你必须严格遵守特定的格式要求，仅在正文内容本身应用上述去AI味风格。千万不要破坏系统要求的语法格式！)"
        )
