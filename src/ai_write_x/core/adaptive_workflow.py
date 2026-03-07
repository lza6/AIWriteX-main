# -*- coding: UTF-8 -*-
"""
V17.0 - Adaptive Workflow (自适应工作流引擎)

动态适应内容创作流程：
1. 智能任务编排
2. 条件分支
3. 并行执行
4. 自动重试
5. 工作流优化
"""

import json
import asyncio
from datetime import datetime
from typing import Dict, List, Optional, Union, Any, Callable
from dataclasses import dataclass, field
from enum import Enum, auto
import threading
from collections import defaultdict
import uuid

from ..utils import log


class TaskStatus(Enum):
    """任务状态"""
    PENDING = "pending"
    RUNNING = "running"
    COMPLETED = "completed"
    FAILED = "failed"
    SKIPPED = "skipped"
    RETRYING = "retrying"


class WorkflowStatus(Enum):
    """工作流状态"""
    ACTIVE = "active"
    PAUSED = "paused"
    COMPLETED = "completed"
    FAILED = "failed"
    CANCELLED = "cancelled"


@dataclass
class Task:
    """工作流任务"""
    id: str
    name: str
    action: Callable
    inputs: Dict[str, Any] = field(default_factory=dict)
    outputs: Dict[str, Any] = field(default_factory=dict)
    dependencies: List[str] = field(default_factory=list)
    status: TaskStatus = TaskStatus.PENDING
    retry_count: int = 0
    max_retries: int = 3
    created_at: datetime = field(default_factory=datetime.now)
    started_at: Optional[datetime] = None
    completed_at: Optional[datetime] = None
    error: Optional[str] = None
    condition: Optional[Callable] = None  # 条件函数


@dataclass
class Workflow:
    """工作流定义"""
    id: str
    name: str
    tasks: Dict[str, Task] = field(default_factory=dict)
    status: WorkflowStatus = WorkflowStatus.ACTIVE
    context: Dict[str, Any] = field(default_factory=dict)
    created_at: datetime = field(default_factory=datetime.now)
    completed_at: Optional[datetime] = None
    on_complete: Optional[Callable] = None
    on_fail: Optional[Callable] = None


class AdaptiveWorkflowEngine:
    """
    V17.0 自适应工作流引擎
    
    提供智能任务编排和动态执行能力。
    """
    
    _instance = None
    _lock = threading.Lock()
    
    def __new__(cls):
        with cls._lock:
            if cls._instance is None:
                cls._instance = super(AdaptiveWorkflowEngine, cls).__new__(cls)
                cls._instance._initialized = False
        return cls._instance
    
    def __init__(self):
        if self._initialized:
            return
        
        self._initialized = True
        
        # 工作流存储
        self.workflows: Dict[str, Workflow] = {}
        
        # 执行统计
        self.execution_stats: Dict[str, Dict] = defaultdict(lambda: {
            "total_executions": 0,
            "successful": 0,
            "failed": 0,
            "avg_duration": 0
        })
        
        # 最大并行任务数
        self.max_parallel_tasks = 5
        
        log.print_log("[V17.0] 🔄 Adaptive Workflow Engine (自适应工作流引擎) 已初始化", "success")
    
    def create_workflow(
        self,
        name: str,
        context: Optional[Dict] = None
    ) -> str:
        """创建工作流"""
        workflow_id = str(uuid.uuid4())[:12]
        
        workflow = Workflow(
            id=workflow_id,
            name=name,
            context=context or {}
        )
        
        self.workflows[workflow_id] = workflow
        log.print_log(f"[V17.0] 创建工作流: {name} ({workflow_id})", "success")
        
        return workflow_id
    
    def add_task(
        self,
        workflow_id: str,
        task_name: str,
        action: Callable,
        inputs: Optional[Dict] = None,
        dependencies: Optional[List[str]] = None,
        condition: Optional[Callable] = None,
        max_retries: int = 3
    ) -> str:
        """添加任务到工作流"""
        workflow = self.workflows.get(workflow_id)
        if not workflow:
            raise ValueError(f"工作流 {workflow_id} 不存在")
        
        task_id = f"{workflow_id}_{task_name}_{len(workflow.tasks)}"
        
        task = Task(
            id=task_id,
            name=task_name,
            action=action,
            inputs=inputs or {},
            dependencies=dependencies or [],
            condition=condition,
            max_retries=max_retries
        )
        
        workflow.tasks[task_id] = task
        return task_id
    
    async def execute_workflow(
        self,
        workflow_id: str,
        initial_context: Optional[Dict] = None
    ) -> Dict[str, Any]:
        """执行工作流"""
        workflow = self.workflows.get(workflow_id)
        if not workflow:
            raise ValueError(f"工作流 {workflow_id} 不存在")
        
        start_time = datetime.now()
        workflow.status = WorkflowStatus.ACTIVE
        
        if initial_context:
            workflow.context.update(initial_context)
        
        try:
            # 获取可执行的任务
            pending_tasks = [
                t for t in workflow.tasks.values()
                if t.status == TaskStatus.PENDING
            ]
            
            # 按依赖关系排序
            execution_order = self._topological_sort(pending_tasks)
            
            # 执行所有任务
            for task_id in execution_order:
                task = workflow.tasks[task_id]
                await self._execute_task(workflow, task)
            
            # 工作流完成
            workflow.status = WorkflowStatus.COMPLETED
            workflow.completed_at = datetime.now()
            
            duration = (workflow.completed_at - start_time).total_seconds()
            self.execution_stats[workflow_id]["total_executions"] += 1
            self.execution_stats[workflow_id]["successful"] += 1
            
            log.print_log(f"[V17.0] ✅ 工作流 {workflow.name} 完成 (耗时: {duration:.2f}s)", "success")
            
            if workflow.on_complete:
                workflow.on_complete(workflow.context)
            
            return {
                "success": True,
                "workflow_id": workflow_id,
                "duration": duration,
                "context": workflow.context
            }
            
        except Exception as e:
            workflow.status = WorkflowStatus.FAILED
            log.print_log(f"[V17.0] ❌ 工作流 {workflow.name} 失败: {e}", "error")
            
            self.execution_stats[workflow_id]["total_executions"] += 1
            self.execution_stats[workflow_id]["failed"] += 1
            
            if workflow.on_fail:
                workflow.on_fail(e)
            
            return {
                "success": False,
                "workflow_id": workflow_id,
                "error": str(e)
            }
    
    async def _execute_task(self, workflow: Workflow, task: Task):
        """执行单个任务"""
        # 检查依赖是否完成
        for dep_id in task.dependencies:
            dep_task = workflow.tasks.get(dep_id)
            if not dep_task or dep_task.status != TaskStatus.COMPLETED:
                task.status = TaskStatus.PENDING
                return
        
        # 检查条件
        if task.condition and not task.condition(workflow.context):
            task.status = TaskStatus.SKIPPED
            log.print_log(f"[V17.0] ⏭️ 任务 {task.name} 被跳过", "info")
            return
        
        # 执行任务
        task.status = TaskStatus.RUNNING
        task.started_at = datetime.now()
        
        try:
            # 准备输入 - 只传递任务定义的参数
            import inspect
            sig = inspect.signature(task.action)
            param_names = set(sig.parameters.keys())
            
            inputs = {}
            for k, v in task.inputs.items():
                if k in param_names:
                    inputs[k] = v
            
            # 执行
            if asyncio.iscoroutinefunction(task.action):
                result = await task.action(**inputs)
            else:
                result = task.action(**inputs)
            
            # 保存输出
            task.outputs = {"result": result}
            task.status = TaskStatus.COMPLETED
            task.completed_at = datetime.now()
            
            # 更新上下文
            workflow.context[f"task_{task.name}_output"] = result
            
            log.print_log(f"[V17.0] ✅ 任务 {task.name} 完成", "info")
            
        except Exception as e:
            task.error = str(e)
            task.retry_count += 1
            
            if task.retry_count < task.max_retries:
                task.status = TaskStatus.RETRYING
                log.print_log(f"[V17.0] 🔄 任务 {task.name} 重试 ({task.retry_count}/{task.max_retries})", "warning")
                await asyncio.sleep(1)  # 延迟重试
                await self._execute_task(workflow, task)
            else:
                task.status = TaskStatus.FAILED
                log.print_log(f"[V17.0] ❌ 任务 {task.name} 失败: {e}", "error")
                raise
    
    def _topological_sort(self, tasks: List[Task]) -> List[str]:
        """拓扑排序任务"""
        # 构建图
        graph = defaultdict(list)
        in_degree = {t.id: 0 for t in tasks}
        
        for task in tasks:
            for dep in task.dependencies:
                if dep in in_degree:
                    graph[dep].append(task.id)
                    in_degree[task.id] += 1
        
        # Kahn算法
        result = []
        queue = [t.id for t in tasks if in_degree[t.id] == 0]
        
        while queue:
            node = queue.pop(0)
            result.append(node)
            
            for neighbor in graph[node]:
                in_degree[neighbor] -= 1
                if in_degree[neighbor] == 0:
                    queue.append(neighbor)
        
        return result
    
    def get_workflow_status(self, workflow_id: str) -> Optional[Dict]:
        """获取工作流状态"""
        workflow = self.workflows.get(workflow_id)
        if not workflow:
            return None
        
        return {
            "id": workflow.id,
            "name": workflow.name,
            "status": workflow.status.value,
            "tasks": {
                task_id: {
                    "name": task.name,
                    "status": task.status.value,
                    "retry_count": task.retry_count
                }
                for task_id, task in workflow.tasks.items()
            },
            "context": workflow.context
        }
    
    def cancel_workflow(self, workflow_id: str) -> bool:
        """取消工作流"""
        workflow = self.workflows.get(workflow_id)
        if not workflow:
            return False
        
        workflow.status = WorkflowStatus.CANCELLED
        log.print_log(f"[V17.0] 工作流 {workflow.name} 已取消", "warning")
        return True
    
    def get_statistics(self) -> Dict[str, Any]:
        """获取统计信息"""
        return {
            "total_workflows": len(self.workflows),
            "by_status": {
                status.value: len([w for w in self.workflows.values() if w.status == status])
                for status in WorkflowStatus
            },
            "execution_stats": dict(self.execution_stats)
        }


# 全局实例
_adaptive_workflow = None


def get_adaptive_workflow() -> AdaptiveWorkflowEngine:
    """获取自适应工作流引擎全局实例"""
    global _adaptive_workflow
    if _adaptive_workflow is None:
        _adaptive_workflow = AdaptiveWorkflowEngine()
    return _adaptive_workflow
