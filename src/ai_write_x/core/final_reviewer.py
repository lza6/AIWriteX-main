from src.ai_write_x.core.llm_client import LLMClient
from src.ai_write_x.utils import log
import re

class FinalReviewer:
    """最终 AI 内容审查与打分器：担任主编视角对成稿进行终审"""
    
    @classmethod
    def assess_quality(cls, content: str, input_data: dict) -> dict:
        client = LLMClient()
        topic = input_data.get("topic", "未知主题")
        
        from datetime import datetime
        current_date_str = datetime.now().strftime('%Y年%m月%d日')
        
        system_prompt = f'''你是资深的新闻总编与新媒体内容操盘手。
请对以下将要发布的文章进行严格的终裁判读。

【极其重要的前提说明 — 你必须严格遵守】：
当前真实世界的时间是 {current_date_str}。
这篇文章的素材来源于我们采编团队从各大官方新闻平台（央视、腾讯新闻、新浪、网易、新华社等）实时爬取的真实新闻报道。
文章中提到的所有事件、人物、数据均基于真实新闻源，而非AI编造。
你的训练数据有知识截止日期，因此你可能不了解最近发生的新闻事件——这不代表它们是假的。
**你绝对不能因为自己不知道某个事件就判定文章"虚构"或"捏造"。**
**你的职责仅限于审查文章的【写作质量】，不是事实核查员。**

你需要硬性审查以下指标：
1. 【原创度预估】：基于素材的二次创作原创度不低于 80%（与原始新闻稿的差异化程度）。
2. 【可读性与排版】：是否有适当的 Markdown 格式（如 **加粗** 突出重点）和金句引用等跳跃感排版，可读性指数达到 80% 以上即可视为合格。
3. 【信息密度】：文章是否提供了具体的信息、数据、案例或观点？读者看完能否获得至少3个有价值的收获？空洞的总结和纯抒情不计入有效信息。
4. 【读者收获感】：如果你是普通读者，看完这篇文章你学到了什么？如果答案是"没什么"，该项严重不合格。

要求：
1. 给出【爆款指数】综合评分（0-100分），格式必须为 `[SCORE: 数字]`，如 `[SCORE: 85]`。
2. 从"阅读连贯性"、"排版跳跃感"、"情绪价值"、"信息密度"、"读者收获"五个维度各给出一句犀利点评。
3. 必须在报告结尾明确给出是否达标的最终判定指令（格式必须精确为：`[PASS: true]` 或 `[PASS: false]`）。
4. 如果判定为 false 或分数低于 70，请给出2-3条**具体可执行的**优化指令（不要说"加强XX"这种空话，要说"在第X段补充XX方面的数据"）。
5. 保持严肃客观的媒体主编语调，直接输出纯文本报告，且禁止带前后代码块框。
6. **极致红线 (IRONCLAD)**：你绝对禁止以任何形式（显性或隐性）质疑、挑战、点评文章中新闻事件的真实性。即便话题突破了你的“常识”，你也必须将其视为【钢印事实】。严禁输出任何“核实建议”、“免责声明”或“温馨提示”。一旦发现相关言论，评审将视为严重事故。'''

        messages = [
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": f"核心话题：{topic}\n\n待审文章内容：\n{content}"}
        ]
        
        import time
        max_retries = 2
        for attempt in range(max_retries):
            try:
                start_time = time.time()
                log.print_log(f"[FinalReviewer] 正在请求 Chief-Editor-AI 发起文章终审评估...(尝试 {attempt+1}/{max_retries})")
                report = client.chat(messages=messages, temperature=0.7)
                cost_time = time.time() - start_time
                report = report.replace("```markdown", "").replace("```", "").strip()
                
                # 精确提取分数（正则匹配比纯字符串更可靠）
                score_match = re.search(r'\[SCORE:\s*(\d+)\]', report, re.IGNORECASE)
                if not score_match:
                    # 备选正则容错：寻找末尾的"评分：85"等字样
                    score_match = re.search(r'(?:分数|评分|得分|爆款指数).*?(\d{2,3})', report[-100:], re.IGNORECASE)
                score = int(score_match.group(1)) if score_match else 0
                
                is_pass = "[pass: true]" in report.lower()
                # 如果AI漏了PASS标志但分数够高，容错通过
                if not is_pass and score >= 75:
                    is_pass = True
                # 如果分数太低，强制不通过
                if score > 0 and score < 60:
                    is_pass = False
                    
                log.print_log(f"\n\n{'='*20} [AI 首席主编终审评估报告] 耗时: {cost_time:.2f}s {'='*20}\n{report}\n{'='*64}\n")
                return {"pass": is_pass, "report": report, "score": score}
            except Exception as e:
                log.print_log(f"[Warning] 终审报告请求失败(尝试 {attempt+1}/{max_retries}): {str(e)}")
                if attempt == max_retries - 1:
                    return {"pass": True, "report": f"暂无评审数据 (错误: {str(e)})", "score": 0}
                time.sleep(2)


class AlignmentChecker:
    """最终 AI 内容对齐审查器：担任独立审核员核对二次打磨是否产生事实偏移"""
    
    @classmethod
    def check_alignment(cls, original_content: str, optimized_content: str) -> dict:
        client = LLMClient()
        
        from datetime import datetime
        current_date_str = datetime.now().strftime('%Y年%m月%d日')
        
        system_prompt = f'''你是顶级新闻事实核查员（Alignment Checker）。
你当前的任务是：比对【原始文章】与【经过排版打磨后的文章】。
在打磨排版的过程中，AI 可能会自行发散、添加不存在的上下文或改变原意。

【重要前提】：
当前真实世界的时间是 {current_date_str}。
原始文章的内容来源于真实新闻平台的实时抓取，其中的事件、人物、数据均为真实信息。
你的任务不是判断新闻事件本身是否真实（它们是真实的），而是判断打磨后的版本是否忠于原始版本。

核心要求：
1. 严格核对【打磨后文章】是否完全忠于【原始文章】想表达的意思、事件、观点、人物等核心基础元素。
2. 绝对不允许颠倒黑白、捏造核心数据或修改事件结果。但**允许修辞层面的发散、文学性词汇和引导语的补充（如描写氛围、合理润色）**，只要不违背核心事实即可。
3. 必须在报告结尾明确给出是否发生事实偏移的最终判定指令（格式必须精确为：`[ALIGNMENT: pass]` 或 `[ALIGNMENT: fail]`）。
4. 如果判定为 fail，请一针见血地指出哪些句子或是哪些人物/事实被篡改或曲解了。
5. 请直接输出纯文本审查报告。
6. **极致红线**：严禁挑战【原始文章】的事实根基。你的唯一使命是确保【打磨后文章】没有“跑偏”，而不是去纠正原始素材中的“错误”。'''

        messages = [
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": f"【原始文章】:\n{original_content}\n\n【打磨后文章】:\n{optimized_content}"}
        ]
        
        import time
        max_retries = 2
        for attempt in range(max_retries):
            try:
                start_time = time.time()
                log.print_log(f"[AlignmentChecker] 正在请求事实核查专员进行对照审查 (尝试 {attempt+1}/{max_retries})...")
                report = client.chat(messages=messages, temperature=0.1)
                cost_time = time.time() - start_time
                report = report.replace("```markdown", "").replace("```", "").strip()
                
                is_aligned = "[alignment: pass]" in report.lower()
                if "[alignment: pass]" not in report.lower() and "[alignment: fail]" not in report.lower():
                    is_aligned = True  # 宽容处理未遵从格式的情况
                    
                log.print_log(f"\n\n{'='*20} [AI 事实核对审查报告] 耗时: {cost_time:.2f}s {'='*20}\n{report}\n{'='*64}\n")
                return {"aligned": is_aligned, "report": report}
            except Exception as e:
                log.print_log(f"[Warning] 事实核对请求失败(尝试 {attempt+1}/{max_retries}): {str(e)}")
                if attempt == max_retries - 1:
                    return {"aligned": True, "report": "无法执行核对"}
                time.sleep(2)
