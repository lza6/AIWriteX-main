"""
向量数据库测试
"""
import asyncio
import sys
sys.path.insert(0, 'C:/Users/Administrator.DESKTOP-EGNE9ND/Desktop/AIxs/AIWriteX-main')

from src.ai_write_x.core.vector_db import (
    VectorDBManager, VectorDBType, get_vector_db_manager
)
from src.ai_write_x.core.vector_db.vector_ops import (
    cosine_similarity, cosine_similarity_batch,
    euclidean_distance, euclidean_distance_batch,
    dot_product, normalize, normalize_batch,
    top_k_indices, search_knn, VectorIndex,
    is_rust_available
)


def test_vector_operations():
    """测试向量运算"""
    print("\n=== 测试向量运算 ===")
    
    # 测试余弦相似度
    a = [1.0, 0.0, 0.0]
    b = [1.0, 0.0, 0.0]
    c = [0.0, 1.0, 0.0]
    
    sim_ab = cosine_similarity(a, b)
    sim_ac = cosine_similarity(a, c)
    
    print(f"cos(a, b) = {sim_ab:.4f} (期望: 1.0)")
    print(f"cos(a, c) = {sim_ac:.4f} (期望: 0.0)")
    
    # 测试批量相似度
    vectors = [[1.0, 0.0, 0.0], [0.0, 1.0, 0.0], [0.707, 0.707, 0.0]]
    batch_scores = cosine_similarity_batch(a, vectors)
    print(f"批量相似度: {batch_scores}")
    
    # 测试欧氏距离
    dist = euclidean_distance(a, b)
    print(f"欧氏距离(a, b) = {dist:.4f}")
    
    # 测试归一化
    vec = [3.0, 4.0]
    normed = normalize(vec)
    print(f"归一化 {vec} -> {normed}")
    
    # 测试 Top-K
    scores = [0.1, 0.9, 0.5, 0.3, 0.8]
    top_k = top_k_indices(scores, 3)
    print(f"Top-3 索引: {top_k}")
    
    # 测试 KNN 搜索
    query = [1.0, 0.0, 0.0]
    vectors = [
        [1.0, 0.0, 0.0],
        [0.0, 1.0, 0.0],
        [0.707, 0.707, 0.0],
        [0.5, 0.5, 0.707]
    ]
    results = search_knn(query, vectors, 2, "cosine")
    print(f"KNN 结果: {results}")
    
    # 测试 VectorIndex
    index = VectorIndex(dimension=3)
    index.add("vec1", [1.0, 0.0, 0.0], {"text": "文档1"})
    index.add("vec2", [0.0, 1.0, 0.0], {"text": "文档2"})
    index.add("vec3", [0.707, 0.707, 0.0], {"text": "文档3"})
    
    search_results = index.search([1.0, 0.0, 0.0], 2)
    print(f"索引搜索结果: {search_results}")
    
    # 检查 Rust 是否可用
    print(f"\nRust 扩展可用: {is_rust_available()}")


async def test_vector_db_manager():
    """测试向量数据库管理器"""
    print("\n=== 测试向量数据库管理器 ===")
    
    manager = get_vector_db_manager()
    
    # 初始化 (不实际连接)
    manager.init(
        db_type=VectorDBType.MILVUS,
        dimension=768,
        collection_name="aiwritex_test",
        host="localhost"
    )
    
    print(f"管理器初始化完成")
    print(f"数据库类型: {VectorDBType.MILVUS.value}")
    
    stats = await manager.get_stats()
    print(f"统计信息: {stats}")


async def test_milvus_client():
    """测试 Milvus 客户端"""
    print("\n=== 测试 Milvus 客户端 ===")
    
    from src.ai_write_x.core.vector_db.milvus_client import MilvusClient
    
    client = MilvusClient(
        collection_name="test_collection",
        dimension=128,
        host="localhost",
        port=19530
    )
    
    connected = await client.connect()
    print(f"Milvus 连接状态: {connected}")
    
    if connected:
        # 创建集合
        await client.create_collection(dimension=128)
        
        # 插入测试数据
        from src.ai_write_x.core.vector_db import VectorEntry
        
        entries = [
            VectorEntry(
                id=f"vec_{i}",
                vector=[0.1 * i] * 128,
                payload={"text": f"测试文档 {i}"}
            )
            for i in range(10)
        ]
        
        ids = await client.insert(entries)
        print(f"插入 {len(ids)} 条向量")
        
        # 搜索
        results = await client.search([0.5] * 128, top_k=3)
        print(f"搜索结果: {len(results)} 条")
        for r in results:
            print(f"  - id={r.id}, score={r.score:.4f}")
        
        await client.disconnect()


async def test_pinecone_client():
    """测试 Pinecone 客户端"""
    print("\n=== 测试 Pinecone 客户端 ===")
    
    from src.ai_write_x.core.vector_db.pinecone_client import PineconeClient
    
    # 注意: 需要有效的 API Key
    client = PineconeClient(
        collection_name="test_collection",
        dimension=128,
        api_key="YOUR_API_KEY",  # 需要替换
        environment="us-west1-gcp"
    )
    
    connected = await client.connect()
    print(f"Pinecone 连接状态: {connected}")


def main():
    """主函数"""
    print("🧪 开始向量数据库测试...")
    
    # 测试向量运算
    test_vector_operations()
    
    # 测试管理器
    asyncio.run(test_vector_db_manager())
    
    # 测试 Milvus (需要 Milvus 服务运行)
    asyncio.run(test_milvus_client())
    
    # 测试 Pinecone (需要有效的 API Key)
    # asyncio.run(test_pinecone_client())
    
    print("\n🎉 测试完成!")


if __name__ == "__main__":
    main()