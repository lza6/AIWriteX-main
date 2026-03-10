"""
AIWriteX 核心模块简化测试
针对实际代码结构编写的测试
"""
import os
import sys
import pytest
from unittest import TestCase

project_root = os.path.dirname(os.path.dirname(__file__))
if project_root not in sys.path:
    sys.path.insert(0, project_root)


class TestLLMClientBasic(TestCase):
    """LLM 客户端基础测试"""

    def test_llm_client_import(self):
        """测试 LLM 客户端可以导入"""
        from src.ai_write_x.core.llm_client import LLMClient
        assert LLMClient is not None

    def test_llm_client_singleton(self):
        """测试 LLM 客户端单例模式"""
        from src.ai_write_x.core.llm_client import LLMClient
        
        client1 = LLMClient()
        client2 = LLMClient()
        assert client1 is client2

    def test_vision_detector(self):
        """测试视觉模型检测器"""
        from src.ai_write_x.core.llm_client import VisionModelDetector
        
        # 测试视觉模型检测
        assert VisionModelDetector.is_vision_model("gpt-4o") == True
        assert VisionModelDetector.is_vision_model("gpt-4-vision") == True
        assert VisionModelDetector.is_vision_model("claude-3") == True
        assert VisionModelDetector.is_vision_model("qwen-vl") == True
        
        # 测试非视觉模型
        assert VisionModelDetector.is_vision_model("gpt-3.5-turbo") == False
        assert VisionModelDetector.is_vision_model("deepseek-chat") == False


class TestConfigBasic(TestCase):
    """配置模块基础测试"""

    def test_config_import(self):
        """测试配置模块可以导入"""
        from src.ai_write_x.config.config import Config
        assert Config is not None

    def test_config_singleton(self):
        """测试配置单例模式"""
        from src.ai_write_x.config.config import Config
        
        config1 = Config.get_instance()
        config2 = Config.get_instance()
        assert config1 is config2


class TestDatabaseBasic(TestCase):
    """数据库模块基础测试"""

    def test_db_models_import(self):
        """测试数据库模型可以导入"""
        from src.ai_write_x.database.models import Topic, Article, AgentMemory
        assert Topic is not None
        assert Article is not None
        assert AgentMemory is not None

    def test_db_manager_import(self):
        """测试数据库管理器可以导入"""
        from src.ai_write_x.database.db_manager import DBManager
        assert DBManager is not None


class TestUtilsBasic(TestCase):
    """工具模块基础测试"""

    def test_log_import(self):
        """测试日志模块可以导入"""
        from src.ai_write_x.utils.log import LogManager
        assert LogManager is not None

    def test_exception_handler_import(self):
        """测试异常处理器可以导入"""
        from src.ai_write_x.utils.exception_handler import exception_handler
        assert exception_handler is not None


class TestPublishersBasic(TestCase):
    """发布器模块基础测试"""

    def test_base_publisher_import(self):
        """测试基础发布器可以导入"""
        from src.ai_write_x.tools.publishers.base_publisher import PlaywrightPublisher
        assert PlaywrightPublisher is not None

    def test_multi_platform_hub_import(self):
        """测试多平台中心可以导入"""
        from src.ai_write_x.tools.publishers.multi_platform_hub import MultiPlatformHub
        assert MultiPlatformHub is not None


class TestSwarmBasic(TestCase):
    """Swarm 模块基础测试"""

    def test_swarm_agent_import(self):
        """测试 Swarm 智能体可以导入"""
        from src.ai_write_x.core.swarm.swarm_agent import AgentNode
        assert AgentNode is not None

    def test_swarm_consciousness_import(self):
        """测试群体意识可以导入"""
        from src.ai_write_x.core.swarm.swarm_consciousness import SwarmConsciousness
        assert SwarmConsciousness is not None


class TestCognitiveBasic(TestCase):
    """认知模块基础测试"""

    def test_working_memory_import(self):
        """测试工作记忆可以导入"""
        from src.ai_write_x.core.cognitive.working_memory_v2 import MemoryChunk
        assert MemoryChunk is not None

    def test_knowledge_graph_import(self):
        """测试知识图谱可以导入"""
        from src.ai_write_x.core.knowledge_graph import KnowledgeGraph
        assert KnowledgeGraph is not None


class TestWebBasic(TestCase):
    """Web 模块基础测试"""

    def test_fastapi_app_import(self):
        """测试 FastAPI 应用可以导入"""
        from src.ai_write_x.web.app import app
        assert app is not None

    def test_websocket_manager_import(self):
        """测试 WebSocket 管理器可以导入"""
        from src.ai_write_x.web.websocket_manager import WebSocketManager
        assert WebSocketManager is not None


class TestVectorDBBasic(TestCase):
    """向量数据库基础测试"""

    def test_vector_db_import(self):
        """测试向量数据库可以导入"""
        from src.ai_write_x.core.vector_db import VectorDBManager
        assert VectorDBManager is not None


class TestHotNewsBasic(TestCase):
    """热点新闻工具基础测试"""

    def test_hotnews_import(self):
        """测试热点新闻工具可以导入"""
        from src.ai_write_x.tools.hotnews import get_platform_news
        assert get_platform_news is not None

    def test_hotnews_functions(self):
        """测试热点新闻工具函数存在"""
        from src.ai_write_x.tools.hotnews import get_tophub_hotnews
        assert callable(get_tophub_hotnews)


class TestMemoryManagerBasic(TestCase):
    """记忆管理器基础测试"""

    def test_memory_manager_import(self):
        """测试记忆管理器可以导入"""
        from src.ai_write_x.core.memory_manager import MemoryManager
        assert MemoryManager is not None


class TestQualityEngineBasic(TestCase):
    """质量引擎基础测试"""

    def test_quality_engine_import(self):
        """测试质量引擎可以导入"""
        from src.ai_write_x.core.quality_engine import QualityEngine
        assert QualityEngine is not None


class TestMonitoringBasic(TestCase):
    """监控模块基础测试"""

    def test_workflow_monitor_import(self):
        """测试工作流监控器可以导入"""
        from src.ai_write_x.core.monitoring import WorkflowMonitor
        assert WorkflowMonitor is not None

    def test_workflow_monitor_singleton(self):
        """测试工作流监控器单例"""
        from src.ai_write_x.core.monitoring import WorkflowMonitor
        
        monitor1 = WorkflowMonitor()
        monitor2 = WorkflowMonitor()
        assert monitor1 is monitor2


class TestAgentFactoryBasic(TestCase):
    """智能体工厂基础测试"""

    def test_agent_factory_import(self):
        """测试智能体工厂可以导入"""
        from src.ai_write_x.core.agent_factory import AgentFactory
        assert AgentFactory is not None


class TestToolRegistryBasic(TestCase):
    """工具注册表基础测试"""

    def test_tool_registry_import(self):
        """测试工具注册表可以导入"""
        from src.ai_write_x.core.tool_registry import GlobalToolRegistry
        assert GlobalToolRegistry is not None

    def test_tool_registry_singleton(self):
        """测试工具注册表实例化"""
        from src.ai_write_x.core.tool_registry import GlobalToolRegistry
        
        registry = GlobalToolRegistry()
        assert registry is not None


class TestSemanticCacheBasic(TestCase):
    """语义缓存基础测试"""

    def test_semantic_cache_import(self):
        """测试语义缓存可以导入"""
        from src.ai_write_x.core.semantic_cache_v2 import SemanticCache
        assert SemanticCache is not None


class TestBatchProcessorBasic(TestCase):
    """批处理器基础测试"""

    def test_batch_processor_import(self):
        """测试批处理器可以导入"""
        from src.ai_write_x.core.batch_processor import SmartBatchProcessor
        assert SmartBatchProcessor is not None


class TestStreamingProcessorBasic(TestCase):
    """流式处理器基础测试"""

    def test_streaming_processor_import(self):
        """测试流式处理器可以导入"""
        from src.ai_write_x.core.streaming_processor import StreamProcessor
        assert StreamProcessor is not None


class TestSchedulerBasic(TestCase):
    """调度器基础测试"""

    def test_scheduler_import(self):
        """测试调度器可以导入"""
        from src.ai_write_x.core.scheduler import SchedulerService
        assert SchedulerService is not None


class TestAutonomousSchedulerBasic(TestCase):
    """自治调度器基础测试"""

    def test_autonomous_scheduler_import(self):
        """测试自治调度器可以导入"""
        from src.ai_write_x.core.autonomous_scheduler import AutonomousScheduler
        assert AutonomousScheduler is not None


class TestPredictiveEngineBasic(TestCase):
    """预测引擎基础测试"""

    def test_predictive_engine_import(self):
        """测试预测引擎可以导入"""
        from src.ai_write_x.core.predictive_engine import PredictiveEngine
        assert PredictiveEngine is not None


class TestReinforcementOptimizerBasic(TestCase):
    """强化学习优化器基础测试"""

    def test_reinforcement_optimizer_import(self):
        """测试强化学习优化器可以导入"""
        from src.ai_write_x.core.reinforcement_optimizer import ReinforcementOptimizer
        assert ReinforcementOptimizer is not None


class TestExperimentEngineBasic(TestCase):
    """实验引擎基础测试"""

    def test_experiment_engine_import(self):
        """测试实验引擎可以导入"""
        from src.ai_write_x.core.experiment_engine import ExperimentEngine
        assert ExperimentEngine is not None


class TestContentAnalyticsBasic(TestCase):
    """内容分析基础测试"""

    def test_content_analytics_import(self):
        """测试内容分析可以导入"""
        from src.ai_write_x.core.content_analytics import ContentAnalytics
        assert ContentAnalytics is not None


class TestIntelligentDashboardBasic(TestCase):
    """智能仪表板基础测试"""

    def test_intelligent_dashboard_import(self):
        """测试智能仪表板可以导入"""
        from src.ai_write_x.core.intelligent_dashboard import IntelligentDashboard
        assert IntelligentDashboard is not None


class TestCollaborationHubBasic(TestCase):
    """协作中心基础测试"""

    def test_collaboration_hub_import(self):
        """测试协作中心可以导入"""
        from src.ai_write_x.core.collaboration_hub import CollaborationHub
        assert CollaborationHub is not None


class TestCrossModalRetrievalBasic(TestCase):
    """跨模态检索基础测试"""

    def test_cross_modal_retrieval_import(self):
        """测试跨模态检索可以导入"""
        from src.ai_write_x.core.cross_modal_retrieval import CrossModalRetrieval
        assert CrossModalRetrieval is not None


class TestMultimodalEngineBasic(TestCase):
    """多模态引擎基础测试"""

    def test_multimodal_engine_import(self):
        """测试多模态引擎可以导入"""
        from src.ai_write_x.core.multimodal_engine import ImageGenerator
        assert ImageGenerator is not None


class TestVisualAssetsBasic(TestCase):
    """视觉资产基础测试"""

    def test_visual_assets_import(self):
        """测试视觉资产管理可以导入"""
        from src.ai_write_x.core.visual_assets import VisualAssetsManager
        assert VisualAssetsManager is not None


class TestWeChatPreviewBasic(TestCase):
    """微信预览基础测试"""

    def test_wechat_preview_import(self):
        """测试微信预览可以导入"""
        from src.ai_write_x.core.wechat_preview import WeChatPreviewEngine
        assert WeChatPreviewEngine is not None


class TestAdaptiveWorkflowBasic(TestCase):
    """自适应工作流基础测试"""

    def test_adaptive_workflow_import(self):
        """测试自适应工作流可以导入"""
        from src.ai_write_x.core.adaptive_workflow import AdaptiveWorkflowEngine
        assert AdaptiveWorkflowEngine is not None


class TestDimensionalEngineBasic(TestCase):
    """维度引擎基础测试"""

    def test_dimensional_engine_import(self):
        """测试维度引擎可以导入"""
        from src.ai_write_x.core.dimensional_engine import DimensionalCreativeEngine
        assert DimensionalCreativeEngine is not None


class TestAntiAIBasic(TestCase):
    """反 AI 检测基础测试"""

    def test_anti_ai_import(self):
        """测试反 AI 检测可以导入"""
        from src.ai_write_x.core.anti_ai import AntiAIEngine
        assert AntiAIEngine is not None


class TestFinalReviewerBasic(TestCase):
    """最终审核器基础测试"""

    def test_final_reviewer_import(self):
        """测试最终审核器可以导入"""
        from src.ai_write_x.core.final_reviewer import FinalReviewer
        assert FinalReviewer is not None


class TestAestheticSummarizerBasic(TestCase):
    """美学摘要器基础测试"""

    def test_aesthetic_summarizer_import(self):
        """测试美学摘要器可以导入"""
        from src.ai_write_x.core.aesthetic_summarizer import AestheticSummarizer
        assert AestheticSummarizer is not None


class TestMetricsBasic(TestCase):
    """指标收集基础测试"""

    def test_metrics_import(self):
        """测试指标收集可以导入"""
        from src.ai_write_x.core.metrics import MetricsCollector
        assert MetricsCollector is not None


class TestSelfHealingBasic(TestCase):
    """自修复系统基础测试"""

    def test_self_healing_import(self):
        """测试自修复系统可以导入"""
        from src.ai_write_x.core.self_healing_v19 import SelfHealingSystem
        assert SelfHealingSystem is not None


class TestExceptionsBasic(TestCase):
    """异常体系基础测试"""

    def test_workflow_exception_import(self):
        """测试工作流异常可以导入"""
        from src.ai_write_x.core.exceptions import WorkflowException
        assert WorkflowException is not None

    def test_exception_hierarchy(self):
        """测试异常层次结构"""
        from src.ai_write_x.core.exceptions import AIWriteXException, WorkflowException
        
        # 测试继承关系
        assert issubclass(WorkflowException, AIWriteXException)


# 运行测试
if __name__ == "__main__":
    pytest.main([__file__, "-v", "--tb=short"])
