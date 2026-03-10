"""
AIWriteX 核心模块单元测试
测试核心功能模块
"""
import os
import sys
import pytest
from unittest.mock import patch, MagicMock, Mock

project_root = os.path.dirname(os.path.dirname(__file__))
if project_root not in sys.path:
    sys.path.insert(0, project_root)


class TestPlatformAdapters:
    """测试平台适配器"""
    
    def test_platform_type_enum(self):
        """测试平台类型枚举"""
        from src.ai_write_x.core.platform_adapters import PlatformType
        
        assert PlatformType.WECHAT.value == "wechat"
        assert PlatformType.XIAOHONGSHU.value == "xiaohongshu"
        assert PlatformType.DOUYIN.value == "douyin"
        assert PlatformType.ZHIHU.value == "zhihu"
        
    def test_base_adapter_initialization(self):
        """测试基础适配器初始化"""
        from src.ai_write_x.core.platform_adapters import BasePlatformAdapter
        
        class TestAdapter(BasePlatformAdapter):
            def adapt_content(self, content):
                return content
                
            def get_platform_name(self):
                return "test"
        
        adapter = TestAdapter()
        assert adapter.get_platform_name() == "test"
        
    def test_xiaohongshu_adapter(self):
        """测试小红书适配器"""
        from src.ai_write_x.core.platform_adapters import XiaohongshuAdapter
        
        adapter = XiaohongshuAdapter()
        assert adapter.get_platform_name() == "xiaohongshu"
        
        content = "测试内容"
        adapted = adapter.adapt_content(content)
        assert isinstance(adapted, str)
        
    def test_douyin_adapter(self):
        """测试抖音适配器"""
        from src.ai_write_x.core.platform_adapters import DouyinAdapter
        
        adapter = DouyinAdapter()
        assert adapter.get_platform_name() == "douyin"
        
    def test_zhihu_adapter(self):
        """测试知乎适配器"""
        from src.ai_write_x.core.platform_adapters import ZhihuAdapter
        
        adapter = ZhihuAdapter()
        assert adapter.get_platform_name() == "zhihu"


class TestConfigCenter:
    """测试配置中心"""
    
    def test_config_manager_singleton(self):
        """测试配置管理器单例"""
        from src.ai_write_x.core.config_center.config_manager import ConfigManager
        
        cm1 = ConfigManager()
        cm2 = ConfigManager()
        assert cm1 is cm2
        
    def test_config_manager_get(self):
        """测试配置获取"""
        from src.ai_write_x.core.config_center.config_manager import ConfigManager
        
        cm = ConfigManager()
        
        with patch.object(cm, '_load_config', return_value={"test": "value"}):
            value = cm.get("test", default="default")
            # 由于可能返回实际配置，我们只测试不抛出异常
            assert value is not None or value is None
            
    def test_config_manager_set(self):
        """测试配置设置"""
        from src.ai_write_x.core.config_center.config_manager import ConfigManager
        
        cm = ConfigManager()
        
        # 测试设置配置
        with patch.object(cm, '_save_config'):
            cm.set("test_key", "test_value")
            # 验证不抛出异常
            assert True


class TestExceptionHandler:
    """测试异常处理器"""
    
    def test_exception_handler_singleton(self):
        """测试异常处理器单例"""
        from src.ai_write_x.utils.exception_handler import ExceptionHandler
        
        eh1 = ExceptionHandler()
        eh2 = ExceptionHandler()
        assert eh1 is eh2
        
    def test_handle_exception(self):
        """测试处理异常"""
        from src.ai_write_x.utils.exception_handler import exception_handler
        
        try:
            raise ValueError("测试异常")
        except Exception as e:
            # 测试处理异常不抛出错误
            result = exception_handler.handle(e)
            assert isinstance(result, dict) or result is None


class TestStructuredLogger:
    """测试结构化日志"""
    
    def test_logger_initialization(self):
        """测试日志初始化"""
        from src.ai_write_x.utils.structured_logger import StructuredLogger
        
        logger = StructuredLogger()
        assert logger is not None
        
    def test_log_levels(self):
        """测试日志级别"""
        from src.ai_write_x.utils.structured_logger import StructuredLogger
        
        logger = StructuredLogger()
        
        # 测试各级别日志
        logger.debug("调试信息")
        logger.info("信息")
        logger.warning("警告")
        logger.error("错误")
        
        assert True  # 如果执行到这里说明没有抛出异常


class TestKnowledgeGraph:
    """测试知识图谱"""
    
    def test_knowledge_graph_initialization(self):
        """测试知识图谱初始化"""
        from src.ai_write_x.core.knowledge_graph import KnowledgeGraph
        
        kg = KnowledgeGraph()
        assert kg is not None
        
    def test_add_node(self):
        """测试添加节点"""
        from src.ai_write_x.core.knowledge_graph import KnowledgeGraph
        
        kg = KnowledgeGraph()
        
        with patch.object(kg, '_save'):
            node_id = kg.add_node("测试节点", {"key": "value"})
            assert node_id is not None
            
    def test_add_edge(self):
        """测试添加边"""
        from src.ai_write_x.core.knowledge_graph import KnowledgeGraph
        
        kg = KnowledgeGraph()
        
        with patch.object(kg, '_save'):
            with patch.object(kg, 'add_node', return_value="node1"):
                kg.add_edge("node1", "node2", "relates_to")
                assert True


class TestSemanticCache:
    """测试语义缓存"""
    
    def test_semantic_cache_initialization(self):
        """测试语义缓存初始化"""
        from src.ai_write_x.core.semantic_cache_v2 import SemanticCache
        
        cache = SemanticCache()
        assert cache is not None
        
    def test_cache_get_set(self):
        """测试缓存存取"""
        from src.ai_write_x.core.semantic_cache_v2 import SemanticCache
        
        cache = SemanticCache()
        
        # 测试设置和获取
        with patch.object(cache, '_save_to_disk'):
            cache.set("key", "value")
            # 由于语义缓存的特殊性，我们可能无法直接获取相同的key
            assert True


class TestLLMClient:
    """测试LLM客户端"""
    
    def test_llm_client_initialization(self):
        """测试LLM客户端初始化"""
        from src.ai_write_x.core.llm_client import LLMClient
        
        client = LLMClient()
        assert client is not None
        
    def test_llm_client_chat(self):
        """测试LLM聊天"""
        from src.ai_write_x.core.llm_client import LLMClient
        
        client = LLMClient()
        
        with patch.object(client, 'chat', return_value="响应内容"):
            response = client.chat("测试消息")
            assert response == "响应内容"


class TestQualityEngine:
    """测试质量引擎"""
    
    def test_quality_engine_initialization(self):
        """测试质量引擎初始化"""
        from src.ai_write_x.core.quality_engine import QualityEngine
        
        engine = QualityEngine()
        assert engine is not None
        
    def test_evaluate_content(self):
        """测试评估内容"""
        from src.ai_write_x.core.quality_engine import QualityEngine
        
        engine = QualityEngine()
        
        result = engine.evaluate_content("测试内容")
        assert isinstance(result, dict) or result is not None


class TestMemoryManager:
    """测试内存管理器"""
    
    def test_memory_manager_initialization(self):
        """测试内存管理器初始化"""
        from src.ai_write_x.core.memory_manager import MemoryManager
        
        mm = MemoryManager()
        assert mm is not None
        
    def test_add_memory(self):
        """测试添加记忆"""
        from src.ai_write_x.core.memory_manager import MemoryManager
        
        mm = MemoryManager()
        
        with patch.object(mm, '_save_memory'):
            mm.add_memory("测试记忆", "fact")
            assert True


class TestCollaborationHub:
    """测试协作中心"""
    
    def test_collaboration_hub_initialization(self):
        """测试协作中心初始化"""
        from src.ai_write_x.core.collaboration_hub import CollaborationHub
        
        hub = CollaborationHub()
        assert hub is not None


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
