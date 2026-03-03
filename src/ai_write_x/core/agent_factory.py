from typing import Dict, Type, Optional, Any
from crewai import Agent

from src.ai_write_x.core.base_framework import AgentConfig
from src.ai_write_x.config.config import Config
from src.ai_write_x.core.tool_registry import GlobalToolRegistry
from src.ai_write_x.core.direct_llm import OpenAIDirectLLM
from src.ai_write_x.utils import log


class AgentFactory:
    """智能体工厂类"""

    def __init__(self):
        self._agent_templates: Dict[str, Type] = {}
        # 使用全局工具注册表
        self._tool_registry = GlobalToolRegistry.get_instance()
        self._llm_cache: Dict[str, OpenAIDirectLLM] = {}

    def register_agent_template(self, name: str, template_class: Type):
        """注册智能体模板"""
        self._agent_templates[name] = template_class

    def register_tool(self, name: str, tool_class):
        """注册工具类"""
        self._tool_registry.register_tool(name, tool_class)

    def _get_llm(self, llm_config: Dict[str, Any] | None = None) -> Optional[OpenAIDirectLLM]:
        """
        获取LLM实例，支持缓存
        
        完全使用 OpenAI 官方 SDK，不依赖 litellm：
        - 直接使用用户配置的模型名称
        - API Base 由用户设置
        - 支持 OpenAI 兼容 API
        """
        config = Config.get_instance()

        # 如果没有指定特殊配置，使用全局配置
        if not llm_config:
            cache_key = f"{config.api_type}_{config.api_model}"
            if cache_key not in self._llm_cache:
                if config.api_key:
                    # 原始模型名（用户配置的）
                    original_model = config.api_model
                    
                    # 使用自定义的 OpenAIDirectLLM，完全绕过 litellm
                    self._llm_cache[cache_key] = OpenAIDirectLLM(
                        model=original_model,
                        api_key=config.api_key,
                        base_url=config.api_apibase,
                        max_tokens=8192
                    )
                    
                    # 日志显示原始模型名，让用户看到自己配置的值
                    log.print_log(f"LLM配置: model={original_model}, base_url={config.api_apibase}", "info")
                else:
                    return None
            return self._llm_cache.get(cache_key)

        # 使用自定义LLM配置
        cache_key = f"{llm_config.get('model', 'default')}_{llm_config.get('api_key', 'default')}"
        if cache_key not in self._llm_cache:
            original_model = llm_config.get("model", "")
            
            # 获取 base_url
            base_url = llm_config.get("base_url") or llm_config.get("api_base", "")
            
            self._llm_cache[cache_key] = OpenAIDirectLLM(
                model=original_model,
                api_key=llm_config.get("api_key", ""),
                base_url=base_url,
                max_tokens=llm_config.get("max_tokens", 8192)
            )
            
            log.print_log(f"自定义LLM配置: model={original_model}", "info")
        return self._llm_cache.get(cache_key)

    def create_agent(self, config: AgentConfig, custom_llm: OpenAIDirectLLM | None = None) -> Agent:
        """创建智能体实例"""
        tools = []
        if config.tools:
            for tool_name in config.tools:
                tool_class = self._tool_registry.get_tool(tool_name)
                if tool_class:
                    tools.append(tool_class())
                else:
                    log.print_log(f"警告: 找不到 {tool_name} 工具")

        agent_kwargs = {
            "role": config.role,
            "goal": config.goal,
            "backstory": config.backstory,
            "tools": tools,
            "allow_delegation": config.allow_delegation,
            "memory": config.memory,
            "max_rpm": config.max_rpm,
            "verbose": config.verbose,
        }

        # 添加模板支持
        if hasattr(config, "system_template") and config.system_template:
            agent_kwargs["system_template"] = config.system_template
        if hasattr(config, "prompt_template") and config.prompt_template:
            agent_kwargs["prompt_template"] = config.prompt_template
        if hasattr(config, "response_template") and config.response_template:
            agent_kwargs["response_template"] = config.response_template

        # LLM优先级：自定义LLM > 配置中的LLM > 全局LLM
        llm = custom_llm or self._get_llm(config.llm_config)
        if llm:
            agent_kwargs["llm"] = llm

        return Agent(**agent_kwargs)

    def create_specialized_agent(self, name: str, **kwargs) -> Agent:
        """创建专门化智能体"""
        if name in self._agent_templates:
            template_class = self._agent_templates[name]
            return template_class(**kwargs)
        else:
            raise ValueError(f"未知 agent : {name}")

    def get_agent_by_name(self, agents: Dict[str, Agent], name: str) -> Optional[Agent]:
        """通过 name 获取 agent 实例"""
        return agents.get(name)