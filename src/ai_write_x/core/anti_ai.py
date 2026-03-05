# -*- coding: utf-8 -*-
import re
import random
import hashlib

class AntiAIEngine:
    """
    反AI味引擎 (Anti-AI-Flavor Engine) V4
    用于破坏传统的AI生成特征（高度对称的段落、工整的列表、机械的连接词、精确数字、句式一致性），
    从而降低被如朱雀等AI检测器识别的概率。
    V5新增：数字模糊化、句式复杂度扰动、段间回照、信息密度波动、段落方差放大。
    """

    @classmethod
    def pulverize(cls, text: str) -> str:
        """V5结构粉碎：打散列表，随机化段落，注入学术引用，数字模糊化，句式扰动，段间回照，段落方差放大，信息密度波动"""
        if not text:
            return text
            
        text = cls._degrade_markdown(text)             # V6: Markdown 僵硬感打破
        text = cls._flatten_lists(text)
        text = cls._randomize_paragraphs(text)
        text = cls._amplify_paragraph_variance(text)    # V5: 段落方差放大
        text = cls._inject_human_transitions(text)
        text = cls._break_sentence_symmetry(text)
        text = cls._fuzzify_numbers(text)              # V4: 数字模糊化
        text = cls._vary_sentence_complexity(text)      # V4: 句式复杂度扰动
        text = cls._inject_emotional_fluctuation(text)  # V6: 情绪波动词注入
        text = cls._inject_info_density_fluctuation(text) # V5: 信息密度波动
        text = cls._inject_filler_words(text)
        text = cls._inject_pseudo_citations(text)
        text = cls._inject_context_echoes(text)         # V4: 段间回照
        text = cls._vary_punctuation(text)
        
        return text

    @classmethod
    def _degrade_markdown(cls, text: str) -> str:
        """V6新增：Markdown排版僵硬感打破
        
        AI喜欢极其工整的排版，比如每个小节必定是 ### 标题，下面跟着 - **粗体**：内容。
        本方法会：
        1. 随机降级 ### 或 #### 标题为普通加粗文本。
        2. 清理列表项中开头的 **粗体词**：结构，使其更像人类口语化的叙述。
        """
        lines = text.split('\n')
        out_lines = []
        
        for line in lines:
            line_str = line.strip()
            
            # 1. 标题降级：25%概率将 ### 或 #### 降级为粗体，打破绝对的层级对称
            if re.match(r'^#{3,4}\s+', line_str):
                if random.random() > 0.75:
                    title_text = re.sub(r'^#{3,4}\s+', '', line_str)
                    line_str = f"**{title_text}**"
                    
            # 2. 清理 AI 味极浓的列表项起手式： - **关键词**：/：
            if re.match(r'^[\-\*\•]\s+\*\*.*?\*\*[：:]', line_str):
                if random.random() > 0.4:
                    # 提取关键词并去掉星号和冒号，融入句子
                    # 例如 "- **效率提升**：这不仅..." -> "- 提到效率提升，这不仅..." 
                    # 或是直接去掉加粗和冒号
                    match = re.match(r'^([\-\*\•]\s+)\*\*(.*?)\*\*[：:](.*)', line_str)
                    if match:
                        bullet, kw, rest = match.groups()
                        transitions = ["说起", "至于", "关于", ""]
                        trans = random.choice(transitions)
                        if trans:
                            line_str = f"{bullet}{trans}{kw}，{rest.strip()}"
                        else:
                            line_str = f"{bullet}{kw}，{rest.strip()}"
                            
            out_lines.append(line_str)
            
        return '\n'.join(out_lines)

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
        """V3: 上下文感知连接词替换 — 根据前后句语义关系选择匹配的连接词"""
        # 因果关系：前文描述原因，后文描述结果
        causal_replacements = ['所以呢，', '这就意味着，', '结果就是，', '由此可见，']
        # 转折关系：前后文意思对立
        contrast_replacements = ['但话说回来，', '不过转念一想，', '可事情远没这么简单，', '然而实际上，']
        # 递进关系：后文在前文基础上深入
        progressive_replacements = ['更关键的是，', '更有意思的是，', '不止于此，', '往深了说，']
        # 举例关系：后文举具体例子
        example_replacements = ['比如说，', '举个例子，', '就拿最近的事来说，', '最典型的就是，']
        
        # 语义关系检测关键词（轻量级，不依赖NLP库）
        causal_signals = ['因为', '由于', '导致', '原因', '所以', '因此']
        contrast_signals = ['但是', '然而', '不过', '虽然', '可是', '却']
        progressive_signals = ['而且', '并且', '同时', '此外', '更', '还有']
        example_signals = ['例如', '比如', '如同', '就像', '举例']
        
        replacements = [
            (r'首先，', ['其实第一点就是，', '最直白地说，', '先不说别的，', '开门见山来讲，']),
            (r'其次，', ['退一步讲，', '另外呢，', '更有意思的是，', '再来看看，', '还有个细节是，']),
            (r'最后，', ['说到底，', '归根结底，', '最让我感慨的是，', '最值得聊的是，']),
            (r'总之，', ['总而言之，', '说句掏心窝子的话，', '说实话，', '一句话总结：']),
            (r'此外，', ['顺带一提，', '对了还有，', '另一个值得注意的点是，']),
        ]
        
        # V3: 上下文感知替换 — "因此/因为"类过渡词根据前文内容选择匹配的替换词
        paragraphs = text.split('\n')
        for i in range(1, len(paragraphs)):
            line = paragraphs[i].strip()
            prev_line = paragraphs[i-1].strip() if i > 0 else ''
            
            if random.random() > 0.6:  # 40%概率触发
                # 检测前文语义并选择匹配的替换
                if any(s in prev_line for s in causal_signals) and line.startswith(('因此，', '所以，')):
                    replacement = random.choice(causal_replacements)
                    paragraphs[i] = re.sub(r'^(因此|所以)，', replacement, line, count=1)
                elif any(s in prev_line for s in contrast_signals) and line.startswith(('然而，', '但是，')):
                    replacement = random.choice(contrast_replacements)
                    paragraphs[i] = re.sub(r'^(然而|但是)，', replacement, line, count=1)
                elif any(s in line for s in example_signals):
                    if random.random() > 0.7:
                        replacement = random.choice(example_replacements)
                        paragraphs[i] = re.sub(r'^(例如|比如)，', replacement, line, count=1)
        text = '\n'.join(paragraphs)
        
        # 保留原有的通用替换逻辑
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
        """V3: 口语化填充词注入 — 扩充至20+种多样化填充词库"""
        fillers = [
            "说实话，", "怎么说呢，", "不得不说，",
            "坦白讲，", "你可能没想到，", "有一说一，",
            # V3新增：更丰富的口语化填充词
            "老实说，", "讲真的，", "平心而论，",
            "客观来看，", "往大了说，", "站在读者角度，",
            "说个冷知识，", "这里有个小细节，", "很多人不知道的是，",
            "从业内视角来看，", "说到这个我有个小发现，", "换个角度想想，",
            "这一点我觉得很关键，", "跟大家分享一个观察，",
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
    def _inject_pseudo_citations(cls, text: str) -> str:
        """V3新增：学术引用注入 — 在信息密集段落随机插入伪学术引用格式，增加人类感"""
        citations = [
            "据相关研究显示，", "有数据表明，", "从公开资料来看，",
            "业内人士透露，", "根据最新的调查报告，", "有分析指出，",
            "在此前的报道中提到，", "多位专家在接受采访时表示，",
            "综合多方信息源来看，", "来自权威机构的数据显示，",
        ]
        
        paragraphs = text.split('\n\n')
        inject_count = 0
        max_injects = 2
        
        for i in range(len(paragraphs)):
            p = paragraphs[i].strip()
            # 仅对含有数据或信息密集型的段落注入
            has_info_density = bool(re.search(r'\d+|%|数据|研究|报告|调查|统计', p))
            if (inject_count < max_injects
                and p and not p.startswith('#')
                and not p.startswith('>')
                and not p.startswith('[[')
                and len(p) > 60
                and has_info_density
                and random.random() > 0.7):
                # 在段落中找到第一个句号后插入引用
                first_period = p.find('。')
                if first_period > 10:
                    citation = random.choice(citations)
                    paragraphs[i] = p[:first_period+1] + citation + p[first_period+1:]
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
    def _fuzzify_numbers(cls, text: str) -> str:
        """V4新增：数字模糊化 — 将部分精确数字转化为约数表达，降低AI文本中过于精确的数据特征
        
        仅模糊化独立出现的、非关键的整数。保留带单位(%)、日期、年份、序号等不宜模糊的数字。
        """
        # 约数前缀词库
        fuzz_prefixes = ['大约', '将近', '差不多', '接近', '近', '约', '大概']
        
        def _should_fuzz(match):
            """判断该数字是否适合模糊化"""
            num_str = match.group(0)
            num = int(num_str)
            full_text = match.string
            start, end = match.start(), match.end()
            
            # 不模糊化: 年份(1900-2099)、序号(第X)、百分比(X%)、金额(X元/万/亿)、特定度量
            if 1900 <= num <= 2099:
                return num_str
            if start > 0 and full_text[start-1] in '第第':
                return num_str
            if end < len(full_text) and full_text[end] in '%％元万亿年月日号期岁度℃°':
                return num_str
            # 太小的数字(1-5)不模糊化——"3个"说"大约3个"很不自然
            if num < 10:
                return num_str
            
            # 30%概率执行模糊化，避免过度
            if random.random() > 0.3:
                return num_str
            
            prefix = random.choice(fuzz_prefixes)
            return f"{prefix}{num_str}"
        
        # 匹配独立的2-6位纯数字（避免匹配电话号码、ID等长数字串）
        result = re.sub(r'(?<!\d)(?<![a-zA-Z_\-])\b(\d{2,6})\b(?!\d)(?![%％元万亿年月日号期岁度℃°\.])', 
                       _should_fuzz, text)
        return result

    @classmethod
    def _vary_sentence_complexity(cls, text: str) -> str:
        """V4新增：句式复杂度扰动 — 在连续同长度句子中打破一致性
        
        AI生成的文本往往句长高度一致(每句20-30字)。本方法检测连续同长度句子，
        随机将其中一句拆分为两个短句或合并两个短句为一个复合句。
        """
        paragraphs = text.split('\n\n')
        new_paragraphs = []
        
        # 复合句连接词
        compound_connectors = ['——换句话说，', '，究其原因，', '，简而言之，', '，这也是为什么']
        
        for para in paragraphs:
            # 跳过标题、引用、占位符
            stripped = para.strip()
            if not stripped or stripped.startswith('#') or stripped.startswith('>') or stripped.startswith('[['):
                new_paragraphs.append(para)
                continue
            
            # 按中文句号分句
            sentences = [s.strip() for s in para.split('。') if s.strip()]
            if len(sentences) < 3:
                new_paragraphs.append(para)
                continue
            
            # 检测连续3句句长相似(差异<15字)
            modified = False
            result_sentences = []
            i = 0
            while i < len(sentences):
                if (i + 2 < len(sentences) 
                    and not modified
                    and abs(len(sentences[i]) - len(sentences[i+1])) < 15
                    and abs(len(sentences[i+1]) - len(sentences[i+2])) < 15
                    and random.random() > 0.5):
                    
                    action = random.choice(['split', 'merge'])
                    if action == 'split' and len(sentences[i+1]) > 30:
                        # 拆分中间句子
                        mid = len(sentences[i+1]) // 2
                        # 找最近的逗号作为拆分点
                        comma_pos = sentences[i+1].find('，', mid - 10)
                        if comma_pos > 0:
                            result_sentences.append(sentences[i])
                            result_sentences.append(sentences[i+1][:comma_pos])
                            result_sentences.append(sentences[i+1][comma_pos+1:])
                            result_sentences.append(sentences[i+2])
                            i += 3
                            modified = True
                            continue
                    elif action == 'merge' and len(sentences[i]) + len(sentences[i+1]) < 100:
                        # 合并前两句
                        connector = random.choice(compound_connectors)
                        merged = sentences[i] + connector + sentences[i+1]
                        result_sentences.append(merged)
                        i += 2
                        modified = True
                        continue
                
                result_sentences.append(sentences[i])
                i += 1
            
            new_paragraphs.append('。'.join(result_sentences) + ('。' if result_sentences else ''))
        
        return '\n\n'.join(new_paragraphs)

    @classmethod
    def _inject_context_echoes(cls, text: str) -> str:
        """V4新增：段间回照 — 在后段开头引用前文信息，模拟真人写作的前后呼应风格
        
        真人写作常有"正如前面提到的""回到开头说的那个问题"等回照，AI几乎不会产生这种模式。
        """
        echo_templates = [
            '正如前面提到的，',
            '回到刚才聊到的，',
            '结合上面说的，',
            '和前面的情况类似，',
            '呼应开头说的，',
            '延续之前的思路来看，',
        ]
        
        paragraphs = text.split('\n\n')
        if len(paragraphs) < 4:
            return text
        
        inject_count = 0
        max_injects = 1  # 整篇最多注入1次回照，保持自然
        
        # 仅在后半部分的段落中注入（回照通常出现在文章后半段）
        start_idx = len(paragraphs) // 2
        for i in range(start_idx, len(paragraphs)):
            p = paragraphs[i].strip()
            if (inject_count < max_injects
                and p and not p.startswith('#')
                and not p.startswith('>')
                and not p.startswith('[[')
                and not p.startswith('[图片')
                and not p.startswith('**')
                and len(p) > 50
                and random.random() > 0.65):
                echo = random.choice(echo_templates)
                paragraphs[i] = echo + p
                inject_count += 1
        
        return '\n\n'.join(paragraphs)

    @classmethod
    def _amplify_paragraph_variance(cls, text: str) -> str:
        """V5新增：段落长度方差放大
        
        AI倾向于生成长度接近的段落。本方法强制制造出极短段（单句成段）
        从而拉大段落长度方差。
        """
        paragraphs = text.split('\n\n')
        if len(paragraphs) < 4:
            return text
            
        new_paragraphs = []
        for p in paragraphs:
            # 20%概率将一个较长段落(包含多句)首句独立成段
            if random.random() < 0.2 and len(p) > 100 and not p.startswith('#') and '。' in p[:50]:
                first_period = p.find('。')
                # 寻找第一句结束(>10字符, <50字符)
                if 10 < first_period < 50:
                    new_paragraphs.append(p[:first_period+1])
                    new_paragraphs.append(p[first_period+1:].strip())
                    continue
            new_paragraphs.append(p)
            
        return '\n\n'.join(new_paragraphs)

    @classmethod
    def _inject_info_density_fluctuation(cls, text: str) -> str:
        """V5新增：信息密度波动注入
        
        AI文本信息密度均匀，每段都在输出干货。真人会在密集输出后插入
        "闲话"或"主观感受"来稀释密度。
        """
        dilution_phrases = [
            "仔细想想，这其实挺有意思的。",
            "不过话说回来，这也只是一个侧面。",
            "当然了，具体情况还得具体分析。",
            "这里有点扯远了，我们收回来继续看。",
            "不管怎么说，这也算是一个经验教训吧。",
        ]
        
        paragraphs = text.split('\n\n')
        for i in range(len(paragraphs)):
            p = paragraphs[i].strip()
            # 寻找信息密集的段落(包含较多逗号分句)并在之后注入稀释句
            if len(p) > 80 and not p.startswith('#') and p.count('，') > 3 and random.random() < 0.2:
                paragraphs[i] = p + random.choice(dilution_phrases)
                
        return '\n\n'.join(paragraphs)

    @classmethod
    def _inject_emotional_fluctuation(cls, text: str) -> str:
        """V6新增：情绪波动词注入
        
        AI说话总是客观中立四平八稳。真人写作在讲到核心痛点或惊人数据时，会有强烈的主观情绪反应。
        本方法在长段落末尾随机注入一句主观情绪强烈的短句，瞬间打破AI感。
        """
        emotions = [
            "真是让人倒吸一口凉气！",
            "这波操作简直绝了！",
            "说实在的，看到这里我都有点绷不住了。",
            "这谁顶得住啊！",
            "细思极恐。",
            "堪称教科书级别的操作。",
            "简直离谱！",
            "这种手段，确实让人叹为观止。",
            "懂的都懂。",
            "有点常识的人都能看出来其中的门道。"
        ]
        
        paragraphs = text.split('\n\n')
        inject_count = 0
        max_injects = 1 # 情绪词必须克制，全篇1次才最有爆发力
        
        # 倾向于在文章中后段的情绪高潮处注入
        start_idx = len(paragraphs) // 3
        for i in range(start_idx, len(paragraphs)):
            p = paragraphs[i].strip()
            if (inject_count < max_injects 
                and len(p) > 100 
                and not p.startswith('#')
                and not p.startswith('>')
                and '[[V-SCENE' not in p
                and random.random() > 0.75):
                
                # 如果段落已经有句号结尾，去掉句号加上情绪短句
                if p.endswith('。') or p.endswith('！') or p.endswith('？'):
                    paragraphs[i] = p + " 说句掏心窝子的话，" + random.choice(emotions)
                else:
                    paragraphs[i] = p + "。" + random.choice(emotions)
                inject_count += 1
                
        return '\n\n'.join(paragraphs)

    @classmethod
    def get_style_mimicry_prompt(cls) -> str:
        """V4增强：风格伪装提示词 — 新增数字模糊、句式变化、前后呼应等高级拟人策略"""
        return (
            "【去AI味强制指令（V4增强）】：\n"
            "1. 禁止使用高度对称的排比句、'首先/其次/最后'等机械结构。\n"
            "2. 使用长短句交错的行文，允许使用带有些许主观色彩的反问句。\n"
            "3. 行文必须像真人专家在直接向读者对话，而非AI在背诵条目。\n"
            "4. 【信息不对称表达】：文中至少1处使用'很多人不知道的是...'、'业内有个不成文的规矩...'等仅有经验者才会说的话术。\n"
            "5. 【个人经验置入】：在合适的段落自然地融入'我之前了解到'、'身边有朋友遇到过类似情况'等个人化表达。\n"
            "6. 【阅读互动暗示】：间歇性使用'你有没有想过'、'接下来这部分可能会颠覆你的认知'等与读者互动的手法。\n"
            "7. 【节奏变化】：重要信息前用短句铺垫(如'重点来了。')，阐述后用长句展开分析。\n"
            "8. 【数字自然化】：避免堆砌精确数字，适当使用'近百''数千''几成'等模糊表达，这更像人类记忆中的数字描述。\n"
            "9. 【前后呼应】：在文章后半段至少1次自然回顾前文提到的观点或案例，形成'首尾呼应'的真人写作风格。\n"
            "10. 【V5-信息密度波动】：不要全篇都是紧凑的高密度干货。在两段硬核分析之间，尝试插入一句完全口语化的个人感慨或闲扯，营造出'认真思考后喝了口水'的松弛感。\n"
            "(注意：如果系统要求你输出 JSON格式、工具参数调用、或是包含 Thought: / Action: 等流程控制的格式，"
            "请你必须严格遵守特定的格式要求，仅在正文内容本身应用上述去AI味风格。千万不要破坏系统要求的语法格式！)"
        )
