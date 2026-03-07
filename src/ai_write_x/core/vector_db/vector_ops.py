"""
PyO3 向量计算性能优化模块
提供高性能的向量相似度计算

使用方法:
1. 确保 Rust 编译完成: maturin develop
2. 或者使用预编译的 wheel
"""
import os
import sys
from typing import List, Optional
import numpy as np

# 尝试导入 Rust 扩展，如果失败则使用 Python 实现
_use_rust = False
_vector_ops = None

try:
    # 尝试导入 Rust 扩展
    from src.ai_write_x.core.vector_db import _vector_ops as _vector_ops
    _use_rust = True
except ImportError:
    # 使用纯 Python 实现
    _use_rust = False


def cosine_similarity(a: List[float], b: List[float]) -> float:
    """计算余弦相似度"""
    if _use_rust:
        return _vector_ops.cosine_similarity(a, b)
    
    # 纯 Python 实现
    dot_product = sum(x * y for x, y in zip(a, b))
    norm_a = sum(x * x for x in a) ** 0.5
    norm_b = sum(x * x for x in b) ** 0.5
    
    if norm_a == 0 or norm_b == 0:
        return 0.0
    
    return dot_product / (norm_a * norm_b)


def cosine_similarity_batch(query: List[float], vectors: List[List[float]]) -> List[float]:
    """批量计算余弦相似度"""
    if _use_rust:
        return _vector_ops.cosine_similarity_batch(query, vectors)
    
    # 纯 Python 实现
    query_norm = sum(x * x for x in query) ** 0.5
    if query_norm == 0:
        return [0.0] * len(vectors)
    
    results = []
    for vec in vectors:
        dot_product = sum(x * y for x, y in zip(query, vec))
        norm_b = sum(x * x for x in vec) ** 0.5
        if norm_b == 0:
            results.append(0.0)
        else:
            results.append(dot_product / (query_norm * norm_b))
    
    return results


def euclidean_distance(a: List[float], b: List[float]) -> float:
    """计算欧氏距离"""
    if _use_rust:
        return _vector_ops.euclidean_distance(a, b)
    
    # 纯 Python 实现
    return sum((x - y) ** 2 for x, y in zip(a, b)) ** 0.5


def euclidean_distance_batch(query: List[float], vectors: List[List[float]]) -> List[float]:
    """批量计算欧氏距离"""
    if _use_rust:
        return _vector_ops.euclidean_distance_batch(query, vectors)
    
    # 纯 Python 实现
    results = []
    for vec in vectors:
        dist = sum((x - y) ** 2 for x, y in zip(query, vec)) ** 0.5
        results.append(dist)
    
    return results


def dot_product(a: List[float], b: List[float]) -> float:
    """计算点积"""
    if _use_rust:
        return _vector_ops.dot_product(a, b)
    
    return sum(x * y for x, y in zip(a, b))


def normalize(vector: List[float]) -> List[float]:
    """归一化向量"""
    if _use_rust:
        return _vector_ops.normalize(vector)
    
    # 纯 Python 实现
    norm = sum(x * x for x in vector) ** 0.5
    if norm == 0:
        return vector
    
    return [x / norm for x in vector]


def normalize_batch(vectors: List[List[float]]) -> List[List[float]]:
    """批量归一化向量"""
    if _use_rust:
        return _vector_ops.normalize_batch(vectors)
    
    # 纯 Python 实现
    results = []
    for vec in vectors:
        results.append(normalize(vec))
    
    return results


def vector_mean(vectors: List[List[float]]) -> List[float]:
    """计算向量均值"""
    if not vectors:
        return []
    
    dim = len(vectors[0])
    result = [0.0] * dim
    
    for vec in vectors:
        for i, v in enumerate(vec):
            result[i] += v
    
    count = len(vectors)
    return [x / count for x in result]


def top_k_indices(scores: List[float], k: int) -> List[int]:
    """获取 Top-K 索引"""
    if _use_rust:
        return _vector_ops.top_k_indices(scores, k)
    
    # 纯 Python 实现
    indexed = [(i, s) for i, s in enumerate(scores)]
    indexed.sort(key=lambda x: x[1], reverse=True)
    return [i for i, _ in indexed[:k]]


def search_knn(
    query: List[float],
    vectors: List[List[float]],
    k: int,
    metric: str = "cosine"
) -> List[tuple]:
    """
    K近邻搜索
    
    返回: [(index, score), ...]
    """
    if metric == "cosine":
        scores = cosine_similarity_batch(query, vectors)
    elif metric == "euclidean":
        # 距离转相似度
        distances = euclidean_distance_batch(query, vectors)
        scores = [1.0 / (1.0 + d) for d in distances]
    else:
        raise ValueError(f"Unknown metric: {metric}")
    
    # 获取 Top-K
    k = min(k, len(scores))
    top_k = top_k_indices(scores, k)
    
    return [(i, scores[i]) for i in top_k]


def compute_centroid(vectors: List[List[float]], labels: List[int], num_clusters: int) -> List[List[float]]:
    """计算每个聚类的质心"""
    centroids = [[0.0] * len(vectors[0]) for _ in range(num_clusters)]
    counts = [0] * num_clusters
    
    for vec, label in zip(vectors, labels):
        for i, v in enumerate(vec):
            centroids[label][i] += v
        counts[label] += 1
    
    # 平均
    for i in range(num_clusters):
        if counts[i] > 0:
            centroids[i] = [x / counts[i] for x in centroids[i]]
    
    return centroids


class VectorIndex:
    """向量索引 - 用于本地快速检索"""
    
    def __init__(self, dimension: int = 768, metric: str = "cosine"):
        self.dimension = dimension
        self.metric = metric
        self.vectors: List[List[float]] = []
        self.ids: List[str] = []
        self.metadata: List[dict] = []
    
    def add(self, id: str, vector: List[float], metadata: dict = None):
        """添加向量"""
        self.ids.append(id)
        self.vectors.append(vector)
        self.metadata.append(metadata or {})
    
    def search(self, query: List[float], top_k: int = 10) -> List[dict]:
        """搜索"""
        results = search_knn(query, self.vectors, top_k, self.metric)
        
        output = []
        for idx, score in results:
            output.append({
                "id": self.ids[idx],
                "score": score,
                "metadata": self.metadata[idx]
            })
        
        return output
    
    def save(self, path: str):
        """保存索引"""
        import pickle
        with open(path, "wb") as f:
            pickle.dump({
                "dimension": self.dimension,
                "metric": self.metric,
                "ids": self.ids,
                "vectors": self.vectors,
                "metadata": self.metadata
            }, f)
    
    def load(self, path: str):
        """加载索引"""
        import pickle
        with open(path, "rb") as f:
            data = pickle.load(f)
            self.dimension = data["dimension"]
            self.metric = data["metric"]
            self.ids = data["ids"]
            self.vectors = data["vectors"]
            self.metadata = data["metadata"]
    
    def __len__(self):
        return len(self.vectors)


def is_rust_available() -> bool:
    """检查 Rust 扩展是否可用"""
    return _use_rust
