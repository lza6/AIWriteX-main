"""
AIWriteX 异步多平台发布中心（高性能版本）
支持真正的异步并发发布，大幅提升性能
"""
import asyncio
import uuid
from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum
from typing import Dict, List, Optional, Any, Tuple
import time

from src.ai_write_x.utils import log as lg
from src.ai_write_x.utils.performance_optimizer import (
    memory_optimizer, 
    performance_monitor,
    browser_pool
)


class PlatformType(Enum):
    """支持的平台类型"""
    XIAOHONGSHU = "xiaohongshu"
    DOUYIN = "douyin"
    ZHIHU = "zhihu"
    TOUTIAO = "toutiao"
    BAIJIAHAO = "baijiahao"


@dataclass
class PlatformConfig:
    """平台配置"""
    platform_type: PlatformType
    enabled: bool = True
    headless: bool = True
    auto_publish: bool = False
    max_retries: int = 3
    timeout: int = 300
    custom_settings: Dict[str, Any] = field(default_factory=dict)


@dataclass
class PublishTask:
    """发布任务"""
    id: str
    title: str
    content: str
    images: List[str] = field(default_factory=list)
    platforms: List[PlatformType] = field(default_factory=list)
    options: Dict[str, Any] = field(default_factory=dict)
    status: str = "pending"  # pending, running, success, failed, partial
    results: Dict[str, Tuple[bool, str]] = field(default_factory=dict)
    created_at: datetime = field(default_factory=datetime.now)
    completed_at: Optional[datetime] = None
    execution_time_ms: float = 0.0


class AsyncMultiPlatformHub:
    """
    异步多平台发布中心（高性能版）
    
    特性:
    - 真正的异步并发发布
    - 浏览器实例池复用
    - 自动重试机制
    - 性能监控
    - 内存优化
    """
    
    def __init__(self, max_concurrent: int = 3):
        self.max_concurrent = max_concurrent
        self.platforms: Dict[PlatformType, Any] = {}
        self.configs: Dict[PlatformType, PlatformConfig] = {}
        self.tasks: Dict[str, PublishTask] = {}
        self._semaphore = asyncio.Semaphore(max_concurrent)
        self._init_platforms()
        
    def _init_platforms(self):
        """初始化所有平台配置"""
        for pt in PlatformType:
            self.configs[pt] = PlatformConfig(
                platform_type=pt,
                enabled=True,
                headless=True,
                max_retries=3
            )
    
    async def get_publisher(self, platform_type: PlatformType):
        """异步获取平台发布器"""
        if platform_type not in self.platforms:
            config = self.configs.get(platform_type)
            if not config or not config.enabled:
                return None
            
            # 动态导入发布器
            if platform_type == PlatformType.XIAOHONGSHU:
                from src.ai_write_x.tools.publishers.xiaohongshu_publisher import XiaohongshuPublisher
                self.platforms[platform_type] = XiaohongshuPublisher(headless=config.headless)
            elif platform_type == PlatformType.DOUYIN:
                from src.ai_write_x.tools.publishers.douyin_publisher import DouyinPublisher
                self.platforms[platform_type] = DouyinPublisher(headless=config.headless)
            elif platform_type == PlatformType.ZHIHU:
                from src.ai_write_x.tools.publishers.zhihu_publisher import ZhihuPublisher
                self.platforms[platform_type] = ZhihuPublisher(headless=config.headless)
            elif platform_type == PlatformType.TOUTIAO:
                from src.ai_write_x.tools.publishers.toutiao_publisher import ToutiaoPublisher
                self.platforms[platform_type] = ToutiaoPublisher(headless=config.headless)
            elif platform_type == PlatformType.BAIJIAHAO:
                from src.ai_write_x.tools.publishers.baijiahao_publisher import BaijiahaoPublisher
                self.platforms[platform_type] = BaijiahaoPublisher(headless=config.headless)
        
        return self.platforms.get(platform_type)
    
    def create_publish_task(
        self,
        title: str,
        content: str,
        images: List[str] = None,
        platforms: List[PlatformType] = None,
        options: Dict[str, Any] = None
    ) -> PublishTask:
        """创建发布任务"""
        if platforms is None:
            platforms = [pt for pt, config in self.configs.items() if config.enabled]
        
        task = PublishTask(
            id=str(uuid.uuid4())[:8],
            title=title,
            content=content,
            images=images or [],
            platforms=platforms,
            options=options or {}
        )
        
        self.tasks[task.id] = task
        return task
    
    async def _publish_to_platform(
        self,
        task: PublishTask,
        platform_type: PlatformType
    ) -> Tuple[bool, str]:
        """
        发布到单个平台（带重试）
        """
        config = self.configs.get(platform_type)
        if not config:
            return False, "平台配置不存在"
        
        publisher = await self.get_publisher(platform_type)
        if not publisher:
            return False, "平台发布器未初始化"
        
        last_error = ""
        
        for attempt in range(config.max_retries):
            try:
                lg.print_log(f"[任务 {task.id}] 发布到 {platform_type.value} (尝试 {attempt + 1}/{config.max_retries})...", "info")
                
                # 使用信号量限制并发
                async with self._semaphore:
                    start_time = time.time()
                    
                    # 执行发布（同步发布器的异步包装）
                    loop = asyncio.get_event_loop()
                    success, message = await asyncio.wait_for(
                        loop.run_in_executor(
                            None,
                            lambda: publisher.publish(
                                title=task.title,
                                content=task.content,
                                images=task.images,
                                commit=config.auto_publish,
                                **task.options
                            )
                        ),
                        timeout=config.timeout
                    )
                    
                    execution_time = (time.time() - start_time) * 1000
                    
                    if success:
                        lg.print_log(f"[任务 {task.id}] {platform_type.value} 发布成功 ({execution_time:.0f}ms)", "success")
                        return True, message
                    else:
                        last_error = message
                        lg.print_log(f"[任务 {task.id}] {platform_type.value} 发布失败: {message}", "warning")
                        
                        if attempt < config.max_retries - 1:
                            await asyncio.sleep(2 ** attempt)  # 指数退避
                        
            except asyncio.TimeoutError:
                last_error = f"发布超时 ({config.timeout}秒)"
                lg.print_log(f"[任务 {task.id}] {platform_type.value} 发布超时", "error")
            except Exception as e:
                last_error = str(e)
                lg.print_log(f"[任务 {task.id}] {platform_type.value} 发布异常: {e}", "error")
                
                if attempt < config.max_retries - 1:
                    await asyncio.sleep(2 ** attempt)
        
        return False, f"重试{config.max_retries}次后仍失败: {last_error}"
    
    async def execute_task(self, task_id: str) -> Dict[str, Tuple[bool, str]]:
        """
        异步执行发布任务（真正的并发）
        """
        task = self.tasks.get(task_id)
        if not task:
            return {}
        
        task.status = "running"
        start_time = time.time()
        
        lg.print_log(f"[任务 {task_id}] 开始异步多平台发布 (目标: {len(task.platforms)} 个平台)...", "info")
        
        # 创建所有平台的发布任务
        publish_coroutines = [
            self._publish_to_platform(task, platform_type)
            for platform_type in task.platforms
        ]
        
        # 并发执行所有发布任务
        results = await asyncio.gather(*publish_coroutines, return_exceptions=True)
        
        # 处理结果
        for platform_type, result in zip(task.platforms, results):
            if isinstance(result, Exception):
                task.results[platform_type.value] = (False, str(result))
            else:
                task.results[platform_type.value] = result
        
        # 计算执行时间
        task.execution_time_ms = (time.time() - start_time) * 1000
        
        # 确定任务状态
        success_count = sum(1 for success, _ in task.results.values() if success)
        if success_count == len(task.platforms):
            task.status = "success"
        elif success_count > 0:
            task.status = "partial"
        else:
            task.status = "failed"
        
        task.completed_at = datetime.now()
        
        lg.print_log(
            f"[任务 {task_id}] 发布完成: {success_count}/{len(task.platforms)} 成功, "
            f"耗时 {task.execution_time_ms:.0f}ms",
            "success" if task.status == "success" else "info"
        )
        
        # 触发内存优化
        memory_optimizer.check_and_optimize()
        
        return task.results
    
    async def publish_to_all(
        self,
        title: str,
        content: str,
        images: List[str] = None,
        options: Dict[str, Any] = None
    ) -> Dict[str, Tuple[bool, str]]:
        """一键异步发布到所有启用平台"""
        task = self.create_publish_task(title, content, images, options=options)
        return await self.execute_task(task.id)
    
    def get_task_status(self, task_id: str) -> Optional[Dict]:
        """获取任务状态"""
        task = self.tasks.get(task_id)
        if not task:
            return None
        
        return {
            "id": task.id,
            "status": task.status,
            "platforms": [p.value for p in task.platforms],
            "results": task.results,
            "execution_time_ms": task.execution_time_ms,
            "created_at": task.created_at.isoformat(),
            "completed_at": task.completed_at.isoformat() if task.completed_at else None
        }
    
    def get_stats(self) -> Dict[str, Any]:
        """获取发布统计"""
        total = len(self.tasks)
        success = sum(1 for t in self.tasks.values() if t.status == "success")
        partial = sum(1 for t in self.tasks.values() if t.status == "partial")
        failed = sum(1 for t in self.tasks.values() if t.status == "failed")
        
        # 计算平均执行时间
        execution_times = [
            t.execution_time_ms for t in self.tasks.values() 
            if t.execution_time_ms > 0
        ]
        avg_time = sum(execution_times) / len(execution_times) if execution_times else 0
        
        return {
            "total_tasks": total,
            "success": success,
            "partial": partial,
            "failed": failed,
            "success_rate": success / total if total > 0 else 0,
            "avg_execution_time_ms": avg_time,
            "browser_pool_stats": browser_pool.get_stats()
        }


# 全局异步多平台发布中心
_async_hub: Optional[AsyncMultiPlatformHub] = None


def get_async_hub() -> AsyncMultiPlatformHub:
    """获取异步多平台发布中心实例"""
    global _async_hub
    if _async_hub is None:
        _async_hub = AsyncMultiPlatformHub()
    return _async_hub


async def async_quick_publish(
    title: str,
    content: str,
    images: List[str] = None,
    **kwargs
) -> Dict[str, Tuple[bool, str]]:
    """
    异步快速发布
    
    示例:
        results = await async_quick_publish(
            title="测试标题",
            content="测试内容",
            images=["/path/to/image.jpg"]
        )
    """
    hub = get_async_hub()
    return await hub.publish_to_all(title, content, images, kwargs)
