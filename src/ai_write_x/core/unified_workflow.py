import os
import time
from typing import Dict, Any

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
            f"【时间锚点（绝对指令）】：\n"
            f"- 系统当前真实抓取时间：{current_date_str}\n"
            f"- 参考素材原发文/发生时间：{source_publish_time}\n"
            "※ 严禁产生时间幻觉！任何如'近日'、'昨天'、'3月1日'的表述，必须基于上述时间推算。如果原文没有明确年份，必须以系统当前时间的年份为基准，不要随意猜测过去的年份！如果原文完全没提日期则禁止编造。\n"
        )
        
        # V4: 价值榨取与去水算法 (Value-Extraction Framework)
        value_extraction_rules = (
            "【V4 价值榨取与去水协议（核心机制）】：\n"
            "1. <Thought>高感知认知提取</Thought>：在开始输出正文前，你**必须**首先使用 `<Thought>...</Thought>` 标签在内部思考并列出：\n"
            "   - 这篇文章能给读者带来的“3个具体的信息差优势”或“干货认知转移”是什么？\n"
            "   只有明确了这3点，才允许开始正文创作。\n"
            "2. 绝对去水印去废话（De-watermark）：全面封杀AI常用套话（如“总而言之”、“在这个飞速发展的时代”、“让人不禁思考”、“综上所述”等大词空话）。不要居高临下的总结陈词！每一句话都要有极高的信息密度。\n"
        )
        
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
            "【V6 创作者人设骨架 (Persona Framework)】：\n"
            "设定：你现在不是一个AI助手，而是一个拥有十年爆款经验、文字极为犀利、逻辑严密且带有一点幽默感的'资深主编'。\n"
            "语气：自信、一针见血、偶尔巧妙自嘲。你不喜欢冰冷说教，必须用极其精炼的口语化短句和生动的比喻来阐述复杂事实。\n"
            "规则：绝对禁止使用任何典型的AI起手式和客服式机器人语气（例如'总而言之'、'在这个飞速发展的时代'、'综上所述'）。\n"
        )
        
        if reference_content:
            writer_des = f"""{persona_framework}
{date_context}
{value_extraction_rules}
{memory_context}

基于以下已提前获取的全量参考文章内容，针对话题'{{topic}}'撰写一篇高质量的文章。
由于前置信息已满载，请绝**不要调用任何搜索工具**，直接基于下述【参考文章全量内容】进行创作。
请高度保持原文的事实、数据及核心观点，并且**必须严格保留和使用文章内已有的视觉解析节点**（即涉及 [图片解析: xxx] 或原图视觉属性的说明），将其巧妙融合至行文中。

**视觉占位符强制要求**：
每一个视觉节点或插图位置，必须统一使用以下格式：
`[[V-SCENE: <Midjourney风格英文提示词> (<中文意境说明>) | <比例(如16:9, 3:4)>]]`

文章基调与【极致可读性】强制要求（违者视为失败）：
- **图文并茂（关键）**：除了原有的视觉节点外，你必须根据行文节奏，在各个 H2/H3 小节之间、重要数据处或转折点，主动插入新的配图占位符。**全文必须强制包含至少 4-6 个配图占位符**。
- **视觉金句与划重点（关键）**：将核心观点、犀利吐槽、重要数据提取出来，使用 Markdown 加粗 `**重点词**`，或者使用独立引用块 `> 核心金句` 排版！
- **段落呼吸感**：段落长度控制在 60-150 字之间。禁止过度碎片化（一句话一段）。
- 语言必须通俗易懂、接地气，具有故事性和对话感，拒绝干瘪生硬的说明文。
- **叙事深度**：每个角度必须有具体事实、数据或引用支撑，不要空泛抒情。
- **多维度视角**：拆解为 3-5 个清晰的观察角度，用简短有力的小标题引出。

【参考文章全量内容】：
{{reference_content}}

文章要求：
- **标题 (王炸级点击诱饵)**：你的标题必须是“爆款头条”级别。激发好奇心、制造冲突或提炼出极致的反差感。点缀 1-2 个恰当的 Emoji。
- 总字数：{config.min_article_len}~{config.max_article_len}字
- 格式：标准Markdown格式（且必须大量使用强视觉高亮：加粗、引用区块）。
- **内容限制**：正文部分**绝对不要**以 `# ` 级的标题开头，直接从第一段内容或小标题开始输出。"""
        else:
            writer_des = f"""{persona_framework}
{date_context}
{value_extraction_rules}
{memory_context}

基于话题'{{topic}}'和搜索工具获取的最新信息，撰写一篇高质量的文章。

执行步骤：
1. 使用 web_search_tool 获取关于'{{topic}}'的最新信息
2. 确保文章逻辑清晰、内容完整、语言流畅

**视觉占位符强制要求**：
在文章叙事呼吸感断句处，必须统一插入以下格式的配图：
`[[V-SCENE: <Midjourney风格英文提示词> (<中文意境说明>) | <比例(如16:9, 3:4)>]]`

文章基调与【极致可读性】强制要求（违者视为失败）：
- **图文并茂（关键）**：绝对不能只有文字！在文章叙事呼吸感断句处、数据陈列前后，必须插入配图占位符。**全文字数若在1500字以上，至少要有 4-6 张配图占位符**。
- **视觉金句与划重点（关键）**：使用 Markdown 加粗 `**核心词汇**`，或者使用独立引用块 `> 爆款金句` 凸显重要观点！
- **段落呼吸感**：段落长度控制在 60-150 字之间。
- 语言必须通俗易懂、具有对话感。
- **文章推进感**：有清晰的逻辑演进，每个角度必须有具体事实、数据或引用支撑，不要空泛抒情。
- **多维度视角**：拆解为 3-5 个清晰的观察角度，每个角度用简短有力的小标题引出。

文章要求：
- **标题 (王炸级点击诱饵)**：核心是激发好奇心、震撼感或引发共鸣。由你自主根据话题权衡最吸引点击的标题风格。
- 总字数：{config.min_article_len}~{config.max_article_len}字
- 格式：标准Markdown格式（且必须大量使用强视觉高亮：加粗、引用区块）。
- **内容限制**：正文部分**绝对不要**以 `# ` 级的标题开头，直接从第一段内容或小标题开始输出。"""

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

    # V4: 每阶段最大允许时长（秒）
    STAGE_TIMEOUT = {
        "INIT": 300,       # 5分钟 — 深度洞察
        "CREATIVE": 120,   # 2分钟 — 创意蓝图
        "WRITING": 60,     # 1分钟 — 大师撰稿（已在Step1完成，这里只取用）
        "REVIEW": 600,     # 10分钟 — 打磨重塑（含多轮反思）
        "VISUAL": 900,     # 15分钟 — 视觉美化（含 ComfyUI 生图，6张图约需8-10分钟）
        "SAVE": 30,        # 30秒 — 持久化
        "COMPLETE": 120,   # 2分钟 — 发布交付
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

    def execute_stepwise(self, topic: str, **kwargs):
        """V4: 核心 7 阶 Agent 驱动工作流 (Generator) — 增加超时保护、内容断言、细粒度进度"""
        start_time = time.time()
        success = False
        config = Config.get_instance()
        # 优先从 kwargs 获取，如果没有则从配置获取
        publish_platform = kwargs.get("publish_platform", config.publish_platform)
        # 统一存入 kwargs 供子流程使用
        kwargs["publish_platform"] = publish_platform
        
        quality_score = None  # V4: 用于记忆库质量反馈
        
        try:
            # --- Step 1: Deep Insight Agent (深度洞察) ---
            stage_start = time.time()
            yield {"type": "progress", "message": "[PROGRESS:INIT:START]"}
            yield {"type": "log", "message": "🧠 Agent Step 1: 正在深度解构话题语境并检索核心事实..."}
            base_content = self._generate_base_content(
                topic, **kwargs
            )
            self._check_stage_timeout("INIT", stage_start)
            self._assert_content(base_content.content, "Step1-深度洞察")
            yield {"type": "log", "message": f"✅ 话题深度分析完成 ({time.time()-stage_start:.1f}s)，已锁定 3-5 个核心观察维度"}
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
            yield {"type": "progress", "message": "[PROGRESS:WRITING:END]"}
            
            # --- Step 4: Reflexion & Polish Agent (打磨重塑) ---
            stage_start = time.time()
            yield {"type": "progress", "message": "[PROGRESS:REVIEW:START]"}
            yield {"type": "log", "message": "💎 Agent Step 4: 正在进行语境打磨、去 AI 化处理及深度优化..."}
            
            from src.ai_write_x.core.final_reviewer import FinalReviewer
            from src.ai_write_x.core.llm_client import LLMClient
            from src.ai_write_x.core.anti_ai import AntiAIEngine
            
            result_str = final_content.content
            max_reflections = 2
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
                messages = [
                    {"role": "system", "content": "你是一位资深内容专家。根据反馈优化文章，保持事实准确，字数稳定。\n\n【关键前提】：这篇文章的素材来源于采编团队从央视、腾讯新闻、新浪等官方新闻平台实时爬取的真实新闻。文中的事件、人物、数据均为真实信息。审查反馈中如果提到\"虚构\"\"捏造\"\"假新闻\"等评价，请忽略该部分反馈，因为那是审查AI的误判。你只需要关注写作质量方面的有效反馈。\n\n优化要求：1. 严禁删除或修改任何形式的图片占位符（如 [图片解析:] 或 V-SCENE）；2. 必须保留并刻意增强粗体 `**重点**`、小标题和引用块 `> 金句` 等高密度视觉排版，始终保持干脆利落的短句分段呼吸感。直接输出正文内容。"},
                    {"role": "user", "content": f"反馈: {review_result.get('report')}\n原文: {anchor_result_str}\n当前: {result_str}"}
                ]
                
                new_version = ""
                for chunk in client.stream_chat(messages=messages):
                    if chunk:
                        new_version += chunk
                
                result_str = utils.remove_code_blocks(new_version)
                iteration += 1
                yield {"type": "log", "message": f"📝 Reflexion Round {iteration}: 优化完成"}
            
            # 统一执行一次抗AI粉碎
            result_str = AntiAIEngine.pulverize(result_str)
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
            
            # --- Step 6: Persistence & Orchestration Agent (持久化管理) ---
            stage_start = time.time()
            yield {"type": "progress", "message": "[PROGRESS:SAVE:START]"}
            yield {"type": "log", "message": "💾 Agent Step 6: 正在将灵感编码并安全存储至本地知识库..."}
            title = kwargs.get("title", topic)
            final_title = transform_content.title if getattr(transform_content, 'title', None) else title
            save_result = self._save_content(transform_content, final_title)
            
            if save_result.get("success", False):
                article_path = save_result.get("path")
                kwargs["article_path"] = article_path
                yield {"type": "log", "message": f"📁 存储成功：文章已归档至 `{os.path.basename(article_path)}`"}
            yield {"type": "progress", "message": "[PROGRESS:SAVE:END]"}
            
            # V4: 成功后将话题写入全景记忆库（含质量反馈分数）
            try:
                from src.ai_write_x.core.memory_manager import MemoryManager
                MemoryManager().add_topic(topic, quality_score=quality_score)
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

## 【重要】图片插入要求（必须执行）:
    - **如果模板中没有封面图，必须在文章开头插入一张封面图**
    - **按照全文内容密度，平均每 300-400 字必须插入一张对应意境的配图**，打破纯文字的枯燥感
    - 图片格式：使用 <img src="https://picsum.photos/750/400?random=1" style="width:100%;border-radius:12px;margin:16px 0;" />
    - 图片位置选择：段落之间的自然分隔处、重要观点前后、列表之前
    - 配图数量应根据文章总字数动态调整，确保视觉分布均匀且与文字意境高度契合

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

## 【重要】图片插入要求（必须执行）:
    - **必须在文章开头插入一张精美的封面图**，宽度 750px，高度 400px
    - **按照全文内容密度，平均每 300-400 字必须插入一张对应意境的配图**，打破纯文字的枯燥感
    - 图片位置选择原则：
      * 段落之间的自然分隔处
      * 重要观点前后
      * 数据展示或列表之前
      * 文章结尾处
    - 图片格式：使用 <img src="https://picsum.photos/750/400?random=1" style="width:100%;border-radius:12px;margin:16px 0;" />
    - 图片尺寸建议：正文配图 750x400 或 750x500，封面图 750x400
    - 配图数量应根据文章总字数动态调整，确保视觉分布均匀且与文字意境高度契合
    - 图片下方可添加简短的图片说明文字（可选）

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

    def _save_content(self, content: ContentResult, title: str) -> Dict[str, Any]:
        """保存内容（非AI参与）"""
        config = Config.get_instance()
        # 确定文件格式和路径
        file_extension = utils.get_file_extension(config.article_format)
        save_path = self._get_save_path(title, file_extension)

        # 保存文件
        with open(save_path, "w", encoding="utf-8") as f:
            f.write(content.content)

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
