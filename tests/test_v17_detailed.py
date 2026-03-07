# -*- coding: UTF-8 -*-
"""V17功能详细测试"""

import sys
import os
import asyncio

sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', 'src'))

print('='*60)
print('Phase 8: V17功能特性详细测试')
print('='*60)

# 1. 多模态引擎
print('\n📌 多模态引擎')
from ai_write_x.core.multimodal_engine import get_multimodal_engine, ModalityType

engine = get_multimodal_engine()

async def test_multimodal():
    # 文本生成
    asset = await engine.generate('测试文本', ModalityType.TEXT)
    print('   ✅ 文本生成:', asset.status.value)
    
    # 批量生成
    from ai_write_x.core.multimodal_engine import GenerationRequest
    requests = [GenerationRequest('r'+str(i), 'test '+str(i), ModalityType.TEXT) for i in range(3)]
    results = await engine.batch_generate(requests)
    print('   ✅ 批量生成:', len(results), '个结果')
    
    # 统计
    stats = engine.get_statistics()
    print('   ✅ 统计:', stats['total_assets'], '资源')

asyncio.run(test_multimodal())

# 2. 协作系统
print('\n📌 协作系统')
from ai_write_x.core.collaboration_hub import get_collaboration_hub, User, CollaborationRole, Operation, OperationType

hub = get_collaboration_hub()
session_id = hub.create_session('doc_123', 'Hello', 'user_1')
print('   ✅ 会话创建:', session_id[:8]+'...')

user = User(id='user_2', name='Test', role=CollaborationRole.EDITOR)
hub.join_session(session_id, user)
print('   ✅ 用户加入')

session = hub.get_session(session_id)
op = Operation(id='op1', type=OperationType.INSERT, position=5, content=' World', user_id='user_1')
session.apply_operation(op)
print('   ✅ 操作应用:', session.get_content())

# 3. 检索系统
print('\n📌 跨模态检索')
from ai_write_x.core.cross_modal_retrieval import get_cross_modal_retrieval
from ai_write_x.core.multimodal_engine import MultiModalAsset

retrieval = get_cross_modal_retrieval()
asset = MultiModalAsset(id='a1', modality=ModalityType.TEXT, content='测试内容')
retrieval.index_content(asset)
results = retrieval.text_search('测试', top_k=5)
print('   ✅ 搜索:', len(results), '结果')

# 4. 仪表盘
print('\n📌 智能仪表盘')
from ai_write_x.core.intelligent_dashboard import get_intelligent_dashboard, ChartType

dashboard = get_intelligent_dashboard()
dashboard.record_metric('cpu', 45.5)
dashboard.record_metric('memory', 78.2)
widget_id = dashboard.create_widget('CPU', ChartType.GAUGE, 'cpu')
result = dashboard.natural_language_query('最新指标')
print('   ✅ NLQ:', result['interpretation'])

# 5. 工作流
print('\n📌 自适应工作流')
from ai_write_x.core.adaptive_workflow import get_adaptive_workflow

async def test_workflow():
    engine = get_adaptive_workflow()
    wf_id = engine.create_workflow('Test')
    
    def task1(x=0):
        return x + 10
    
    engine.add_task(wf_id, 'add10', task1, {'x': 5})
    result = await engine.execute_workflow(wf_id)
    print('   ✅ 工作流执行: success=', result['success'])

asyncio.run(test_workflow())

print('\n' + '='*60)
print('V17功能测试完成!')
print('='*60)
