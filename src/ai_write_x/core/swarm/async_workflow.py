"""
异步蜂群工作流架构 (Asynchronous Swarm Workflow)
基于asyncio的完全异步工作流系统

核心组件:
1. 异步任务图 - 动态优化的任务依赖
2. 并行执行器 - 最大化并行度
3. 动态工作流引擎
"""
import asyncio
from enum import Enum
from typing import Dict, List, Any, Optional, Callable, Set, Awaitable
from datetime import datetime
from collections import defaultdict
import uuid
import json
import copy
import math

from src.ai_write_x.utils import log


class TaskStatus(str, Enum):
    """任务状态"""
    PENDING = "pending"
    RUNNING = "running"
    COMPLETED = "completed"
    FAILED = "failed"
    CANCELLED = "cancelled"


class AsyncTask:
    """
    异步任务
    
    支持:
    - 依赖声明
    - 异步执行
    - 结果传递
    """
    
    def __init__(
        self,
        task_id: str = None,
        name: str = "task",
        func: Callable = None,
        args: tuple = None,
        kwargs: Dict = None,
        depends_on: List[str] = None,
        timeout: float = 300.0,
        retry_count: int = 0,
        max_retries: int = 3
    ):
        self.task_id = task_id or str(uuid.uuid4())[:8]
        self.name = name
        self.func = func
        self.args = args or ()
        self.kwargs = kwargs or {}
        self.depends_on = depends_on or []
        self.timeout = timeout
        self.retry_count = retry_count
        self.max_retries = max_retries
        
        # 状态
        self.status = TaskStatus.PENDING
        self.result: Any = None
        self.error: Optional[Exception] = None
        
        # 元数据
        self.created_at = datetime.now()
        self.started_at: Optional[datetime] = None
        self.completed_at: Optional[datetime] = None
        
        # 资源
        self.cpu_required: float = 1.0
        self.memory_required: float = 512.0  # MB
    
    async def execute(self, context: Dict[str, Any] = None) -> Any:
        """执行任务"""
        if self.status != TaskStatus.PENDING:
            return self.result
        
        self.status = TaskStatus.RUNNING
        self.started_at = datetime.now()
        
        context = context or {}
        
        try:
            # 检查是否为协程函数
            if asyncio.iscoroutinefunction(self.func):
                if asyncio.iscoroutine(self.func(*self.args, **self.kwargs)):
                    self.result = await asyncio.wait_for(
                        self.func(*self.args, **self.kwargs),
                        timeout=self.timeout
                    )
                else:
                    self.result = self.func(*self.args, **self.kwargs)
            else:
                # 同步函数在线程池中执行
                loop = asyncio.get_event_loop()
                self.result = await asyncio.wait_for(
                    loop.run_in_executor(None, lambda: self.func(*self.args, **self.kwargs)),
                    timeout=self.timeout
                )
            
            self.status = TaskStatus.COMPLETED
            self.completed_at = datetime.now()
            
            return self.result
            
        except asyncio.TimeoutError:
            self.error = TimeoutError(f"Task {self.task_id} timed out after {self.timeout}s")
            self.status = TaskStatus.FAILED
            
            if self.retry_count < self.max_retries:
                self.retry_count += 1
                self.status = TaskStatus.PENDING
                return await self.execute(context)
            
            raise self.error
            
        except Exception as e:
            self.error = e
            self.status = TaskStatus.FAILED
            
            if self.retry_count < self.max_retries:
                self.retry_count += 1
                self.status = TaskStatus.PENDING
                return await self.execute(context)
            
            raise
    
    def get_duration(self) -> float:
        """获取执行时长"""
        if not self.started_at:
            return 0.0
        
        end = self.completed_at or datetime.now()
        return (end - self.started_at).total_seconds()
    
    def to_dict(self) -> Dict:
        return {
            "task_id": self.task_id,
            "name": self.name,
            "status": self.status.value,
            "depends_on": self.depends_on,
            "duration": self.get_duration(),
            "retry_count": self.retry_count,
            "error": str(self.error) if self.error else None
        }


class TaskGraph:
    """
    任务依赖图
    
    支持:
    - 动态依赖添加
    - 拓扑排序
    - 并行度计算
    """
    
    def __init__(self):
        self.tasks: Dict[str, AsyncTask] = {}
        self.edges: Dict[str, Set[str]] = defaultdict(set)  # task_id -> depends_on
        self.reverse_edges: Dict[str, Set[str]] = defaultdict(set)  # task_id -> dependent_by
        
        self._lock = asyncio.Lock()
    
    def add_task(self, task: AsyncTask):
        """添加任务"""
        self.tasks[task.task_id] = task
        
        # 添加依赖边
        for dep_id in task.depends_on:
            self.edges[task.task_id].add(dep_id)
            self.reverse_edges[dep_id].add(task.task_id)
    
    def remove_task(self, task_id: str):
        """移除任务"""
        if task_id not in self.tasks:
            return
        
        # 移除相关边
        for dep_id in self.edges[task_id]:
            self.reverse_edges[dep_id].discard(task_id)
        
        for dependent_id in self.reverse_edges[task_id]:
            self.edges[dependent_id].discard(task_id)
        
        del self.tasks[task_id]
        del self.edges[task_id]
        del self.reverse_edges[task_id]
    
    def add_dependency(self, task_id: str, depends_on: str):
        """添加依赖"""
        if task_id not in self.tasks or depends_on not in self.tasks:
            return
        
        self.edges[task_id].add(depends_on)
        self.reverse_edges[depends_on].add(task_id)
    
    def topological_sort(self) -> List[List[str]]:
        """
        拓扑排序 - 返回层级
        
        Returns:
            按执行层级分组的任务ID列表
        """
        # 计算入度
        in_degree = {tid: len(deps) for tid, deps in self.edges.items()}
        
        # 从入度为0的开始
        levels = []
        current = {tid for tid, deg in in_degree.items() if deg == 0}
        processed = set()
        
        while current:
            levels.append(list(current))
            processed.update(current)
            
            # 下一层
            next_level = set()
            for tid in current:
                for dependent in self.reverse_edges[tid]:
                    if dependent not in processed:
                        in_degree[dependent] -= 1
                        if in_degree[dependent] == 0:
                            next_level.add(dependent)
            
            current = next_level
        
        return levels
    
    def get_ready_tasks(self, completed: Set[str]) -> List[str]:
        """获取就绪任务（所有依赖都已完成）"""
        ready = []
        
        for task_id, deps in self.edges.items():
            if task_id in completed:
                continue
            
            if deps.issubset(completed):
                ready.append(task_id)
        
        return ready
    
    def get_parallelism(self) -> int:
        """计算最大并行度"""
        levels = self.topological_sort()
        return max(len(level) for level in levels) if levels else 0
    
    async def optimize(self) -> 'TaskGraph':
        """
        优化任务图
        
        策略:
        - 合并可以合并的任务
        - 重排依赖顺序
        - 标记可并行的任务
        """
        # 简单优化: 标记可并行任务
        levels = self.topological_sort()
        
        optimized = TaskGraph()
        
        for level in levels:
            for task_id in level:
                task = copy.copy(self.tasks[task_id])
                optimized.add_task(task)
        
        return optimized
    
    def to_dict(self) -> Dict:
        return {
            "task_count": len(self.tasks),
            "edge_count": sum(len(e) for e in self.edges.values()),
            "parallelism": self.get_parallelism(),
            "tasks": {tid: t.to_dict() for tid, t in self.tasks.items()}
        }


class ParallelExecutor:
    """
    并行执行器
    
    特性:
    - 动态任务调度
    - 资源管理
    - 错误处理
    """
    
    def __init__(
        self,
        max_concurrency: int = 10,
        resource_limits: Dict[str, float] = None
    ):
        self.max_concurrency = max_concurrency
        self.resource_limits = resource_limits or {
            "cpu": 100.0,  # 百分比
            "memory": 1024.0  # MB
        }
        
        # 运行状态
        self.running_tasks: Dict[str, asyncio.Task] = {}
        self.completed: Set[str] = set()
        self.failed: Set[str] = set()
        
        # 资源跟踪
        self.used_cpu = 0.0
        self.used_memory = 0.0
        
        # 信号量
        self._semaphore = asyncio.Semaphore(max_concurrency)
        self._lock = asyncio.Lock()
        
        # 回调
        self.on_task_complete: Optional[Callable] = None
        self.on_task_fail: Optional[Callable] = None
    
    async def execute_task(
        self,
        task: AsyncTask,
        context: Dict[str, Any] = None
    ) -> Any:
        """执行单个任务"""
        async with self._semaphore:
            # 检查资源
            if not await self._can_allocate(task):
                # 等待资源
                await self._wait_for_resources(task)
            
            # 分配资源
            await self._allocate(task)
            
            try:
                # 执行
                result = await task.execute(context)
                
                # 释放资源
                await self._release(task)
                
                # 标记完成
                async with self._lock:
                    self.completed.add(task.task_id)
                
                # 回调
                if self.on_task_complete:
                    await self.on_task_complete(task, result)
                
                return result
                
            except Exception as e:
                await self._release(task)
                
                async with self._lock:
                    self.failed.add(task.task_id)
                
                if self.on_task_fail:
                    await self.on_task_fail(task, e)
                
                raise
    
    async def _can_allocate(self, task: AsyncTask) -> bool:
        """检查是否可以分配资源"""
        return (
            self.used_cpu + task.cpu_required <= self.resource_limits["cpu"] and
            self.used_memory + task.memory_required <= self.resource_limits["memory"]
        )
    
    async def _allocate(self, task: AsyncTask):
        """分配资源"""
        async with self._lock:
            self.used_cpu += task.cpu_required
            self.used_memory += task.memory_required
    
    async def _release(self, task: AsyncTask):
        """释放资源"""
        async with self._lock:
            self.used_cpu = max(0, self.used_cpu - task.cpu_required)
            self.used_memory = max(0, self.used_memory - task.memory_required)
    
    async def _wait_for_resources(self, task: AsyncTask):
        """等待资源"""
        while not await self._can_allocate(task):
            await asyncio.sleep(0.1)
    
    async def execute_graph(
        self,
        graph: TaskGraph,
        context: Dict[str, Any] = None
    ) -> Dict[str, Any]:
        """
        执行任务图
        
        使用动态调度最大化并行度
        """
        context = context or {}
        results = {}
        
        # 获取执行层级
        levels = graph.topological_sort()
        
        for level_idx, level in enumerate(levels):
            log.print_log(
                f"[执行器] 执行层级 {level_idx + 1}/{len(levels)}, "
                f"任务数: {len(level)}",
                "debug"
            )
            
            # 并行执行当前层级
            tasks = []
            for task_id in level:
                task = graph.tasks[task_id]
                
                # 准备上下文（包含依赖结果）
                task_context = context.copy()
                for dep_id in task.depends_on:
                    if dep_id in results:
                        task_context[f"dep_{dep_id}"] = results[dep_id]
                
                # 创建执行任务
                coro = self.execute_task(task, task_context)
                tasks.append(coro)
            
            # 并行执行
            level_results = await asyncio.gather(*tasks, return_exceptions=True)
            
            # 收集结果
            for task_id, result in zip(level, level_results):
                if isinstance(result, Exception):
                    results[task_id] = {"error": str(result)}
                    log.print_log(f"[执行器] 任务 {task_id} 失败: {result}", "error")
                else:
                    results[task_id] = result
        
        return results
    
    def get_stats(self) -> Dict[str, Any]:
        """获取统计信息"""
        return {
            "running_tasks": len(self.running_tasks),
            "completed": len(self.completed),
            "failed": len(self.failed),
            "used_cpu": self.used_cpu,
            "used_memory": self.used_memory,
            "max_concurrency": self.max_concurrency
        }


class AsyncSwarmWorkflow:
    """
    异步蜂群工作流引擎
    
    特性:
    - 基于asyncio的完全异步架构
    - 任务依赖图的动态优化
    - 并行执行的最大化
    """
    
    def __init__(
        self,
        workflow_id: str = None,
        max_concurrency: int = 10
    ):
        self.workflow_id = workflow_id or str(uuid.uuid4())[:8]
        
        # 组件
        self.task_graph = TaskGraph()
        self.executor = ParallelExecutor(max_concurrency=max_concurrency)
        
        # 状态
        self.status = "idle"  # idle, running, completed, failed
        self.results: Dict[str, Any] = {}
        
        # 统计
        self.start_time: Optional[datetime] = None
        self.end_time: Optional[datetime] = None
        self.total_tasks = 0
        self.completed_tasks = 0
        
        # 回调
        self.on_workflow_complete: Optional[Callable] = None
    
    def add_task(
        self,
        name: str,
        func: Callable,
        args: tuple = None,
        kwargs: Dict = None,
        depends_on: List[str] = None,
        timeout: float = 300.0
    ) -> str:
        """添加任务"""
        task = AsyncTask(
            name=name,
            func=func,
            args=args,
            kwargs=kwargs,
            depends_on=depends_on,
            timeout=timeout
        )
        
        self.task_graph.add_task(task)
        self.total_tasks += 1
        
        return task.task_id
    
    async def run(
        self,
        context: Dict[str, Any] = None
    ) -> Dict[str, Any]:
        """运行工作流"""
        self.status = "running"
        self.start_time = datetime.now()
        
        log.print_log(f"[工作流] {self.workflow_id} 开始执行", "info")
        
        try:
            # 优化任务图
            optimized_graph = await self.task_graph.optimize()
            
            # 执行
            self.results = await self.executor.execute_graph(
                optimized_graph,
                context
            )
            
            self.status = "completed"
            self.end_time = datetime.now()
            
            log.print_log(
                f"[工作流] {self.workflow_id} 完成, "
                f"耗时: {self.get_duration():.2f}s",
                "info"
            )
            
            # 回调
            if self.on_workflow_complete:
                await self.on_workflow_complete(self.results)
            
            return self.results
            
        except Exception as e:
            self.status = "failed"
            self.end_time = datetime.now()
            
            log.print_log(f"[工作流] {self.workflow_id} 失败: {e}", "error")
            
            raise
    
    async def cancel(self):
        """取消工作流"""
        # 取消所有运行中的任务
        for task in self.executor.running_tasks.values():
            task.cancel()
        
        self.status = "cancelled"
        log.print_log(f"[工作流] {self.workflow_id} 已取消", "info")
    
    def get_duration(self) -> float:
        """获取执行时长"""
        if not self.start_time:
            return 0.0
        
        end = self.end_time or datetime.now()
        return (end - self.start_time).total_seconds()
    
    def get_progress(self) -> float:
        """获取进度"""
        if self.total_tasks == 0:
            return 0.0
        
        return len(self.executor.completed) / self.total_tasks
    
    def get_stats(self) -> Dict[str, Any]:
        """获取统计信息"""
        return {
            "workflow_id": self.workflow_id,
            "status": self.status,
            "total_tasks": self.total_tasks,
            "completed_tasks": len(self.executor.completed),
            "failed_tasks": len(self.executor.failed),
            "duration": self.get_duration(),
            "progress": self.get_progress(),
            "graph": self.task_graph.to_dict(),
            "executor": self.executor.get_stats()
        }


# 工作流工厂
_workflows: Dict[str, AsyncSwarmWorkflow] = {}


def create_workflow(
    workflow_id: str = None,
    max_concurrency: int = 10
) -> AsyncSwarmWorkflow:
    """创建异步工作流"""
    wf = AsyncSwarmWorkflow(workflow_id, max_concurrency)
    _workflows[wf.workflow_id] = wf
    return wf


def get_workflow(workflow_id: str) -> Optional[AsyncSwarmWorkflow]:
    """获取工作流"""
    return _workflows.get(workflow_id)
