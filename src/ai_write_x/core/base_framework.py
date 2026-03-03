from abc import ABC, abstractmethod
from typing import Dict, List, Any, Optional
from crewai import Agent, Task
from dataclasses import dataclass, field
from enum import Enum
import threading
from datetime import datetime
from src.ai_write_x.core.tool_registry import GlobalToolRegistry


class WorkflowType(Enum):
    SEQUENTIAL = "sequential"
    PARALLEL = "parallel"
    HIERARCHICAL = "hierarchical"
    CUSTOM = "custom"


class ContentType(Enum):
    ARTICLE = "article"
    SOCIAL_POST = "social_post"
    VIDEO_SCRIPT = "video_script"
    PODCAST_SCRIPT = "podcast_script"
    MULTIMEDIA = "multimedia"


@dataclass
class AgentConfig:
    name: str
    role: str
    goal: str
    backstory: str
    tools: List[str] = field(default_factory=list)
    llm_config: Dict[str, Any] = field(default_factory=dict)
    allow_delegation: bool = False
    memory: bool = True
    max_rpm: int = 100
    verbose: bool = True
    system_template: Optional[str] = None
    prompt_template: Optional[str] = None
    response_template: Optional[str] = None


@dataclass
class TaskConfig:
    name: str
    description: str
    agent_name: str
    expected_output: str
    context: List[str] = field(default_factory=list)
    tools: List[str] = field(default_factory=list)
    callback: Optional[str] = None
    async_execution: bool = False


@dataclass
class WorkflowConfig:
    name: str
    description: str
    workflow_type: WorkflowType
    content_type: ContentType
    agents: List[AgentConfig]
    tasks: List[TaskConfig]
    validation_rules: Dict[str, Any] = field(default_factory=dict)
    metadata: Dict[str, Any] = field(default_factory=dict)


@dataclass
class ContentResult:
    """统一的内容结果格式"""

    title: str
    content: str
    summary: str
    content_format: str
    metadata: Dict[str, Any] = field(default_factory=dict)
    created_at: datetime = field(default_factory=datetime.now)
    content_type: ContentType = ContentType.ARTICLE


class BaseWorkflowFramework(ABC):
    """通用工作流框架基类"""

    def __init__(self, config: WorkflowConfig):
        self.config = config
        self.agents: Dict[str, Agent] = {}
        self.tasks: Dict[str, Task] = {}
        # 使用全局工具注册表替代本地注册表
        self.tools_registry = GlobalToolRegistry.get_instance()
        self._lock = threading.Lock()

    @abstractmethod
    def setup_agents(self) -> Dict[str, Agent]:
        """设置智能体"""
        pass

    @abstractmethod
    def setup_tasks(self) -> Dict[str, Task]:
        """设置任务"""
        pass

    @abstractmethod
    def execute_workflow(self, input_data: Dict[str, Any]) -> ContentResult:
        """执行工作流"""
        pass

    def register_tool(self, name: str, tool_class):
        """注册工具到全局注册表"""
        self.tools_registry.register_tool(name, tool_class)

    def validate_config(self) -> bool:
        # 现有验证逻辑
        agent_names = {agent.name for agent in self.config.agents}
        task_agent_names = {task.agent_name for task in self.config.tasks}

        if not task_agent_names.issubset(agent_names):
            missing_agents = task_agent_names - agent_names
            raise ValueError(f"缺少Agents: {missing_agents}")

        # 验证工具依赖
        required_tools = set()
        for agent in self.config.agents:
            required_tools.update(agent.tools)

        available_tools = set(self.tools_registry._tools.keys())
        missing_tools = required_tools - available_tools
        if missing_tools:
            raise ValueError(f"缺少工具: {missing_tools}")

        return True
