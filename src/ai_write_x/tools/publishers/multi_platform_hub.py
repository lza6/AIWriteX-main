"""
AIWriteX 多平台发布中心
统一管理小红书、抖音、知乎、今日头条、百家号等多平台发布
"""
import asyncio
from typing import Dict, List, Optional, Any, Tuple
from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum
from concurrent.futures import ThreadPoolExecutor, as_completed
import threading

from src.ai_write_x.utils import log as lg
from src.ai_write_x.utils.performance_optimizer import (
    memory_optimizer,
    browser_pool,
    performance_monitor
)
from src.ai_write_x.tools.publishers.xiaohongshu_publisher import XiaohongshuPublisher
from src.ai_write_x.tools.publishers.douyin_publisher import DouyinPublisher
from src.ai_write_x.tools.publishers.zhihu_publisher import ZhihuPublisher
from src.ai_write_x.tools.publishers.toutiao_publisher import ToutiaoPublisher
from src.ai_write_x.tools.publishers.baijiahao_publisher import BaijiahaoPublisher


class PlatformType(Enum):
    """支持的平台类型"""
    XIAOHONGSHU = "xiaohongshu"    # 小红书
    DOUYIN = "douyin"              # 抖音
    ZHIHU = "zhihu"                # 知乎
    TOUTIAO = "toutiao"            # 今日头条
    BAIJIAHAO = "baijiahao"        # 百家号


@dataclass
class PlatformConfig:
    """平台配置"""
    platform_type: PlatformType
    enabled: bool = True
    headless: bool = True
    auto_publish: bool = False  # 是否自动点击发布
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
    status: str = "pending"  # pending, running, success, failed
    results: Dict[str, Tuple[bool, str]] = field(default_factory=dict)
    created_at: datetime = field(default_factory=datetime.now)
    completed_at: Optional[datetime] = None


class MultiPlatformHub:
    """
    多平台发布中心
    
    统一管理多个社交媒体平台的内容发布
    支持并行发布、任务调度、发布状态追踪
    """
    
    _instance = None
    _lock = threading.Lock()
    
    def __new__(cls):
        if cls._instance is None:
            with cls._lock:
                if cls._instance is None:
                    cls._instance = super().__new__(cls)
                    cls._instance._initialized = False
        return cls._instance
    
    def __init__(self):
        if self._initialized:
            return
            
        self._initialized = True
        self.platforms: Dict[PlatformType, Any] = {}
        self.configs: Dict[PlatformType, PlatformConfig] = {}
        self.tasks: Dict[str, PublishTask] = {}
        self.executor = ThreadPoolExecutor(max_workers=5)
        
        # 初始化平台配置
        self._init_platforms()
    
    def _init_platforms(self):
        """初始化所有平台"""
        # 小红书
        self.configs[PlatformType.XIAOHONGSHU] = PlatformConfig(
            platform_type=PlatformType.XIAOHONGSHU,
            enabled=True,
            headless=True
        )
        
        # 抖音
        self.configs[PlatformType.DOUYIN] = PlatformConfig(
            platform_type=PlatformType.DOUYIN,
            enabled=True,
            headless=True
        )
        
        # 知乎
        self.configs[PlatformType.ZHIHU] = PlatformConfig(
            platform_type=PlatformType.ZHIHU,
            enabled=True,
            headless=True
        )
        
        # 今日头条
        self.configs[PlatformType.TOUTIAO] = PlatformConfig(
            platform_type=PlatformType.TOUTIAO,
            enabled=True,
            headless=True
        )
        
        # 百家号
        self.configs[PlatformType.BAIJIAHAO] = PlatformConfig(
            platform_type=PlatformType.BAIJIAHAO,
            enabled=True,
            headless=True
        )
    
    def get_publisher(self, platform_type: PlatformType) -> Optional[Any]:
        """获取平台发布器实例"""
        if platform_type not in self.platforms:
            config = self.configs.get(platform_type)
            if not config or not config.enabled:
                return None
            
            # 创建发布器实例
            if platform_type == PlatformType.XIAOHONGSHU:
                self.platforms[platform_type] = XiaohongshuPublisher(headless=config.headless)
            elif platform_type == PlatformType.DOUYIN:
                self.platforms[platform_type] = DouyinPublisher(headless=config.headless)
            elif platform_type == PlatformType.ZHIHU:
                self.platforms[platform_type] = ZhihuPublisher(headless=config.headless)
            elif platform_type == PlatformType.TOUTIAO:
                self.platforms[platform_type] = ToutiaoPublisher(headless=config.headless)
            elif platform_type == PlatformType.BAIJIAHAO:
                self.platforms[platform_type] = BaijiahaoPublisher(headless=config.headless)
        
        return self.platforms.get(platform_type)
    
    def configure_platform(self, platform_type: PlatformType, **kwargs):
        """配置平台参数"""
        if platform_type in self.configs:
            config = self.configs[platform_type]
            for key, value in kwargs.items():
                if hasattr(config, key):
                    setattr(config, key, value)
            lg.print_log(f"[{platform_type.value}] 平台配置已更新", "info")
    
    def enable_platform(self, platform_type: PlatformType):
        """启用平台"""
        if platform_type in self.configs:
            self.configs[platform_type].enabled = True
            lg.print_log(f"[{platform_type.value}] 平台已启用", "success")
    
    def disable_platform(self, platform_type: PlatformType):
        """禁用平台"""
        if platform_type in self.configs:
            self.configs[platform_type].enabled = False
            lg.print_log(f"[{platform_type.value}] 平台已禁用", "info")
    
    def create_publish_task(
        self,
        title: str,
        content: str,
        images: List[str] = None,
        platforms: List[PlatformType] = None,
        options: Dict[str, Any] = None
    ) -> PublishTask:
        """
        创建发布任务
        
        Args:
            title: 内容标题
            content: 内容正文
            images: 图片路径列表
            platforms: 目标平台列表（默认全部启用平台）
            options: 额外选项
            
        Returns:
            发布任务对象
        """
        import uuid
        
        if platforms is None:
            # 默认使用所有启用的平台
            platforms = [
                pt for pt, config in self.configs.items()
                if config.enabled
            ]
        
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
    
    def execute_task(self, task_id: str) -> Dict[str, Tuple[bool, str]]:
        """
        执行发布任务
        
        Args:
            task_id: 任务ID
            
        Returns:
            各平台发布结果
        """
        task = self.tasks.get(task_id)
        if not task:
            return {}
        
        task.status = "running"
        lg.print_log(f"[任务 {task_id}] 开始执行多平台发布...", "info")
        
        # 串行执行发布（避免Cookie冲突）
        for platform_type in task.platforms:
            publisher = self.get_publisher(platform_type)
            if not publisher:
                task.results[platform_type.value] = (False, "平台未启用或未配置")
                continue
            
            lg.print_log(f"[任务 {task_id}] 正在发布到 {platform_type.value}...", "info")
            
            try:
                # 获取平台配置
                config = self.configs.get(platform_type)
                commit = config.auto_publish if config else False
                
                # 执行发布
                success, message = publisher.publish(
                    title=task.title,
                    content=task.content,
                    images=task.images,
                    commit=commit,
                    **task.options
                )
                
                task.results[platform_type.value] = (success, message)
                
                if success:
                    lg.print_log(f"[任务 {task_id}] {platform_type.value} 发布成功", "success")
                else:
                    lg.print_log(f"[任务 {task_id}] {platform_type.value} 发布失败: {message}", "warning")
                    
            except Exception as e:
                error_msg = str(e)
                task.results[platform_type.value] = (False, error_msg)
                lg.print_log(f"[任务 {task_id}] {platform_type.value} 发布异常: {error_msg}", "error")
        
        task.status = "success" if all(r[0] for r in task.results.values()) else "failed"
        task.completed_at = datetime.now()
        
        lg.print_log(f"[任务 {task_id}] 发布任务执行完成", "info")
        return task.results
    
    async def execute_task_async(self, task_id: str) -> Dict[str, Tuple[bool, str]]:
        """异步执行发布任务"""
        loop = asyncio.get_event_loop()
        return await loop.run_in_executor(None, self.execute_task, task_id)
    
    def publish_to_all(
        self,
        title: str,
        content: str,
        images: List[str] = None,
        options: Dict[str, Any] = None
    ) -> Dict[str, Tuple[bool, str]]:
        """
        一键发布到所有启用的平台
        
        Args:
            title: 标题
            content: 内容
            images: 图片列表
            options: 额外选项
            
        Returns:
            各平台发布结果
        """
        task = self.create_publish_task(
            title=title,
            content=content,
            images=images,
            options=options
        )
        
        return self.execute_task(task.id)
    
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
            "created_at": task.created_at.isoformat(),
            "completed_at": task.completed_at.isoformat() if task.completed_at else None
        }
    
    def get_platform_status(self) -> Dict[str, Dict]:
        """获取所有平台状态"""
        return {
            pt.value: {
                "enabled": config.enabled,
                "headless": config.headless,
                "auto_publish": config.auto_publish,
                "custom_settings": config.custom_settings
            }
            for pt, config in self.configs.items()
        }
    
    def test_platform_login(self, platform_type: PlatformType) -> bool:
        """测试平台登录状态"""
        publisher = self.get_publisher(platform_type)
        if not publisher:
            return False
        
        try:
            lg.print_log(f"[{platform_type.value}] 测试登录状态...", "info")
            publisher.check_and_login()
            return True
        except Exception as e:
            lg.print_log(f"[{platform_type.value}] 登录测试失败: {e}", "error")
            return False
    
    def get_publish_stats(self) -> Dict[str, Any]:
        """获取发布统计（包含性能指标）"""
        total_tasks = len(self.tasks)
        success_tasks = sum(1 for t in self.tasks.values() if t.status == "success")
        failed_tasks = sum(1 for t in self.tasks.values() if t.status == "failed")
        
        platform_stats = {}
        for task in self.tasks.values():
            for platform, (success, _) in task.results.items():
                if platform not in platform_stats:
                    platform_stats[platform] = {"success": 0, "failed": 0}
                if success:
                    platform_stats[platform]["success"] += 1
                else:
                    platform_stats[platform]["failed"] += 1
        
        # 添加性能指标
        memory_stats = {
            "process_memory_mb": round(memory_optimizer.get_memory_usage_mb(), 2),
            "system_memory": memory_optimizer.get_system_memory()
        }
        
        browser_stats = browser_pool.get_stats()
        
        return {
            "total_tasks": total_tasks,
            "success_tasks": success_tasks,
            "failed_tasks": failed_tasks,
            "success_rate": round(success_tasks / total_tasks, 4) if total_tasks > 0 else 0,
            "platform_stats": platform_stats,
            "performance": {
                "memory": memory_stats,
                "browser_pool": browser_stats
            }
        }


# 全局多平台发布中心实例
multi_platform_hub = MultiPlatformHub()


def get_multi_platform_hub() -> MultiPlatformHub:
    """获取多平台发布中心实例"""
    return multi_platform_hub


# 便捷函数
def quick_publish(title: str, content: str, images: List[str] = None, **kwargs) -> Dict[str, Tuple[bool, str]]:
    """
    快速发布到所有启用平台
    
    示例:
        results = quick_publish(
            title="测试标题",
            content="测试内容",
            images=["/path/to/image.jpg"]
        )
    """
    hub = get_multi_platform_hub()
    return hub.publish_to_all(title, content, images, kwargs)
