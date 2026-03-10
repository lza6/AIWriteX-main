"""
Qdrant 向量数据库客户端测试
测试 Qdrant 客户端的基本功能
"""
from src.ai_write_x.core.vector_db.qdrant_client import QdrantClient
from src.ai_write_x.core.vector_db import (
    VectorEntry, get_vector_db_manager, VectorDBType
)
import asyncio
import sys
sys.path.insert(
    0, 'C:/Users/Administrator.DESKTOP-EGNE9ND/Desktop/AIxs/AIWriteX-main')


async def test_qdrant_basic():
    """测试 Qdrant 基本功能"""
    print("\n=== Qdrant 基础功能测试 ===\n")
     
    # 1. 初始化客户端
    print("1. 初始化 Qdrant 客户端...")
    client = QdrantClient(
        host="localhost",
        port=6333,
        collection_name="test_aiwritex",
        dimension=768
    )
    print(f"   ✓ 客户端已创建：{client.collection_name}")
     
    # 2. 连接测试（需要运行中的 Qdrant 服务）
    print("\n2. 测试连接...")
    try:
        connected = await client.connect()
        if connected:
            print("   ✓ 连接成功")
        else:
            print("   ⚠ 连接失败（Qdrant 服务可能未启动）")
            print("   提示：使用 docker run -p 6333:6333 qdrant/qdrant 启动服务")
            return False
    except Exception as e:
        print(f"   ✗ 连接异常：{e}")
        print("   ⚠ Qdrant 服务可能未启动")
        return False
     
    # 3. 创建集合
    print("\n3. 创建集合...")
    try:
        created = await client.create_collection(dimension=768)
        if created:
            print("   ✓ 集合创建成功")
    except Exception as e:
        print(f"   ⚠ 集合创建异常：{e}")
     
    # 4. 插入测试数据
    print("\n4. 插入测试向量...")
    try:
        test_entries = [
            VectorEntry(
                id="doc_001",
                vector=[0.1] * 768,  # 模拟向量
                payload={"text": "测试文档 1", "category": "tech"}
            ),
            VectorEntry(
                id="doc_002",
                vector=[0.2] * 768,
                payload={"text": "测试文档 2", "category": "science"}
            ),
            VectorEntry(
                id="doc_003",
                vector=[0.15] * 768,
                payload={"text": "测试文档 3", "category": "tech"}
            )
        ]
         
        ids = await client.insert(test_entries)
        print(f"   ✓ 成功插入 {len(ids)} 个向量")
        print(f"   IDs: {ids}")
    except Exception as e:
        print(f"   ✗ 插入失败：{e}")
        return False
     
    # 5. 相似度搜索
    print("\n5. 相似度搜索测试...")
    try:
        query_vector = [0.12] * 768  # 接近 doc_001 和 doc_003
        results = await client.search(
            query_vector=query_vector,
            top_k=2
        )
         
        print(f"   ✓ 搜索到 {len(results)} 个结果:")
        for i, result in enumerate(results, 1):
            print(f"   {i}. ID={result.id}, Score={result.score:.4f}, " +
                    f"Category={result.payload.get('category', 'N/A')}")
    except Exception as e:
        print(f"   ✗ 搜索失败：{e}")
     
    # 6. 带过滤器的搜索
    print("\n6. 带过滤器的搜索测试...")
    try:
        results = await client.search(
            query_vector=query_vector,
            top_k=2,
            filter_expr="category=tech"
        )
         
        print(f"   ✓ 过滤搜索结果：{len(results)} 个 tech 类别结果")
        for result in results:
            print(f"   - ID={result.id}, Score={result.score:.4f}")
    except Exception as e:
        print(f"   ✗ 过滤搜索失败：{e}")
     
    # 7. 获取统计信息
    print("\n7. 获取统计信息...")
    try:
        stats = await client.get_stats()
        print(f"   ✓ 统计信息:")
        print(f"      - 集合名称：{stats.get('collection_name')}")
        print(f"      - 向量数量：{stats.get('vectors_count', 0)}")
        print(f"      - 维度：{stats.get('dimension')}")
        print(f"      - 度量类型：{stats.get('metric_type')}")
    except Exception as e:
        print(f"   ✗ 获取统计失败：{e}")
     
    # 8. 删除测试
    print("\n8. 删除向量测试...")
    try:
        deleted = await client.delete(["doc_001"])
        if deleted:
            print(f"   ✓ 成功删除 doc_001")
             
            # 验证删除
            remaining = await client.count()
            print(f"   - 剩余向量数：{remaining}")
    except Exception as e:
        print(f"   ✗ 删除失败：{e}")
     
    # 9. 清理：删除集合
    print("\n9. 清理测试集合...")
    try:
        deleted = await client.delete_collection()
        if deleted:
            print("   ✓ 集合已删除")
    except Exception as e:
        print(f"   ⚠ 删除集合异常：{e}")
     
    # 10. 断开连接
    print("\n10. 断开连接...")
    await client.disconnect()
    print("   ✓ 已断开连接")
     
    print("\n=== 测试完成 ===\n")
    return True


async def test_vector_db_manager():
    """测试向量数据库管理器（统一接口）"""
    print("\n=== 向量数据库管理器测试 ===\n")
     
    manager = get_vector_db_manager()
     
    # 初始化为 Qdrant
    print("1. 初始化为 Qdrant...")
    manager.init(
        db_type=VectorDBType.QDRANT,
        host="localhost",
        port=6333,
        dimension=768
    )
    print("   ✓ 管理器已初始化")
     
    # 连接
    print("\n2. 连接数据库...")
    try:
        connected = await manager.connect()
        if connected:
            print("   ✓ 连接成功")
        else:
            print("   ⚠ 连接失败")
    except Exception as e:
        print(f"   ✗ 连接异常：{e}")
     
    # 添加向量
    print("\n3. 批量添加向量...")
    try:
        vectors = [[0.1]*768, [0.2]*768, [0.3]*768]
        payloads = [
            {"text": "文档 A"},
            {"text": "文档 B"},
            {"text": "文档 C"}
        ]
         
        ids = await manager.add_vectors(vectors, payloads)
        print(f"   ✓ 添加了 {len(ids)} 个向量")
    except Exception as e:
        print(f"   ✗ 添加失败：{e}")
     
    # 搜索
    print("\n4. 相似度搜索...")
    try:
        results = await manager.search_similar(
            query_vector=[0.15]*768,
            top_k=2
        )
        print(f"   ✓ 找到 {len(results)} 个相似结果")
    except Exception as e:
        print(f"   ✗ 搜索失败：{e}")
     
    print("\n=== 管理器测试完成 ===\n")


async def main():
    """主测试函数"""
    print("=" * 60)
    print("AIWriteX V21.1 - Qdrant 向量数据库测试")
    print("=" * 60)
     
    # 测试 1: 基本功能
    basic_ok = await test_qdrant_basic()
     
    # 测试 2: 管理器接口
    if basic_ok:
        await test_vector_db_manager()
     
    print("\n" + "=" * 60)
    print("测试总结:")
    print("-" * 60)
    if basic_ok:
        print("✅ 所有测试通过！")
    else:
        print("⚠️  部分测试失败（可能是 Qdrant 服务未启动）")
        print("\n启动 Qdrant 服务:")
        print("  docker run -d -p 6333:6333 -p 6334:6334 qdrant/qdrant")
    print("=" * 60 + "\n")


if __name__ == "__main__":
    asyncio.run(main())
