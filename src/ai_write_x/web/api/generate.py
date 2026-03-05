#!/usr/bin/env python
# -*- coding: UTF-8 -*-

from fastapi import APIRouter, HTTPException, WebSocket, WebSocketDisconnect
from fastapi.responses import FileResponse
from pydantic import BaseModel
from typing import Optional
import asyncio
import time
import queue

from ..state import get_app_state

from src.ai_write_x.config.config import Config
from src.ai_write_x.crew_main import ai_write_x_main
from src.ai_write_x.tools import hotnews
from src.ai_write_x.utils import utils, log
from src.ai_write_x.utils.topic_deduplicator import TopicDeduplicator

router = APIRouter(prefix="/api", tags=["generate"])

# 全局任务管理
_current_process = None
_current_log_queue = None
_current_worker_thread = None  # 外层批量生成线程
# V5: 增加时间戳供前端展示生成耗时
_task_status = {"status": "idle", "error": None, "started_at": None, "finished_at": None}


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
    global _current_process, _current_log_queue, _task_status, _current_worker_thread

    # 防重入：同时检查子进程和外层worker线程
    if (_current_process and _current_process.is_alive()) or \
       (_current_worker_thread and _current_worker_thread.is_alive()):
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
        if not topic and not request.reference:
            # 在这里，如果前端点了获取热搜但没传过来，说明有问题
            raise HTTPException(status_code=400, detail="请输入话题或选择参考文章")

        # 将 post_action 保存到 Config 以便后续执行发布
        config.post_action = request.post_action or "none"
        config.article_count = request.article_count or 1

        # 我们需要一个特殊的后台任务进程，用于循环生成文章
        from multiprocessing import Process, Queue

        import threading
        import queue
        
        def batch_thread_worker(global_config_dict, req_topic, req_platform, is_reference, ref_config_dict, log_q, ai_beautify):
            global _task_status
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
            
            # 设置当前线程(主进程的一个线程)的日志队列，这样 batch_thread_worker 里的 print_log 也能被前端 WebSocket 捕获
            lg.set_process_queue(log_q)
            
            try:
                candidate_topics = []
                
                # 如果前台指定了 topic 且数量为 1，直接使用，不进行发散/批量逻辑
                if req_topic and article_count == 1:
                    candidate_topics = [{"title": req_topic, "platform": req_platform, "date_str": "近期"}]
                    lg.print_log(f"单篇文章生成模式启动，话题: {req_topic}")
                
                # 如果开启了自动搜刮热点且需要多篇，或者没给明确话题，我们需要动态寻找多个热点
                if not candidate_topics and article_count > 1 and not is_reference and not req_topic:
                    lg.print_log(f"批量生成模式开启，目标数量: {article_count} 篇", "info")
                    from src.ai_write_x.core.llm_client import LLMClient
                    from src.ai_write_x.tools.spider_runner import SpiderRunner
                    from src.ai_write_x.tools.spider_manager import spider_data_manager
                    from src.ai_write_x.utils.topic_deduplicator import TopicDeduplicator
                    import random
                    import asyncio
                    
                    # 提前初始化 deduplicator，确保后续代码可用
                    deduplicator = TopicDeduplicator(dedup_days=3)
                    
                    try:
                        runner = SpiderRunner()
                        enabled_spiders = [name for name, info in runner.spiders.items() if info.get("enabled", True)]
                        
                        if enabled_spiders:
                            # 选择几个爬虫跑一波
                            loop = asyncio.new_event_loop()
                            asyncio.set_event_loop(loop)
                            
                            tasks = []
                            for spider_name in random.sample(enabled_spiders, min(3, len(enabled_spiders))):
                                tasks.append(asyncio.wait_for(runner.run_spider(spider_name, limit=15), timeout=20.0))
                                
                            if tasks:
                                results = loop.run_until_complete(asyncio.gather(*tasks, return_exceptions=True))
                            loop.close()
                                
                            articles = spider_data_manager.get_articles(limit=100)
                            for a in articles:
                                t = a.get("title", "")
                                if t and not deduplicator.is_duplicate(t) and t not in [c['title'] for c in candidate_topics]:
                                    _platform = runner.spiders.get(a.get("spider"), {}).get("source", a.get("spider"))
                                    candidate_topics.append({"title": t, "platform": _platform, "date_str": a.get("date_str", "")})
                                    # 立即标记为已用
                                    deduplicator.add_topic(t)
                                    if len(candidate_topics) >= article_count * 2:
                                        break
                                        
                        # 如果没有抓取到足够的，或者需要从权威源补充
                        if len(candidate_topics) < article_count:
                            # 优先从权威源加持
                            candidate = hotnews.select_platform_topic(_platform, cnt=200, exclude_topics=[c['title'] for c in candidate_topics], authority_priority=True)
                            if candidate and not deduplicator.is_duplicate(candidate) and candidate not in [c['title'] for c in candidate_topics]:
                                candidate_topics.append({"title": candidate, "platform": "权威源", "date_str": "最新"})
                                deduplicator.add_topic(candidate)
                                        
                        if len(candidate_topics) < article_count:
                            lg.print_log("抓取的热点数量不足以支撑批量生成，将交由 LLM 发散补足...", "info")
                            llm = LLMClient()
                            prompt = f"请提供 {article_count - len(candidate_topics)} 个当下的热门互联网资讯或科技社会热点话题，确保每个话题都独特且具有国际新闻价值（类似BBC/华尔街日报风格）。只需输出标题列表，每行一个。不要包含这些已存在的话题: {', '.join([c['title'] for c in candidate_topics])}"
                            fallback_text = llm.chat([{"role": "user", "content": prompt}])
                            for line in fallback_text.split('\n'):
                                line = line.strip().strip('-*0123456789. ')
                                if line and len(line) > 5 and not deduplicator.is_duplicate(line):
                                    candidate_topics.append({"title": line, "platform": "AI发散", "date_str": "近期"})
                                    deduplicator.add_topic(line)
                                    if len(candidate_topics) >= article_count:
                                        break
                                        
                        random.shuffle(candidate_topics)
                        candidate_topics = candidate_topics[:article_count]
                    except Exception as e:
                        print(f"Exception preparing topics: {e}")
                        lg.print_log(f"批量话题准备异常: {e}", "error")
                
                print("Checking candidate_topics after spider step")
                # 如果前台指定了 topic 或者候选不够，用前台的或者AI发散的填充
                if not candidate_topics:
                    print("Candidate topic was empty, filling with LLM")
                    # 此代码块独立，需要自己初始化 deduplicator
                    from src.ai_write_x.utils.topic_deduplicator import TopicDeduplicator
                    deduplicator = TopicDeduplicator(dedup_days=3)
                    candidate_topics = []
                    if req_topic:
                        candidate_topics.append({"title": req_topic, "platform": req_platform, "date_str": "近期"})
                    
                    # 补齐
                    if len(candidate_topics) < article_count:
                        # 对于剩余的部分如果还需要，可以生成相似的或者AI发散的话题
                        lg.print_log("使用 LLM 为固定话题发散更多相关话题...", "info")
                        from src.ai_write_x.core.llm_client import LLMClient
                        llm = LLMClient()
                        prompt = f"以“{req_topic or '最新热点'}”为核心，请提供 {article_count - len(candidate_topics)} 个互不相同、切入点独特的延伸或相关新闻话题。只需输出标题列表，每行一个。避开以下已选标题: {', '.join([c['title'] for c in candidate_topics])}"
                        fallback_text = llm.chat([{"role": "user", "content": prompt}])
                        for line in fallback_text.split('\n'):
                            line = line.strip().strip('-*0123456789. ')
                            if line and len(line) > 5 and not deduplicator.is_duplicate(line):
                                candidate_topics.append({"title": line, "platform": "AI发散", "date_str": "近期"})
                                deduplicator.add_topic(line)
                                if len(candidate_topics) >= article_count:
                                    break
                
                for i, c_topic in enumerate(candidate_topics):
                    t = c_topic.get("title", "")
                    p = c_topic.get("platform", "")
                    d_str = c_topic.get("date_str", "")
                    
                    lg.print_log(f"=====================================", "internal")
                    lg.print_log(f"🔜 [批量进度] 正在生成第 {i+1}/{article_count} 篇文章", "success")
                    lg.print_log(f"📌 平台: {p} | 话题: {t}", "info")
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
                        global _current_process
                        
                        process, p_log_queue = ai_write_x_main(config_data)
                        if process and p_log_queue:
                            process.start()
                            _current_process = process # 记录下来让 /generate/stop 可以停止当前进程
                            final_result = None
                            
                            # 循环读取日志，同时检测子进程存活状态
                            while process.is_alive() or not p_log_queue.empty():
                                try:
                                    msg = p_log_queue.get(timeout=0.1)
                                    # 将 internal 的 任务执行完成 拦截掉（如果不拦截会被前端认为是整体完成）
                                    if msg.get("type") == "internal" and "任务执行完成" in msg.get("message", ""):
                                        if "result" in msg:
                                            final_result = msg.get("result")
                                            
                                        if i == len(candidate_topics) - 1:
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
                                    from src.ai_write_x.database import db_manager
                                    db_title = final_result.get("save_result", {}).get("title", t)
                                    db_content = final_result.get("formatted_content", "")
                                    db_manager.save_article(topic_title=db_title, content=db_content, fmt="HTML")
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
                        
                    if i < len(candidate_topics) - 1:
                        lg.print_log("等待 10 秒后开始下一篇文章生成...", "internal")
                        time.sleep(10)
                        
                if success_count > 0:
                    lg.print_log(f"🎉 批量生成任务全部完成！共成功生成 {success_count}/{article_count} 篇文章。", "success")
                    # 发送总的完成消息 如果上面没有截断发出去过的话，为了保险再发一次
                    log_q.put({"type": "internal", "message": "任务执行完成", "timestamp": time.time()})
                else:
                    lg.print_log("❌ 所有文章生成失败", "error")
                    log_q.put({"type": "internal", "message": "任务执行失败", "error": "所有文章生成均失败", "timestamp": time.time()})
                    
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
                if success_count > 0:
                    _task_status = {"status": "completed", "error": None, "started_at": _task_status.get("started_at"), "finished_at": time.time()}
                    print(f"[batch_thread_worker] 任务状态已更新为 completed，成功 {success_count} 篇")
                else:
                    _task_status = {"status": "failed", "error": "所有文章生成均失败", "started_at": _task_status.get("started_at"), "finished_at": time.time()}
                    print(f"[batch_thread_worker] 任务状态已更新为 failed")
                
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

        import queue
        log_queue = queue.Queue()
        _current_log_queue = log_queue
        
        ref_dict = {
            "is_reference": True if request.reference else False,
            "template_category": request.reference.template_category if request.reference else "",
            "template_name": request.reference.template_name if request.reference else "",
            "reference_article_id": request.reference.reference_article_id if request.reference else "",
            "reference_urls": request.reference.reference_urls if request.reference else "",
            "reference_ratio": request.reference.reference_ratio if request.reference else 30
        }
        
        worker = threading.Thread(
            target=batch_thread_worker,
            args=(
                config.__dict__,
                topic,
                request.platform,
                ref_dict["is_reference"],
                ref_dict,
                log_queue,
                request.ai_beautify,
            ),
            daemon=True,
        )
        
        _task_status = {"status": "running", "error": None, "started_at": time.time(), "finished_at": None}
        log.print_log(f"生成线程启动中，话题: {topic}", "info")
        worker.start()
        
        # 保存外层worker线程引用，供状态轮询检测
        _current_worker_thread = worker


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
    """
    停止当前生成任务

    """
    global _current_process, _current_log_queue, _task_status, _current_worker_thread

    if not _current_process or not _current_process.is_alive():
        return {"status": "info", "message": "没有正在运行的任务"}

    try:
        log.print_log("正在停止任务...", "info")

        # 首先尝试优雅终止
        _current_process.terminate()
        _current_process.join(timeout=2.0)

        # 检查是否真正终止
        if _current_process.is_alive():
            log.print_log("执行未响应,强制终止", "warning")
            _current_process.kill()
            _current_process.join(timeout=1.0)

            if _current_process.is_alive():
                log.print_log("警告:执行可能未完全终止", "warning")
            else:
                log.print_log("任务执行已强制终止", "info")
        else:
            log.print_log("任务执行已停止", "info")

        # 清理队列中的剩余消息
        if _current_log_queue:
            try:
                while True:
                    _current_log_queue.get_nowait()
            except queue.Empty:
                pass

        # 重置状态
        _current_process = None
        _current_log_queue = None
        _current_worker_thread = None
        _task_status = {"status": "stopped", "error": None}

        return {"status": "success", "message": "任务已停止"}

    except Exception as e:
        log.print_log(f"终止执行时出错: {str(e)}", "error")

        # 即使出错也要重置状态
        _current_process = None
        _current_log_queue = None
        _current_worker_thread = None
        _task_status = {"status": "error", "error": str(e)}

        raise HTTPException(status_code=500, detail=str(e))


@router.get("/generate/status")
async def get_generation_status():
    global _current_process, _task_status, _current_log_queue, _current_worker_thread

    # 检查外层worker线程状态（批量生成线程）
    if _current_worker_thread and _current_worker_thread.is_alive():
        return {"status": "running", "error": None}
    
    # 如果外层线程已结束，检查其设置的状态
    if _current_worker_thread and not _current_worker_thread.is_alive():
        # 线程已结束，返回其设置的最终状态
        status = _task_status.copy()
        if status.get("status") in ("completed", "failed"):
            print(f"[generate/status] 外层线程已结束，返回状态: {status['status']}")
            # 清理资源
            _current_worker_thread = None
            _current_process = None
            _current_log_queue = None
            _task_status = {"status": "idle", "error": None}
            return status

    # 检查子进程状态（向后兼容）
    if _current_process:
        if _current_process.is_alive():
            return {"status": "running", "error": None}
        else:
            # 进程已结束,检查退出码
            exit_code = _current_process.exitcode
            if exit_code == 0:
                status = {"status": "completed", "error": None}
            else:
                status = {"status": "failed", "error": f"退出码: {exit_code}"}

            # 清理资源
            _current_process = None
            _current_log_queue = None
            _current_worker_thread = None
            _task_status = {"status": "idle", "error": None}

            return status

    return _task_status


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
        while True:
            # 1. 检查子进程状态
            # 在批量模式下，_current_process 可能在单篇完成后暂时结束，但外层 Thread 还在继续
            if _current_process and not _current_process.is_alive():
                # 我们不再这里直接 break，让 '任务执行完成' 标记来控制退出
                pass

            # 2. 检查子进程日志队列
            if _current_log_queue:
                try:
                    msg = _current_log_queue.get_nowait()

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
                                    remaining_msg = _current_log_queue.get_nowait()
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
    except Exception as e:
        log.print_log(f"WebSocket 错误: {str(e)}", "error")
    finally:
        if websocket.client_state.name != "DISCONNECTED":
            try:
                await websocket.close()
            except RuntimeError:
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
            import asyncio
            loop = asyncio.get_running_loop()
            import re
            
            # 使用 run_in_executor 避免同步的 LLM 调用阻塞 FastAPI 的事件循环
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
