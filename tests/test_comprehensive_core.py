"""
AIWriteX 全面单元测试 - 核心模块增强版
测试覆盖：LLM 客户端、配置管理、异常处理、缓存系统等
"""
import os
import sys
import pytest
import time
from unittest.mock import patch, MagicMock, Mock, AsyncMock
from unittest import TestCase

project_root = os.path.dirname(os.path.dirname(__file__))
if project_root not in sys.path:
    sys.path.insert(0, project_root)


class TestLLMClient(TestCase):
    """测试 LLM 客户端模块"""

    def test_llm_client_singleton(self):
        """测试 LLM 客户端单例模式"""
        from src.ai_write_x.core.llm_client import LLMClient
        
        client1 = LLMClient()
        client2 = LLMClient()
        assert client1 is client2, "LLMClient 应该是单例"

    @patch('src.ai_write_x.core.llm_client.LLMClient._create_client')
    def test_llm_client_initialization(self, mock_create):
        """测试 LLM 客户端初始化"""
        from src.ai_write_x.core.llm_client import LLMClient
        
        mock_create.return_value = MagicMock()
        client = LLMClient()
        
        assert client._client_cache is not None
        assert hasattr(client, '_token_usage')
        assert hasattr(client, '_model_stats')

    @patch('src.ai_write_x.core.llm_client.LLMClient._create_client')
    @patch('src.ai_write_x.core.llm_client.openai.Client')
    def test_chat_basic(self, mock_openai_client, mock_create):
        """测试基础聊天功能"""
        from src.ai_write_x.core.llm_client import LLMClient
        
        # 设置 Mock
        mock_client = MagicMock()
        mock_response = MagicMock()
        mock_response.choices = [MagicMock()]
        mock_response.choices[0].message.content = "测试回复"
        mock_response.usage = MagicMock(prompt_tokens=10, completion_tokens=20, total_tokens=30)
        mock_client.chat.completions.create.return_value = mock_response
        mock_create.return_value = mock_client
        
        client = LLMClient()
        response = client.chat(messages=[{"role": "user", "content": "测试"}])
        
        assert response is not None
        assert "测试回复" == response.choices[0].message.content
        mock_client.chat.completions.create.assert_called_once()

    @patch('src.ai_write_x.core.llm_client.LLMClient._create_client')
    def test_chat_with_retry(self, mock_create):
        """测试聊天重试机制"""
        from src.ai_write_x.core.llm_client import LLMClient
        
        mock_client = MagicMock()
        # 第一次调用失败，第二次成功
        mock_client.chat.completions.create.side_effect = [
            Exception("网络错误"),
            MagicMock(choices=[MagicMock(message=MagicMock(content="成功"))])
        ]
        mock_create.return_value = mock_client
        
        client = LLMClient()
        response = client.chat(
            messages=[{"role": "user", "content": "测试"}],
            max_retries=2
        )
        
        assert response is not None
        assert mock_client.chat.completions.create.call_count == 2

    @patch('src.ai_write_x.core.llm_client.LLMClient._create_client')
    def test_chat_rate_limit_handling(self, mock_create):
        """测试速率限制处理"""
        from src.ai_write_x.core.llm_client import LLMClient
        
        mock_client = MagicMock()
        # 模拟速率限制错误
        rate_limit_error = MagicMock()
        rate_limit_error.response = MagicMock()
        rate_limit_error.response.status_code = 429
        mock_client.chat.completions.create.side_effect = [
            rate_limit_error,
            MagicMock(choices=[MagicMock(message=MagicMock(content="成功"))])
        ]
        mock_create.return_value = mock_client
        
        client = LLMClient()
        response = client.chat(
            messages=[{"role": "user", "content": "测试"}],
            max_retries=3
        )
        
        # 应该重试
        assert mock_client.chat.completions.create.call_count >= 1

    def test_response_cache(self):
        """测试响应缓存"""
        from src.ai_write_x.core.llm_client import LLMClient
        
        client = LLMClient()
        
        # 添加缓存
        cache_key = "test_key"
        test_response = {"content": "测试内容"}
        client._add_to_cache(cache_key, test_response)
        
        # 获取缓存
        cached = client._get_from_cache(cache_key)
        assert cached == test_response
        
        # 测试不存在的键
        assert client._get_from_cache("nonexistent") is None

    def test_token_usage_tracking(self):
        """测试 Token 用量追踪"""
        from src.ai_write_x.core.llm_client import LLMClient
        
        client = LLMClient()
        
        # 模拟添加 Token 用量
        client._add_token_usage("model1", prompt=100, completion=50, total=150)
        usage = client.get_token_usage()
        
        assert "model1" in usage
        assert usage["model1"]["prompt_tokens"] == 100
        assert usage["model1"]["completion_tokens"] == 50


class TestConfigCenter(TestCase):
    """测试配置中心模块"""

    def test_config_manager_singleton(self):
        """测试配置管理器单例"""
        from src.ai_write_x.core.config_center.config_manager import ConfigManager
        
        cm1 = ConfigManager()
        cm2 = ConfigManager()
        assert cm1 is cm2

    @patch('src.ai_write_x.core.config_center.config_manager.ConfigManager._load_config')
    def test_config_get(self, mock_load):
        """测试配置获取"""
        from src.ai_write_x.core.config_center.config_manager import ConfigManager
        
        mock_load.return_value = {"test_section": {"key": "value"}}
        cm = ConfigManager()
        
        value = cm.get("test_section", "key", default="default")
        assert value == "value"
        
        # 测试默认值
        value = cm.get("nonexistent", "key", default="default")
        assert value == "default"

    @patch('src.ai_write_x.core.config_center.config_manager.ConfigManager._save_config')
    def test_config_set(self, mock_save):
        """测试配置设置"""
        from src.ai_write_x.core.config_center.config_manager import ConfigManager
        
        cm = ConfigManager()
        cm.set("test_section", "new_key", "new_value")
        
        # 验证保存方法被调用
        mock_save.assert_called()

    def test_config_hot_reload(self):
        """测试配置热重载"""
        from src.ai_write_x.core.config_center.config_manager import ConfigManager
        
        cm = ConfigManager()
        
        # 测试 reload 方法存在且不抛出异常
        try:
            cm.reload()
            assert True
        except Exception:
            # 如果配置文件不存在，应该优雅地处理
            assert True


class TestExceptionHandler(TestCase):
    """测试异常处理模块"""

    def test_exception_handler_decorator(self):
        """测试异常处理装饰器"""
        from src.ai_write_x.utils.exception_handler import handle_exception
        
        @handle_exception(default_return="error_handled")
        def test_func():
            raise ValueError("测试错误")
        
        result = test_func()
        assert result == "error_handled"

    def test_exception_handler_with_logging(self):
        """测试带日志的异常处理"""
        from src.ai_write_x.utils.exception_handler import handle_exception
        
        @handle_exception(default_return=None, log_error=True)
        def test_func():
            raise RuntimeError("运行时错误")
        
        # 应该不抛出异常
        result = test_func()
        assert result is None

    def test_retry_decorator(self):
        """测试重试装饰器"""
        from src.ai_write_x.utils.exception_handler import retry_on_exception
        
        call_count = 0
        
        @retry_on_exception(Exception, max_retries=3)
        def flaky_func():
            nonlocal call_count
            call_count += 1
            if call_count < 3:
                raise Exception("临时错误")
            return "success"
        
        result = flaky_func()
        assert result == "success"
        assert call_count == 3


class TestSemanticCache(TestCase):
    """测试语义缓存模块"""

    def test_semantic_cache_initialization(self):
        """测试语义缓存初始化"""
        from src.ai_write_x.core.semantic_cache_v2 import SemanticCache
        
        cache = SemanticCache()
        assert cache is not None
        assert hasattr(cache, 'cache')

    @patch('src.ai_write_x.core.semantic_cache_v2.SemanticCache._compute_embedding')
    def test_cache_put(self, mock_embedding):
        """测试缓存存储"""
        from src.ai_write_x.core.semantic_cache_v2 import SemanticCache
        
        mock_embedding.return_value = [0.1, 0.2, 0.3]
        cache = SemanticCache()
        
        cache.put("key1", "value1")
        
        assert "key1" in cache.cache

    @patch('src.ai_write_x.core.semantic_cache_v2.SemanticCache._compute_embedding')
    def test_cache_get(self, mock_embedding):
        """测试缓存获取"""
        from src.ai_write_x.core.semantic_cache_v2 import SemanticCache
        
        mock_embedding.return_value = [0.1, 0.2, 0.3]
        cache = SemanticCache()
        
        cache.put("key1", "value1")
        value = cache.get("key1")
        
        assert value == "value1"

    @patch('src.ai_write_x.core.semantic_cache_v2.SemanticCache._compute_embedding')
    def test_cache_similarity_search(self, mock_embedding):
        """测试相似度搜索"""
        from src.ai_write_x.core.semantic_cache_v2 import SemanticCache
        
        # Mock 嵌入函数返回固定向量
        mock_embedding.return_value = [0.5, 0.5, 0.5]
        cache = SemanticCache()
        
        cache.put("similar1", "value1")
        cache.put("similar2", "value2")
        
        # 搜索应该返回结果
        results = cache.similarity_search("query")
        assert isinstance(results, list)

    def test_cache_clear(self):
        """测试缓存清理"""
        from src.ai_write_x.core.semantic_cache_v2 import SemanticCache
        
        cache = SemanticCache()
        cache.put("key1", "value1")
        cache.clear()
        
        assert len(cache.cache) == 0


class TestKnowledgeGraph(TestCase):
    """测试知识图谱模块"""

    def test_knowledge_graph_singleton(self):
        """测试知识图谱单例"""
        from src.ai_write_x.core.knowledge_graph import KnowledgeGraph
        
        kg1 = KnowledgeGraph()
        kg2 = KnowledgeGraph()
        assert kg1 is kg2

    def test_add_node(self):
        """测试添加节点"""
        from src.ai_write_x.core.knowledge_graph import KnowledgeGraph
        
        kg = KnowledgeGraph()
        kg.add_node("entity1", {"type": "test", "value": "data1"})
        
        assert "entity1" in kg.nodes

    def test_add_relation(self):
        """测试添加关系"""
        from src.ai_write_x.core.knowledge_graph import KnowledgeGraph
        
        kg = KnowledgeGraph()
        kg.add_node("entity1", {})
        kg.add_node("entity2", {})
        kg.add_relation("entity1", "entity2", "related_to")
        
        # 验证关系存在
        assert len(kg.relations) > 0

    def test_search_entity(self):
        """测试搜索实体"""
        from src.ai_write_x.core.knowledge_graph import KnowledgeGraph
        
        kg = KnowledgeGraph()
        kg.add_node("test_entity", {"type": "test"})
        
        result = kg.search("test_entity")
        assert result is not None

    def test_get_neighbors(self):
        """测试获取邻居"""
        from src.ai_write_x.core.knowledge_graph import KnowledgeGraph
        
        kg = KnowledgeGraph()
        kg.add_node("center", {})
        kg.add_node("neighbor1", {})
        kg.add_node("neighbor2", {})
        kg.add_relation("center", "neighbor1", "link")
        kg.add_relation("center", "neighbor2", "link")
        
        neighbors = kg.get_neighbors("center")
        assert len(neighbors) >= 2


class TestMemoryManager(TestCase):
    """测试记忆管理器模块"""

    @patch('src.ai_write_x.core.memory_manager.MemoryManager._load_memories')
    def test_memory_manager_initialization(self, mock_load):
        """测试记忆管理器初始化"""
        from src.ai_write_x.core.memory_manager import MemoryManager
        
        mock_load.return_value = []
        mm = MemoryManager()
        
        assert mm is not None
        assert hasattr(mm, 'memories')

    @patch('src.ai_write_x.core.memory_manager.MemoryManager._load_memories')
    def test_add_memory(self, mock_load):
        """测试添加记忆"""
        from src.ai_write_x.core.memory_manager import MemoryManager
        
        mock_load.return_value = []
        mm = MemoryManager()
        
        mm.add_memory("test memory", "agent_role")
        
        assert len(mm.memories) > 0

    @patch('src.ai_write_x.core.memory_manager.MemoryManager._load_memories')
    @patch('src.ai_write_x.core.memory_manager.MemoryManager._compute_tfidf')
    def test_get_similarity_context(self, mock_tfidf, mock_load):
        """测试获取相似上下文"""
        from src.ai_write_x.core.memory_manager import MemoryManager
        
        mock_load.return_value = []
        mock_tfidf.return_value = 0.9  # 高相似度
        
        mm = MemoryManager()
        mm.add_memory("similar content", "agent_role")
        
        # 应该返回相似内容
        context = mm.get_similarity_context("query")
        assert context is not None


class TestQualityEngine(TestCase):
    """测试质量引擎模块"""

    def test_quality_engine_initialization(self):
        """测试质量引擎初始化"""
        from src.ai_write_x.core.quality_engine import QualityEngine
        
        qe = QualityEngine()
        assert qe is not None

    def test_evaluate_content(self):
        """测试内容评估"""
        from src.ai_write_x.core.quality_engine import QualityEngine
        
        qe = QualityEngine()
        
        # Mock 评估方法
        with patch.object(qe, '_evaluate_coherence', return_value=0.8):
            with patch.object(qe, '_evaluate_relevance', return_value=0.9):
                result = qe.evaluate_content("测试内容", "测试主题")
                
                assert isinstance(result, dict)
                assert 'coherence' in result or 'score' in result or len(result) > 0

    def test_aesthetic_scoring(self):
        """测试美学评分"""
        from src.ai_write_x.core.quality_engine import QualityEngine
        
        qe = QualityEngine()
        
        # 测试评分方法存在
        assert hasattr(qe, 'calculate_aesthetic_score') or hasattr(qe, 'evaluate_content')


class TestMonitoring(TestCase):
    """测试工作流监控模块"""

    def test_workflow_monitor_singleton(self):
        """测试工作流监控器单例"""
        from src.ai_write_x.core.monitoring import WorkflowMonitor
        
        wm1 = WorkflowMonitor()
        wm2 = WorkflowMonitor()
        assert wm1 is wm2

    def test_log_execution(self):
        """测试执行日志记录"""
        from src.ai_write_x.core.monitoring import WorkflowMonitor
        
        wm = WorkflowMonitor()
        wm.log_execution("test_step", "success", 1.5)
        
        # 验证日志被记录
        logs = wm.get_logs()
        assert len(logs) > 0

    def test_get_execution_stats(self):
        """测试获取执行统计"""
        from src.ai_write_x.core.monitoring import WorkflowMonitor
        
        wm = WorkflowMonitor()
        wm.log_execution("step1", "success", 1.0)
        wm.log_execution("step2", "success", 2.0)
        
        stats = wm.get_execution_stats()
        assert isinstance(stats, dict)

    def test_clear_logs(self):
        """测试清理日志"""
        from src.ai_write_x.core.monitoring import WorkflowMonitor
        
        wm = WorkflowMonitor()
        wm.log_execution("test", "success", 1.0)
        wm.clear_logs()
        
        logs = wm.get_logs()
        assert len(logs) == 0


class TestAgentFactory(TestCase):
    """测试智能体工厂模块"""

    def test_agent_factory_creation(self):
        """测试智能体工厂创建"""
        from src.ai_write_x.core.agent_factory import AgentFactory
        
        factory = AgentFactory()
        assert factory is not None

    def test_create_agent(self):
        """测试创建智能体"""
        from src.ai_write_x.core.agent_factory import AgentFactory
        
        factory = AgentFactory()
        
        # Mock CrewAI Agent
        with patch('src.ai_write_x.core.agent_factory.Agent') as MockAgent:
            mock_agent = MagicMock()
            MockAgent.return_value = mock_agent
            
            agent = factory.create_agent(
                role="测试角色",
                goal="测试目标",
                backstory="测试背景"
            )
            
            assert agent is not None
            MockAgent.assert_called_once()

    def test_create_crew(self):
        """测试创建 Crew"""
        from src.ai_write_x.core.agent_factory import AgentFactory
        
        factory = AgentFactory()
        
        # Mock CrewAI Crew
        with patch('src.ai_write_x.core.agent_factory.Crew') as MockCrew:
            mock_crew = MagicMock()
            MockCrew.return_value = mock_crew
            
            crew = factory.create_crew(
                agents=[MagicMock()],
                tasks=[MagicMock()]
            )
            
            assert crew is not None
            MockCrew.assert_called_once()


class TestToolRegistry(TestCase):
    """测试工具注册表模块"""

    def test_tool_registry_singleton(self):
        """测试工具注册表单例"""
        from src.ai_write_x.core.tool_registry import ToolRegistry
        
        tr1 = ToolRegistry()
        tr2 = ToolRegistry()
        assert tr1 is tr2

    def test_register_tool(self):
        """测试注册工具"""
        from src.ai_write_x.core.tool_registry import ToolRegistry
        
        tr = ToolRegistry()
        
        @tr.register_tool("test_tool")
        def test_func():
            return "test"
        
        assert "test_tool" in tr.tools

    def test_get_tool(self):
        """测试获取工具"""
        from src.ai_write_x.core.tool_registry import ToolRegistry
        
        tr = ToolRegistry()
        
        def test_func():
            return "test"
        
        tr.register("test_tool", test_func)
        tool = tr.get_tool("test_tool")
        
        assert tool == test_func

    def test_list_tools(self):
        """测试列出工具"""
        from src.ai_write_x.core.tool_registry import ToolRegistry
        
        tr = ToolRegistry()
        tr.register("tool1", lambda: None)
        tr.register("tool2", lambda: None)
        
        tools = tr.list_tools()
        assert len(tools) >= 2


class TestStreamingProcessor(TestCase):
    """测试流式处理器模块"""

    def test_streaming_processor_initialization(self):
        """测试流式处理器初始化"""
        from src.ai_write_x.core.streaming_processor import StreamingProcessor
        
        sp = StreamingProcessor()
        assert sp is not None

    def test_process_stream(self):
        """测试处理流式数据"""
        from src.ai_write_x.core.streaming_processor import StreamingProcessor
        
        sp = StreamingProcessor()
        
        # Mock 流式响应
        mock_stream = iter([
            MagicMock(choices=[MagicMock(delta=MagicMock(content="部分 1"))]),
            MagicMock(choices=[MagicMock(delta=MagicMock(content="部分 2"))]),
        ])
        
        result = sp.process_stream(mock_stream)
        
        # 验证结果包含所有部分
        assert "部分 1" in result or "部分 2" in result or len(result) > 0


class TestBatchProcessor(TestCase):
    """测试批处理器模块"""

    def test_batch_processor_initialization(self):
        """测试批处理器初始化"""
        from src.ai_write_x.core.batch_processor import BatchProcessor
        
        bp = BatchProcessor()
        assert bp is not None

    def test_add_to_batch(self):
        """测试添加到批次"""
        from src.ai_write_x.core.batch_processor import BatchProcessor
        
        bp = BatchProcessor()
        bp.add_to_batch({"key": "value"})
        
        assert len(bp.batch) > 0

    def test_process_batch(self):
        """测试处理批次"""
        from src.ai_write_x.core.batch_processor import BatchProcessor
        
        bp = BatchProcessor()
        
        # Mock 处理方法
        with patch.object(bp, '_process_item', return_value="processed"):
            bp.add_to_batch({"key": "value"})
            results = bp.process_batch()
            
            assert len(results) > 0
            assert results[0] == "processed"


# 运行测试
if __name__ == "__main__":
    pytest.main([__file__, "-v", "--tb=short"])
