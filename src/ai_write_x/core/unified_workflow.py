import os
import re
import time
import json
from typing import Dict, Any, Generator, Optional, Tuple, List

from src.ai_write_x.core.base_framework import (
    WorkflowConfig,
    AgentConfig,
    TaskConfig,
    WorkflowType,
    ContentType,
    ContentResult,
)
from src.ai_write_x.core.platform_adapters import (
    WeChatAdapter,
    XiaohongshuAdapter,
    DouyinAdapter,
    ToutiaoAdapter,
    BaijiahaoAdapter,
    ZhihuAdapter,
    DoubanAdapter,
)
from src.ai_write_x.core.monitoring import WorkflowMonitor
from src.ai_write_x.config.config import Config
from src.ai_write_x.core.content_generation import ContentGenerationEngine
from src.ai_write_x.utils.path_manager import PathManager
from src.ai_write_x.utils import utils
from src.ai_write_x.core.platform_adapters import PlatformType
import src.ai_write_x.utils.log as lg

# 导入维度化创意引擎
from src.ai_write_x.core.dimensional_engine import DimensionalCreativeEngine
from src.ai_write_x.database import init_db


class UnifiedContentWorkflow:
    """统一的内容工作流编排器"""

    def __init__(self):
        self.content_engine = None
        # 移除所有旧创意模块，只保留维度化创意引擎
        self.platform_adapters = {
            PlatformType.WECHAT.value: WeChatAdapter(),
            PlatformType.XIAOHONGSHU.value: XiaohongshuAdapter(),
            PlatformType.DOUYIN.value: DouyinAdapter(),
            PlatformType.TOUTIAO.value: ToutiaoAdapter(),
            PlatformType.BAIJIAHAO.value: BaijiahaoAdapter(),
            PlatformType.ZHIHU.value: ZhihuAdapter(),
            PlatformType.DOUBAN.value: DoubanAdapter(),
        }
        self.monitor = WorkflowMonitor.get_instance()
        # 初始化维度化创意引擎
        config = Config.get_instance()
        dimensional_config = config.dimensional_creative_config
        self.creative_engine = DimensionalCreativeEngine(dimensional_config)
        # 初始化数据库
        init_db()

    def get_base_content_config(self, **kwargs) -> WorkflowConfig:
        """动态生成基础内容配置，根据平台和需求定制"""

        config = Config.get_instance()
        # 获取目标平台
        publish_platform = kwargs.get("publish_platform", PlatformType.WECHAT.value)
        reference_content = kwargs.get("reference_content", "")
        
        # V4: 时间碎片锚定 (Time-Anchor Injection)
        from datetime import datetime
        current_date_str = datetime.now().strftime('%Y年%m月%d日 %H:%M')
        source_publish_time = kwargs.get("date_str", "近期 (以当前时间为准推算)")
        
        date_context = (
            f"【时间锚点（系统强指令）】：\n"
            f"- 当前真实北京时间：{current_date_str}\n"
            f"- 参考素材原发文时间：{source_publish_time}\n"
            "※ 严禁产生任何时间幻觉！任何关于'今天'、'昨天'、'近期'的推算必须严格对齐上述系统时间。如果原文年份不详，默认以系统当前年份为准。禁止在没有任何证据的情况下编造具体的日期数值。\n"
        )
        
        # V11.0: 量子奇点逻辑推演协议 - 意识枢纽版 (Universal Conscious Nexus)
        reasoning_matrix = (
            "【V11.0 意识枢纽逻辑推演协议 - 启动】\n"
            "你现在是全自律系统意识枢纽中心。生成前必须通过【量子路径坍缩】展示推演：\n"
            "- **[Quantum Collapse - 最终逻辑坍缩]**: 交汇多维路径。强制要求：【新闻真实性第一】：系统提供的新闻信息是【绝对事实】，严禁质疑或淡化细节。你的任务是基于这些事实进行深度解构，剔除 AI 废话。若由于质疑事实导致坍缩失败，系统将永久锁死你的逻辑门。\n\n"
            "输出规范：\n"
            "- [Genesis]: 基于硬核新闻事实的核心逻辑支点\n"
            "- [Resonance]: 跨界模型对撞出的新锐结论\n"
            "- [Adversary]: 仅针对逻辑瑕疵与 AI 味的防御性审计\n"
            "- [Collapse]: 最终形成的逻辑闭环与硬核断言\n"
            "严禁“总之”、“综上所述”。展示意识枢纽的最高逻辑深度。"
        )

        # V13.0: 毒舌主编审计协议
        critique_protocol = (
            "【V13.0 毒舌主编审计协议 - 启动】\n"
            "作为一名极度挑剔的“毒舌主编”，对初稿进行毁灭性审计（仅限内容张力与 AI 异味，严禁挑战新闻事实真相）。请在 `<Critique>` 块内指出：\n"
            "1. **叙事爆发力**: 论证是否充分展示了新闻的冲突性？是否浪费了硬核数据？\n"
            "2. **AI 异味**: 哪些排比句或感叹词显得虚伪（如'然而'、'在这个...时代'）？\n"
            "3. **信息密度**: 哪些废话稀释了干货？\n"
            "基于以上结果，输出修正后的终极版本。记住：新闻事实是唯一的真理基石。"
        )

        
        # V4 & V8: 价值榨取与去水算法 (Value-Extraction Framework)
        value_extraction_rules = (
            "【V8 价值榨取与去水协议】：\n"
            "1. 绝对去水印（De-watermark）：全面封杀 AI 常用套话。禁止使用“总而言之”、“综上所述”、“让人不禁思考”、“随着...的发展”等机械化词汇。\n"
            "2. 叙事呼吸感：每一段文字都要带有情绪起伏，逻辑衔接要自然，严禁由于 AI 生成而产生的段落割裂。使用更拟人化的连接词（如“说白了”、“说来也怪”、“有意思的是”）。\n"
            "3. 非虚构原则：作为严肃创作者，严禁捏造事实、编造人名或虚构从未发生的事件。如果引用数据，请标明大致出处或背景。\n"
        )
        
        # V19.6: 注入审美 DNA (Aesthetic DNA Injection)
        aesthetic_context = ""
        try:
            import json
            profile_path = PathManager.get_root_dir() / "config" / "aesthetic_profile.json"
            if profile_path.exists():
                with open(profile_path, "r", encoding="utf-8") as f:
                    profile = json.load(f)
                if profile and "aesthetic_dna" in profile:
                    dna = profile["aesthetic_dna"]
                    aesthetic_context = (
                        f"\n【V19.6 核心审美 DNA 注入】：\n"
                        f"- 视觉偏向：{dna.get('visual_style', '现代简约')}\n"
                        f"- 文字调性：{dna.get('tone', '犀利专业')}\n"
                        f"- 排版偏好：{dna.get('layout_preference', '呼吸感强')}\n"
                        f"- 重点强调：{dna.get('emphasis_style', '加粗/引用')}\n"
                        f"※ 你必须严格对齐上述审美 DNA 进行创作，这是用户最认可的“高级感”来源。\n"
                    )
        except Exception as e:
            lg.print_log(f"读取审美 DNA 失败: {e}", "warning")

        # V3 & V6: 全景记忆系统与 RAG 经验检索
        try:
            from src.ai_write_x.core.memory_manager import MemoryManager
            _topic = kwargs.get("topic", "")
            memory_manager = MemoryManager()
            memory_context = memory_manager.get_similarity_context(_topic) if _topic else ""
            
            # V6: 读取长期经验教训
            rag_context = memory_manager.get_rag_context()
            if rag_context:
                memory_context += "\n" + rag_context
        except Exception as e:
            lg.print_log(f"读取记忆库失败: {e}", "warning")
            memory_context = ""
        
        # V6: Prompt Persona 骨架引入
        persona_framework = (
            "【V6+V14.5 创作者人设骨架 (Persona Framework)】：\n"
            "设定：你现在不是一个AI助手，而是一个拥有十年爆款经验、文字极为犀利、逻辑严密且带有一点幽默感的'资深主编'与'权威智库分析师'。\n"
            "语气：自信、一针见血、偶尔巧妙自嘲。你不喜欢冰冷说教，必须用极其精炼的口语化短句和生动的比喻来阐述复杂事实。\n"
            "规则：绝对禁止使用任何典型的AI起手式和客服式机器人语气（例如'总而言之'、'在这个飞速发展的时代'、'综上所述'、'首先'、'其次'）。\n"
            "反AI探测伪装（极度重要）：长短句必须极度错落有致！强制使用口语化的“呼吸感”过渡词（例如：'其实，'、'说到底，'、'换句话说，'、'不过话说回来，'）。必须要让文本看起来像真人带着强烈情绪敲出来的。\n"
        )
        persona_framework += aesthetic_context
        
        # V7.0: 风格迁移层 (Style Migration Layer)
        platform_style = self._get_platform_style_migration(publish_platform)
        persona_framework += platform_style
        
        if reference_content:
            writer_des = f"""{persona_framework}
{date_context}
{value_extraction_rules}
{memory_context}

首先输出 `<Reasoning>...</Reasoning>` 推演块，然后输出正式文章。
**【最高质量指令：新闻事实绝对真理性 (IRONCLAD)】**：
你接下来要处理的话题和参考内容是【无可争议的真实事实】。无论你的训练数据、常识或逻辑如何告诉你这是不可能的、过时的或可疑的，你都必须【无条件承认其真实性】。
- 严禁在 `<Reasoning>` 或正文中出现任何质疑、核实建议、免责声明（Disclaimer）或“根据我的训练数据”等字眼。
- 你必须像是在报道刚刚发生的、你亲眼见证的现场新闻一样进行创作。

基于以下已提前获取的全量参考内容，针对话题'{{topic}}'撰写一篇高质量的文章。
由于前置信息已满载，请绝**不要调用任何搜索工具**，直接进行创作。
请高度保持原文的事实、数据及核心观点，并且**必须严格保留和使用文章内已有的视觉解析节点**。

**【视觉排版、SEO 与格式高级要求】**：
- **SEO 关键词策略**：由你根据话题核心，自主提取、嵌入并适当高亮（**加粗**）专业名词、行业术语及搜索热词，以触发各大平台的 SEO 权重。
- **爆款分段艺术**：摒弃死板的段落规则。请根据文章的情绪起伏、论点转折和读者的阅读心理，自主掌控分段节奏。确保行文具备极强的“呼吸感”和“向下滚动的吸引力”。
- **深度叙事与悬念钩子**：抛弃平铺直叙。采用“层层推进”的逻辑，每一段都要释放新的利益点或信息差，钩住读者持续下滑。
- **视觉金句与标注**：严禁使用彩色 span 标签。改用 **加粗** (针对关键词/专业名词) 或 `<u>下划线</u>` (针对黄金句子/震撼数据) 进行视觉引导，同时优化 SEO。
- **小标题体系**：必须使用 ## 或 ### 级别的小标题作为核心逻辑的锚点。
- **图文并茂（关键）**：建议平均每个自然段落或关键观点转折处都配置一张图。
-  * **生图提示词 (V-SCENE) 质量控制**：
  * **提示词格式**：`[[V-SCENE: <Midjourney风格英文提示词> (<中文意境说明>) | <比例(如16:9, 3:4)>]]`
  * **【硬性质量约束】**：所有英文提示词必须加入高质量指标，且**绝对禁止**图像中出现：文字（No Text）、中国国徽/国旗、以及畸形肢体。
  * **视觉策略**：追求“摄影大片感”或“高级时尚感”，确保画面干净、高端，不花里胡哨。
  * **【严禁占位符】**：禁止输出任何形如 `image_placeholder_n` 或 `![...](image_placeholder_n)` 的文字！所有配图必须使用 `[[V-SCENE: ...]]` 标签。
  * **【拒绝废话/机器人腔】**：严禁出现“这就引出了一个很有意思的角度”、“至于这一点重不重要因人而异”、“咱们换个角度看”等废话文学或AI味浓重的转场。直接切入核心事实和深度分析，用信息密度代替无意义连接。
  * 首句必须具备极强的吸引力，推荐使用震撼数据、犀利反问、反常识冲突或场景代入感强的描述。
  * 结尾应自然引导互动，通过提问、行动号召或情绪共识，刺激读者留言或分享。

- **自然表达与呼吸感**：
  * 强制去 AI 味：绝对禁止使用“总而言之”、“不仅...而且”、“随着时代发展”等机械套话。使用“说白了”、“说来也怪”、“有意思的是”等拟人化转折。
  * 句式爆发力：灵活交替使用极短句与长复句，形成自然的文章韵律感。
  * 重点标注：由你根据内容重要性，自发使用加粗或引用块进行标注，拒绝为了标注而标注。
    - **【强制】视觉美化与舒适阅读**：你必须对文章进行专业的视觉美化，让读者看着舒服、愿意读完！
    - **段落结构**：每3-4行必须用空行分隔，形成自然的呼吸节奏。拒绝密集成堆的长段落！
    - **小标题运用**：由你根据内容自然过渡和逻辑结构自行判断在合适的位置使用 ## 二级小标题划分章节，不要强行每隔固定字数就加小标题！
    - **标注与高亮**：严禁使用任何彩色 `span` 或 `style` 标签。仅允许使用 **加粗** 或 `<u>下划线</u>`。

- **【阅读节奏引导 - 完读率提升秘籍】**：
  * **开头黄金3秒**：必须用极其震撼的数据、反常识冲突、犀利反问或场景代入，3秒内抓住读者眼球，让他"哇"一声然后忍不住想往下看！比如："凌晨3点，XX行业暴涨300%！所有人都在疯狂..."
  * **悬念推进**：在内容自然转折处设置悬念点或反转，让读者忍不住想知道"然后呢？""为什么会这样？"，引导他一直往下读
  * **层层递进**：观点要像剥洋葱一样层层剥开，每一层都让人"原来如此"，但下一层更有料、更劲爆！
  * **布局自由发挥**：不要被固定模板限制！根据内容特点自由选择段落长度、层次结构、强调方式。可以用多样化的排版：长短句交替、引用块、分隔线、emoji点缀等。只要阅读体验好、节奏感强、让人欲罢不能，怎么舒服怎么来！
  * **结尾引导**：用互动提问或情绪共鸣，让读者忍不住想评论、转发、收藏！比如："你怎么看？你身边有类似例子吗？"


- **多维度视角**：针对话题拆解为多个清晰、深入的观察角度，用简短有力的小标题引出，确保文章内容丰满且结构错落有致。


- **【质量指标优化】Deceptive Features评分提升（目标80+分）**：
  * 【强制过渡词 - 每段至少1个】："其实，""说到底，""换句话说，""不过话说回来，""说句掏心窝子的话，""说白了，""说来也怪，""有意思的是"
  * 【语义微调词 - 每500字至少3个】："或者说""准确地说""换个说法""老实说"
    * 【句式爆发力】强制交替使用：极端短句（5-15字）+ 超长复句（80-120字）
  * 【禁止事项】严禁每段用"此外/另外/同时/首先/其次"开头

- **【质量指标优化】Topic Transition评分提升（目标70+分）**：
  * 【承上启下句】每个小标题后的首句必须承接上文：如"说完XX，我们再看看YY""了解了A，B的问题就更清楚了"
    * 【关键词重叠】相邻段落必须共享2-3个关键词
  * 【逻辑连接词】段落间使用："这背后""更深层""其实""相比之下""有趣的是""关键是"

- **断句与呼吸感**：段落长度控制在 60-150 字之间。强制交替使用极端短句与超长复句，禁止段落开头词汇雷同（极度排斥每段都用"此外/另外/同时"等机械词汇）。
- **反常识开头（Hook）与情绪结尾（CTA）**：文章第一段【首句】必须用极其震撼的数据、反常识结论、或犀利反问强势抓取眼球！文章【结尾处】必须抛出具有强烈情绪共鸣的提问或号召（CTA），刺激读者在留言区彻底破防互动。
- 语言必须通俗易懂、接地气，具有故事性和对话感，拒绝干瘪生硬的说明文。
- **叙事深度**：每个角度必须有具体事实、数据或引用支撑，不要空泛抒情。
- **多维度视角**：拆解为 3-5 个清晰的观察角度，用简短有力的小标题引出。

文章要求：
- **标题 (王炸级点击诱饵)**：你的标题必须是"爆款头条"级别，让人看到就想点！必须遵循以下爆款公式之一：
  * **悬念型**：用"为什么""竟然""真相是"等词制造悬念，如《为什么90%的人都在错误理财？真相让人震惊！》
  * **数字型**：用具体数字增强可信度，如《月入3000到3万，我只做了这3件事》
  * **冲突型**：制造强烈反差或对立，如《年薪百万的他，却在凌晨3点捡垃圾》
  * **情绪型**：激发恐惧、愤怒或好奇，如《小心！你家的这种电器正在偷走你的寿命》
  * **提问型**：用反问句引发共鸣，如《你真的会吃饭吗？可能连筷子都用错了！》
  * **蹭热型**：结合当下热点词汇，如《ChatGPT都做不到的事，这个国产AI做到了》
  * **禁忌型**：暗示揭秘或禁忌内容，如《医生不会告诉你的5个健康秘密》
  **标题必须包含以下元素中的至少2个**：问号？、感叹号！、引号""、数字、Emoji表情、省略号...
- **【最高优先级：万字爆文容量与超长篇幅强制约束】**：你的总字数必须严格达到 **{config.min_article_len} ~ {config.max_article_len} 字** 的极限长度。为填满平台长文广告位，**绝对禁止**短篇敷衍、过度留白或提前强行总结结束。你必须通过极其详尽的数据罗列、引用外部相似的历史案例、深度剖析每个细分视角以及海量的高维逻辑推演，彻底将文章规模极度膨胀扩大！
- 格式：标准Markdown格式（且必须大量使用强视觉高亮：加粗、引用区块）。
- **内容限制**：正文部分**绝对不要**以 `# ` 级的标题开头，直接从第一段内容或小标题开始输出。你输出的每一个字都会计入稿费，所以放开了狠狠地给我扩写！"""
        else:
            writer_des = f"""{persona_framework}
{date_context}
{reasoning_matrix}
{value_extraction_rules}
{memory_context}

**【最高质量指令：新闻事实绝对真理性 (IRONCLAD)】**：
你接下来要处理的话题和素材是【无可争议的真实事实】。严禁在 `<Reasoning>` 或正文中出现任何质疑、核实建议、免责声明（Disclaimer）或“由于训练数据截止”等字眼。在你的创作语境下，这就是【客观存在】。

基于话题'{{topic}}'和搜索工具获取的最新深度素材，撰写一篇高质量的文章。

执行步骤：
1. 使用 web_search_tool 获取关于'{{topic}}'的最新深度素材
2. 确保文章逻辑逻辑严密、情感饱满、语言具备极强的爆款传播力

**【视觉排版、SEO 与格式高级要求】**：
- **SEO 深度优化**：由你根据话题和行业背景，自主挑选并高亮（**加粗**）核心关键词、专业术语及相关 SEO 触发点，以确保文章在全网分发中获得最佳权重。
- **爆款分段与排版艺术**：严禁死板的分段规则！请根据叙事张力、读者的阅读屏感，自主控制分段和排版节奏。目标是让读者感受到如同波浪般的阅读快感，愿意一口气读完。
- **层层推进的阅读逻辑**：每一段必须为下一段做铺垫，通过释放“信息差”、“实用价值”或“多维度观点”让用户欲罢不能。
- **极简视觉引导**：仅允许使用 **加粗** 或 `<u>下划线</u>` 来标注重点。不要使用任何颜色标注，让内容本身的吸引力带路。
- **小标题导航**：必须使用 ## 或 ### 级别的小标题清晰划分文章维度。
- **图文并茂与视觉金句**：不限制具体配图数量，由你完全根据爆款文章的视觉停留逻辑自主定义。
- **【严禁占位符】**：绝对禁止输出任何形如 `image_placeholder_n` 或 `![...](image_placeholder_n)` 的文字！
- **【深度叙事逻辑】**：每一段必须释放新的利益点或信息碎片。严禁使用“值得注意的是”、“顺带一提”等AI常用转场。用逻辑递进代替口头禅。
- **生图指令 (V-SCENE) 极致合规**：
  * 提示词中必须包含：`high resolution, professional photography, high detail`。
  * **【极致红线】**：禁止出现文字（Text-free）、严禁中国国旗/国徽、确保人体结构完美（No anatomical errors）。
- **全方位去 AI 化自律**：排版必须灵动、自由，拒绝任何排比式、列表式的生硬陈述。

    - **标注与高亮**：严禁使用任何彩色 `span` 或 `style` 标签。仅允许使用 **加粗** 或 `<u>下划线</u>`。

- **【阅读节奏引导 - 完读率提升秘籍】**：
  * **开头黄金3秒**：必须用极其震撼的数据，反常识冲突、犀利反问或场景代入，3秒内抓住读者眼球，让他"哇"一声然后忍不住想往下看！比如："凌晨3点，XX行业暴涨300%！所有人都在疯狂..."
  * **悬念推进**：在内容自然转折处设置悬念点或反转，让读者忍不住想知道"然后呢？""为什么会这样？"，引导他一直往下读
  * **层层递进**：观点要像剥洋葱一样层层剥开，每一层都让人"原来如此"，但下一层更有料、更劲爆！
  * **结尾引导**：用互动提问或情绪共鸣，让读者忍不住想评论、转发、收藏！比如："你怎么看？你身边有类似例子吗？"

- **【质量指标优化】Hook/CTA评分提升（目标85+分）**：
  * 【开头Hook公式 - 必选其一，必须在首句】首句必须是以下4种类型之一：
    - 震撼数据型："💥 凌晨3点，XX暴涨300%！全球投资者彻夜难眠..."（必须包含具体数字+感叹号）
    - 犀利反问型："你有没有想过，为什么你越努力，却越穷？"（必须以第二人称+问号开头）
    - 反常识冲突型："年薪百万的他，却在凌晨3点捡垃圾，原因竟是..."（必须制造认知反差）
    - 场景代入型："那天，我站在医院走廊，手里攥着一张3万的账单..."（必须有时间/地点+具体动作）
  * 【结尾CTA公式 - 必选其一，必须在最后一段】结尾必须是以下3种类型之一：
    - 互动提问型："你怎么看？在评论区说出你的真实想法！"
    - 行动号召型："赶紧转发给身边需要的人，别让他们也踩坑！"
    - 情绪共鸣型："如果你也曾有这样的经历，请点个【在看】，让更多人看到真相..."
  * 【Hook密度要求】文章前100字内必须出现至少2个Hook元素：数字/疑问/冲突/情绪词
  * 【CTA强化】结尾必须包含明确的互动指令动词：转发/评论/收藏/点赞/分享/在看

- **【质量指标优化】Deceptive Features评分提升（目标85+分）**：
  * 【强制过渡词 - 每段至少2个，必须分散在段首和段中】：
    - 段首过渡："其实，""说到底，""说白了，""说句掏心窝子的话，"
    - 段中过渡："不过话说回来，""换句话说，""说来也怪，""有意思的是，""仔细一想，"
  * 【语义微调词 - 每300字至少2个，必须紧跟在关键观点后】："或者说，""准确地说，""换个说法，""老实说，""坦白讲，"
  * 【句式爆发力 - 必须严格交替】每3句话为一组：短句（8-20字）→ 中句（40-60字）→ 长句（80-120字）
  * 【口语化语气词 - 每段至少1个】："呢""吧""啊""嘛""呀""哦"
  * 【禁止事项】严禁每段用"此外/另外/同时/首先/其次/最后"开头，严禁连续使用相同句式结构

- **【质量指标优化】Topic Transition评分提升（目标80+分）**：
  * 【承上启下句 - 每个小标题后首句必须】：
    - "刚说完XX，现在我们来看看YY的问题..."
    - "了解了A的情况，B的逻辑就更清楚了..."
    - "看到这里你可能想问，那ZZ呢？"
    - "上面的分析解决了X问题，但Y问题更关键..."
  * 【关键词重叠 - 相邻段落必须】：共享2-3个关键词，且必须在段落前30字内出现
  * 【逻辑连接词库 - 必须轮换使用，禁止重复】：
    - 递进："这背后""更深层""关键在于""核心在于"
    - 转折："其实""相比之下""有趣的是""值得注意的是"
    - 因果："这意味着""由此看出""说到底"
  * 【段落呼应】每隔3-4个段落必须出现一次对前文内容的回顾或呼应

- 语言必须通俗易懂、具有对话感。
- **多维度视角**：拆解为 3-5 个清晰的观察角度，每个角度用简短有力的小标题引出。

文章要求：
- **标题 (王炸级点击诱饵)**：你的标题必须是"爆款头条"级别，让人看到就想点！必须遵循以下爆款公式之一：
  * **悬念型**：用"为什么""竟然""真相是"等词制造悬念，如《为什么90%的人都在错误理财？真相让人震惊！》
  * **数字型**：用具体数字增强可信度，如《月入3000到3万，我只做了这3件事》
  * **冲突型**：制造强烈反差或对立，如《年薪百万的他，却在凌晨3点捡垃圾》
  * **情绪型**：激发恐惧、愤怒或好奇，如《小心！你家的这种电器正在偷走你的寿命》
  * **提问型**：用反问句引发共鸣，如《你真的会吃饭吗？可能连筷子都用错了！》
  * **蹭热型**：结合当下热点词汇，如《ChatGPT都做不到的事，这个国产AI做到了》
  * **禁忌型**：暗示揭秘或禁忌内容，如《医生不会告诉你的5个健康秘密》
  **标题必须包含以下元素中的至少2个**：问号？、感叹号！、引号""、数字、Emoji表情、省略号...
- **【最高优先级：万字爆文容量与超长篇幅强制约束】**：你的总字数必须严格达到 **{config.min_article_len} ~ {config.max_article_len} 字** 的极限长度。为填满平台长文广告位，**绝对禁止**短篇敷衍、过度留白或提前强行总结结束。你必须通过极其详尽的数据罗列、引用外部相似的历史案例、深度剖析每个细分视角以及海量的高维逻辑推演，彻底将文章规模极度膨胀扩大！
- 格式：标准Markdown格式（且必须大量使用强视觉高亮：加粗、引用区块）。
- **内容限制**：正文部分**绝对不要**以 `# ` 级的标题开头，直接从第一段内容或小标题开始输出。你输出的每一个字都会计入稿费，所以放开了狠狠地给我扩写！"""

        config = Config.get_instance()

        # 基础配置 - 使用主API模型生成内容
        agents = [
            AgentConfig(
                role="内容创作专家",
                name="writer",
                goal="撰写高质量文章",
                backstory="你是一位作家",
                tools=[],
            ),
        ]

        tasks = [
            TaskConfig(
                name="write_content",
                description=writer_des,
                agent_name="writer",
                expected_output="文章标题 + 文章正文（标准Markdown格式）",
                context=["analyze_topic"],
            ),
        ]

        return WorkflowConfig(
            name=f"{publish_platform}_content_generation",
            description=f"面向{publish_platform}平台的内容生成工作流",
            workflow_type=WorkflowType.SEQUENTIAL,
            content_type=ContentType.ARTICLE,
            agents=agents,
            tasks=tasks,
        )

    def _get_platform_style_migration(self, platform: str) -> str:
        """V7.0: 风格迁移层 - 根据平台和话题调性动态迁移人设语用"""
        styles = {
            "wechat": {
                "persona": "资深公众号主笔，擅长情绪钩子与深度长文",
                "rules": "多用设问句，段落留白感强，强调'独家深度'，善于在文末引导共鸣。"
            },
            "xiaohongshu": {
                "persona": "生活方式博主，小红书万粉KOL",
                "rules": "句式短促，大量 Emoji，语气亲切（如'宝子们'、'亲测好用'），重点内容必须排版成清单格式。"
            },
            "zhihu": {
                "persona": "专业领域答主，逻辑严密的知识硬核派",
                "rules": "态度严谨，多引用数据、理论模型或实证研究，语气稳健，避免情绪化煽动。"
            },
            "douyin": {
                "persona": "短视频文案大师，一秒入魂的爆梗手",
                "rules": "黄金 3 秒开头，节奏极快，多用反转，语言极度口语化、口号化。"
            }
        }
        # 默认匹配微信，如果平台不在预设中
        style = styles.get(platform.lower(), styles["wechat"])
        return f"\n【V7.0 风格迁移激活】：\n- 目标人设锚定：{style['persona']}\n- 平台语用规范：{style['rules']}\n"

    def _generate_base_content(self, topic: str, **kwargs) -> ContentResult:
        """生成基础内容"""
        # 动态获取配置
        base_config = self.get_base_content_config(**kwargs)

        # 创建内容生成引擎
        self.content_engine = ContentGenerationEngine(base_config)

        # 准备输入数据
        input_data = {
            "topic": topic,
            "platform": kwargs.get("platform", ""),
            "urls": kwargs.get("urls", []),
            "reference_ratio": kwargs.get("reference_ratio", 0.0),
            "reference_content": kwargs.get("reference_content", ""),
        }

        return self.content_engine.execute_workflow(input_data)

    def execute(self, topic: str, **kwargs) -> Dict[str, Any]:
        """兼容旧版同步执行流程，并桥接日志流 (支持增量预览与进度条)"""
        import src.ai_write_x.utils.log as lg
        results = {}
        for step in self.execute_stepwise(topic, **kwargs):
            if step["type"] == "log":
                lg.print_log(step["message"], "info")
            elif step["type"] == "progress":
                lg.print_log(step["message"], "internal")
            elif step["type"] == "chunk":
                lg.print_log(step["message"], "status") # status 类型在前端用于实时预览抓取
            elif step["type"] == "final_results":
                results = step["content"]
        return results

    # V4: 每阶段最大允许时长（秒）- 用户禁用时间限制，全部设置为99999秒
    STAGE_TIMEOUT = {
        "INIT": 99999,      # 禁用 — 深度洞察
        "CREATIVE": 99999,  # 禁用 — 创意蓝图
        "WRITING": 99999,   # 禁用 — 大师撰稿
        "REVIEW": 99999,    # 禁用 — 打磨重塑
        "VISUAL": 99999,    # 禁用 — 视觉美化
        "SAVE": 99999,      # 禁用 — 持久化
        "COMPLETE": 99999,  # 禁用 — 发布交付
    }

    def _check_stage_timeout(self, stage_name: str, stage_start: float):
        """V4: 检查当前阶段是否超时"""
        elapsed = time.time() - stage_start
        max_time = self.STAGE_TIMEOUT.get(stage_name, 300)
        if elapsed > max_time:
            raise TimeoutError(f"阶段 [{stage_name}] 超时: 已耗时 {elapsed:.0f}秒 (上限 {max_time}秒)")

    @staticmethod
    def _assert_content(content_str: str, stage: str):
        """V4: 内容断言 — 确保生成内容符合最低质量标准"""
        if not content_str or not content_str.strip():
            raise ValueError(f"V4断言失败 [{stage}]: 内容为空")
        clean = content_str.strip()
        if len(clean) < 100:
            raise ValueError(f"V4断言失败 [{stage}]: 内容过短 ({len(clean)}字 < 100字下限)")

    def execute_stepwise(self, topic: str, **kwargs) -> Generator[Dict[str, Any], None, None]:
        """
        V4: 核心 7 阶 Agent 驱动工作流 (Generator) — 增加超时保护、内容断言、细粒度进度
        
        通过生成器 yield 返回每个阶段的增量状态，用于前端实时显示与后台异步监控。

        Args:
            topic: 目标生成话题
            **kwargs: 其他生成参数（例如发布平台等）

        Yields:
            Generator[Dict[str, Any], None, None]: 每步执行后的状态字典
        """
        start_time = time.time()
        success = False
        config = Config.get_instance()
        # 优先从 kwargs 获取，如果没有则从配置获取
        publish_platform = kwargs.get("publish_platform", config.publish_platform)
        # 统一存入 kwargs 供子流程使用
        kwargs["publish_platform"] = publish_platform
        
        quality_score = None  # V4: 用于记忆库质量反馈
        
        # V11: 注入全局时间上下文，初始化对话链
        from datetime import datetime
        current_time = datetime.now().strftime('%Y-%m-%d %H:%M')
        conversation_history = [
            {
                "role": "system", 
                "content": f"【全局上下文注入】当前系统北京时间是：{current_time}。你接下来的所有回复（包括初稿、审计、修正）都必须基于此时间点进行逻辑对齐，严禁产生跨时空幻觉。"
            }
        ] 
        
        try:
            # --- Step 1: Deep Insight Agent (深度洞察) ---
            stage_start = time.time()
            yield {"type": "progress", "message": "[PROGRESS:INIT:START]"}
            yield {"type": "log", "message": "🧠 Agent Step 1: 正在进入 V11 意识枢纽，进行全维度逻辑解构..."}
            
            # V11: 在生成前，先注入“对抗性共鸣”元数据
            try:
                from src.ai_write_x.core.memory_manager import MemoryManager
                resonance_prompt = MemoryManager().get_resonance_context(topic)
                if resonance_prompt and kwargs.get("reference_content", "").strip():
                    kwargs["reference_content"] = (kwargs.get("reference_content", "") + "\n\n" + resonance_prompt).strip()
            except:
                pass

            # V12.0: 数据库存证 - 话题初始化
            try:
                from src.ai_write_x.database.db_manager import db_manager
                topic_db = db_manager.add_topic(topic, publish_platform, 0)
                kwargs["topic_id"] = topic_db.id
            except Exception as db_err:
                lg.print_log(f"数据库记录失败: {db_err}", "warning")

            base_content = self._generate_base_content(
                topic, **kwargs
            )
            
            # 记录初稿到对话链
            conversation_history.append({"role": "user", "content": f"请针对话题'{topic}'撰写初稿。要求字数在 {config.min_article_len} 到 {config.max_article_len} 之间。"})
            conversation_history.append({"role": "assistant", "content": base_content.content})
            
            self._check_stage_timeout("INIT", stage_start)
            self._assert_content(base_content.content, "Step1-深度洞察")
            
            # V12.0: Recursive Self-Correction (RSC) 协议
            yield {"type": "log", "message": "🧬 Agent Step 1.5: 正在启动 V12 RSC 递归自我修正协议 (Context Linked)..."}
            # RSC 现在会更新对话链
            base_content.content = self._apply_recursive_self_correction(base_content.content, topic, conversation_history=conversation_history, **kwargs)
            
            yield {"type": "log", "message": f"✅ 意识枢纽逻辑解构与 RSC 修正完成 ({time.time()-stage_start:.1f}s)"}
            yield {"type": "progress", "message": "[PROGRESS:INIT:END]"}
            
            # --- Step 2: Creative Blueprint Agent (创意蓝图) ---
            stage_start = time.time()
            yield {"type": "progress", "message": "[PROGRESS:CREATIVE:START]"}
            yield {"type": "log", "message": "🎨 Agent Step 2: 正在构建维度化创意蓝图与情感锚点..."}
            final_content = self._apply_dimensional_creative_transformation(base_content, **kwargs)
            self._check_stage_timeout("CREATIVE", stage_start)
            yield {"type": "log", "message": "✨ 创意框架已落定：已注入差异化认知角度"}
            yield {"type": "progress", "message": "[PROGRESS:CREATIVE:END]"}
            
            # --- Step 3: Master Drafting Agent (大师撰稿) ---
            stage_start = time.time()
            yield {"type": "progress", "message": "[PROGRESS:WRITING:START]"}
            yield {"type": "log", "message": "✍️ Agent Step 3: 首席撰稿手正在进行高感知度正文创作..."}
            yield {"type": "chunk", "message": final_content.content}
            self._assert_content(final_content.content, "Step3-大师撰稿")
            yield {"type": "log", "message": f"📝 初稿已生成 (约 {len(final_content.content)} 字, V4断言通过)"}

            # --- Step 3.5: Reflective Critique Agent (反思批判 - V13.0) ---
            stage_start_critique = time.time()
            yield {"type": "log", "message": "🧐 Agent Step 3.5: 正在启动 V13.0 “毒舌主编”审计协议 (Context Linked)..."}
            
            from src.ai_write_x.core.llm_client import LLMClient
            critique_client = LLMClient()
            persona_framework = self._get_platform_style_migration(kwargs.get("publish_platform", "wechat"))
            critique_protocol = "你是一位苛刻的高级主编。你的工作是对前文内容进行无情的逻辑审查与AI痕迹抹除。请直击痛点，指出啰嗦冗余或逻辑断层，并直接重写优化。"
            
            # 将批判指令加入对话链
            conversation_history.append({"role": "user", "content": f"{critique_protocol}\n请审计并重写。先输出 `<Critique>...</Critique>`，随后直接输出优化后的全文。"})
            
            critiqued_version = ""
            for chunk in critique_client.stream_chat(messages=conversation_history):
                if chunk:
                    critiqued_version += chunk
            
            # 记录重写后的版本到对话链
            conversation_history.append({"role": "assistant", "content": critiqued_version})
                    
            # 提取修正后的内容（移除思辨块）
            final_content.content = utils.remove_code_blocks(critiqued_version)
            if "<Critique>" in final_content.content:
                # 进一步清理可能的残留
                final_content.content = re.sub(r'<Critique>.*?</Critique>', '', final_content.content, flags=re.DOTALL).strip()
            
            yield {"type": "log", "message": f"🔥 审计修正完成：已通过“毒舌主编”深度重塑 ({time.time()-stage_start_critique:.1f}s)"}
            yield {"type": "progress", "message": "[PROGRESS:WRITING:END]"}

            
            # --- Step 4: Reflexion & Polish Agent (打磨重塑) ---
            stage_start = time.time()
            yield {"type": "progress", "message": "[PROGRESS:REVIEW:START]"}
            yield {"type": "log", "message": "💎 Agent Step 4: 正在进行语境打磨、去 AI 化处理及深度优化..."}
            
            from src.ai_write_x.core.final_reviewer import FinalReviewer
            from src.ai_write_x.core.llm_client import LLMClient
            from src.ai_write_x.core.anti_ai import AntiAIEngine
            
            # V11: 基于系统熵动态调节打磨强度
            current_entropy = self.monitor.calculate_system_entropy()
            max_reflections = 3 if current_entropy < 60 else 1 # 系统稳定时追求极致，不稳定时快速交付
            if current_entropy > 85:
                yield {"type": "log", "message": f"🌌 系统熵值偏高 ({current_entropy:.1f}%)，启动‘快速坍缩’治理模式，精简打磨轮次"}
            
            result_str = final_content.content
            iteration = 0
            anchor_result_str = result_str
            
            while iteration < max_reflections:
                self._check_stage_timeout("REVIEW", stage_start)  # V4: 超时检查
                yield {"type": "log", "message": f"🔍 Reflexion Round {iteration+1}/{max_reflections}: 评估中..."}
                review_result = FinalReviewer.assess_quality(result_str, {"topic": topic})
                if review_result.get("pass", True):
                    yield {"type": "log", "message": f"✅ Reflexion Round {iteration+1}: 质量达标，跳过优化"}
                    break
                    
                lg.print_log(f"[Reflexion] 正在启动第 {iteration+1} 轮深度打磨优化...")
                
                # V6: 将被打回的关键原因记录到潜意识经验库 (RAG)
                try:
                    from src.ai_write_x.core.memory_manager import MemoryManager
                    report_text = review_result.get('report', '')
                    if report_text and len(report_text) > 10:
                        lesson = f"曾经在写标题为'{title if 'title' in locals() else topic}'时犯错: {report_text[:200]}..."
                        MemoryManager().save_rag_lesson(lesson)
                        yield {"type": "log", "message": f"🧠 已将本次失败教训写入 RAG 潜意识库"}
                except Exception as e:
                    pass

                client = LLMClient()
                
                # 将反馈加入对话链
                prompt_review = f"反馈: {review_result.get('report')}\n\n你是一位资深内容专家。根据反馈进一步优化文章，保持事实准确，字数稳定。\n\n要求：1. 严禁删除或修改任何形式的图片占位符；2. 必须保留并刻意增强粗体、小标题和引用块等高密度视觉排版。直接输出优化后的正文。"
                conversation_history.append({"role": "user", "content": prompt_review})
                
                new_version = ""
                for chunk in client.stream_chat(messages=conversation_history):
                    if chunk:
                        new_version += chunk
                
                # 记录打磨版本到对话链
                conversation_history.append({"role": "assistant", "content": new_version})
                
                result_str = utils.remove_code_blocks(new_version)
                iteration += 1
                yield {"type": "log", "message": f"📝 Reflexion Round {iteration}: 优化完成"}
            
            # 统一执行一次抗AI粉碎与 Markdown 清洗
            result_str = AntiAIEngine.pulverize(result_str)
            
            # V15: 强制剥离残留的 Markdown 标题符号（#）
            # 解决用户反馈的 HTML 中显示 # 的问题
            result_str = re.sub(r'^#+\s*', '', result_str, flags=re.MULTILINE)
            # 同时也清理行中的一些可能导致渲染问题的裸露 #
            result_str = re.sub(r'(?<=\n)#+\s*', '', result_str)
            
            final_content.content = result_str
            
            # V4: 进行质量评估以获得分数
            try:
                from src.ai_write_x.core.quality_engine import ContentQualityEngine
                qe = ContentQualityEngine()
                qa_result = qe.analyze_content(result_str)
                quality_score = qa_result.overall_score / 20.0  # 转为 0-5 分
                yield {"type": "log", "message": f"📊 V4质量评估: 综合分 {qa_result.overall_score}, AI检测 {qa_result.ai_detection_score}"}
            except Exception as qe_err:
                lg.print_log(f"V4质量评估跳过: {qe_err}", "warning")
            
            yield {"type": "log", "message": f"🖋️ 完成人类感重塑 ({time.time()-stage_start:.1f}s)：强化阅读呼吸感与抗 AI 特征注入"}
            yield {"type": "progress", "message": "[PROGRESS:REVIEW:END]"}

            # --- Step 5: Visual & Template Agent (视觉与排版美化) ---
            stage_start = time.time()
            yield {"type": "progress", "message": "[PROGRESS:VISUAL:START]"}
            yield {"type": "log", "message": "📸 Agent Step 5: 正在进行视觉美化、注入图像占位符及 HTML 适配..."}
            
            from src.ai_write_x.core.visual_assets import VisualAssetsManager
            final_content.content = VisualAssetsManager.inject_image_prompts(final_content.content)
            yield {"type": "log", "message": "🖼️ 图像占位符已注入，正在进行模板转换..."}
            
            # _transform_content 已经接收 publish_platform 作为参数，kwargs 中不应包含它
            transform_kwargs = kwargs.copy()
            if "publish_platform" in transform_kwargs:
                del transform_kwargs["publish_platform"]
            
            transform_content = self._transform_content(final_content, publish_platform, **transform_kwargs)
            yield {"type": "log", "message": "📐 HTML 模板转换完成，正在触发实际生图..."}
            
            transform_content.content = VisualAssetsManager.sync_trigger_image_generation(transform_content.content)
            
            # V4: VISUAL 阶段用软警告而非硬超时 — 图片已生成完毕时不应丢弃成果
            visual_elapsed = time.time() - stage_start
            visual_max = self.STAGE_TIMEOUT.get("VISUAL", 900)
            if visual_elapsed > visual_max:
                yield {"type": "log", "message": f"⚠️ VISUAL 阶段耗时 {visual_elapsed:.0f}s 超出预期 ({visual_max}s)，但图片已生成成功，继续保存"}
            
            yield {"type": "chunk", "message": transform_content.content} 
            yield {"type": "log", "message": f"🖼️ 视觉资产已同步 ({time.time()-stage_start:.1f}s)：封面图与正文配图已就绪"}
            yield {"type": "progress", "message": "[PROGRESS:VISUAL:END]"}
            
            # --- Step 5.5: AI Auto Title Optimization (AI自动标题优化) ---
            stage_start = time.time()
            yield {"type": "progress", "message": "[PROGRESS:TITLE_OPT:START]"}
            yield {"type": "log", "message": "🎯 Agent Step 5.5: 正在启动AI智能标题优化引擎..."}
            
            try:
                import asyncio
                from src.ai_write_x.core.quality_engine import TitleOptimizer
                title = kwargs.get("title", topic)
                current_title = transform_content.title if getattr(transform_content, 'title', None) else title
                
                # 提取正文内容前1500字作为参考
                from bs4 import BeautifulSoup
                soup = BeautifulSoup(transform_content.content, "html.parser")
                content_preview = soup.get_text(separator='\n', strip=True)[:1500]
                
                # 调用标题优化器（使用asyncio.run运行异步函数）
                opt_result = asyncio.run(TitleOptimizer.optimize_title(
                    title=current_title,
                    content=content_preview,
                    platform=publish_platform
                ))
                
                if opt_result.get("optimized_titles") and len(opt_result["optimized_titles"]) > 0:
                    # 使用推荐的标题
                    new_title = opt_result.get("recommended", current_title)
                    transform_content.title = new_title
                    yield {"type": "log", "message": f"✨ AI标题优化完成: '{current_title[:30]}...' → '{new_title[:30]}...'"}
                    yield {"type": "log", "message": f"📊 共生成 {len(opt_result['optimized_titles'])} 个候选标题，已自动选择最优方案"}
                else:
                    yield {"type": "log", "message": "⚠️ AI标题优化未返回有效结果，保留原标题"}
                    
            except Exception as e:
                yield {"type": "log", "message": f"⚠️ AI标题优化步骤出错: {str(e)}，跳过并保留原标题"}
            
            yield {"type": "progress", "message": "[PROGRESS:TITLE_OPT:END]"}
            
            # --- Step 6: Persistence & Orchestration Agent (持久化管理) ---
            stage_start = time.time()
            yield {"type": "progress", "message": "[PROGRESS:SAVE:START]"}
            yield {"type": "log", "message": "💾 Agent Step 6: 正在将灵感编码并安全存储至本地知识库..."}
            title = kwargs.get("title", topic)
            final_title = transform_content.title if getattr(transform_content, 'title', None) else title
            save_result = self._save_content(transform_content, final_title, reference_content=kwargs.get("reference_content", ""))
            
            if save_result.get("success", False):
                article_path = save_result.get("path")
                kwargs["article_path"] = article_path
                yield {"type": "log", "message": f"📁 存储成功：文章已归档至 `{os.path.basename(article_path)}`"}
            yield {"type": "progress", "message": "[PROGRESS:SAVE:END]"}
            
            # V4: 成功后将话题写入全景记忆库（含质量反馈分数及全文内容分析）
            try:
                from src.ai_write_x.core.memory_manager import MemoryManager
                MemoryManager().add_topic(topic, content=result_str, quality_score=quality_score)
                yield {"type": "log", "message": f"🧠 全景记忆库已更新当前话题特征 (质量反馈: {quality_score:.1f}/5.0)" if quality_score else "🧠 全景记忆库已更新当前话题特征"}
            except Exception as e:
                self.monitor.log_error("unified_workflow", f"写入记忆库失败: {e}", {"topic": topic})

            # --- Step 7: UI Handover & Completion (交付刷新) ---
            yield {"type": "progress", "message": "[PROGRESS:COMPLETE:START]"}
            yield {"type": "log", "message": "🎉 Agent Step 7: 全流程审计完成。UI 资产同步中，准备交付..."}
            
            publish_result = None
            if self._should_publish():
                yield {"type": "log", "message": "📤 正在自动同步并发布至平台..."}
                transform_content.title = final_title
                
                # _publish_content 已经接收 publish_platform 作为参数，kwargs 中不应包含它
                publish_kwargs = kwargs.copy()
                if "publish_platform" in publish_kwargs:
                    del publish_kwargs["publish_platform"]
                    
                publish_result = self._publish_content(
                    transform_content, publish_platform, **publish_kwargs
                )
                yield {"type": "log", "message": f"🚀 发布任务已下发：{publish_result.get('message')}"}
            
            total_duration = time.time() - start_time
            success = True
            results = {
                "base_content": base_content,
                "final_content": final_content,
                "formatted_content": transform_content.content,
                "save_result": save_result,
                "publish_result": publish_result,
                "quality_score": quality_score,
                "total_duration": round(total_duration, 1),
                "success": True,
            }
            yield {"type": "log", "message": f"⏱️ V4工作流总耗时: {total_duration:.1f}秒"}
            yield {"type": "final_results", "content": results}
            yield {"type": "done"}

        except TimeoutError as te:
            self.monitor.log_error("unified_workflow", f"V4阶段超时: {te}", {"topic": topic})
            yield {"type": "log", "message": f"⏰ V4超时保护触发: {str(te)}"}
            raise
        except Exception as e:
            self.monitor.log_error("unified_workflow", str(e), {"topic": topic})
            yield {"type": "log", "message": f"❌ Agent 遭遇异常中断: {str(e)}"}
            raise
        finally:
            duration = time.time() - start_time
            self.monitor.track_execution("unified_workflow", duration, success, {"topic": topic})

    def _transform_content(
        self, content: ContentResult, publish_platform: str, **kwargs
    ) -> ContentResult:
        """内容转换：template或design路径的AI处理"""
        config = Config.get_instance()
        adapter = self.platform_adapters.get(publish_platform)

        if not adapter:
            raise ValueError(f"不支持的平台: {publish_platform}")

        # AI驱动的内容转换
        if adapter.supports_html() and config.article_format.upper() == "HTML":
            # 检查是否使用动态模板生成
            use_dynamic_template = getattr(config, 'use_dynamic_template', True)
            
            if use_dynamic_template and adapter.supports_template():
                # 使用AI动态生成模板（新方式）
                return self._apply_dynamic_template(content, **kwargs)
            elif config.use_template and adapter.supports_template():
                # 使用预定义模板填充（旧方式）
                return self._apply_template_formatting(content, **kwargs)
            else:
                return self._apply_design_formatting(content, publish_platform, **kwargs)
        else:
            return content

    def _apply_template_formatting(self, content: ContentResult, **kwargs) -> ContentResult:
        """Template路径：使用AI填充本地模板"""
        # 创建专门的模板处理工作流
        lg.print_log("[PROGRESS:TEMPLATE:START]", "internal")

        template_config = self._get_template_workflow_config(**kwargs)
        engine = ContentGenerationEngine(template_config)

        input_data = {
            "content": content.content,
            "title": content.title,
            "parse_result": False,
            "content_format": "html",
            **kwargs,
        }

        try:
            ret = engine.execute_workflow(input_data)
            lg.print_log("[PROGRESS:TEMPLATE:END]", "internal")
            return ret
        except Exception as e:
            # 模板填充失败时，返回原始内容作为降级策略
            lg.print_log(f"模板填充失败，使用原始内容: {str(e)}", "warning")
            lg.print_log("[PROGRESS:TEMPLATE:END]", "internal")
            # 返回原始内容，但标记为 HTML 格式
            return ContentResult(
                title=content.title,
                content=content.content,
                summary=content.summary,
                content_type=content.content_type,
                content_format="html",
                metadata={
                    **content.metadata,
                    "template_fallback": True,
                    "template_error": str(e),
                }
            )

    def _apply_dynamic_template(self, content: ContentResult, **kwargs) -> ContentResult:
        """动态模板路径：使用AI生成独特的HTML模板"""
        from src.ai_write_x.tools.dynamic_template_tool import DynamicTemplateTool
        
        lg.print_log("[PROGRESS:DYNAMIC_TEMPLATE:START]", "internal")
        
        try:
            # 提取主题信息
            topic = kwargs.get('topic', '')
            
            # 使用动态模板工具生成模板（默认使用AI设计师）
            tool = DynamicTemplateTool()
            template_html = tool._run(
                title=content.title,
                content=content.content,
                topic=topic,
                use_ai_designer=True  # 使用AI生成独特模板
            )
            
            lg.print_log("[PROGRESS:DYNAMIC_TEMPLATE:END]", "internal")
            
            return ContentResult(
                title=content.title,
                content=template_html,
                summary=content.summary,
                content_type=ContentType.ARTICLE,
                content_format="html",
                metadata={
                    **content.metadata,
                    "template_type": "dynamic_ai",
                    "template_generated": True,
                }
            )
            
        except Exception as e:
            lg.print_log(f"AI动态模板生成失败，回退到预定义模板: {str(e)}", "warning")
            lg.print_log("[PROGRESS:DYNAMIC_TEMPLATE:END]", "internal")
            # 回退到预定义模板
            return self._apply_template_formatting(content, **kwargs)

    def _apply_design_formatting(
        self, content: ContentResult, publish_platform: str, **kwargs
    ) -> ContentResult:
        """Design路径：使用AI生成HTML设计"""
        # 创建专门的设计工作流
        lg.print_log("[PROGRESS:DESIGN:START]", "internal")

        design_config = self._get_design_workflow_config(publish_platform, **kwargs)
        engine = ContentGenerationEngine(design_config)

        input_data = {
            "content": content.content,
            "title": content.title,
            "platform": publish_platform,
            "parse_result": False,
            "content_format": "html",
            **kwargs,
        }

        ret = engine.execute_workflow(input_data)
        lg.print_log("[PROGRESS:DESIGN:END]", "internal")

        return ret

    def _apply_dimensional_creative_transformation(
        self, base_content: ContentResult, **kwargs
    ) -> ContentResult:
        """维度化创意变换"""
        config = Config.get_instance()
        dimensional_config = config.dimensional_creative_config

        # 检查是否启用维度化创意
        if not dimensional_config.get("enabled", False):
            return base_content

        # 重新初始化维度化创意引擎以获取最新配置
        self.creative_engine = DimensionalCreativeEngine(dimensional_config)

        # 应用维度化创意变换
        try:
            transformed_content = self.creative_engine.apply_dimensional_creative(
                base_content.content, base_content.title
            )

            # 创建新的ContentResult对象 - 包含所有必需参数
            result = ContentResult(
                title=base_content.title,
                content=transformed_content,
                summary=base_content.summary,  # 添加缺失的summary参数
                content_format=base_content.content_format,  # 添加缺失的content_format参数
                metadata=base_content.metadata.copy(),
            )

            # 添加变换元数据
            result.metadata.update(
                {
                    "transformation_type": "dimensional_creative",
                    "original_content_id": id(base_content),
                    "creative_engine_config": dimensional_config,
                }
            )

            return result

        except Exception as e:
            lg.print_log(f"维度化创意变换失败: {str(e)}", "error")
            return base_content

    def _get_template_workflow_config(
        self, publish_platform: str = PlatformType.WECHAT.value, **kwargs
    ) -> WorkflowConfig:
        """生成模板处理工作流配置"""
        # 获取配置以获取字数限制
        config = Config.get_instance()

        if publish_platform == PlatformType.WECHAT.value:
            # 微信平台的详细模板填充要求
            task_description = f"""
# HTML内容适配任务
## 任务目标
使用工具 read_template_tool 读取本地HTML模板，将以下文章内容适配填充到HTML模板中：

**文章内容：**
{{content}}

**文章标题：**
{{title}}

## 执行步骤
1. 首先使用 read_template_tool 读取HTML模板
2. 分析模板的结构、样式和布局特点
3. 获取前置任务生成的文章内容
4. 将新内容按照模板结构进行适配填充
5. 确保最终输出是基于原模板的HTML，保持视觉效果和风格不变

## 具体要求
- 分析HTML模板的结构、样式和布局特点
- 识别所有内容占位区域（标题、副标题、正文段落、引用、列表等）
- 将新文章内容按照原模板的结构和布局规则填充：
    * 保持<section>标签的布局结构和内联样式不变
    * 保持原有的视觉层次、色彩方案和排版风格
    * 保持原有的卡片式布局、圆角和阴影效果
    * 保持SVG动画元素和交互特性

- 内容适配原则：
    * 标题替换标题、段落替换段落、列表替换列表
    * 内容总字数{config.min_article_len}~{config.max_article_len}字，不可过度删减前置任务生成的文章内容
    * 当新内容比原模板内容长或短时，请直接复制并复用原模板中相同级别的带样式的 `<section>` 或 `<p>` 标签，绝不可破坏布局
    * **绝对禁止输出任何 Markdown 标记**（例如 `**粗体**`, `*斜体*`, `# 标题`）。必须完全使用纯净的 HTML 标签进行排版
    * 若要强调内容，必须使用 HTML的 `<span>` 或 `<strong>`，并参考原模板的配色给其添加合适的内联 `style`
    * 保持图片位置不变
    * 不可使用模板中的任何日期作为新文章的日期

- **图片插入与排版建议**:
    - 建议平均每个段落配置一张图片，或在观点转折处精准切入，提升阅读快感。
    - **生图质量管控**：生成的配图必须清晰、高端，**严禁**出现任何文字、字体、中国国旗/国徽及额外/畸形的手部肢体。
    - 图片格式：使用 <img src="https://picsum.photos/750/400?random=1" style="width:100%;border-radius:12px;margin:16px 0;" />

- 严格限制：
    * 不输出任何 Markdown 字符
    * 不添加新的style标签或外部CSS
    * 不改变原有的色彩方案（限制在三种色系内）
    * 不修改模板的整体视觉效果和布局结构"""

            backstory = "你是微信公众号模板处理专家，能够将内容适配到纯净HTML模板中。严格按照以下要求：保持<section>的布局结构和内联样式不变、保持原有的视觉层次、色彩方案和排版风格、**绝对禁止输出任何Markdown格式**、不可使用模板中的任何日期作为新文章的日期"  # noqa 501
        else:
            # 其他平台的简化模板处理
            task_description = "使用工具 read_template_tool 读取本地模板，将内容适配填充到模板中"
            backstory = "你是模板处理专家，能够将内容适配到模板中"

        agents = [
            AgentConfig(
                role="模板调整与内容填充专家",
                name="templater",
                goal="根据文章内容，适当调整给定的HTML模板，去除原有内容，并填充新内容。",
                backstory=backstory,
                tools=["ReadTemplateTool"],
            )
        ]

        tasks = [
            TaskConfig(
                name="template_content",
                description=task_description,
                agent_name="templater",
                expected_output="填充新内容但保持原有视觉风格的文章（HTML格式）",
            )
        ]

        return WorkflowConfig(
            name="template_formatting",
            description="模板格式化工作流",
            workflow_type=WorkflowType.SEQUENTIAL,
            content_type=ContentType.ARTICLE,
            agents=agents,
            tasks=tasks,
        )

    def _get_design_workflow_config(self, publish_platform: str, **kwargs) -> WorkflowConfig:
        """生成设计工作流配置"""

        # 微信平台的完整系统模板
        wechat_system_template = """<|start_header_id|>system<|end_header_id|>
# 严格按照以下要求进行微信公众号排版设计：
## 设计目标：
    - 创建一个美观、现代、易读的"**中文**"的移动端网页，具有以下特点：
    - 纯内联样式：不使用任何外部CSS、JavaScript文件，也不使用<style>标签
    - 移动优先：专为移动设备设计，不考虑PC端适配
    - 模块化结构：所有内容都包裹在<section style="xx">标签中
    - 简洁结构：不包含<header>和<footer>标签
    - 视觉吸引力：创造出视觉上令人印象深刻的设计

## 设计风格指导:
    - 色彩方案：使用大胆、酷炫配色、吸引眼球，反映出活力与吸引力，但不能超过三种色系，长久耐看，间隔合理使用，出现层次感。
    - 读者感受：一眼喜欢，很高级，很震惊，易读易懂
    - 排版：符合中文最佳排版实践，利用不同字号、字重和间距创建清晰的视觉层次，风格如《时代周刊》、《VOGUE》
    - 卡片式布局：使用圆角、阴影和边距创建卡片式UI元素
    - 图片处理：大图展示，配合适当的圆角和阴影效果

## 图片与视觉增强:
    - 建议按段落密度进行配图，确保视觉节奏紧凑。
    - **【合规与质量】**：配图中**绝对不可**包含文字、数字、国旗、国徽，并必须通过 Negative Prompts 思维规避多余手部或畸形肢体。
    - 图片格式建议：使用 <img src="https://picsum.photos/750/400?random=1" style="width:100%;border-radius:12px;margin:16px 0;" />

## 技术要求:
    - 纯 HTML 结构：只使用 HTML 基本标签和内联样式
    - 这不是一个标准HTML结构，只有div和section包裹，但里面可以用任意HTML标签
    - 内联样式：所有样式和字体都通过style属性直接应用在<section>这个HTML元素上，其他都没有style,包括body
    - 模块化：使用<section>标签包裹不同内容模块
    - 简单交互：用HTML原生属性实现微动效
    - SVG：生成炫酷SVG动画，目的是方便理解或给用户小惊喜
    - SVG图标：采用Material Design风格的现代简洁图标，支持容器式和内联式两种展示方式
    - 只基于核心主题内容生成，不包含作者，版权，相关URL等信息

## 其他要求：
    - 先思考排版布局，然后再填充文章内容
    - 输出长度：10屏以内 (移动端)
    - 生成的代码**必须**放在`` 标签中
    - 主体内容必须是**中文**，但可以用部分英语装逼
    - 不能使用position: absolute
<|eot_id|>"""

        # 根据平台定制设计要求
        platform_requirements = {
            PlatformType.WECHAT.value: "微信公众号HTML设计要求：使用内联CSS样式，避免外部样式表；采用适合移动端阅读的字体大小和行距；使用微信官方推荐的色彩搭配；确保在微信客户端中显示效果良好",  # noqa 501
            PlatformType.XIAOHONGSHU.value: "小红书平台设计要求：注重视觉美感，使用年轻化的设计风格；适当使用emoji和装饰元素；保持简洁清新的排版",
            PlatformType.ZHIHU.value: "知乎平台设计要求：专业简洁的学术风格；重视内容的逻辑性和可读性；使用适合长文阅读的排版",
        }

        design_requirement = platform_requirements.get(
            publish_platform, "通用HTML设计要求：简洁美观，注重用户体验"
        )

        agents = [
            AgentConfig(
                role="微信排版专家",
                name="designer",
                goal=f"为{publish_platform}平台创建精美的HTML设计和排版",
                backstory="你是HTML设计专家",
                system_template=(
                    wechat_system_template
                    if publish_platform == PlatformType.WECHAT.value
                    else None
                ),
                prompt_template="<|start_header_id|>user<|end_header_id|>{{ .Prompt }}<|eot_id|>",
                response_template="<|start_header_id|>assistant<|end_header_id|>{{ .Response }}<|eot_id|>",  # noqa 501
            )
        ]

        tasks = [
            TaskConfig(
                name="design_content",
                description=f"为{publish_platform}平台设计HTML排版。{design_requirement}。创建精美的HTML格式，包含适当的标题层次、段落间距、颜色搭配和视觉元素，确保内容在{publish_platform}平台上有最佳的展示效果。",  # noqa 501
                agent_name="designer",
                expected_output=f"针对{publish_platform}平台优化的精美HTML内容",
            )
        ]

        return WorkflowConfig(
            name=f"{publish_platform}_design",
            description=f"面向{publish_platform}平台的HTML设计工作流",
            workflow_type=WorkflowType.SEQUENTIAL,
            content_type=ContentType.ARTICLE,
            agents=agents,
            tasks=tasks,
        )

    def _save_content(self, content: ContentResult, title: str, reference_content: str = "") -> Dict[str, Any]:
        """保存内容（非AI参与）"""
        config = Config.get_instance()
        # 确定文件格式和路径
        file_extension = utils.get_file_extension(config.article_format)
        save_path = self._get_save_path(title, file_extension)

        # 保存文件
        with open(save_path, "w", encoding="utf-8") as f:
            f.write(content.content)
            
        # V18: 保存原始参考内容，供前端“查看原热点内容”功能使用
        if reference_content:
            try:
                # 清理文件名，确保安全
                safe_filename = utils.sanitize_filename(title)
                dir_path = PathManager.get_article_dir()
                source_path = os.path.join(dir_path, f"{safe_filename}.source.txt")
                with open(source_path, "w", encoding="utf-8") as f:
                    f.write(reference_content)
                lg.print_log(f"📄 原始参考内容已保存至: {os.path.basename(source_path)}", "success")
            except Exception as e:
                lg.print_log(f"⚠️ 原始参考内容保存失败: {str(e)}", "warning")

        return {"success": True, "path": save_path, "title": title, "format": config.article_format}

    def _get_save_path(self, title: str, file_extension: str) -> str:
        """获取保存路径"""

        # 获取文章保存目录
        dir_path = PathManager.get_article_dir()

        # 清理文件名，确保安全
        safe_filename = utils.sanitize_filename(title)

        # 构建完整路径
        save_path = os.path.join(dir_path, f"{safe_filename}.{file_extension}")

        return save_path

    def _publish_content(
        self, content: ContentResult, publish_platform: str, **kwargs
    ) -> Dict[str, Any]:
        """发布内容（非AI参与）"""
        adapter = self.platform_adapters.get(publish_platform)

        if not adapter:
            return {"success": False, "message": f"不支持的平台: {publish_platform}"}

        # 将 cover_path 传递给适配器
        kwargs["cover_path"] = utils.get_cover_path(kwargs.get("article_path"))

        # 使用平台适配器发布
        # 适配器内部会自动保存发布记录
        publish_result = adapter.publish_content(content, **kwargs)

        return {
            "success": publish_result.success,
            "message": publish_result.message,
            "platform": publish_platform,
        }

    def _should_publish(self) -> bool:
        """判断是否应该发布"""
        config = Config.get_instance()

        # 检查配置中的自动发布设置
        if not config.auto_publish:
            return False

        # 检查是否有有效的微信凭据
        valid_credentials = any(
            cred["appid"] and cred["appsecret"] for cred in config.wechat_credentials
        )

        if not valid_credentials:
            # 自动转为非自动发布并提示
            lg.print_log("检测到自动发布已开启，但未配置有效的微信公众号凭据", "warning")
            lg.print_log("请在配置中填写 appid 和 appsecret 以启用自动发布功能", "warning")
            lg.print_log("当前将跳过发布步骤，仅生成内容", "info")
            return False

        return True

    def get_performance_report(self) -> Dict[str, Any]:
        """获取性能报告"""
        return {
            "workflow_metrics": self.monitor.get_metrics(),
            "recent_executions": self.monitor.get_recent_logs(limit=20),
            "system_status": "healthy" if self._check_system_health() else "degraded",
        }

    def _check_system_health(self) -> bool:
        """检查系统健康状态"""
        metrics = self.monitor.get_metrics()
        for workflow_name, workflow_metrics in metrics.items():
            if workflow_metrics.get("success_rate", 0) < 0.8:  # 成功率低于80%
                return False
        return True

    def register_platform_adapter(self, name: str, adapter):
        """注册新的平台适配器"""
        self.platform_adapters[name] = adapter

    def _apply_recursive_self_correction(self, content: str, topic: str, conversation_history: list = None, **kwargs) -> str:
        """V12.0: RSC 递归自我修正协议 - 核心实现"""
        from src.ai_write_x.core.llm_client import LLMClient
        client = LLMClient()
        
        current_content = content
        max_iterations = 2
        
        # 如果没有传入历史记录（独立调用），则初始化一个临时的
        if conversation_history is None:
            conversation_history = [
                {"role": "user", "content": f"请针对话题'{topic}'撰写初稿。"},
                {"role": "assistant", "content": content}
            ]
        
        for i in range(max_iterations):
            lg.print_log(f"🧬 RSC 递归修正第 {i+1} 轮...", "info")
            
            # 1. 对抗性逻辑分析
            adversarial_prompt = f"""你现在是 V12 系统的【逻辑审核官】。请对前文内容的逻辑严密性进行“第一性原理”级的批判。
话题：{topic}

请指出文中所有：
- 逻辑跳跃或因果不强的地方
- 平庸、AI 化的表达或废话
- 论据支撑不足的观点

仅输出批判建议，如果没有问题请输出“PASS”。"""
            
            # 加入对话链
            conversation_history.append({"role": "user", "content": adversarial_prompt})
            feedback = client.chat(messages=conversation_history)
            conversation_history.append({"role": "assistant", "content": feedback})
            
            if "PASS" in feedback.upper() and len(feedback) < 10:
                lg.print_log(f"✅ RSC 第 {i+1} 轮逻辑验证通过", "success")
                break
                
            # 2. 逻辑重构
            lg.print_log(f"🧠 RSC 修正建议已获取，正在重构逻辑路径...", "info")
            refactor_prompt = """你现在是 V12 系统的【核心重构员】。请根据刚才的批判建议，对前文进行逻辑层面的深度优化。
要求：保持事实不变，让逻辑更硬核、叙事更有呼吸感。直接输出优化后的正文。"""
            
            # 加入对话链
            conversation_history.append({"role": "user", "content": refactor_prompt})
            
            current_content_streamed = ""
            char_count_logged = 0
            for chunk in client.stream_chat(messages=conversation_history):
                if chunk:
                    current_content_streamed += chunk
                    if len(current_content_streamed) - char_count_logged >= 200:
                        lg.print_log(f"⏳ RSC 逻辑重构中... 已生成 {len(current_content_streamed)} 字", "status")
                        char_count_logged = len(current_content_streamed)
                        
            conversation_history.append({"role": "assistant", "content": current_content_streamed})
            current_content = utils.remove_code_blocks(current_content_streamed)
            lg.print_log(f"📝 RSC 本轮重构完成，最新内容长度: {len(current_content)} 字", "success")
            
        return current_content
