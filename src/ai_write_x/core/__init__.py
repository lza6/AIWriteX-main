"""
AIWriteX Core 模块
"""
from src.ai_write_x.core.vector_db import (
    VectorDBManager,
    VectorDBType,
    get_vector_db_manager,
    SearchResult,
    VectorEntry
)
from src.ai_write_x.core.vector_db.vector_ops import (
    cosine_similarity,
    cosine_similarity_batch,
    euclidean_distance,
    euclidean_distance_batch,
    dot_product,
    normalize,
    normalize_batch,
    top_k_indices,
    search_knn,
    VectorIndex,
    is_rust_available
)
