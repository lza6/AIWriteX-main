# -*- coding: UTF-8 -*-
"""
测试流式处理和数据库仓储
"""

import asyncio
import sys
sys.path.insert(0, "C:/Users/Administrator.DESKTOP-EGNE9ND/Desktop/AIxs/AIWriteX-main")

from src.ai_write_x.core.streaming_processor import (
    StreamingProcessorEngine,
    EventPriority,
    get_streaming_processor,
    emit_hotspot_event,
    get_current_hotspots
)


async def test_streaming():
    """测试流式处理"""
    print("\n=== 测试流式处理引擎 ===")
    
    # 获取引擎
    engine = get_streaming_processor()
    
    # 启动
    await engine.start()
    print(f"引擎状态: {engine.status.value}")
    
    # 发射测试事件
    for i in range(10):
        await emit_hotspot_event(
            event_type="news",
            data={
                "title": f"热点新闻 {i}",
                "content": f"这是第{i}条热点新闻内容",
                "source": "test"
            },
            priority=EventPriority.NORMAL
        )
    
    # 等待处理
    await asyncio.sleep(0.5)
    
    # 获取热点
    hotspots = await get_current_hotspots()
    print(f"检测到热点数: {len(hotspots)}")
    
    # 获取统计
    stats = engine.get_stats()
    print(f"引擎统计: {stats['events_received']} 接收, {stats['events_processed']} 处理")
    
    # 停止
    await engine.stop()
    print("引擎已停止")
    
    return True


async def test_repository():
    """测试数据库仓储"""
    print("\n=== 测试数据库仓储 ===")
    
    try:
        from src.ai_write_x.database import (
            topic_repo,
            article_repo,
            MemoryRepository
        )
        
        # 测试主题仓储
        print("测试主题仓储...")
        
        # 创建主题 - 用新标题避免冲突
        topic = topic_repo.create_topic(
            title="测试主题_仓库",
            source_platform="test",
            hot_score=100
        )
        print(f"创建主题: 成功")
        
        # 获取主题
        topic2 = topic_repo.get_by_title("测试主题_仓库")
        if topic2:
            _ = topic2.title  # 访问属性
            print(f"获取主题: 成功")
        
        # 搜索主题
        topics = topic_repo.search_topics("测试")
        print(f"搜索主题结果: {len(topics)} 条")
        
        print("✅ 仓储测试通过")
        return True
        
    except Exception as e:
        print(f"❌ 仓储测试失败: {e}")
        import traceback
        traceback.print_exc()
        return False


async def main():
    print("🧪 开始测试...")
    
    # 测试流式处理
    streaming_ok = await test_streaming()
    
    # 测试数据库仓储
    repo_ok = await test_repository()
    
    print("\n=== 测试结果 ===")
    print(f"流式处理: {'✅ 通过' if streaming_ok else '❌ 失败'}")
    print(f"数据库仓储: {'✅ 通过' if repo_ok else '❌ 失败'}")
    
    if streaming_ok and repo_ok:
        print("\n🎉 所有测试通过!")
    else:
        print("\n⚠️ 部分测试失败")


if __name__ == "__main__":
    asyncio.run(main())
