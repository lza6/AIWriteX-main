"""
向量数据库接口层 (Vector Database Interface)
支持 Milvus、Pinecone 等向量数据库
"""
from abc import ABC, abstractmethod
from typing import Any, Dict, List, Optional, Tuple
from dataclasses import dataclass
from enum import Enum
import numpy as np


class VectorDBType(str, Enum):
    """向量数据库类型"""
    MILVUS = "milvus"
    PINECONE = "pinecone"
    QDRANT = "qdrant"
    WEAVIATE = "weaviate"
    CHROMA = "chroma"


@dataclass
class SearchResult:
    """搜索结果"""
    id: str
    score: float
    payload: Dict[str, Any]
    vector: Optional[List[float]] = None


@dataclass
class VectorEntry:
    """向量条目"""
    id: str
    vector: List[float]
    payload: Dict[str, Any]


class VectorDBBase(ABC):
    """向量数据库基类"""
    
    def __init__(
        self,
        collection_name: str = "default",
        dimension: int = 768,
        metric_type: str = "COSINE",
        **kwargs
    ):
        self.collection_name = collection_name
        self.dimension = dimension
        self.metric_type = metric_type
        self._connected = False
    
    @abstractmethod
    async def connect(self) -> bool:
        """连接数据库"""
        pass
    
    @abstractmethod
    async def disconnect(self):
        """断开连接"""
        pass
    
    @abstractmethod
    async def create_collection(
        self,
        dimension: int = None,
        metric_type: str = "COSINE",
        index_type: str = "IVF_FLAT"
    ) -> bool:
        """创建集合"""
        pass
    
    @abstractmethod
    async def delete_collection(self) -> bool:
        """删除集合"""
        pass
    
    @abstractmethod
    async def insert(self, entries: List[VectorEntry]) -> List[str]:
        """插入向量"""
        pass
    
    @abstractmethod
    async def search(
        self,
        query_vector: List[float],
        top_k: int = 10,
        filter_expr: str = None,
        output_fields: List[str] = None
    ) -> List[SearchResult]:
        """搜索向量"""
        pass
    
    @abstractmethod
    async def delete(self, ids: List[str]) -> bool:
        """删除向量"""
        pass
    
    @abstractmethod
    async def get_by_id(self, id: str) -> Optional[VectorEntry]:
        """根据ID获取向量"""
        pass
    
    @abstractmethod
    async def upsert(self, entries: List[VectorEntry]) -> bool:
        """更新或插入"""
        pass
    
    @abstractmethod
    async def count(self) -> int:
        """获取向量数量"""
        pass
    
    @abstractmethod
    async def get_stats(self) -> Dict[str, Any]:
        """获取统计信息"""
        pass
    
    @property
    def is_connected(self) -> bool:
        return self._connected


class VectorDBFactory:
    """向量数据库工厂"""
    
    _clients: Dict[str, VectorDBBase] = {}
    
    @classmethod
    def create(
        cls,
        db_type: VectorDBType,
        **config
    ) -> VectorDBBase:
        """创建向量数据库客户端"""
        if db_type == VectorDBType.MILVUS:
            from src.ai_write_x.core.vector_db.milvus_client import MilvusClient
            return MilvusClient(**config)
        elif db_type == VectorDBType.PINECONE:
            from src.ai_write_x.core.vector_db.pinecone_client import PineconeClient
            return PineconeClient(**config)
        elif db_type == VectorDBType.QDRANT:
            from src.ai_write_x.core.vector_db.qdrant_client import QdrantClient
            return QdrantClient(**config)
        elif db_type == VectorDBType.WEAVIATE:
            from src.ai_write_x.core.vector_db.weaviate_client import WeaviateClient
            return WeaviateClient(**config)
        elif db_type == VectorDBType.CHROMA:
            from src.ai_write_x.core.vector_db.chroma_client import ChromaClient
            return ChromaClient(**config)
        else:
            raise ValueError(f"Unsupported vector DB type: {db_type}")
    
    @classmethod
    def get_client(
        cls,
        name: str = "default",
        db_type: VectorDBType = VectorDBType.MILVUS,
        **config
    ) -> VectorDBBase:
        """获取或创建客户端实例"""
        key = f"{db_type.value}:{name}"
        if key not in cls._clients:
            cls._clients[key] = cls.create(db_type, **config)
        return cls._clients[key]
    
    @classmethod
    def clear(cls):
        """清除所有客户端"""
        cls._clients.clear()


# 全局向量数据库管理器
class VectorDBManager:
    """向量数据库管理器 - 统一接口"""
    
    def __init__(self):
        self._db: Optional[VectorDBBase] = None
        self._fallback_enabled = True
    
    def init(
        self,
        db_type: VectorDBType = VectorDBType.MILVUS,
        dimension: int = 768,
        collection_name: str = "aiwritex",
        **config
    ):
        """初始化向量数据库"""
        self._db = VectorDBFactory.create(
            db_type=db_type,
            collection_name=collection_name,
            dimension=dimension,
            **config
        )
    
    @property
    def db(self) -> Optional[VectorDBBase]:
        return self._db
    
    async def connect(self) -> bool:
        """连接数据库"""
        if self._db:
            return await self._db.connect()
        return False
    
    async def disconnect(self):
        """断开连接"""
        if self._db:
            await self._db.disconnect()
    
    async def add_vectors(
        self,
        vectors: List[List[float]],
        payloads: List[Dict[str, Any]],
        ids: List[str] = None
    ) -> List[str]:
        """添加向量"""
        if not self._db:
            return []
        
        entries = []
        for i, (vec, payload) in enumerate(zip(vectors, payloads)):
            entry_id = ids[i] if ids else f"vec_{i}"
            entries.append(VectorEntry(
                id=entry_id,
                vector=vec,
                payload=payload
            ))
        
        return await self._db.insert(entries)
    
    async def search_similar(
        self,
        query_vector: List[float],
        top_k: int = 10,
        filter_expr: str = None,
        min_score: float = 0.7
    ) -> List[SearchResult]:
        """搜索相似向量"""
        if not self._db:
            return []
        
        results = await self._db.search(
            query_vector=query_vector,
            top_k=top_k,
            filter_expr=filter_expr
        )
        
        # 过滤低分结果
        return [r for r in results if r.score >= min_score]
    
    async def delete_vectors(self, ids: List[str]) -> bool:
        """删除向量"""
        if not self._db:
            return False
        return await self._db.delete(ids)
    
    async def get_vector_count(self) -> int:
        """获取向量数量"""
        if not self._db:
            return 0
        return await self._db.count()
    
    async def get_stats(self) -> Dict[str, Any]:
        """获取统计"""
        if not self._db:
            return {"status": "not initialized"}
        return await self._db.get_stats()


# 全局实例
_vector_db_manager: Optional[VectorDBManager] = None


def get_vector_db_manager() -> VectorDBManager:
    """获取向量数据库管理器"""
    global _vector_db_manager
    if _vector_db_manager is None:
        _vector_db_manager = VectorDBManager()
    return _vector_db_manager
