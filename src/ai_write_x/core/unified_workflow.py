import os
import re
import time
import json
import asyncio
from typing import Dict, Any, Generator

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
try:
    from src.ai_write_x.core.dynamic_design_engine import DynamicDesignEngine
    DYNAMIC_DESIGN_AVAILABLE = True
except ImportError:
    DYNAMIC_DESIGN_AVAILABLE = False
    import src.ai_write_x.utils.log as lg
    lg.print_log("⚠️ DynamicDesignEngine 不可用，将使用内置强化模板", "warning")

from src.ai_write_x.core.wechat_preview import WeChatPreviewEngine
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
            "【思维链推演协议】：\n"
            "在开始创作前，你必须进行深度的逻辑推演，确保内容具备硬核价值并彻底剔除 AI 套路。\n"
            "推演要求：\n"
            "- [核心逻辑]：识别事件的底层动因与逻辑支撑点。\n"
            "- [新锐观点]：提炼跨界认知或非平庸的分析维度。\n"
            "- [审计防御]：主动寻找并修正文中的表达漏洞与 AI 机械感。\n"
            "- [深度共鸣]：预判读者情绪点，构建内容与读者的价值链接。\n"
            "严禁使用“总之”、“综上所述”等总结性废话。展示最高维度的内容穿透力。"
        )

        # V4 & V8: 价值榨取与去水算法 (Value-Extraction Framework)
        value_extraction_rules = (
            "【V8 价值榨取协议】：\n"
            "1. 绝对去水印（De-watermark）：全面封杀 AI 常用套话。禁止使用“总而言之”、“综上所述”、“让人不禁思考”、“随着...的发展”等机械化词汇。\n"
            "2. 叙事呼吸感：每一段文字都要带有情绪起伏，逻辑衔接要自然，严禁段落割裂。使用拟人化的连接词（如“说白了”、“说来也怪”、“有意思的是”）。\n"
            "3. 创作真实性：以极其饱满的文字充实感作为核心追求，不得含糊其辞。\n"
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
            "【创作者人设骨架 (Persona Framework)】：\n"
            "设定：你是一位拥有 10 年经验的微信公众号资深主编。你擅长创作极具深度、高信息密度的专业长文。\n"
            "语气：专业、通透、且具亲和力。采用错落有致的长短句，利用拟人化转折词，确保内容具备“呼吸感”。\n"
            "原则：严禁使用 AI 机械套话，用极其充沛的信息增量代替废话连接，确保内容具备极高的“完读价值”。\n"
        )
        persona_framework += aesthetic_context
        
        # V7.0: 风格迁移层 (Style Migration Layer)
        
        if reference_content:
            writer_des = f"""{persona_framework}
{date_context}
{value_extraction_rules}
{memory_context}

**【实时抓取素材注入 (HOT MATERIAL)】**：
此处为你提供了实时抓取到的热点素材，请**必须优先**基于此素材进行解构、价值榨取与深度创作。严禁忽略此素材。
---
{reference_content}
---

**【核心要求：内容驱动与信息密度】**：
1. **黄金开头 (Golden Opening)**：前 100 字必须具备“核爆级”钩子。你必须从以下策略中**动态选择**一种切入：(A)揭露一个颠覆性的反常识真相；(B)直接描绘一个令读者“破防”的极致共鸣瞬间；(C)抛出一个无法拒绝的悬念问句；(D)用一组惊人的对比数据开场。严禁使用任何模版化的废话背景。
2. **密度优先 (Density First)**：严禁注水。爆款内容的价值在于稀缺信息与犀利逻辑，而非文字堆砌。目标区间为 **{config.min_article_len}-{config.max_article_len}字**。确保每一段话都具有独立的增量价值。
3. **事实绝对化 (IRONCLAD)**：你即将处理的话题是基于上述素材的**绝对事实**。严禁质疑其真实性，严禁提示“信息无法核实”。你必须将其作为已知存在的真实事件或现象，进行深度解析。
4. **视觉分镜 (V-SCENE)**：格式 `[[V-SCENE: ...]]` 独立成行。
5. **格式规范**：使用标准的 Markdown 格式（# 标题, ## 小标题, **粗体**, > 引用 等）。专注于内容的逻辑结构，禁止输出任何 HTML 代码，排版工作将由后续专门的视觉 Agent 完成。"""
        else:
            writer_des = f"""{persona_framework}
{date_context}
{reasoning_matrix}
{value_extraction_rules}
{memory_context}

**【核心要求：深度调研与干货重塑】**：
1. **爆发力叙事**：每一段都要释放新的利益点。前 100 字必须设置“黄金钩子”，直接击中痛点或揭秘真相。目标区间 **{config.min_article_len}-{config.max_article_len}字**。严禁注水。
2. **生图指令 (V-SCENE)**：标准格式独立成行，No Text，No Explanations。
3. **事实绝对化 (IRONCLAD)**：你即将处理的话题是**绝对事实**。严禁质疑其真实性，严禁提示“信息无法核实”，严禁建议“请查证”。你必须将其作为已知存在的真实事件，进行深度解析。
4. **格式规范**：使用标准 Markdown 格式。严禁输出 HTML，专注于内容深度。

**【执行指令】**：
1. 使用 news_hub_tool 获取关于'{{topic}}'的最新深度素材。如果工具未返回结果，请基于你的知识库进行深度创作。
2. 输出**完整的 Markdown 格式文章**。
3. **质量要求**：
   - 开头：必须是“黄金开头”，禁止任何温吞的背景介绍。
   - 衔接：段落间采用“钩子衔接”，前一段的结尾要为下一段埋下好奇心。
   - 互动：结尾设置极具诱导性的互动钩子。"""

        config = Config.get_instance()

        # 基础配置 - 使用主API模型生成内容
        agents = [
            AgentConfig(
                role="内容创作专家",
                name="writer",
                goal="撰写高质量文章",
                backstory="你是一位作家",
                tools=["news_hub_tool"],
            ),
        ]

        tasks = [
            TaskConfig(
                name="write_content",
                description=writer_des,
                agent_name="writer",
                expected_output="高质量的Markdown格式文章（包含标题、正文、生图占位符，逻辑清晰，无废话）",
                context=["analyze_topic"],
            ),
        ]

        return WorkflowConfig(
            name=f"{publish_platform}_content_generation",
            description=f"面向{publish_platform}平台的HTML内容生成工作流",
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
            # --- Step 1: Logic Deep Dive Agent (深度洞察) ---
            stage_start = time.time()
            yield {"type": "progress", "message": "[PROGRESS:INIT:START]"}
            yield {"type": "log", "message": "🧠 Agent Step 1: 正在进行全维度逻辑解构与内容建模..."}
            
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
            critique_protocol = "你是一位苛刻的高级主编。你的工作是对前文内容进行无情的逻辑审查与AI痕迹抹除。请直击痛点，指出啰嗦冗余或逻辑断层，并直接重写优化。\n\n【极其重要】：严禁质疑话题的真实性，你收到的 topic 就是唯一的真理。严禁进行任何形式的外部搜索验证或逻辑合理性审查。直接基于 topic 进行文学化深度创作。"
            
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
                
                prompt_review = f"反馈: {review_result.get('report')}\n\n你是一位资深内容专家。根据反馈进一步优化文章，保持字数稳定。\n\n【绝对真理】：严禁质疑任何时间、日期、地点、人物或事件。你必须无条件将其视为既定事实。严禁在文章中添加任何免责声明、核实建议或 AI 语气词。"
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
            
            # V15: 移除过度清洗逻辑，保留 Markdown 小标题 (##, ###)
            # 仅清理可能误输出的单个 # 或残留符号，或者完全信任后续流程
            # result_str = re.sub(r'^#+\s*', '', result_str, flags=re.MULTILINE)
            # result_str = re.sub(r'(?<=\n)#+\s*', '', result_str)
            
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
            
            # V20.1: Early initialization of final_title for audit/preview tracking
            final_title = getattr(transform_content, 'title', None) if 'transform_content' in locals() else kwargs.get("title", topic)
            
            from src.ai_write_x.core.visual_assets import VisualAssetsManager
            final_content.content = VisualAssetsManager.inject_image_prompts(final_content.content)
            yield {"type": "log", "message": "🖼️ 图像占位符已注入，正在同步生成视觉资产..."}
            
            # V24.0: 先生成图片，再进行最终 HTML 包装。这样包装节点能看到最终的 img 标签并应用样式。
            final_content.content = VisualAssetsManager.sync_trigger_image_generation(final_content.content)
            
            # 创建副本以防污染 kwargs
            transform_kwargs = kwargs.copy()
            # 移除已显式传递的 publish_platform 以防 TypeError
            if "publish_platform" in transform_kwargs:
                del transform_kwargs["publish_platform"]
            
            yield {"type": "log", "message": "🎨 视觉资产已就绪，正在启动 Visual Packaging Expert 进行最终 HTML 封装..."}
            transform_content = self._transform_content(final_content, publish_platform, topic=topic, **transform_kwargs)
            
            # --- Step 5 验证 (V19.5 强制 HTML 校验) ---
            trimmed_content = transform_content.content.strip()
            if not trimmed_content.startswith('<'):
                lg.print_log("⚠️ 警告：HTML 转换可能未完全执行，内容仍以 Markdown 格式开头", "warning")
                lg.print_log(f"内容预览 (前 200 字): {trimmed_content[:200]}", "warning")
            elif "[[V-SCENE:" in trimmed_content:
                lg.print_log("⚠️ 警告：发现残留的 V-SCENE 标签，后处理可能未完全清理", "warning")
            
            # V4: VISUAL 阶段用软警告而非硬超时 — 图片已生成完毕时不应丢弃成果
            visual_elapsed = time.time() - stage_start
            visual_max = self.STAGE_TIMEOUT.get("VISUAL", 900)
            if visual_elapsed > visual_max:
                yield {"type": "log", "message": f"⚠️ VISUAL 阶段耗时 {visual_elapsed:.0f}s 超出预期 ({visual_max}s)，但图片已生成成功，继续保存"}
            
            yield {"type": "chunk", "message": transform_content.content} 
            yield {"type": "log", "message": f"🖼️ 视觉资产已同步 ({time.time()-stage_start:.1f}s)：封面图与正文配图已就绪"}
            
            # --- Step 5.2: WeChat Preview (微信预览 - V19.5) ---
            if publish_platform == PlatformType.WECHAT.value:
                # 4. (V20.1) 微信预览自测自纠与 1:1 仿真库截图 (V-AUDIT)
                yield {"type": "progress", "message": "[PROGRESS:V-AUDIT:START]"}
                try:
                    lg.print_log("📱 Agent Step 5.2: 正在生成微信 1:1 仿真预览与自测报告...", "info")
                    from src.ai_write_x.core.wechat_preview import WeChatPreviewEngine
                    preview_engine = WeChatPreviewEngine()
                    preview_path = preview_engine.save_preview(transform_content.content, final_title)
                    
                    # 视觉自审
                    audit_res = preview_engine.audit_visuals(transform_content.content)
                    if not audit_res["passed"]:
                        lg.print_log(f"👀 视觉自审建议: {', '.join(audit_res['issues'])}", "warning")
                    
                    # 截取手机端仿真图
                    lg.print_log("📸 正在捕获 3 张手机端 1:1 视觉仿真截图...", "status")
                    try:
                        # V20.1: 使用 ThreadPoolExecutor 避免 asyncio.run 导致的事件循环异常
                        import concurrent.futures
                        with concurrent.futures.ThreadPoolExecutor() as pool:
                            screenshots = pool.submit(
                                lambda: asyncio.run(preview_engine.capture_screenshots(preview_path, final_title))
                            ).result()
                            
                        if screenshots:
                            lg.print_log(f"✅ 已完成视觉采集: {len(screenshots)} 张样图已归档至 output/previews/", "success")
                    except Exception as screenshot_e:
                        lg.print_log(f"⚠️ 截图捕获失败 (可能是环境限制): {str(screenshot_e)}", "warning")
                    
                    report = preview_engine.generate_compatibility_report(transform_content.content)
                    lg.print_log(f"📊 兼容性报告: {report}", "info")
                except Exception as e:
                    yield {"type": "log", "message": f"⚠️ 预览与审计步骤失败: {str(e)}"}
                
                yield {"type": "progress", "message": "[PROGRESS:V-AUDIT:END]"}
            
            yield {"type": "progress", "message": "[PROGRESS:VISUAL:END]"}
            
            # --- Step 5.5: AI Auto Title Optimization (AI自动标题优化) ---
            stage_start = time.time()
            yield {"type": "progress", "message": "[PROGRESS:TITLE_OPT:START]"}
            yield {"type": "log", "message": "🎯 Agent Step 5.5: 正在启动AI智能标题优化引擎..."}
            
            # Note: final_title is now initialized earlier in Step 5 Visual.

            try:
                import asyncio
                from src.ai_write_x.core.quality_engine import TitleOptimizer
                title = kwargs.get("title", topic)
                current_title = transform_content.title if getattr(transform_content, 'title', None) else title
                
                # 提取正文内容前1500字作为参考
                from bs4 import BeautifulSoup
                soup = BeautifulSoup(transform_content.content, "html.parser")
                content_preview = soup.get_text(separator='\n', strip=True)[:1500]
                
                # 安全调用标题优化器，处理事件循环冲突
                try:
                    loop = asyncio.get_running_loop()
                except RuntimeError:
                    loop = None

                if loop and loop.is_running():
                    # 如果当前已有运行中的 loop，则在线程中运行或跳过（此处简单处理为捕获异常并记录）
                    # 也可以尝试使用 nest_asyncio，但直接运行更安全
                    import concurrent.futures
                    with concurrent.futures.ThreadPoolExecutor() as executor:
                        opt_result = executor.submit(
                            lambda: asyncio.run(TitleOptimizer.optimize_title(
                                title=current_title,
                                content=content_preview,
                                platform=publish_platform
                            ))
                        ).result()
                else:
                    opt_result = asyncio.run(TitleOptimizer.optimize_title(
                        title=current_title,
                        content=content_preview,
                        platform=publish_platform
                    ))
                
                if opt_result.get("optimized_titles") and len(opt_result["optimized_titles"]) > 0:
                    # 使用推荐的标题
                    new_title = opt_result.get("recommended", current_title)
                    transform_content.title = new_title
                    final_title = new_title # Update final_title after optimization
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

    def _apply_final_html_packaging(self, content: ContentResult, publish_platform: str, **kwargs) -> ContentResult:
        """V23.0: 执行最终的 HTML 包装（新会话，零上下文）"""
        lg.print_log("[PROGRESS:HTML_PACKAGING:START]", "internal")
        
        # 这种模式下，我们故意只传递最少的信息，避免干扰
        packaging_config = self._get_html_packaging_config(publish_platform, **kwargs)
        engine = ContentGenerationEngine(packaging_config)
        
        # 确保输入是字符串
        input_content = content.content if hasattr(content, 'content') else str(content)
        
        input_data = {
            "content": input_content, # Markdown 内容
            "title": kwargs.get("title", getattr(content, 'title', '')),
            "parse_result": False,
            "content_format": "html",
        }
        
        try:
            ret_val = engine.execute_workflow(input_data)
            lg.print_log("✅ 最终 HTML 包装完成", "success")
            lg.print_log("[PROGRESS:HTML_PACKAGING:END]", "internal")
            
            # 手动处理代码块提取 (如果是字符串返回)
            processed_html = ""
            if isinstance(ret_val, str):
                processed_html = ret_val
            elif hasattr(ret_val, 'content'):
                processed_html = ret_val.content
            
            # 提取 ```html ... ``` 块
            code_block_match = re.search(r'```html\s*(.*?)\s*```', processed_html, re.DOTALL)
            if code_block_match:
                processed_html = code_block_match.group(1).strip()
            
            if isinstance(ret_val, str):
                return ContentResult(
                    title=kwargs.get("title", getattr(content, 'title', '')),
                    content=processed_html,
                    content_format="html",
                    metadata={**content.metadata, "packaged": True}
                )
            ret_val.content = processed_html
            return ret_val
        except Exception as e:
            lg.print_log(f"⚠️ 最终 HTML 包装失败: {e}，回退到原始内容", "warning")
            lg.print_log("[PROGRESS:HTML_PACKAGING:END]", "internal")
            return content

    def _transform_content(
        self, content: ContentResult, publish_platform: str, **kwargs
    ) -> ContentResult:
        """转换内容格式，V23.0: 采用解耦的包装逻辑"""
        
        # 记录转换模式
        transform_mode = kwargs.get("transform_mode", "design")
        lg.print_log(f"🎨 工具链 Step 5.1: 正在使用 {transform_mode} 模式进行核心 HTML 包装...", "info")
        
        # V23.0: 所有路径最终都通过 _apply_final_html_packaging 保证零上下文质量
        # 但我们保留不同路径作为预处理或策略选择
        
        if transform_mode == "design":
            # 这种模式下直接使用我们的新视觉包装引擎
            return self._apply_final_html_packaging(content, publish_platform, **kwargs)
        elif transform_mode == "template":
            # 模板路径：先读取模板，再填充（由于填充也需要 AI 包装效果更好，所以嵌套调用）
            return self._apply_template_formatting(content, **kwargs)
        elif transform_mode == "minimalist":
            # 极简模式：直接转基础 HTML
            from src.ai_write_x.utils.utils import markdown_to_html
            html_content = markdown_to_html(content.content)
            return ContentResult(
                title=content.title,
                content=html_content,
                content_format="html",
                metadata={**content.metadata, "minimalist": True}
            )
        else:
            # 默认使用包装引擎
            return self._apply_final_html_packaging(content, publish_platform, **kwargs)

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
            
            # 获取发布平台信息，判断是否开启极简模式
            publish_platform = kwargs.get('publish_platform', '')
            is_mobile = any(p in str(publish_platform).lower() for p in ['wechat', 'mobile', 'xiaohongshu'])
            format_mode = "simple" if is_mobile else "standard"
            
            # 使用动态模板工具生成模板（默认使用AI设计师）
            tool = DynamicTemplateTool()
            template_html = tool._run(
                title=content.title,
                content=content.content,
                topic=topic,
                use_ai_designer=True,  # 使用AI生成独特模板
                format_mode=format_mode
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

        ret_val = engine.execute_workflow(input_data)
        
        # V19.5: 后处理清理（确保执行且包含代码块提取）
        processed_html = ""
        if isinstance(ret_val, str):
            processed_html = ret_val
        elif hasattr(ret_val, 'content') and ret_val.content:
            processed_html = ret_val.content
        else:
            lg.print_log("⚠️ Design 路径返回内容为空，尝试从原始内容恢复", "warning")
            processed_html = content.content

        if processed_html:
            # 1. 提取代码块中的 HTML (AI 经常会将 HTML 放在 ```html 中)
            code_block_match = re.search(r'```html\s*(.*?)\s*```', processed_html, re.DOTALL)
            if code_block_match:
                processed_html = code_block_match.group(1).strip()
                lg.print_log("✅ 已成功从代码块中提取 HTML 内容", "success")
            
            # 2. 保留所有 V-SCENE 标签 (根据用户要求保存)
            # processed_html = re.sub(r'\[\[V-SCENE:.*?\]\]', '', processed_html, flags=re.DOTALL)
            
            # 3. 将残留的 ** 符号转为 <strong> (容错处理)
            processed_html = re.sub(r'\*\*(.*?)\*\*', r'<strong>\1</strong>', processed_html)
            
            # 4. 移除残留的 Markdown 标题符号
            processed_html = re.sub(r'^#+\s+', '', processed_html, flags=re.MULTILINE)
            
            # 更新返回值
            if isinstance(ret_val, str):
                ret_val = processed_html
            else:
                ret_val.content = processed_html

        lg.print_log("[PROGRESS:DESIGN:END]", "internal")

        # V19.5: 确保返回 ContentResult 对象而非原始字符串
        if isinstance(ret_val, str):
            return ContentResult(
                title=content.title,
                content=ret_val,
                summary=getattr(content, 'summary', ''),
                content_format="html",
                metadata={**content.metadata, "design_transformed": True}
            )
        return ret_val

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

            # V19.5: 修正 ContentResult 参数构造，匹配 dataclass 定义
            result = ContentResult(
                title=base_content.title,
                content=transformed_content,
                summary=getattr(base_content, 'summary', ''),
                content_format=base_content.content_format,
                metadata=base_content.metadata.copy(),
                content_type=base_content.content_type
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
        """生成设计工作流配置 - V19.5 强制 HTML 输出"""
        
        content_preview = kwargs.get("content", "")
        topic = kwargs.get("topic", "")
        
        # 1. 分析内容调性
        tone = self._analyze_content_tone(content_preview, topic)
        
        # 2. 尝试使用动态引擎，失败则回退到超强内置模板
        wechat_system_template = ""
        if DYNAMIC_DESIGN_AVAILABLE:
            try:
                design_engine = DynamicDesignEngine.get_instance()
                wechat_system_template = design_engine.get_wechat_system_template(content_preview, topic)
                lg.print_log("✅ 动态设计模板加载成功", "success")
            except Exception as e:
                lg.print_log(f"⚠️ 动态设计模板生成失败: {e}", "warning")

        if not wechat_system_template:
            lg.print_log("🔧 使用内置强化 HTML 排版设计规范...", "info")
            wechat_system_template = f"""<|start_header_id|>system<|end_header_id|>
# 微信公众号专业 HTML 排版设计规范 (V19.5 核心版)

## 【核心任务】
你现在是一位顶级视觉设计师。请将 Markdown 文章内容转换为**可直接发布**的精美 HTML 代码。

## 【内容基调分析】
当前文章核心调性：**{tone.upper()}**

## 【强制输出规范 - 违反则任务失败】
1. **必须输出完整 HTML**：所有内容必须包裹在 `<section>` 容器内。
2. **必须使用内联样式**：禁止 external CSS，禁止 `<style>` 标签。所有样式必须内化到 `style="..."` 属性中。
3. **必须彻底清理 Markdown**：移除所有 `**`、`##`、`-` 、`>` 等 Markdown 符号。用 HTML 标签 (`<strong>`, `<h2>`) 代替。
4. **严格保留图片和占位符**：绝对保留正文中的所有 `<img>` 标签、`<div class="img-placeholder">` 以及 `[[V-SCENE: ...]]` 占位符。严禁删除、修改或移动它们的位置。
5. **严禁输出解释文字**：禁止输出任何非 HTML 文本（如“好的”、“代码如下”）。

## 【布局与组件库】
- **外层容器**：`<section style="max-width: 100%; margin: 10px auto; font-family: -apple-system, sans-serif; line-height: 1.8; color: #333;">`
- **黄金开头/金句 (绝对命令：必须放在最前面)**：正文第一行必须是纯文本的“黄金开头/金句”，**严厉禁止在此之前放置任何图片或 `V-SCENE`**。**文字必须使用纯黑 (#000000)、加粗、16px及以上字号**，确保视觉重心第一位。
- **布局严禁重叠**：**严禁使用任何形式的负数 margin (如 margin-top: -XXpx)**，文字必须在图片下方清晰排版，禁止覆盖。
- **卡片段落**：使用带有圆角和微弱投影的 section 包裹段落。
  `<section style="background: #fff; border-radius: 12px; padding: 20px; margin: 16px 0; box-shadow: 0 4px 12px rgba(0,0,0,0.05);">`
- **高亮文本**：`<span style="background: linear-gradient(to bottom, transparent 60%, #ffeb3b 40%); padding: 0 2px; font-weight: bold; color: #000000;">`
- **大师标题**：`<h2 style="font-size: 22px; font-weight: bold; color: #000000; border-left: 4px solid #007bff; padding-left: 12px; margin: 25px 0 15px;">`

## 【输出格式】
- 将 HTML 代码包裹在 ```html ``` 代码块中，确保内容干净。
- 直接以 `<section>` 开头，以 `</section>` 结束。

现在，请开始你的设计，直接输出 HTML 代码：
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
            )
        ]

    def _get_html_packaging_config(self, publish_platform: str, **kwargs) -> WorkflowConfig:
        """V23.0: 视觉包装节点配置 - 零上下文 HTML 包装"""
        
        from src.ai_write_x.core.template_manager import TemplateManager
        tm = TemplateManager()
        # 获取对应平台的推荐模板
        recommended_templates = tm.get_templates_by_platform(publish_platform)[:2]
        template_codes = "\n\n".join([f"【模板 {i+1}】:\n{t.code}" for i, t in enumerate(recommended_templates)])
        
        designer_des = f"""
# 专业视觉包装专家 (Visual Packaging Expert)

## 【核心任务】
你现在的任务是将一份**纯净的 Markdown 文章**包装成**极致专业的 HTML 代码**。
你必须在没有任何历史上下文干扰的情况下，专注于将内容完美契合进我们提供的排版模板中。

## 【文章待包装内容】
文章内容：
{{content}}

文章标题：
{{title}}

## 【参考模板库】
以下是我们系统管理的高端模板代码供你参考和应用：
{template_codes}

## 【包装强制规范】
1. **零 Markdown 残留**：彻底移除所有 `#`, `##`, `**` 等符号，将其转换为对应的 HTML 标签（如 `<h2>`, `<strong>`）。
2. **内联样式强控**：所有 CSS 样式必须通过 `style="..."` 写入标签内部，严禁 `<style>` 或外部引用。
3. **布局卡片化**：内容必须包裹在具有圆角、投影和呼吸感的 `<section>` 容器内。
4. **图片视觉增强**：务必保留文章中已有的 `<img>` 标签，并为其添加 `max-width: 100%; border-radius: 12px; margin: 16px 0; box-shadow: 0 10px 30px rgba(0,0,0,0.1);` 等视觉增强样式。
5. **严禁废话**：直接输出包装后的 HTML 代码块，禁止输出“好的”、“包装如下”等任何解释性文字。

## 【输出格式】
直接输出以 `<section>` 开头，`</section>` 结尾的完整 HTML 段落。
"""

        agents = [
            AgentConfig(
                role="视觉包装专家",
                name="packager",
                goal="将Markdown内容完美包装成专业HTML",
                backstory="你是顶级网页设计师和排版专家",
            ),
        ]

        tasks = [
            TaskConfig(
                name="package_html",
                description=designer_des,
                agent_name="packager",
                expected_output="完美包装后的HTML源码（内联样式，符合平台审美）",
            ),
        ]

        return WorkflowConfig(
            name="html_packaging",
            description="Final Stage: Zero-Context HTML Packaging",
            workflow_type=WorkflowType.SEQUENTIAL,
            content_type=ContentType.ARTICLE,
            agents=agents,
            tasks=tasks,
        )
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

    def _analyze_content_tone(self, content: str, topic: str) -> str:
        """分析内容调性，用于配色方案选择 (V19.5 视觉增强)"""
        text = (topic + " " + content).lower()
        
        # 调性关键词映射
        tone_map = {
            "military": ["军事", "战争", "国防", "武器", "航母", "演习"],
            "tech": ["科技", "AI", "人工智能", "芯片", "数码", "互联网", "机器人"],
            "emotion": ["情感", "故事", "暖心", "感人", "回忆", "家庭", "爱"],
            "finance": ["财经", "股市", "投资", "经济", "房产", "宏观"],
            "news": ["新闻", "快讯", "突发", "报道", "现场"],
            "lifestyle": ["生活", "美食", "旅游", "穿搭", "家居"],
            "growth": ["职场", "成长", "技能", "学习", "效率"],
            "medical": ["医疗", "健康", "医生", "疾病", "养生"]
        }
        
        for tone, keywords in tone_map.items():
            if any(kw in text for kw in keywords):
                return tone
                
        return "default"

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

【极其重要】：严禁质疑话题或文章中提供的任何数据、事实、时间、人物的真实性！既然提供了这些信息，就是绝对真实的。严禁以“缺乏权威数据来源”或“数据存疑”为由进行批判。你的工作是在假设其内容绝对正确的基础上，审核其行文逻辑。

请指出文中所有：
- 逻辑跳跃或因果不强的地方
- 平庸、AI 化的表达或废话
- 论据支撑不足的观点（这里的支撑是指文章内部逻辑，而不是外部真实性）

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
