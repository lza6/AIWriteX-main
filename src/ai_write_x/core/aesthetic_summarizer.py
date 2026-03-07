import json
from pathlib import Path
from datetime import datetime
from typing import List, Dict, Any
from sqlmodel import select

from src.ai_write_x.database.db_manager import get_session
from src.ai_write_x.database.models import ArticleAesthetic
from src.ai_write_x.core.agent_factory import AgentFactory
from src.ai_write_x.core.base_framework import AgentConfig
from src.ai_write_x.config.config import Config
from src.ai_write_x.utils.path_manager import PathManager
from src.ai_write_x.utils import log

class AestheticSummarizer:
    """审美特征总结器：将用户投票转化为 AI 可理解的审美 DNA"""
    
    def __init__(self):
        self.config = Config.get_instance()
        self.profile_path = PathManager.get_root_dir() / "config" / "aesthetic_profile.json"
        self.agent_factory = AgentFactory()

    async def summarize(self):
        """执行审美总结流程"""
        log.print_log("🧬 正在启动审美特征深度审计与总结...", "info")
        
        # 0. 加载已有的审美特征DNA（如果有的话）
        existing_profile = self._load_existing_profile()
        
        # 1. 采集历史投票数据
        feedback_data = self._collect_feedback()
        if not feedback_data:
            log.print_log("⚠️ 未发现足够的审美反馈数据，通过默认风格继续。", "warning")
            return self._generate_default_profile()

        # 2. 准备 AI Summarizer Agent
        summarizer_agent = self._create_summarizer_agent()
        
        # 3. 构建分析任务（传入已有profile供AI参考调整）
        prompt = self._build_analysis_prompt(feedback_data, existing_profile)
        
        try:
            log.print_log("🎨 AI 审美专家正在解析排版偏置与视觉偏好...", "info")
            
            # 获取 LLM 实例并记录配置
            llm = self.agent_factory._get_llm()
            
            # 打印详细的调试信息
            log.print_log("=" * 60, "debug")
            log.print_log("📤 [审美DNA] 发送请求详情:", "debug")
            log.print_log(f"   模型: {llm._original_model}", "debug")
            log.print_log(f"   API Base: {llm.base_url}", "debug")
            log.print_log(f"   Temperature: {llm.temperature}", "debug")
            log.print_log(f"   Max Tokens: {llm.max_tokens}", "debug")
            log.print_log(f"   Stream: {llm._stream}", "debug")
            log.print_log("-" * 60, "debug")
            log.print_log("📝 [审美DNA] 发送的 Prompt 内容:", "debug")
            log.print_log("-" * 60, "debug")
            # 打印 prompt 内容（可能很长，分段打印）
            prompt_lines = prompt.split('\n')
            for i, line in enumerate(prompt_lines[:50]):  # 限制打印前50行
                log.print_log(f"   {line}", "debug")
            if len(prompt_lines) > 50:
                log.print_log(f"   ... (共 {len(prompt_lines)} 行, 省略 {len(prompt_lines)-50} 行)", "debug")
            log.print_log("=" * 60, "debug")
            
            # 调用 LLM
            response = llm.call(prompt)
            
            # 打印返回结果
            log.print_log("📥 [审美DNA] LLM 返回结果:", "debug")
            log.print_log(f"   返回类型: {type(response)}", "debug")
            log.print_log(f"   返回长度: {len(response) if response else 0} 字符", "debug")
            if response:
                log.print_log(f"   返回内容前500字符: {response[:500]}", "debug")
            log.print_log("=" * 60, "debug")
            
            # 4. 解析并持久化 JSON
            profile = self._parse_ai_response(response)
            
            # 5. 记录本次汇总时间
            profile["last_summary_time"] = datetime.now().isoformat()
            profile["total_votes_analyzed"] = len(feedback_data)
            
            self._save_profile(profile)
            
            log.print_log("✅ 审美特征文件 (Aesthetic Profile) 已更新，AI 已习得最新审美偏好。", "success")
            log.print_log(f"📊 已分析 {len(feedback_data)} 条投票记录", "info")
            return profile
        except Exception as e:
            log.print_log(f"审美总结失败: {e}", "error")
            return None

    def _load_existing_profile(self) -> Dict[str, Any]:
        """加载已有的审美特征DNA，供下次汇总时参考调整"""
        if self.profile_path.exists():
            try:
                with open(self.profile_path, "r", encoding="utf-8") as f:
                    profile = json.load(f)
                    log.print_log(f"📂 检测到已有审美DNA，将作为调整基准", "info")
                    return profile
            except Exception as e:
                log.print_log(f"⚠️ 加载已有DNA失败: {e}", "warning")
        return None

    def _collect_feedback(self, limit: int = 50) -> List[Dict[str, Any]]:
        """从数据库读取最新的评价数据"""
        with get_session() as session:
            statement = select(ArticleAesthetic).order_by(ArticleAesthetic.created_at.desc()).limit(limit)
            results = session.exec(statement).all()
            
            feedback = []
            for r in results:
                feedback.append({
                    "rating": r.rating,
                    "positive_tags": json.loads(r.positive_tags),
                    "negative_tags": json.loads(r.negative_tags),
                    "comment": r.comment or ""
                })
            return feedback

    def _create_summarizer_agent(self):
        """创建专门负责审美总结的 Agent"""
        config = AgentConfig(
            name="审美DNA架构师",
            role="AI Aesthetic DNA Architect",
            goal="Analyze user design feedback to distill specific aesthetic rules for layout, color, and structure.",
            backstory="You are an expert in graphic design and generative AI. You excel at turning subjective feedback into objective generative rules.",
            capabilities=["aesthetic-analysis", "rule-distillation"]
        )
        return self.agent_factory.create_agent(config)

    def _build_analysis_prompt(self, feedback: List[Dict[str, Any]], existing_profile: Dict[str, Any] = None) -> str:
        """构建 AI 分析提示词，传入已有profile供调整参考"""
        feedback_str = json.dumps(feedback, ensure_ascii=False, indent=2)
        
        # 如果有已有profile，加入到prompt中
        existing_context = ""
        if existing_profile:
            existing_context = f"""
【已有审美DNA基准 - 请在此基础上根据新的投票反馈进行微调优化】
- 当前布局偏好: {existing_profile.get('layout_preferences', 'N/A')}
- 当前配色风格: {existing_profile.get('color_style', 'N/A')}
- 当前结构规则: {existing_profile.get('structural_rules', 'N/A')}
- 已有氛围关键词: {', '.join(existing_profile.get('vibe_keywords', []))}
- 上次汇总时间: {existing_profile.get('last_summary_time', 'N/A')}

请基于以上基准，结合新的投票反馈进行分析，适当微调优化而非完全重写。
"""
        
        return f"""
你是一位顶尖的 AI 审美架构师。请通过以下用户对 AI 生成文章/模板的评价数据，总结出一套"审美特征 DNA"。
{existing_context}
评价数据：
{feedback_str}

请输出一个合法的 JSON 对象，包含以下字段：
1. "layout_preferences": 布局偏好 (如：喜欢留白、喜欢紧凑、喜欢大图等)
2. "color_style": 配色风格偏好
3. "structural_rules": 结构化规则 (如：必须有总结盒、必须有三级标题、禁忌事项)
4. "vibe_keywords": 核心氛围关键词 (3-5个)
5. "last_updated": ISO格式当前时间

注意：只输出 JSON 内容，不要任何解释。
"""

    def _parse_ai_response(self, response: str) -> Dict[str, Any]:
        """从 AI 响应中提取 JSON"""
        try:
            # 去除可能存在的 markdown 标记
            clean_res = response.strip().replace("```json", "").replace("```", "").strip()
            return json.loads(clean_res)
        except Exception:
            log.print_log("❌ AI 返回的审美特征格式有误，无法解析。", "error")
            return self._generate_default_profile()

    def _save_profile(self, profile: Dict[str, Any]):
        """持久化审美特征文件"""
        self.profile_path.parent.mkdir(parents=True, exist_ok=True)
        with open(self.profile_path, "w", encoding="utf-8") as f:
            json.dump(profile, f, ensure_ascii=False, indent=2)

    def _generate_default_profile(self) -> Dict[str, Any]:
        """生成默认的初级审美特征"""
        return {
            "layout_preferences": "简约呼吸感，主次分明",
            "color_style": "现代商务，低饱和度渐变",
            "structural_rules": "强化 H2/H3 层次感，引入知识卡片模块",
            "vibe_keywords": ["专业", "科技", "现代"],
            "last_updated": datetime.now().isoformat()
        }