# -*- coding: UTF-8 -*-
"""
全面功能测试套件 - 测试所有模块和UI功能
"""

import sys
import os
import asyncio

sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', 'src'))


class TestReport:
    """测试报告"""
    def __init__(self):
        self.results = []
        self.current_phase = ""
    
    def start_phase(self, name):
        self.current_phase = name
        print(f"\n{'='*60}")
        print(f"🔬 {name}")
        print('='*60)
    
    def test(self, name, success, error=None):
        status = "✅" if success else "❌"
        msg = f"   {status} {name}"
        if error:
            msg += f" - {error}"
        print(msg)
        self.results.append({
            'phase': self.current_phase,
            'name': name,
            'success': success,
            'error': error
        })
    
    def summary(self):
        total = len(self.results)
        passed = sum(1 for r in self.results if r['success'])
        failed = total - passed
        
        print(f"\n{'='*60}")
        print(f"📊 测试总结: {passed}/{total} 通过, {failed} 失败")
        print('='*60)
        return failed == 0


report = TestReport()


def test_phase1_core_engines():
    """Phase 1: 核心引擎测试"""
    report.start_phase("Phase 1: 核心引擎组件")
    
    # 1. 版本测试
    try:
        from ai_write_x.version import get_build_info
        info = get_build_info()
        report.test("版本信息", True)
    except Exception as e:
        report.test("版本信息", False, str(e))
    
    # 2. V15组件
    try:
        from ai_write_x.core.batch_processor import get_batch_processor
        bp = get_batch_processor()
        report.test("V15 BatchProcessor", True)
    except Exception as e:
        report.test("V15 BatchProcessor", False, str(e))
    
    try:
        from ai_write_x.core.semantic_cache_v2 import get_semantic_cache
        sc = get_semantic_cache()
        report.test("V15 SemanticCacheV2", True)
    except Exception as e:
        report.test("V15 SemanticCacheV2", False, str(e))
    
    try:
        from ai_write_x.core.adaptive_router import get_adaptive_router
        ar = get_adaptive_router()
        report.test("V15 AdaptiveRouter", True)
    except Exception as e:
        report.test("V15 AdaptiveRouter", False, str(e))
    
    # 3. V16组件
    try:
        from ai_write_x.core.predictive_engine import get_predictive_engine
        pe = get_predictive_engine()
        report.test("V16 PredictiveEngine", True)
    except Exception as e:
        report.test("V16 PredictiveEngine", False, str(e))
    
    try:
        from ai_write_x.core.autonomous_scheduler import get_autonomous_scheduler
        ash = get_autonomous_scheduler()
        report.test("V16 AutonomousScheduler", True)
    except Exception as e:
        report.test("V16 AutonomousScheduler", False, str(e))
    
    try:
        from ai_write_x.core.experiment_engine import get_experiment_engine
        ee = get_experiment_engine()
        report.test("V16 ExperimentEngine", True)
    except Exception as e:
        report.test("V16 ExperimentEngine", False, str(e))
    
    try:
        from ai_write_x.core.reinforcement_optimizer import get_reinforcement_optimizer
        ro = get_reinforcement_optimizer()
        report.test("V16 ReinforcementOptimizer", True)
    except Exception as e:
        report.test("V16 ReinforcementOptimizer", False, str(e))
    
    try:
        from ai_write_x.core.content_analytics import get_content_analytics
        ca = get_content_analytics()
        report.test("V16 ContentAnalytics", True)
    except Exception as e:
        report.test("V16 ContentAnalytics", False, str(e))
    
    # 4. V17组件
    try:
        from ai_write_x.core.v17_init import initialize_v17
        result = asyncio.run(initialize_v17())
        report.test("V17初始化", len(result['components']) == 5)
    except Exception as e:
        report.test("V17初始化", False, str(e))


def test_phase2_config():
    """Phase 2: 配置系统测试"""
    report.start_phase("Phase 2: 配置系统")
    
    try:
        from ai_write_x.config.config import Config
        cfg = Config.get_instance()
        report.test("Config单例", cfg is not None)
    except Exception as e:
        report.test("Config单例", False, str(e))
    
    try:
        from ai_write_x.utils.path_manager import PathManager
        root = PathManager.get_base_dir()
        report.test("PathManager", root is not None)
    except Exception as e:
        report.test("PathManager", False, str(e))


def test_phase3_database():
    """Phase 3: 数据库测试"""
    report.start_phase("Phase 3: 数据库和模型")
    
    try:
        from ai_write_x.database.models import Article
        report.test("Article模型导入", True)
    except Exception as e:
        report.test("Article模型导入", False, str(e))
    
    try:
        from ai_write_x.database.db_manager import DBManager
        report.test("DBManager导入", True)
    except Exception as e:
        report.test("DBManager导入", False, str(e))


def test_phase4_web_api():
    """Phase 4: Web API测试"""
    report.start_phase("Phase 4: Web API")
    
    try:
        from ai_write_x.web.app import app
        report.test("FastAPI应用导入", True)
    except Exception as e:
        report.test("FastAPI应用导入", False, str(e))
    
    try:
        from ai_write_x.web.api.generate import router
        report.test("生成API路由", True)
    except Exception as e:
        report.test("生成API路由", False, str(e))


def test_phase5_scrapers():
    """Phase 5: 爬虫系统测试"""
    report.start_phase("Phase 5: 爬虫系统")
    
    try:
        from ai_write_x.scrapers.base import BaseSpider
        report.test("BaseSpider基类", True)
    except Exception as e:
        report.test("BaseSpider基类", False, str(e))
    
    try:
        from ai_write_x.tools.spider_runner import SpiderRunner
        runner = SpiderRunner()
        report.test("SpiderRunner", True)
    except Exception as e:
        report.test("SpiderRunner", False, str(e))


def test_phase6_tools():
    """Phase 6: 工具系统测试"""
    report.start_phase("Phase 6: 工具系统")
    
    try:
        from ai_write_x.tools.web_search import WebSearchTool
        report.test("WebSearchTool", True)
    except Exception as e:
        report.test("WebSearchTool", False, str(e))
    
    try:
        from ai_write_x.tools.hot_topics import HotTopicsTool
        report.test("HotTopicsTool", True)
    except Exception as e:
        report.test("HotTopicsTool", False, str(e))
    
    try:
        from ai_write_x.utils.utils import create_timestamp
        ts = create_timestamp()
        report.test("工具函数", ts is not None)
    except Exception as e:
        report.test("工具函数", False, str(e))


def test_phase7_main_entry():
    """Phase 7: 主程序入口测试"""
    report.start_phase("Phase 7: 主程序入口")
    
    try:
        import main
        report.test("main.py导入", True)
    except Exception as e:
        report.test("main.py导入", False, str(e))
    
    try:
        from ai_write_x.crew_main import WorkflowEngine
        report.test("CrewMain工作流引擎", True)
    except Exception as e:
        report.test("CrewMain工作流引擎", False, str(e))


def test_phase8_v17_features():
    """Phase 8: V17功能特性测试"""
    report.start_phase("Phase 8: V17功能特性")
    
    # 多模态
    try:
        from ai_write_x.core.multimodal_engine import get_multimodal_engine, ModalityType
        engine = get_multimodal_engine()
        
        async def test_multimodal():
            asset = await engine.generate("test", ModalityType.TEXT)
            return asset.status.value == "completed"
        
        result = asyncio.run(test_multimodal())
        report.test("多模态文本生成", result)
    except Exception as e:
        report.test("多模态文本生成", False, str(e))
    
    # 协作
    try:
        from ai_write_x.core.collaboration_hub import get_collaboration_hub
        hub = get_collaboration_hub()
        sid = hub.create_session("test_doc")
        report.test("协作会话创建", len(sid) > 0)
    except Exception as e:
        report.test("协作会话创建", False, str(e))
    
    # 检索
    try:
        from ai_write_x.core.cross_modal_retrieval import get_cross_modal_retrieval
        retrieval = get_cross_modal_retrieval()
        stats = retrieval.get_statistics()
        report.test("跨模态检索", "total_indexed" in stats)
    except Exception as e:
        report.test("跨模态检索", False, str(e))
    
    # 仪表盘
    try:
        from ai_write_x.core.intelligent_dashboard import get_intelligent_dashboard
        dashboard = get_intelligent_dashboard()
        dashboard.record_metric("test", 100)
        summary = dashboard.get_summary()
        report.test("智能仪表盘", "total_metrics" in summary)
    except Exception as e:
        report.test("智能仪表盘", False, str(e))
    
    # 工作流
    try:
        from ai_write_x.core.adaptive_workflow import get_adaptive_workflow
        engine = get_adaptive_workflow()
        
        async def test_workflow():
            wf_id = engine.create_workflow("test")
            def dummy():
                return 42
            engine.add_task(wf_id, "task1", dummy)
            result = await engine.execute_workflow(wf_id)
            return result["success"]
        
        result = asyncio.run(test_workflow())
        report.test("自适应工作流", result)
    except Exception as e:
        report.test("自适应工作流", False, str(e))


def run_all_tests():
    """运行所有测试"""
    print("\n" + "🧪 AIWriteX 全面功能测试".center(60, "="))
    
    try:
        test_phase1_core_engines()
    except Exception as e:
        print(f"Phase 1错误: {e}")
        import traceback
        traceback.print_exc()
    
    try:
        test_phase2_config()
    except Exception as e:
        print(f"Phase 2错误: {e}")
    
    try:
        test_phase3_database()
    except Exception as e:
        print(f"Phase 3错误: {e}")
    
    try:
        test_phase4_web_api()
    except Exception as e:
        print(f"Phase 4错误: {e}")
    
    try:
        test_phase5_scrapers()
    except Exception as e:
        print(f"Phase 5错误: {e}")
    
    try:
        test_phase6_tools()
    except Exception as e:
        print(f"Phase 6错误: {e}")
    
    try:
        test_phase7_main_entry()
    except Exception as e:
        print(f"Phase 7错误: {e}")
        import traceback
        traceback.print_exc()
    
    try:
        test_phase8_v17_features()
    except Exception as e:
        print(f"Phase 8错误: {e}")
        import traceback
        traceback.print_exc()
    
    return report.summary()


if __name__ == "__main__":
    import traceback
    try:
        success = run_all_tests()
        sys.exit(0 if success else 1)
    except Exception as e:
        print(f"\n测试运行失败: {e}")
        traceback.print_exc()
        sys.exit(1)
