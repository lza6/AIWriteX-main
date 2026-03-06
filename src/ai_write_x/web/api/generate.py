#!/usr/bin/env python
# -*- coding: UTF-8 -*-

from fastapi import APIRouter, HTTPException, WebSocket, WebSocketDisconnect
from fastapi.responses import FileResponse
from pydantic import BaseModel
from typing import Optional
import asyncio
import time
import queue
import os
from datetime import datetime

from ..state import get_app_state
from src.ai_write_x.core.task_manager import task_manager, TaskStatus

from src.ai_write_x.config.config import Config
from src.ai_write_x.crew_main import ai_write_x_main
from src.ai_write_x.tools import hotnews
from src.ai_write_x.utils import utils, log
from src.ai_write_x.utils.topic_deduplicator import TopicDeduplicator

router = APIRouter(prefix="/api", tags=["generate"])

# V5: 增加时间戳供前端展示生成耗时
# V7: 状态管理由 BackgroundTaskManager 托管


class ReferenceConfig(BaseModel):
    """借鉴模式配置"""

    template_category: Optional[str] = None
    template_name: Optional[str] = None
    reference_urls: Optional[str] = None
    reference_ratio: Optional[int] = 30
    reference_article_id: Optional[str] = None


class GenerateRequest(BaseModel):
    """内容生成请求"""

    topic: Optional[str] = ""
    platform: Optional[str] = ""
    reference: Optional[ReferenceConfig] = None
    article_count: Optional[int] = 1
    post_action: Optional[str] = "none"
    ai_beautify: Optional[bool] = False


@router.get("/config/validate")
async def validate_config():
    """
    验证系统配置

    返回友好的错误消息,前端可以直接显示给用户
    """
    try:
        config = Config.get_instance()

        if not config.validate_config():
            # 根据错误类型返回不同的消息
            error_msg = config.error_message

            # 检查是否是 API KEY 相关错误
            if "API KEY" in error_msg or "api_key" in error_msg:
                detail = f"{error_msg}\n\n请前往【系统设置 → 大模型API】配置您的 API 密钥。"
            elif "Model" in error_msg or "model" in error_msg:
                detail = f"{error_msg}\n\n请前往【系统设置 → 大模型API】配置模型参数。"
            elif "微信公众号" in error_msg or "appid" in error_msg:
                detail = f"{error_msg}\n\n请前往【系统设置 → 微信公众号】配置账号信息。"
            else:
                detail = f"配置错误: {error_msg}"

            raise HTTPException(status_code=400, detail=detail)

        return {"status": "success", "message": "配置验证通过"}

    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"配置验证失败: {str(e)}")


@router.post("/generate")
async def generate_content(request: GenerateRequest):
    # V7: 使用 TaskManager 检查状态
    status = task_manager.get_task_status("main_generate")
    if status["status"] == TaskStatus.RUNNING:
        raise HTTPException(status_code=409, detail="任务正在运行中,请先停止当前任务")

    try:
        config = Config.get_instance()

        # 系统配置校验
        if not config.validate_config():
            raise HTTPException(status_code=400, detail=f"配置错误: {config.error_message}")

        topic = request.topic.strip() if request.topic else ""
        
        # 借鉴模式下，如果没有话题但有文章ID，从文章提取话题
        if request.reference and not topic:
            if request.reference.reference_article_id:
                # 从文章数据库获取话题
                from src.ai_write_x.tools.spider_manager import spider_data_manager
                articles = spider_data_manager.get_articles(limit=1000)
                article = next((a for a in articles if str(a.get('id', '')) == request.reference.reference_article_id), None)
                if article:
                    topic = article.get('title', '')
                    log.print_log(f"从文章提取话题: {topic}", "info")
                    # 如果文章有URL且没有填reference_urls，自动填入
                    if article.get('url') and not request.reference.reference_urls:
                        request.reference.reference_urls = article.get('url', '')
            
            # 如果还是没有话题但有参考链接，使用链接作为参考
            if not topic and request.reference.reference_urls:
                log.print_log("将根据参考链接生成内容", "info")
        # 如果最终还是没话题，报错（在热搜模式下，可能前面尚未获取）
        # V14.4: 当未填话题时，允许热点为空，后端会自动全网盲搜（单篇/批量均适用）
        # if not topic and not request.reference:
        #    raise HTTPException(status_code=400, detail="请输入话题或选择参考文章")
        # 将 post_action 保存到 Config 以便后续执行发布
        config.post_action = request.post_action or "none"
        config.article_count = request.article_count or 1

        # 我们需要一个特殊的后台任务进程，用于循环生成文章
        from multiprocessing import Process, Queue

        import threading
        import queue
        
        def batch_thread_worker(global_config_dict, req_topic, req_platform, is_reference, ref_config_dict, ai_beautify):
            # V11 Hotfix: 通过 log.get_process_queue() 动态获取当前线程绑定的日志队列
            # 兼容 task_manager.py 的 _worker_wrapper 注入逻辑
            import src.ai_write_x.utils.log as lg
            log_q = lg.get_process_queue()
            # global _task_status # Removed
            from src.ai_write_x.config.config import Config as ProcessConfig
            import traceback
            import time
            from src.ai_write_x.web.state import get_app_state
            from src.ai_write_x.crew_main import ai_write_x_main
            import src.ai_write_x.utils.log as lg
            
            # 恢复 Config 
            cfg = ProcessConfig.get_instance()
            for k, v in global_config_dict.items():
                setattr(cfg, k, v)
                
            article_count = getattr(cfg, "article_count", 1)
            success_count = 0
            
            # 设置当前线程(主进程的一个线程)的日志队列已由 task_manager 处理，无需重复调用
            # lg.set_process_queue(log_q)
            
            try:
                from src.ai_write_x.utils.topic_deduplicator import TopicDeduplicator
                deduplicator = TopicDeduplicator(dedup_days=3)
                used_session_topics = []
                
                for i in range(article_count):
                    lg.print_log(f"=====================================", "internal")
                    lg.print_log(f"🔜 [批量进度] 正在生成第 {i+1}/{article_count} 篇文章", "success")
                    
                    # V12 Enhancement: 记录本次生成的起始时间，用于隔离旧数据
                    # 如果开启了严格模式，则每次循环都重置时间戳，确保只取“刚刚生成的”
                    strict_mode = getattr(cfg, "strict_freshness", True)
                    session_start_time = time.time() if strict_mode else (time.time() - 3 * 3600)
                    
                    # 50% 概率回退逻辑（仅在关闭严格模式时生效）
                    if not strict_mode and random.random() < 0.5:
                        lg.print_log("🎲 按照用户偏好（非严格模式）：本次 50% 概率允许采用 3 小时内的历史优质话题", "info")
                        # 已经是 -3h 了，不做额外处理
                    elif not strict_mode:
                        session_start_time = time.time() # 另外 50% 还是强制实时
                    
                    t = ""
                    p = req_platform or "全网发现"
                    d_str = "最新"
                    
                    # 1. 前台指定了明确的话题
                    if req_topic:
                        if i == 0:
                            t = req_topic
                        else:
                            lg.print_log("🧠 正在让 AI 基于原话题发散全新视角...", "info")
                            from src.ai_write_x.core.llm_client import LLMClient
                            try:
                                llm = LLMClient()
                                prompt = f"以“{req_topic}”为核心，请发散提供一个互不相同、切入点独特的相关新闻话题。只需输出一句话标题。必须避开以下这几个相似标题: {', '.join(used_session_topics)}"
                                t = llm.chat([{"role": "user", "content": prompt}]).strip().strip('-*0123456789. \n')
                            except Exception:
                                t = f"{req_topic} 独家深度追踪 {i+1}"
                    # 2. 空白话题，需要搜刮全网+AI人工严选
                    elif not is_reference:
                        lg.print_log("🌍 正在重新抓取全网实时数据，准备搜寻下一个热点...", "info")
                        from src.ai_write_x.core.llm_client import LLMClient
                        from src.ai_write_x.tools.spider_runner import SpiderRunner
                        from src.ai_write_x.tools.spider_manager import spider_data_manager
                        import asyncio
                        import random
                        
                        try:
                            runner = SpiderRunner()
                            enabled_spiders = [name for name, info in runner.spiders.items() if info.get("enabled", True)]
                            
                            # 定义权威源集合
                            authority_spiders = {"bbc", "xinhua", "nytimes", "wsj", "zaobao", "voa", "8world", "zhongguoribao"}
                            
                            if enabled_spiders:
                                loop_spider = asyncio.new_event_loop()
                                asyncio.set_event_loop(loop_spider)
                                tasks = []
                                
                                # 将已启用的爬虫分为权威和普通两组
                                available_authority = [s for s in enabled_spiders if s in authority_spiders]
                                available_normal = [s for s in enabled_spiders if s not in authority_spiders]
                                
                                # 优先选取权威源 (最多2-3个)
                                selected_spiders = []
                                if available_authority:
                                    selected_spiders.extend(random.sample(available_authority, min(2, len(available_authority))))
                                
                                # 再补充一些普通源保证多样性 (补齐到3-4个)
                                remaining_slots = max(1, 4 - len(selected_spiders))
                                if available_normal:
                                    selected_spiders.extend(random.sample(available_normal, min(remaining_slots, len(available_normal))))
                                    
                                for spider_name in selected_spiders:
                                    tasks.append(asyncio.wait_for(runner.run_spider(spider_name, limit=15), timeout=20.0))
                                    
                                if tasks:
                                    loop_spider.run_until_complete(asyncio.gather(*tasks, return_exceptions=True))
                                loop_spider.close()
                                
                            # V12: 传入 min_time 以实现话题隔离
                            articles = spider_data_manager.get_articles(limit=100, min_time=session_start_time)
                            candidate_titles = []
                            for a in articles:
                                a_title = a.get("title", "")
                                if a_title and not deduplicator.is_duplicate(a_title) and a_title not in used_session_topics:
                                    candidate_titles.append(f"[{a.get('spider', '资讯')}] {a_title}")
                            
                            # 后备手段: 如果不够用，上权威榜单
                            if len(candidate_titles) < 5:
                                from src.ai_write_x.tools import hotnews
                                # V12: 同时支持权威源的时间过滤
                                cand_hot = hotnews.select_platform_topic(
                                    "全网热点", 
                                    cnt=100, 
                                    exclude_topics=used_session_topics, 
                                    authority_priority=True,
                                    min_time=session_start_time
                                )
                                if isinstance(cand_hot, str) and cand_hot:
                                    candidate_titles.append(f"[全网热搜] {cand_hot}")
                                elif isinstance(cand_hot, list):
                                    candidate_titles.extend([f"[全网热搜] {x}" for x in cand_hot if isinstance(x, str)])
                            
                            # 过滤掉空的
                            candidate_titles = [ct for ct in candidate_titles if ct.strip()]
                            
                            lg.print_log(f"📡 抓取完成，共获得 {len(candidate_titles)} 个全新独立候选话题（已启用权威源优先机制）", "info")
                            lg.print_log("🧠 AI总编正在执行严苛审查，挑选本期最具爆炸力与深度的唯一热点...", "info")
                            
                            llm = LLMClient()
                            if candidate_titles:
                                prompt = f"""以下是从全网各大平台及海外权威媒体（如BBC、纽时、新华社）抓取的最新热点候选列表。
请作为首席国际新闻主编，从中挑选出【唯一一个】最具有社会价值、爆款潜质、深度讨论空间和国际视野的权威级话题。

要求：
- 必须优先考虑那些带有国际地缘、重大科技、宏观经济或深远社会影响的硬核新闻（如源自bbc、xinhua、nytimes等标签的内容）。
- 坚决过滤掉无意义的娱乐剥削或低俗八卦。
- 绝不要选择纯粹为博眼球但毫无信息量的标题党。
- 我们的系统已经写过以下话题（必须严格避开）：
{', '.join(used_session_topics) if used_session_topics else "无"}

候选列表（最多看前50个）：
{chr(10).join(candidate_titles[:50])}

最终输出要求：
1. 请直接返回最终选定的一句话标题。
2. 绝对不要包含任何前缀（如[BBC]）、标签、理由或多余符号。"""
                                picked_title = llm.chat([{"role": "user", "content": prompt}]).strip().strip('-*0123456789. \n"\'')
                                import re
                                picked_title = re.sub(r'^\[.*?\]\s*', '', picked_title)
                                t = picked_title
                            else:
                                prompt_empty = f"请提供一个当下的热门互联网资讯或科技社会热点话题，确保独特且具有国际新闻价值。只需输出标题。避开: {', '.join(used_session_topics)}"
                                t = llm.chat([{"role": "user", "content": prompt_empty}]).strip().strip('-*0123456789. \n"\'')
                        except Exception as e:
                            lg.print_log(f"AI严选及抓取过程出现异常: {e}，将采用备用方案", "warning")
                            t = f"全球最新前沿资讯与独家深度追踪 {i+1}"
                    
                    if not t:
                        t = "全球热点聚合与最新行业动态追踪"

                    # 记录并标记使用状态
                    import re
                    t = re.sub(r'^\[.*?\]\s*', '', t) # Double check strip
                    used_session_topics.append(t)
                    deduplicator.add_topic(t)
                    
                    lg.print_log(f"🎯 正式确定话题: 【{t}】", "success")
                    lg.print_log(f"=====================================", "internal")
                    
                    config_data = {
                        "custom_topic": t,
                        "urls": [],
                        "reference_ratio": 0.0,
                        "custom_template_category": ref_config_dict.get("template_category", ""),
                        "custom_template": ref_config_dict.get("template_name", ""),
                        "platform": p,
                        "reference_content": "",
                        "date_str": d_str
                    }
                    
                    if ref_config_dict and ref_config_dict.get("is_reference"):
                        if ref_config_dict.get("reference_article_id"):
                            from src.ai_write_x.tools.spider_manager import spider_data_manager
                            articles = spider_data_manager.get_articles(limit=1000)
                            art = next((a for a in articles if str(a.get('id', '')) == ref_config_dict.get("reference_article_id")), None)
                            if art:
                                content_text = art.get('content') or art.get('article_info', '')
                                if content_text:
                                    config_data["reference_content"] = content_text
                                config_data["date_str"] = art.get('date_str', '')
                        
                        if ref_config_dict.get("reference_urls"):
                            urls = [u.strip() for u in ref_config_dict.get("reference_urls").split("|") if u.strip()]
                            config_data["urls"] = urls
                            
                        config_data["reference_ratio"] = float(ref_config_dict.get("reference_ratio", 30)) / 100
                    
                    try:
                        # 核心生成节点
                        lg.print_log(f"[{i+1}/{article_count}] 开始执行生成线程...", "info")
                        # 确保主模块状态
                        process, p_log_queue = ai_write_x_main(config_data)
                        if process and p_log_queue:
                            process.start()
                            # V7: 注册子进程以便统一管理
                            task_manager.register_sub_process("main_generate", process)
                            final_result = None
                            
                            # 循环读取日志，同时检测子进程存活状态
                            while process.is_alive() or not p_log_queue.empty():
                                try:
                                    msg = p_log_queue.get(timeout=0.1)
                                    # 将 internal 的 任务执行完成 拦截掉（如果不拦截会被前端认为是整体完成）
                                    if msg.get("type") == "internal" and "任务执行完成" in msg.get("message", ""):
                                        if "result" in msg:
                                            final_result = msg.get("result")
                                            
                                        if i == article_count - 1:
                                            # 最后一条的话，直接放行，告诉前端真正完成了
                                            log_q.put(msg)
                                        else:
                                            # 截断它，不发送给前端，或者转换成 info 告诉前端这一篇完成了
                                            pass 
                                    else:
                                        log_q.put(msg)
                                except queue.Empty:
                                    pass
                                    
                            process.join()
                            if process.exitcode != 0 and process.exitcode is not None:
                                lg.print_log(f"⚠ 进程异常退出 (可能被手动停止)，退出码: {process.exitcode}", "warning")
                                break
                            
                            success_count += 1
                            
                            # 自动化动作
                            post_action = getattr(cfg, "post_action", "none")
                            
                            # === [新增] V6: 文章生成后入库及自动补图逻辑 ===
                            if final_result and final_result.get("success"):
                                try:
                                    db_title = final_result.get("save_result", {}).get("title", t)
                                    db_content = final_result.get("formatted_content", "")
                                    # V13.0.4: 使用 DataManager 实例进行保存
                                    from src.ai_write_x.database.db_manager import db_manager
                                    db_manager.save_article(topic_title=db_title, content=db_content)
                                    lg.print_log(f"💾 文章已归档到本地知识库引擎", "success")
                                except Exception as db_e:
                                    lg.print_log(f"数据库保存异常: {db_e}", "warning")
                                    
                                try:
                                    save_res = final_result.get("save_result", {})
                                    article_path = save_res.get("path")
                                    if article_path and ai_beautify:
                                            
                                        from src.ai_write_x.core.visual_assets import VisualAssetsManager
                                        lg.print_log(f"🎨 正在后台检测并自动补齐文章图片...", "info")
                                        # 异步触发补图，避免阻塞日志流
                                        import threading
                                        img_thread = threading.Thread(
                                            target=VisualAssetsManager.auto_fix_article_images,
                                            args=(article_path,),
                                            daemon=True
                                        )
                                        img_thread.start()
                                    elif article_path and not ai_beautify:
                                        lg.print_log(f"⏭️ AI美化开关未开启，跳过自动补齐图片步骤...", "info")
                                except Exception as img_fix_e:
                                    lg.print_log(f"自动补图过程出现异常: {img_fix_e}", "warning")

                            if post_action != "none" and final_result and final_result.get("success"):
                                lg.print_log(f"⚡ 正在执行文章完成后的自动化动作: {post_action}", "info")
                                if post_action in ["publish", "save"]:
                                        try:
                                            save_res = final_result.get("save_result", {})
                                            title = save_res.get("title", "未命名文章")
                                            article_path = save_res.get("path")
                                            content_html = final_result.get("formatted_content", "")
                                            
                                            import re
                                            pure_text = re.sub(r'<[^>]+>', '', content_html)
                                            digest = pure_text[:115] + "..." if len(pure_text) > 115 else pure_text
                                            
                                            import src.ai_write_x.utils.utils as _utils
                                            cover_path = _utils.get_cover_path(article_path) or ""
                                            
                                            wechat_creds = cfg.config.get("wechat", {}).get("credentials", [{}])
                                            if wechat_creds:
                                                wechat_cfg = wechat_creds[0]
                                            else:
                                                wechat_cfg = {}
                                                
                                            appid = wechat_cfg.get("appid", "")
                                            appsecret = wechat_cfg.get("appsecret", "")
                                            author = wechat_cfg.get("author", "AIWriteX")
                                            
                                            if not appid or not appsecret:
                                                lg.print_log("无法执行自动化动作: 未配置微信公众号 AppID 和 AppSecret", "warning")
                                            else:
                                                from src.ai_write_x.tools.wx_publisher import WeixinPublisher
                                                publisher = WeixinPublisher(appid, appsecret, author)
                                                lg.print_log("正在上传封面图到微信素材库...", "info")
                                                media_id, _, err = publisher.upload_image(cover_path)
                                                
                                                if err:
                                                    lg.print_log(f"封面图上传失败: {err}，将使用默认封面", "warning")
                                                    media_id = "SwCSRjrdGJNaWioRQUHzgF68BHFkSlb_f5xlTquvsOSA6Yy0ZRjFo0aW9eS3JJu_"
                                                    
                                                if post_action == "save":
                                                    lg.print_log("正在上传文章到草稿箱...", "info")
                                                    res, err = publisher.add_draft(content_html, title, digest, media_id)
                                                    if err:
                                                        lg.print_log(f"保存到草稿箱失败: {err}", "error")
                                                    else:
                                                        lg.print_log(f"✅ 成功保存到草稿箱!", "success")
                                                elif post_action == "publish":
                                                    lg.print_log("正在上传并发布文章...", "info")
                                                    res, err = publisher.add_draft(content_html, title, digest, media_id)
                                                    if err:
                                                        lg.print_log(f"上传草稿失败，无法发布: {err}", "error")
                                                    else:
                                                        pub_res, pub_err = publisher.publish(res.publishId)
                                                        if pub_err:
                                                            lg.print_log(f"草稿发布失败: {pub_err}", "error")
                                                        else:
                                                            lg.print_log(f"✅ 文章发布任务已提交!", "success")
                                        except Exception as we:
                                            lg.print_log(f"自动化动作执行异常: {we}", "error")
                        else:
                            lg.print_log(f"无法启动生成进程: process is None", "error")
                    except Exception as loop_e:
                        lg.print_log(f"❌ 第 {i+1} 篇文章生成失败: {str(loop_e)}", "error")
                        traceback.print_exc()
                        
                    if i < article_count - 1:
                        lg.print_log("等待 10 秒后开始下一篇文章生成...", "internal")
                        time.sleep(10)
                        
                if success_count > 0:
                    lg.print_log(f"🎉 批量生成任务全部完成！共成功生成 {success_count}/{article_count} 篇文章。", "success")
                else:
                    lg.print_log("❌ 所有文章生成失败", "error")
                
                # V7: 任务管理器会自动处理最终状态，但我们仍需通过日志反馈给前端
                log_q.put({"type": "internal", "message": "任务执行完成", "timestamp": time.time(), "success": success_count > 0})
                    
            except Exception as e:
                import traceback
                error_trace = traceback.format_exc()
                log_q.put({
                    "type": "internal", 
                    "message": "任务执行失败", 
                    "error": str(e), 
                    "timestamp": time.time()
                })
                log_q.put({
                    "type": "error", 
                    "message": f"程序执行异常:\n```\n{error_trace}\n```", 
                    "timestamp": time.time()
                })
            finally:
                # 恢复日志队列为空，防止影响后续其它请求
                lg.set_process_queue(None)
                
                # 显式更新全局任务状态，确保前端轮询能检测到任务完成
                # if success_count > 0: # Removed
                #     _task_status = {"status": "completed", "error": None, "started_at": _task_status.get("started_at"), "finished_at": time.time()} # Removed
                #     print(f"[batch_thread_worker] 任务状态已更新为 completed，成功 {success_count} 篇") # Removed
                # else: # Removed
                #     _task_status = {"status": "failed", "error": "所有文章生成均失败", "started_at": _task_status.get("started_at"), "finished_at": time.time()} # Removed
                #     print(f"[batch_thread_worker] 任务状态已更新为 failed") # Removed
                
                # P2: 自动清理临时文件（超过1小时的env_*.json）
                try:
                    import glob
                    temp_dir = os.path.join(os.path.dirname(os.path.dirname(os.path.dirname(os.path.dirname(os.path.dirname(__file__))))), "temp")
                    if os.path.isdir(temp_dir):
                        cutoff = time.time() - 3600  # 1小时前
                        for f in glob.glob(os.path.join(temp_dir, "env_*.json")):
                            if os.path.getmtime(f) < cutoff:
                                os.remove(f)
                except Exception:
                    pass  # 清理失败不影响主流程
                
                # P2: 强制GC回收，防止长时间运行内存泄漏
                import gc
                gc.collect()

        # import queue # Removed, task_manager provides queue
        # log_queue = queue.Queue() # Removed
        # _current_log_queue = log_queue # Removed
        
        ref_dict = {
            "is_reference": True if request.reference else False,
            "template_category": request.reference.template_category if request.reference else "",
            "template_name": request.reference.template_name if request.reference else "",
            "reference_article_id": request.reference.reference_article_id if request.reference else "",
            "reference_urls": request.reference.reference_urls if request.reference else "",
            "reference_ratio": request.reference.reference_ratio if request.reference else 30
        }
        
        # V7: 使用 TaskManager 启动任务
        success, res = task_manager.start_task(
            "main_generate", 
            batch_thread_worker, 
            (
                config.__dict__,
                topic,
                request.platform,
                ref_dict["is_reference"],
                ref_dict,
                request.ai_beautify,
            )
        )
        
        if not success:
            raise HTTPException(status_code=500, detail=f"任务启动失败: {res}")

        msg = "正在批量生成内容，请耐心等待..." if request.article_count > 1 else "正在生成内容，请耐心等待..."
        log.print_log("生成请求已接受，正在后台处理...", "info")
        return {
            "status": "success",
            "message": msg,
            "mode": "reference" if request.reference else "hot_search",
            "topic": topic,
            "article_count": request.article_count
        }

    except HTTPException:
        print("HTTPException caught in generate")
        raise
    except Exception as e:
        import traceback
        traceback.print_exc()
        print(f"Exception caught in generate: {e}")
        log.print_log(f"生成启动失败: {str(e)}", "error")
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/generate/stop")
async def stop_generation():
    """停止当前生成任务"""
    success, msg = task_manager.stop_task("main_generate")
    if success:
        return {"status": "success", "message": "任务已停止"}
    return {"status": "info", "message": msg}


@router.get("/generate/status")
async def get_generation_status():
    return task_manager.get_task_status("main_generate")


@router.websocket("/ws/generate/logs")
async def websocket_logs(websocket: WebSocket):
    """WebSocket日志连接 - 统一处理主进程和子进程日志"""
    await websocket.accept()

    global _current_log_queue, _current_process

    # 初始化文件日志处理器
    from datetime import datetime
    from src.ai_write_x.utils.path_manager import PathManager

    app_state = get_app_state()
    log_file = PathManager.get_log_dir() / f"WEB_{datetime.now().strftime('%Y-%m-%d')}.log"
    log.LogManager.get_instance().set_file_handler(log_file)
    file_handler = log.LogManager.get_instance().get_file_handler()

    try:
        log_queue = task_manager.get_log_queue("main_generate")
        while True:
            # 检查子进程日志队列
            if log_queue:
                try:
                    msg = log_queue.get_nowait()

                    # 发送到前端
                    await websocket.send_json(
                        {
                            "type": msg.get("type", "info"),
                            "message": msg.get("message", ""),
                            "timestamp": msg.get("timestamp", time.time()),
                        }
                    )

                    # 保存到文件
                    if file_handler:
                        file_handler.write_log(msg)

                    # 检查任务完成
                    if msg.get("type") == "internal":
                        if "任务执行完成" in msg.get("message", ""):
                            # 先清空队列中剩余的消息
                            while True:
                                try:
                                    remaining_msg = log_queue.get_nowait()
                                    await websocket.send_json(
                                        {
                                            "type": remaining_msg.get("type", "info"),
                                            "message": remaining_msg.get("message", ""),
                                            "timestamp": remaining_msg.get(
                                                "timestamp", time.time()
                                            ),
                                        }
                                    )
                                    if file_handler:
                                        file_handler.write_log(remaining_msg)
                                except queue.Empty:
                                    break

                            # 最后发送完成消息
                            await websocket.send_json(
                                {
                                    "type": "completed",
                                    "message": "任务执行完成",
                                    "timestamp": time.time(),
                                }
                            )
                            break
                        elif "任务执行失败" in msg.get("message", ""):
                            await websocket.send_json(
                                {
                                    "type": "failed",
                                    "message": "任务执行失败",
                                    "error": msg.get("error", "未知错误"),
                                    "timestamp": time.time(),
                                }
                            )
                            break

                except queue.Empty:
                    pass

            # 3. 检查主进程日志队列
            if app_state.log_queue:
                try:
                    main_msg = app_state.log_queue.get_nowait()

                    # 发送到前端
                    await websocket.send_json(
                        {
                            "type": main_msg.get("type", "info"),
                            "message": main_msg.get("message", ""),
                            "timestamp": main_msg.get("timestamp", time.time()),
                        }
                    )

                    # 保存到文件
                    if file_handler:
                        file_handler.write_log(main_msg)

                except queue.Empty:
                    pass

            await asyncio.sleep(0.1)

    except WebSocketDisconnect:
        log.print_log("WebSocket 连接断开", "info")
    finally:
        if websocket.client_state.name != "DISCONNECTED":
            try:
                await websocket.close()
            except:
                pass


@router.get("/hot-topics")
async def get_hot_topics():
    """
    获取热搜话题（自动执行爬虫抓取并返回带有 Vision 解析的 article_id）
    
    优先级策略：
    1. 强制优先并发运行权威媒体爬虫（BBC、纽约时报、新华社等）
    2. 如果候选不足，再运行其他普通爬虫
    3. 最后兜底：热点聚合（NewsHub缓存）
    """
    try:
        from src.ai_write_x.tools.spider_runner import SpiderRunner
        from src.ai_write_x.tools.spider_manager import spider_data_manager
        import random

        config = Config.get_instance()
        deduplicator = TopicDeduplicator(dedup_days=3)

        from src.ai_write_x.core.llm_client import LLMClient
        
        runner = SpiderRunner()
        enabled_spiders = [name for name, info in runner.spiders.items() if info.get("enabled", True)]
        if not enabled_spiders:
            raise ValueError("没有启用的爬虫节点")

        log.print_log(f"[PROGRESS:SPIDER:START]", "internal")
        log.print_log("UI自动拾取: 正在跨平台抓取最新前沿资讯以供AI评估...", "info")

        import asyncio
        target_article_count = 15  # 期望至少收集15个候选话题供AI甄选
        all_candidate_articles = []

        # 权威媒体列表（高公信力、国际视野）
        high_authority_spiders = ["bbc", "nytimes", "wsj", "zaobao", "xinhua", "voa"]

        # ========== 第1优先级：强制并发运行权威媒体爬虫 ==========
        priority_spiders = [s for s in enabled_spiders if s in high_authority_spiders]
        if priority_spiders:
            log.print_log(f"🚀 第1优先级：正在并发抓取权威媒体（{', '.join(priority_spiders)}）...", "info")
            
            tasks = []
            for spider_name in priority_spiders:
                task = asyncio.wait_for(runner.run_spider(spider_name, limit=10), timeout=20.0)
                tasks.append(task)
            
            results = await asyncio.gather(*tasks, return_exceptions=True)
            
            for spider_name, result in zip(priority_spiders, results):
                if isinstance(result, Exception):
                    log.print_log(f"[{spider_name}] 权威媒体获取超时或异常: {str(result)}", "warn")
                    continue
                    
                if result and result.get("success") and result.get("saved", 0) > 0:
                    articles = spider_data_manager.get_articles(limit=50)
                    spider_articles = [a for a in articles if a.get("spider") == spider_name]
                    spider_articles.sort(key=lambda x: x.get("fetch_time", ""), reverse=True)
                    
                    for article in spider_articles:
                        topic = article.get("title", "")
                        if not topic or deduplicator.is_duplicate(topic):
                            continue
                        if any(a.get("title") == topic for a in all_candidate_articles):
                            continue
                        spider_info = runner.spiders.get(spider_name, {})
                        article['_platform_name'] = spider_info.get("source", spider_name)
                        all_candidate_articles.append(article)
            
            log.print_log(f"权威媒体抓取完成，已获取 {len(all_candidate_articles)} 个候选话题", "info")

        # ========== 第2优先级：运行其他普通爬虫 ==========
        normal_spiders = [s for s in enabled_spiders if s not in high_authority_spiders]
        if len(all_candidate_articles) < target_article_count and normal_spiders:
            log.print_log(f"📰 第2优先级：正在抓取其他平台...", "info")
            
            random.shuffle(normal_spiders)
            batch_size = 5
            
            for i in range(0, len(normal_spiders), batch_size):
                batch_spiders = normal_spiders[i:i+batch_size]
                
                tasks = []
                for spider_name in batch_spiders:
                    task = asyncio.wait_for(runner.run_spider(spider_name, limit=10), timeout=15.0)
                    tasks.append(task)
                
                results = await asyncio.gather(*tasks, return_exceptions=True)
                
                for spider_name, result in zip(batch_spiders, results):
                    if isinstance(result, Exception):
                        log.print_log(f"[{spider_name}] 获取超时或异常: {str(result)}", "warn")
                        continue
                        
                    if result and result.get("success") and result.get("saved", 0) > 0:
                        articles = spider_data_manager.get_articles(limit=50)
                        spider_articles = [a for a in articles if a.get("spider") == spider_name]
                        spider_articles.sort(key=lambda x: x.get("fetch_time", ""), reverse=True)
                        
                        for article in spider_articles:
                            topic = article.get("title", "")
                            if not topic or deduplicator.is_duplicate(topic):
                                continue
                            if any(a.get("title") == topic for a in all_candidate_articles):
                                continue
                            spider_info = runner.spiders.get(spider_name, {})
                            article['_platform_name'] = spider_info.get("source", spider_name)
                            all_candidate_articles.append(article)
                            
                if len(all_candidate_articles) >= target_article_count:
                    break

        # ========== 最后兜底：热点聚合（NewsHub缓存）==========
        if len(all_candidate_articles) < target_article_count:
            log.print_log(f"📦 最后兜底：正在从热点聚合缓存获取...", "info")
            try:
                from src.ai_write_x.web.api.newshub import get_hub_manager
                hub_manager = get_hub_manager()
                cached_news = hub_manager.get_cached_news(limit=15)
                for item in cached_news:
                    if not deduplicator.is_duplicate(item["title"]):
                        if any(a.get("title") == item["title"] for a in all_candidate_articles):
                            continue
                        all_candidate_articles.append({
                            "id": item["id"],
                            "title": item["title"],
                            "spider": "newshub",
                            "url": item["url"],
                            "_platform_name": "热点聚合"
                        })
                if cached_news:
                    log.print_log(f"热点聚合兜底获取 {len(cached_news)} 个话题", "info")
            except Exception as e:
                print(f"Hot-topics NewsHub cache error: {e}")
        
        if not all_candidate_articles:
            raise ValueError("未能获取到全新热门内容，所有抓取话题均已写过或为空，请稍后再试或手动输入")
            
        # ========== AI主编甄选 ==========
        llm = LLMClient()
        prompt = "你是一位资深国际新闻主编，具有极高的新闻敏感度和专业判断力。\n\n"
        prompt += "以下是我们从各大权威媒体和平台抓取的最新话题列表。\n\n"
        prompt += "【核心甄选标准 - 按权重排序】：\n"
        prompt += "1. 【最高权重】优先选择来自 BBC、纽约时报、华尔街日报、联合早报、新华社 等权威国际媒体的话题\n"
        prompt += "2. 【高权重】话题应具备国际视野和深度，能引发读者深度思考\n"
        prompt += "3. 【中权重】话题应具有社会公信力，避免八卦娱乐类浅层内容\n"
        prompt += "4. 【基础权重】话题应具有传播价值，能吸引读者关注\n\n"
        prompt += "请你从以下列表中，挑选出一个【最符合上述标准】的话题。\n"
        prompt += "你只能返回你选中的那个话题的数字序号(ID)，不要回复任何解释、思考或其他文字。必须且只能输出数字！\n\n"
        
        for idx, art in enumerate(all_candidate_articles):
            p_name = art.get('_platform_name')
            # 为权威平台添加特殊标记，引导AI选择
            is_authority = art.get('spider') in high_authority_spiders
            authority_tag = "⭐⭐⭐【权威国际媒体】" if is_authority else ""
            prompt += f"[{idx}] 平台: {p_name} {authority_tag} | 标题: {art.get('title')}\n"
            
        log.print_log(f"已收集到 {len(all_candidate_articles)} 个新鲜候选话题，正在请AI主编进行智能甄选...", "info")
        
        choice_idx = 0
        try:
            import re
            
            # 使用 run_in_executor 避免同步的 LLM 调用阻塞 FastAPI 的事件循环
            import asyncio
            loop = asyncio.get_running_loop()
            choice_str = await loop.run_in_executor(
                None, 
                lambda: llm.chat([{"role": "user", "content": prompt}], temperature=0.3)
            )
            
            match = re.search(r'\d+', choice_str)
            if match:
                choice_idx = int(match.group(0))
            if choice_idx < 0 or choice_idx >= len(all_candidate_articles):
                choice_idx = 0
        except Exception as e:
            log.print_log(f"AI甄选环节出错，将默认随机选取: {e}", "warning")
            choice_idx = random.randint(0, len(all_candidate_articles) - 1)
            
        selected_article = all_candidate_articles[choice_idx]
        topic = selected_article.get("title", "")
        platform_name = selected_article.get("_platform_name", "")
        
        log.print_log(f"AI主编最终选中话题: 平台={platform_name}, 话题={topic}", "success")
        return {
            "status": "success", 
            "platform": platform_name, 
            "topic": topic,
            "article_id": str(selected_article.get("id"))
        }

    except Exception as e:
        log.print_log(f"自动抓取热点文章失败: {str(e)}", "error")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/logs/latest")
async def get_latest_log():
    """获取最新的日志文件"""
    from src.ai_write_x.utils.path_manager import PathManager

    log_dir = PathManager.get_log_dir()
    if not log_dir.exists():
        return {"error": "日志目录不存在"}

    # 查找最新的WEB_*.log文件
    log_files = sorted(log_dir.glob("WEB_*.log"), key=lambda p: p.stat().st_mtime, reverse=True)
    if not log_files:
        return {"error": "没有找到日志文件"}

    latest_log = log_files[0]
    return FileResponse(path=str(latest_log), filename=latest_log.name, media_type="text/plain")


class OptimizeContentRequest(BaseModel):
    """内容优化请求"""
    content: str
    suggestions: list = []
    optimize_type: str = "quality"


@router.post("/generate/optimize-content")
async def optimize_content(request: OptimizeContentRequest):
    """
    优化内容质量
    
    使用AI重写内容以降低AI检测概率、提高原创性
    """
    try:
        from src.ai_write_x.core.llm_client import get_llm_instance
        from src.ai_write_x.config.config import Config
        
        config = Config.get_instance()
        
        # 构建优化提示
        suggestions_text = "\n".join([f"- {s}" for s in request.suggestions]) if request.suggestions else ""
        
        optimize_prompt = f"""请对以下内容进行优化，要求：

1. 降低AI生成痕迹，使用更自然、更人性化的表达方式
2. 提高原创性和独特性
3. 保持原文的核心观点和信息不变
4. 丰富词汇表达，避免重复用词
5. 调整句式结构，增加变化性

优化建议：
{suggestions_text}

原文内容：
{request.content}

请直接输出优化后的内容，不要添加任何解释或说明。"""

        # 获取LLM实例
        llm = get_llm_instance()
        
        # 调用AI生成优化内容
        response = llm.call([
            {"role": "system", "content": "你是一位专业的内容优化专家，擅长将AI生成的内容改写为更自然、更人性化的表达。"},
            {"role": "user", "content": optimize_prompt}
        ])
        
        optimized_content = response.strip() if response else request.content
        
        return {
            "status": "success",
            "data": {
                "content": optimized_content,
                "original_length": len(request.content),
                "optimized_length": len(optimized_content)
            }
        }
        
    except Exception as e:
        log.print_log(f"内容优化失败: {str(e)}", "error")
        raise HTTPException(status_code=500, detail=str(e))
