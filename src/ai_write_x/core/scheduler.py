import threading
import time
import asyncio
import traceback
from datetime import datetime, timedelta
from typing import Optional, List

from src.ai_write_x.database.db_manager import db_manager
from src.ai_write_x.core.unified_workflow import UnifiedContentWorkflow
from src.ai_write_x.utils import log
from src.ai_write_x.config.config import Config

class SchedulerService:
    _instance = None
    _lock = threading.Lock()

    def __new__(cls):
        with cls._lock:
            if cls._instance is None:
                cls._instance = super(SchedulerService, cls).__new__(cls)
                cls._instance._initialized = False
        return cls._instance

    def __init__(self):
        if self._initialized:
            return
        self.is_running = False
        self.thread = None
        self._initialized = True

    def start(self):
        """启动后台调度线程"""
        if self.is_running:
            return
        
        self.is_running = True
        self.thread = threading.Thread(target=self._run_loop, name="SchedulerThread", daemon=True)
        self.thread.start()
        log.print_log("⏰ Scheduler Service (定时任务系统) 已启动", "success")

    def stop(self):
        """停止后台调度线程"""
        self.is_running = False
        log.print_log("⏰ Scheduler Service 已停止", "info")

    def _run_loop(self):
        """心跳轮询逻辑 (每 60 秒检查一次)"""
        while self.is_running:
            try:
                self._check_and_execute_tasks()
            except Exception as e:
                log.print_log(f"[Scheduler] 轮询异常: {e}\n{traceback.format_exc()}", "error")
            
            # 每 60 秒检查一次，直到停止
            for _ in range(60):
                if not self.is_running:
                    break
                time.sleep(1)

    def _check_and_execute_tasks(self):
        """检查并执行到期的任务"""
        active_tasks = db_manager.get_active_tasks()
        if not active_tasks:
            return

        for task in active_tasks:
            log.print_log(f"🕒 发现到期任务: {task.topic} ({task.platform})", "info")
            
            # 使用独立线程执行任务，避免阻塞调度循环和内存堆积
            t = threading.Thread(
                target=self._execute_single_task, 
                args=(task.id,), 
                name=f"TaskExecutor-{task.id[:8]}",
                daemon=True
            )
            t.start()

    def _execute_single_task(self, task_id: str):
        """执行单个具体任务"""
        from src.ai_write_x.database.models import ScheduledTask
        
        task = None
        try:
            # 重新获取任务对象确保状态最新
            task = ScheduledTask.get_by_id(task_id)
            if task.status != 'enabled':
                return

            # 更新状态为运行中
            db_manager.update_task_status(task_id, 'running')
            db_manager.log_task_execution(task_id, 'running', "任务开始执行...")

            # 初始化工作流
            workflow = UnifiedContentWorkflow()
            
            # 定时任务配置
            kwargs = {
                "publish_platform": task.platform,
                "auto_publish": True,
                "use_ai_beautify": task.use_ai_beautify
            }
            
            # 如果话题为空，尝试自动拾取热点话题（复用立马生成的逻辑）
            original_topic = task.topic.strip() if task.topic else ""
            
            count = task.article_count if task.article_count > 0 else 1
            success_count = 0
            
            for i in range(count):
                # 动态确定本次生成的话题
                if not original_topic:
                    from src.ai_write_x.tools import hotnews
                    # 随机从微博、头条、百度之一取热点
                    platforms = ["微博", "今日头条", "百度热点"]
                    try:
                        current_topic = hotnews.select_platform_topic(platforms[i % len(platforms)])
                        log.print_log(f"🔥 [Scheduler] 话题为空，自动拾取热点: {current_topic}", "info")
                    except Exception as e:
                        current_topic = "最新热点科技深度解析"
                        log.print_log(f"⚠️ [Scheduler] 自动拾取话题失败: {e}，将使用备用话题", "warning")
                else:
                    current_topic = original_topic

                log.print_log(f"🚀 [Scheduler] 正在执行任务: {current_topic} ({i+1}/{count})", "info")
                results = workflow.execute(current_topic, **kwargs)
                
                if results.get("success"):
                    success_count += 1
                    msg = f"文章 {i+1} 生成成功"
                    if results.get("publish_result"):
                        msg += f"并已发布: {results['publish_result'].get('message', '')}"
                    
                    db_manager.log_task_execution(
                        task_id=task_id, 
                        status='success', 
                        message=msg,
                        article_id=results.get("save_result", {}).get("path")
                    )
                else:
                    db_manager.log_task_execution(task_id, 'failed', f"文章 {i+1} 执行失败")
            
            if success_count == count:
                log.print_log(f"✅ [Scheduler] 任务全部完成 ({success_count}/{count})", "success")
            else:
                log.print_log(f"⚠️ [Scheduler] 任务部分完成 ({success_count}/{count})", "warning")

        except Exception as e:
            err_msg = f"任务执行异常: {str(e)}"
            log.print_log(f"[Scheduler] {err_msg}", "error")
            if task_id:
                db_manager.log_task_execution(task_id, 'failed', f"{err_msg}\n{traceback.format_exc()}")
        finally:
            # 更新下一次执行时间或禁用任务
            self._finalize_task(task_id)

    def _finalize_task(self, task_id: str):
        """处理任务后续逻辑：更新时间或禁用"""
        from src.ai_write_x.database.models import ScheduledTask
        try:
            task = ScheduledTask.get_by_id(task_id)
            task.last_run_at = datetime.now()
            
            if task.is_recurring and task.interval_hours > 0:
                # 计算下一次运行时间
                task.execution_time = task.last_run_at + timedelta(hours=task.interval_hours)
                task.status = 'enabled' # 恢复为可用
            else:
                # 一次性任务，标记为已完成（实际上通过状态禁用即可）
                task.status = 'completed'
            
            task.save()
        except Exception as e:
            log.print_log(f"[Scheduler] 任务结算失败: {e}", "error")

scheduler_service = SchedulerService()
