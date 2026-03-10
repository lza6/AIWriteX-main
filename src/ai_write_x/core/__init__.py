"""
AIWriteX Core 模块
"""
# 使用相对导入，避免在直接运行时的导入问题
try:
    from .vector_db import (
        VectorDBManager,
        VectorDBType,
        get_vector_db_manager,
        SearchResult,
        VectorEntry
    )
    from .vector_db.vector_ops import (
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
except ImportError:
    # 如果相对导入失败，跳过这些导入（用于独立测试）
    pass

# V18 新增模块 - 使用延迟导入避免循环依赖
def get_collective_mind():
    """获取CollectiveMind实例（延迟导入）"""
    from .swarm_v2.collective_mind import CollectiveMind
    return CollectiveMind

def get_consensus_protocol():
    """获取ConsensusProtocol类（延迟导入）"""
    from .swarm_v2.consensus_protocol import ConsensusProtocol
    return ConsensusProtocol

def get_knowledge_organism():
    """获取KnowledgeOrganism类（延迟导入）"""
    from .swarm_v2.knowledge_organism import KnowledgeOrganism
    return KnowledgeOrganism

def get_self_healing():
    """获取SelfHealing类（延迟导入）"""
    from .swarm_v2.self_healing import SelfHealing
    return SelfHealing
