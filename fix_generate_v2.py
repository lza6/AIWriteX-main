import traceback

file_path = r"c:\Users\Administrator.DESKTOP-EGNE9ND\Desktop\AIxs\AIWriteX-main\src\ai_write_x\web\api\generate.py"

with open(file_path, 'r', encoding='utf-8') as f:
    content = f.read()

# We need to replace batch_generate_worker and the Process invocation at the bottom.
# First, let's remove batch_generate_worker entirely
start_idx = content.find('# 定义一个批处理外壳函数')
if start_idx != -1:
    end_idx = content.find('@router.post("/generate")')
    if end_idx != -1:
        # We will keep everything outside this range
        content = content[:start_idx] + content[end_idx:]

# Next, inside generate_content, we need to create a simple batch_thread_worker
# find where 'batch_generate_worker' was previously started in generate_content
def build_batch_thread_worker():
    return """
        import threading
        import queue
        
        def batch_thread_worker(global_config_dict, req_topic, req_platform, is_reference, ref_config_dict, log_q):
            from src.ai_write_x.config.config import Config as ProcessConfig
            import traceback
            import time
            from src.ai_write_x.state import get_app_state
            from src.ai_write_x.crew_main import ai_write_x_run
            import src.ai_write_x.utils.log as lg
            
            # 恢复 Config 
            cfg = ProcessConfig.get_instance()
            for k, v in global_config_dict.items():
                setattr(cfg, k, v)
                
            article_count = getattr(cfg, "article_count", 1)
            success_count = 0
            
            try:
                candidate_topics = []
                
                # 如果开启了自动搜刮热点且需要多篇，我们需要动态去重和寻找多个热点
                if article_count > 1 and not is_reference and not req_topic:
                    lg.print_log(f"批量生成模式开启，目标数量: {article_count} 篇", "info")
                    from src.ai_write_x.core.llm_client import LLMClient
                    from src.ai_write_x.tools.spider_runner import SpiderRunner
                    from src.ai_write_x.tools.spider_manager import spider_data_manager
                    from src.ai_write_x.utils.topic_deduplicator import TopicDeduplicator
                    import random
                    import asyncio
                    
                    try:
                        deduplicator = TopicDeduplicator(dedup_days=3)
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
                                    candidate_topics.append({"title": t, "platform": _platform})
                                    if len(candidate_topics) >= article_count * 2:
                                        break
                                        
                        if len(candidate_topics) < article_count:
                            lg.print_log("抓取的热点数量不足以支撑批量生成，将交由 LLM 发散补足...", "info")
                            llm = LLMClient()
                            prompt = f"请提供 {article_count - len(candidate_topics)} 个当下的热门互联网资讯或科技社会热点话题，只需输出标题列表，每行一个。"
                            fallback_text = llm.chat([{"role": "user", "content": prompt}])
                            for line in fallback_text.split('\\n'):
                                line = line.strip().strip('-*0123456789. ')
                                if line and len(line) > 5:
                                    candidate_topics.append({"title": line, "platform": "AI发散"})
                                    if len(candidate_topics) >= article_count:
                                        break
                                        
                        random.shuffle(candidate_topics)
                        candidate_topics = candidate_topics[:article_count]
                    except Exception as e:
                        lg.print_log(f"批量话题准备异常: {e}", "error")
                
                # 如果前台指定了 topic 或者候选不够，用前台的或者AI发散的填充
                if not candidate_topics:
                    candidate_topics = []
                    if req_topic:
                        candidate_topics.append({"title": req_topic, "platform": req_platform})
                    
                    # 补齐
                    if len(candidate_topics) < article_count:
                        # 对于剩余的部分如果还需要，可以生成相似的或者AI发散的话题
                        lg.print_log("使用 LLM 为固定话题发散更多相关话题...", "info")
                        from src.ai_write_x.core.llm_client import LLMClient
                        llm = LLMClient()
                        prompt = f"以“{req_topic or '最新热点'}”为核心，请提供 {article_count - len(candidate_topics)} 个延伸或相关的新闻话题，只需输出标题列表，每行一个。"
                        fallback_text = llm.chat([{"role": "user", "content": prompt}])
                        for line in fallback_text.split('\\n'):
                            line = line.strip().strip('-*0123456789. ')
                            if line and len(line) > 5:
                                candidate_topics.append({"title": line, "platform": "AI发散"})
                                if len(candidate_topics) >= article_count:
                                    break
                
                for i, c_topic in enumerate(candidate_topics):
                    t = c_topic.get("title", "")
                    p = c_topic.get("platform", "")
                    
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
                        "reference_content": ""
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
                        
                        if ref_config_dict.get("reference_urls"):
                            urls = [u.strip() for u in ref_config_dict.get("reference_urls").split("|") if u.strip()]
                            config_data["urls"] = urls
                            
                        config_data["reference_ratio"] = float(ref_config_dict.get("reference_ratio", 30)) / 100
                    
                    try:
                        # 确保主模块状态
                        global _current_process
                        
                        process, p_log_queue = ai_write_x_run(config_data)
                        if process and p_log_queue:
                            process.start()
                            _current_process = process # 记录下来让 /generate/stop 可以停止当前进程
                            
                            # 循环读取日志，同时检测子进程存活状态
                            while process.is_alive() or not p_log_queue.empty():
                                try:
                                    msg = p_log_queue.get(timeout=0.1)
                                    # 将 internal 的 任务执行完成 拦截掉（如果不拦截会被前端认为是整体完成）
                                    if msg.get("type") == "internal" and "任务执行完成" in msg.get("message", ""):
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
                            success_count += 1
                            
                            # 自动化动作
                            post_action = getattr(cfg, "post_action", "none")
                            if post_action != "none":
                                lg.print_log(f"⚡ 正在执行文章完成后的自动化动作: {post_action}", "info")
                                if post_action in ["publish", "save"]:
                                    try:
                                        from src.ai_write_x.tools.spider_manager import spider_data_manager
                                        articles = spider_data_manager.get_articles(limit=1)
                                        if articles:
                                            latest_article = articles[0]
                                            
                                            title = latest_article.get("title", "未命名文章")
                                            import re
                                            pure_text = re.sub(r'<[^>]+>', '', latest_article.get("content", ""))
                                            digest = pure_text[:115] + "..." if len(pure_text) > 115 else pure_text
                                            content_html = latest_article.get("content", "")
                                            cover_path = latest_article.get("cover_image", "")
                                            
                                            wechat_cfg = getattr(cfg, "wechat", {})
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
                    "message": f"程序执行异常:\\n```\\n{error_trace}\\n```", 
                    "timestamp": time.time()
                })
"""

# Replace in generate_content
search_pattern = """        import multiprocessing
        

        # 启动外层批量进程
        log_queue = multiprocessing.Queue()
        
        ref_dict = {
            "is_reference": True if request.reference else False,
            "template_category": request.reference.template_category if request.reference else "",
            "template_name": request.reference.template_name if request.reference else "",
            "reference_article_id": request.reference.reference_article_id if request.reference else "",
            "reference_urls": request.reference.reference_urls if request.reference else "",
            "reference_ratio": request.reference.reference_ratio if request.reference else 30
        }
        
        process = Process(
            target=batch_generate_worker,
            args=(
                config.__dict__,
                topic,
                request.platform,
                ref_dict["is_reference"],
                ref_dict,
                log_queue
            )
        )
        
        _current_process = process
        _current_log_queue = log_queue
        _task_status = {"status": "running", "error": None}
        _current_process.start()"""

replacement = build_batch_thread_worker() + """
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
        
        thread = threading.Thread(
            target=batch_thread_worker,
            args=(
                config.__dict__,
                topic,
                request.platform,
                ref_dict["is_reference"],
                ref_dict,
                log_queue
            ),
            daemon=True
        )
        
        _task_status = {"status": "running", "error": None}
        thread.start()
        
        # 不要覆盖 _current_process，让 _current_process = thread 启动的真实子进程
"""

new_content = content.replace(search_pattern, replacement)

# We also need to fix `stop_generation` because `_current_process` might be None temporarily when batch_thread_worker is sleeping.
# The user can still stop the active crew_main process if there is one. 
# Also check if multiprocessing import exists to replace search_pattern.
if search_pattern in content:
    with open(file_path, 'w', encoding='utf-8') as f:
        f.write(new_content)
    print("Replaced successfully")
else:
    print("Could not find pattern")

