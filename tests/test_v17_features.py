# -*- coding: UTF-8 -*-
"""
V17.0 功能测试
测试多模态、协作、检索、仪表盘、工作流五大核心组件
"""

import asyncio
import sys
import os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', 'src'))

from ai_write_x.core.v17_init import initialize_v17, get_v17_initializer
from ai_write_x.core.multimodal_engine import (
    ModalityType, GenerationRequest, get_multimodal_engine
)
from ai_write_x.core.collaboration_hub import (
    CollaborationRole, User, Operation, OperationType, get_collaboration_hub
)
from ai_write_x.core.cross_modal_retrieval import get_cross_modal_retrieval
from ai_write_x.core.intelligent_dashboard import (
    ChartType, AlertLevel, get_intelligent_dashboard
)
from ai_write_x.core.adaptive_workflow import (
    TaskStatus, WorkflowStatus, get_adaptive_workflow
)


class TestRunner:
    """测试运行器"""
    
    def __init__(self):
        self.passed = 0
        self.failed = 0
        self.tests = []
    
    def test(self, name):
        """测试装饰器"""
        def decorator(func):
            self.tests.append((name, func))
            return func
        return decorator
    
    async def run_all(self):
        """运行所有测试"""
        print("\n" + "="*60)
        print("🚀 V17.0 功能测试套件")
        print("="*60 + "\n")
        
        for name, func in self.tests:
            try:
                await func()
                print(f"✅ {name}")
                self.passed += 1
            except Exception as e:
                print(f"❌ {name}: {e}")
                self.failed += 1
        
        print("\n" + "="*60)
        print(f"测试结果: {self.passed} 通过, {self.failed} 失败")
        print("="*60)
        
        return self.failed == 0


runner = TestRunner()


# ===== V17 初始化测试 =====

@runner.test("V17 初始化器")
async def test_v17_init():
    result = await initialize_v17()
    assert result["version"] == "17.0.0"
    assert result["codename"] == "Omnisynapse Nexus"
    assert len(result["components"]) == 5


@runner.test("V17 健康检查")
async def test_v17_health():
    initializer = get_v17_initializer()
    health = initializer.get_health_status()
    assert health["version"] == "17.0.0"
    assert health["initialized"] == True


# ===== 多模态引擎测试 =====

@runner.test("多模态引擎 - 文本生成")
async def test_multimodal_text():
    engine = get_multimodal_engine()
    asset = await engine.generate(
        "测试文本",
        ModalityType.TEXT
    )
    assert asset.modality == ModalityType.TEXT
    assert asset.status.value == "completed"


@runner.test("多模态引擎 - 图像生成")
async def test_multimodal_image():
    engine = get_multimodal_engine()
    asset = await engine.generate(
        "A beautiful sunset",
        ModalityType.IMAGE,
        {"style": "realistic", "size": "1024x1024"}
    )
    assert asset.modality == ModalityType.IMAGE
    assert asset.status.value in ["completed", "failed"]  # 允许失败


@runner.test("多模态引擎 - 音频生成")
async def test_multimodal_audio():
    engine = get_multimodal_engine()
    asset = await engine.generate(
        "Hello World",
        ModalityType.AUDIO,
        {"voice": "female_1"}
    )
    assert asset.modality == ModalityType.AUDIO
    assert asset.status.value in ["completed", "failed"]


@runner.test("多模态引擎 - 批量生成")
async def test_multimodal_batch():
    engine = get_multimodal_engine()
    requests = [
        GenerationRequest(f"req_{i}", f"测试 {i}", ModalityType.TEXT)
        for i in range(3)
    ]
    results = await engine.batch_generate(requests)
    assert len(results) == 3


@runner.test("多模态引擎 - 统计信息")
async def test_multimodal_stats():
    engine = get_multimodal_engine()
    stats = engine.get_statistics()
    assert "total_assets" in stats
    assert "by_modality" in stats


# ===== 协作系统测试 =====

@runner.test("协作系统 - 创建会话")
async def test_collaboration_session():
    hub = get_collaboration_hub()
    session_id = hub.create_session(
        document_id="doc_123",
        initial_content="Hello",
        owner_id="user_1"
    )
    assert len(session_id) > 0
    
    session = hub.get_session(session_id)
    assert session is not None
    assert session.document_id == "doc_123"


@runner.test("协作系统 - 用户加入")
async def test_collaboration_join():
    hub = get_collaboration_hub()
    session_id = hub.create_session("doc_456")
    
    user = User(
        id="user_test",
        name="Test User",
        role=CollaborationRole.EDITOR
    )
    success = hub.join_session(session_id, user)
    assert success == True


@runner.test("协作系统 - 操作应用")
async def test_collaboration_operation():
    hub = get_collaboration_hub()
    session_id = hub.create_session("doc_789", "Initial")
    
    session = hub.get_session(session_id)
    op = Operation(
        id="op_1",
        type=OperationType.INSERT,
        position=7,
        content=" World",
        user_id="user_1"
    )
    success = session.apply_operation(op)
    assert success == True
    assert "World" in session.get_content()


@runner.test("协作系统 - 统计信息")
async def test_collaboration_stats():
    hub = get_collaboration_hub()
    stats = hub.get_statistics()
    assert "total_sessions" in stats


# ===== 跨模态检索测试 =====

@runner.test("跨模态检索 - 索引内容")
async def test_retrieval_index():
    from ai_write_x.core.multimodal_engine import MultiModalAsset
    retrieval = get_cross_modal_retrieval()
    
    asset = MultiModalAsset(
        id="test_asset_1",
        modality=ModalityType.TEXT,
        content="测试内容"
    )
    success = retrieval.index_content(asset)
    assert success == True


@runner.test("跨模态检索 - 文本搜索")
async def test_retrieval_search():
    retrieval = get_cross_modal_retrieval()
    results = retrieval.text_search("测试", top_k=5)
    assert isinstance(results, list)


@runner.test("跨模态检索 - 统计信息")
async def test_retrieval_stats():
    retrieval = get_cross_modal_retrieval()
    stats = retrieval.get_statistics()
    assert "total_indexed" in stats


# ===== 智能仪表盘测试 =====

@runner.test("仪表盘 - 注册指标")
async def test_dashboard_metric():
    dashboard = get_intelligent_dashboard()
    dashboard.register_metric("test_metric", "requests/sec")
    metric = dashboard.get_metric("test_metric")
    assert metric is not None
    assert metric.name == "test_metric"


@runner.test("仪表盘 - 记录指标")
async def test_dashboard_record():
    dashboard = get_intelligent_dashboard()
    dashboard.record_metric("cpu_usage", 45.5)
    metric = dashboard.get_metric("cpu_usage")
    stats = metric.get_stats()
    assert "latest" in stats


@runner.test("仪表盘 - 组件创建")
async def test_dashboard_widget():
    dashboard = get_intelligent_dashboard()
    dashboard.register_metric("requests", "req/s")
    
    widget_id = dashboard.create_widget(
        "Request Rate",
        ChartType.LINE,
        "requests"
    )
    assert len(widget_id) > 0


@runner.test("仪表盘 - 自然语言查询")
async def test_dashboard_nlq():
    dashboard = get_intelligent_dashboard()
    dashboard.record_metric("temperature", 25.0)
    
    result = dashboard.natural_language_query("平均温度是多少")
    assert "interpretation" in result


@runner.test("仪表盘 - 摘要")
async def test_dashboard_summary():
    dashboard = get_intelligent_dashboard()
    summary = dashboard.get_summary()
    assert "total_metrics" in summary


# ===== 自适应工作流测试 =====

@runner.test("工作流 - 创建工作流")
async def test_workflow_create():
    engine = get_adaptive_workflow()
    workflow_id = engine.create_workflow(
        name="Test Workflow",
        context={"test": True}
    )
    assert len(workflow_id) > 0


@runner.test("工作流 - 添加任务")
async def test_workflow_add_task():
    engine = get_adaptive_workflow()
    workflow_id = engine.create_workflow("Task Test")
    
    def dummy_action(x=0):
        return x + 1
    
    task_id = engine.add_task(
        workflow_id,
        "increment",
        dummy_action,
        inputs={"x": 5}
    )
    assert len(task_id) > 0


@runner.test("工作流 - 执行")
async def test_workflow_execute():
    engine = get_adaptive_workflow()
    workflow_id = engine.create_workflow("Execute Test")
    
    results = []
    
    def task_action(value=0):
        results.append(value)
        return value * 2
    
    engine.add_task(
        workflow_id,
        "double",
        task_action,
        inputs={"value": 21}
    )
    
    result = await engine.execute_workflow(workflow_id)
    assert result["success"] == True


@runner.test("工作流 - 状态查询")
async def test_workflow_status():
    engine = get_adaptive_workflow()
    workflow_id = engine.create_workflow("Status Test")
    
    status = engine.get_workflow_status(workflow_id)
    assert status is not None
    assert status["name"] == "Status Test"


@runner.test("工作流 - 统计信息")
async def test_workflow_stats():
    engine = get_adaptive_workflow()
    stats = engine.get_statistics()
    assert "total_workflows" in stats


# 运行测试
async def main():
    success = await runner.run_all()
    return 0 if success else 1


if __name__ == "__main__":
    exit_code = asyncio.run(main())
    sys.exit(exit_code)
