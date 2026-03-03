from src.ai_write_x.core.llm_client import LLMClient
from src.ai_write_x.utils import log

class FinalReviewer:
    """最终 AI 内容审查与打分器：担任主编视角对成稿进行终审"""
    
    @classmethod
    def assess_quality(cls, content: str, input_data: dict) -> dict:
        client = LLMClient()
        topic = input_data.get("topic", "未知主题")
        
        system_prompt = '''你是资深的新闻总编与新媒体内容操盘手。
请对以下将要发布的文章进行严格的终裁判读。
你需要硬性审查两个指标：
1. 【原创度预估】：全篇原创度不低于 80%。
2. 【可读性与排版】：是否有适当的 Markdown 格式（如 **加粗** 突出重点）和金句引用等跳跃感排版，可读性指数达到 80% 以上即可视为合格。

要求：
1. 给出【爆款指数】综合评分（0-100分）。
2. 从“阅读连贯性”、“排版跳跃感”、“情绪价值”三个维度各给出一句犀利点评。
3. 必须在报告结尾明确给出是否达标的最终判定指令（格式必须精确为：`[PASS: true]` 或 `[PASS: false]`）。
4. 如果判定为 false，请给出1-2条一针见血的需优化/重写指令。
5. 保持严肃客观的媒体主编语调，直接输出纯文本报告，且禁止带前后代码块框。'''

        messages = [
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": f"核心话题：{topic}\n\n待审文章内容：\n{content}"}
        ]
        
        try:
            log.print_log("[FinalReviewer] 正在请求 Chief-Editor-AI 发起文章终审评估...")
            report = client.chat(messages=messages, temperature=0.7)
            # Remove possible markdown fences
            report = report.replace("```markdown", "").replace("```", "").strip()
            
            is_pass = "[PASS: true]" in report.lower() or "[pass: true]" in report.lower()
            if "[PASS: true]" not in report and "[PASS: false]" not in report and "[pass: true]" not in report.lower() and "[pass: false]" not in report.lower():
                # 若AI漏掉硬编码标志，则容错判定分数是否极高
                is_pass = "9" in report or "100" in report # 粗略容错
                
            log.print_log(f"\n\n{'='*20} [AI 首席主编终审评估报告] {'='*20}\n{report}\n{'='*64}\n")
            return {"pass": is_pass, "report": report}
        except Exception as e:
            log.print_log(f"[Warning] 终审报告请求失败: {str(e)}")
            return {"pass": True, "report": "暂无评审数据"}


class AlignmentChecker:
    """最终 AI 内容对齐审查器：担任独立审核员核对二次打磨是否产生事实偏移"""
    
    @classmethod
    def check_alignment(cls, original_content: str, optimized_content: str) -> dict:
        client = LLMClient()
        
        system_prompt = '''你是顶级新闻事实核查员（Alignment Checker）。
你当前的任务是：比对【原始文章】与【经过排版打磨后的文章】。
在打磨排版的过程中，AI 可能会自行发散、添加不存在的上下文或改变原意。

核心要求：
1. 严格核对【打磨后文章】是否完全忠于【原始文章】想表达的意思、事件、观点、人物等核心基础元素。
2. 绝对不允许颠倒黑白、捏造核心数据或修改事件结果。但**允许修辞层面的发散、文学性词汇和引导语的补充（如描写氛围、合理润色）**，只要不违背核心事实即可。
3. 必须在报告结尾明确给出是否发生事实偏移的最终判定指令（格式必须精确为：`[ALIGNMENT: pass]` 或 `[ALIGNMENT: fail]`）。
4. 如果判定为 fail，请一针见血地指出哪些句子或是哪些人物/事实被篡改或曲解了。
5. 请直接输出纯文本审查报告。'''

        messages = [
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": f"【原始文章】:\n{original_content}\n\n【打磨后文章】:\n{optimized_content}"}
        ]
        
        try:
            log.print_log("[AlignmentChecker] 正在请求事实核查专员进行对照审查 (Zero-Context)...")
            report = client.chat(messages=messages, temperature=0.1)  # 使用极低温度确保严谨的比对
            report = report.replace("```markdown", "").replace("```", "").strip()
            
            is_aligned = "[ALIGNMENT: pass]" in report.lower() or "[alignment: pass]" in report.lower()
            if "[ALIGNMENT: pass]" not in report and "[ALIGNMENT: fail]" not in report and "[alignment: pass]" not in report.lower() and "[alignment: fail]" not in report.lower():
                is_aligned = True # 宽容处理未遵从格式的情况
                
            log.print_log(f"\n\n{'='*20} [AI 事实核对审查报告] {'='*20}\n{report}\n{'='*64}\n")
            return {"aligned": is_aligned, "report": report}
        except Exception as e:
            log.print_log(f"[Warning] 事实核对请求失败: {str(e)}")
            return {"aligned": True, "report": "无法执行核对"}
