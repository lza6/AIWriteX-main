from fastapi import APIRouter, HTTPException, BackgroundTasks
from pydantic import BaseModel
from typing import List, Optional
from datetime import datetime
import traceback

from src.ai_write_x.database.db_manager import db_manager
from src.ai_write_x.core.scheduler import scheduler_service
from src.ai_write_x.utils import log

router = APIRouter(prefix="/api/scheduler", tags=["Scheduler"])

class TaskCreate(BaseModel):
    topic: str
    execution_time: str # ISO format or YYYY-MM-DD HH:MM:SS
    platform: str = "wechat"
    is_recurring: bool = False
    interval_hours: int = 0
    article_count: int = 1
    use_ai_beautify: bool = True

class TaskUpdate(BaseModel):
    status: Optional[str] = None
    topic: Optional[str] = None
    execution_time: Optional[str] = None
    platform: Optional[str] = None
    is_recurring: Optional[bool] = None
    interval_hours: Optional[int] = None

@router.get("/tasks")
async def get_tasks():
    tasks = db_manager.get_all_tasks()
    return [{
        "id": t.id,
        "topic": t.topic,
        "platform": t.platform,
        "execution_time": t.execution_time.strftime("%Y-%m-%d %H:%M:%S"),
        "is_recurring": t.is_recurring,
        "interval_hours": t.interval_hours,
        "article_count": t.article_count,
        "use_ai_beautify": t.use_ai_beautify,
        "status": t.status,
        "last_run_at": t.last_run_at.strftime("%Y-%m-%d %H:%M:%S") if t.last_run_at else None,
        "created_at": t.created_at.strftime("%Y-%m-%d %H:%M:%S")
    } for t in tasks]

@router.post("/tasks")
async def create_task(data: TaskCreate):
    try:
        # 尝试解析时间
        try:
            exec_time = datetime.fromisoformat(data.execution_time.replace("Z", "+00:00"))
        except:
            exec_time = datetime.strptime(data.execution_time, "%Y-%m-%d %H:%M:%S")
        
        task = db_manager.add_scheduled_task(
            topic=data.topic,
            execution_time=exec_time,
            platform=data.platform,
            is_recurring=data.is_recurring,
            interval_hours=data.interval_hours,
            article_count=data.article_count,
            use_ai_beautify=data.use_ai_beautify
        )
        if task:
            return {"status": "success", "id": task.id}
        raise HTTPException(status_code=500, detail="Failed to create task in DB")
    except Exception as e:
        log.print_log(f"创建定时任务失败: {e}", "error")
        raise HTTPException(status_code=400, detail=str(e))

@router.put("/tasks/{task_id}")
async def update_task(task_id: str, data: TaskUpdate):
    from src.ai_write_x.database.models import ScheduledTask
    try:
        task = ScheduledTask.get_by_id(task_id)
        if data.status:
            task.status = data.status
        if data.topic:
            task.topic = data.topic
        if data.platform:
            task.platform = data.platform
        if data.is_recurring is not None:
            task.is_recurring = data.is_recurring
        if data.interval_hours is not None:
            task.interval_hours = data.interval_hours
        if data.execution_time:
            try:
                task.execution_time = datetime.fromisoformat(data.execution_time.replace("Z", "+00:00"))
            except:
                task.execution_time = datetime.strptime(data.execution_time, "%Y-%m-%d %H:%M:%S")
        
        task.updated_at = datetime.now()
        task.save()
        return {"status": "success"}
    except Exception as e:
        raise HTTPException(status_code=404, detail="Task not found or update failed")

@router.delete("/tasks/{task_id}")
async def delete_task(task_id: str):
    if db_manager.delete_task(task_id):
        return {"status": "success"}
    raise HTTPException(status_code=404, detail="Task not found")

@router.get("/logs")
async def get_logs(limit: int = 50):
    logs = db_manager.get_recent_task_logs(limit)
    return [{
        "id": l.id,
        "task_id": l.task_id,
        "status": l.status,
        "message": l.message,
        "article_id": l.article_id,
        "run_time": l.run_time.strftime("%Y-%m-%d %H:%M:%S")
    } for l in logs]

@router.get("/verify-platform")
async def verify_platform(platform: str):
    """验证发布平台连接性"""
    try:
        if platform == "wechat":
            from src.ai_write_x.tools.publishers.wechat_publisher import WeChatPublisher
            publisher = WeChatPublisher()
            success, msg = await publisher.verify_credentials()
            return {"success": success, "message": msg}
        # 其他平台暂不实现或默认成功
        return {"success": True, "message": f"{platform} 暂不支持连接性检测，默认为通过"}
    except Exception as e:
        return {"success": False, "message": f"检测异常: {str(e)}"}
