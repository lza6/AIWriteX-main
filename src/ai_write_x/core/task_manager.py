import asyncio
import multiprocessing
import threading
import queue
import time
import uuid
from typing import Dict, Optional, Any, List
from src.ai_write_x.utils import log

class TaskStatus:
    IDLE = "idle"
    RUNNING = "running"
    COMPLETED = "completed"
    FAILED = "failed"
    STOPPED = "stopped"

class BackgroundTaskManager:
    _instance = None
    _lock = threading.Lock()

    def __new__(cls):
        with cls._lock:
            if cls._instance is None:
                cls._instance = super(BackgroundTaskManager, cls).__new__(cls)
                cls._instance._init()
            return cls._instance

    def _init(self):
        self.active_tasks: Dict[str, Any] = {} # taskId -> {process, thread, status, start_time, etc}
        self.log_queues: Dict[str, queue.Queue] = {} # taskId -> Queue
        self.task_registry_lock = threading.Lock()

    def start_task(self, task_id: str, target_func, args=()):
        """启动一个新的后台任务线程"""
        with self.task_registry_lock:
            if task_id in self.active_tasks and self.active_tasks[task_id]['status'] == TaskStatus.RUNNING:
                return False, "Task already running"

            log_q = queue.Queue()
            self.log_queues[task_id] = log_q
            
            task_info = {
                "id": task_id,
                "status": TaskStatus.RUNNING,
                "start_time": time.time(),
                "log_queue": log_q,
                "sub_processes": [] # 用于追踪产生的子进程
            }
            
            # 开启监控线程/Worker线程
            worker_thread = threading.Thread(
                target=self._worker_wrapper,
                args=(task_id, target_func, args, log_q),
                daemon=True
            )
            task_info["thread"] = worker_thread
            self.active_tasks[task_id] = task_info
            worker_thread.start()
            return True, task_id

    def _worker_wrapper(self, task_id, func, args, log_q):
        try:
            # 注入日志队列，让子流程的 log.print_log 能够定向到这里
            log.set_process_queue(log_q)
            
            # V11.1: 智能参数适配 (Signature Alignment)
            import inspect
            sig = inspect.signature(func)
            params = sig.parameters
            
            if len(args) != len(params):
                log.print_log(f"❌ 参数量严重不匹配 (sig: {len(params)}, args: {len(args)})，任务拒绝执行", "error")
                raise ValueError(f"Task argument mismatch: expected {len(params)}, got {len(args)}")
            
            func(*args)
                
            self.update_task_status(task_id, TaskStatus.COMPLETED)
        except Exception as e:
            log.print_log(f"Task {task_id} failed: {str(e)}", "error")
            self.update_task_status(task_id, TaskStatus.FAILED, error=str(e))
        finally:
            log.set_process_queue(None)

    def update_task_status(self, task_id: str, status: str, error: str = None):
        with self.task_registry_lock:
            if task_id in self.active_tasks:
                self.active_tasks[task_id]["status"] = status
                self.active_tasks[task_id]["finished_at"] = time.time()
                if error:
                    self.active_tasks[task_id]["error"] = error

    def get_task_status(self, task_id: str) -> Dict:
        with self.task_registry_lock:
            if task_id not in self.active_tasks:
                return {"status": TaskStatus.IDLE}
            
            task = self.active_tasks[task_id]
            return {
                "status": task["status"],
                "error": task.get("error"),
                "started_at": task.get("start_time"),
                "finished_at": task.get("finished_at")
            }

    def stop_task(self, task_id: str):
        with self.task_registry_lock:
            if task_id not in self.active_tasks:
                return False, "Task not found"
            
            task = self.active_tasks[task_id]
            # 这里的终止逻辑较为复杂，通常需要通知 Worker 线程并清理子进程
            # 实际上在 generate.py 中我们通常用 _current_process.terminate()
            # 这里我们建议保留子进程引用在 task["sub_processes"]
            for p in task.get("sub_processes", []):
                if p.is_alive():
                    p.terminate()
            
            task["status"] = TaskStatus.STOPPED
            return True, "Task stopped"

    def register_sub_process(self, task_id: str, process):
        with self.task_registry_lock:
            if task_id in self.active_tasks:
                self.active_tasks[task_id].setdefault("sub_processes", []).append(process)

    def get_log_queue(self, task_id: str) -> Optional[queue.Queue]:
        return self.log_queues.get(task_id)

task_manager = BackgroundTaskManager()
