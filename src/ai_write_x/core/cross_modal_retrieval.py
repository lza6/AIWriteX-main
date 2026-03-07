# -*- coding: UTF-8 -*-
"""
V17.0 - Cross-Modal Retrieval (跨模态检索引擎)

支持文本、图像、音频、视频之间的语义检索：
1. 语义向量索引
2. 跨模态相似度计算
3. 统一检索接口
4. 多模态查询融合
"""

import json
import asyncio
import hashlib
from datetime import datetime
from typing import Dict, List, Optional, Union, Any, Tuple
from dataclasses import dataclass, field
from enum import Enum
import threading
from collections import defaultdict
import numpy as np

from ..utils import log
from .multimodal_engine import ModalityType, MultiModalAsset


@dataclass
class Embedding:
    """语义向量"""
    vector: np.ndarray
    modality: ModalityType
    content_id: str
    metadata: Dict[str, Any] = field(default_factory=dict)
    created_at: datetime = field(default_factory=datetime.now)
    
    def to_list(self) -> List[float]:
        """转换为列表"""
        return self.vector.tolist()
    
    @classmethod
    def from_list(cls, vector_list: List[float], **kwargs):
        """从列表创建"""
        return cls(vector=np.array(vector_list), **kwargs)


@dataclass
class RetrievalResult:
    """检索结果"""
    content_id: str
    modality: ModalityType
    content: Any
    similarity: float
    metadata: Dict[str, Any] = field(default_factory=dict)


class VectorIndex:
    """向量索引"""
    
    def __init__(self, dimension: int = 768):
        self.dimension = dimension
        self.embeddings: Dict[str, Embedding] = {}
        self.vectors: Optional[np.ndarray] = None
        self.ids: List[str] = []
        self._dirty = True
        self._lock = threading.Lock()
    
    def add(self, embedding: Embedding):
        """添加向量"""
        with self._lock:
            self.embeddings[embedding.content_id] = embedding
            self._dirty = True
    
    def remove(self, content_id: str):
        """移除向量"""
        with self._lock:
            if content_id in self.embeddings:
                del self.embeddings[content_id]
                self._dirty = True
    
    def _rebuild(self):
        """重建索引"""
        if not self._dirty or not self.embeddings:
            return
        
        self.ids = list(self.embeddings.keys())
        if self.ids:
            self.vectors = np.vstack([
                self.embeddings[eid].vector for eid in self.ids
            ])
        else:
            self.vectors = np.array([])
        
        self._dirty = False
    
    def search(
        self,
        query_vector: np.ndarray,
        top_k: int = 10,
        modality_filter: Optional[ModalityType] = None
    ) -> List[Tuple[str, float]]:
        """向量检索"""
        if not self.embeddings:
            return []
        
        with self._lock:
            self._rebuild()
            
            if self.vectors.size == 0:
                return []
            
            # 计算余弦相似度
            query_norm = query_vector / (np.linalg.norm(query_vector) + 1e-8)
            vectors_norm = self.vectors / (np.linalg.norm(self.vectors, axis=1, keepdims=True) + 1e-8)
            
            similarities = np.dot(vectors_norm, query_norm)
            
            # 模态过滤
            valid_indices = []
            for i, eid in enumerate(self.ids):
                if modality_filter is None or self.embeddings[eid].modality == modality_filter:
                    valid_indices.append(i)
            
            if not valid_indices:
                return []
            
            # 获取Top-K
            valid_sims = [(i, similarities[i]) for i in valid_indices]
            valid_sims.sort(key=lambda x: x[1], reverse=True)
            
            return [(self.ids[i], float(sim)) for i, sim in valid_sims[:top_k]]


class CrossModalEncoder:
    """跨模态编码器 - 将不同模态编码到统一语义空间"""
    
    def __init__(self, dimension: int = 768):
        self.dimension = dimension
        # 实际项目中应该加载CLIP等多模态模型
        log.print_log(f"[V17.0] 跨模态编码器初始化 (dim={dimension})", "info")
    
    def encode_text(self, text: str) -> np.ndarray:
        """编码文本"""
        # 简化实现 - 实际应该使用预训练模型
        # 使用哈希生成伪向量
        hash_val = hashlib.md5(text.encode()).hexdigest()
        np.random.seed(int(hash_val, 16) % (2**32))
        return np.random.randn(self.dimension).astype(np.float32)
    
    def encode_image(self, image_path: str) -> np.ndarray:
        """编码图像"""
        np.random.seed(hash(image_path) % (2**32))
        return np.random.randn(self.dimension).astype(np.float32)
    
    def encode_audio(self, audio_path: str) -> np.ndarray:
        """编码音频"""
        np.random.seed(hash(audio_path) % (2**32))
        return np.random.randn(self.dimension).astype(np.float32)
    
    def encode_video(self, video_path: str) -> np.ndarray:
        """编码视频"""
        np.random.seed(hash(video_path) % (2**32))
        return np.random.randn(self.dimension).astype(np.float32)


class CrossModalRetrieval:
    """
    V17.0 跨模态检索引擎
    
    实现文本、图像、音频、视频的统一语义检索。
    """
    
    _instance = None
    _lock = threading.Lock()
    
    def __new__(cls):
        with cls._lock:
            if cls._instance is None:
                cls._instance = super(CrossModalRetrieval, cls).__new__(cls)
                cls._instance._initialized = False
        return cls._instance
    
    def __init__(self):
        if self._initialized:
            return
        
        self._initialized = True
        
        # 编码器
        self.encoder = CrossModalEncoder(dimension=768)
        
        # 索引
        self.index = VectorIndex(dimension=768)
        
        # 内容存储
        self.contents: Dict[str, MultiModalAsset] = {}
        
        log.print_log("[V17.0] 🔍 Cross-Modal Retrieval (跨模态检索引擎) 已初始化", "success")
    
    def index_content(self, asset: MultiModalAsset) -> bool:
        """索引内容"""
        try:
            # 根据模态编码
            if asset.modality == ModalityType.TEXT:
                vector = self.encoder.encode_text(asset.content)
            elif asset.modality == ModalityType.IMAGE:
                vector = self.encoder.encode_image(str(asset.content))
            elif asset.modality == ModalityType.AUDIO:
                vector = self.encoder.encode_audio(str(asset.content))
            elif asset.modality == ModalityType.VIDEO:
                vector = self.encoder.encode_video(str(asset.content))
            else:
                return False
            
            # 创建嵌入
            embedding = Embedding(
                vector=vector,
                modality=asset.modality,
                content_id=asset.id,
                metadata=asset.metadata
            )
            
            # 添加到索引
            self.index.add(embedding)
            self.contents[asset.id] = asset
            
            return True
            
        except Exception as e:
            log.print_log(f"[V17.0] 索引失败: {e}", "error")
            return False
    
    def text_search(
        self,
        query: str,
        top_k: int = 10,
        target_modality: Optional[ModalityType] = None
    ) -> List[RetrievalResult]:
        """文本检索"""
        query_vector = self.encoder.encode_text(query)
        return self._vector_search(query_vector, top_k, target_modality)
    
    def image_search(
        self,
        image_path: str,
        top_k: int = 10,
        target_modality: Optional[ModalityType] = None
    ) -> List[RetrievalResult]:
        """以图搜图/搜其他"""
        query_vector = self.encoder.encode_image(image_path)
        return self._vector_search(query_vector, top_k, target_modality)
    
    def _vector_search(
        self,
        query_vector: np.ndarray,
        top_k: int,
        target_modality: Optional[ModalityType]
    ) -> List[RetrievalResult]:
        """向量检索"""
        results = self.index.search(query_vector, top_k, target_modality)
        
        retrieval_results = []
        for content_id, similarity in results:
            if content_id in self.contents:
                asset = self.contents[content_id]
                retrieval_results.append(RetrievalResult(
                    content_id=content_id,
                    modality=asset.modality,
                    content=asset.content,
                    similarity=similarity,
                    metadata=asset.metadata
                ))
        
        return retrieval_results
    
    def cross_modal_search(
        self,
        query_asset: MultiModalAsset,
        target_modality: ModalityType,
        top_k: int = 10
    ) -> List[RetrievalResult]:
        """跨模态检索"""
        # 将查询内容编码
        if query_asset.modality == ModalityType.TEXT:
            query_vector = self.encoder.encode_text(query_asset.content)
        elif query_asset.modality == ModalityType.IMAGE:
            query_vector = self.encoder.encode_image(str(query_asset.content))
        elif query_asset.modality == ModalityType.AUDIO:
            query_vector = self.encoder.encode_audio(str(query_asset.content))
        elif query_asset.modality == ModalityType.VIDEO:
            query_vector = self.encoder.encode_video(str(query_asset.content))
        else:
            return []
        
        return self._vector_search(query_vector, top_k, target_modality)
    
    def get_statistics(self) -> Dict[str, Any]:
        """获取统计信息"""
        return {
            "total_indexed": len(self.contents),
            "by_modality": {
                modality.value: len([
                    c for c in self.contents.values()
                    if c.modality == modality
                ])
                for modality in ModalityType
            }
        }


# 全局实例
_cross_modal_retrieval = None


def get_cross_modal_retrieval() -> CrossModalRetrieval:
    """获取跨模态检索全局实例"""
    global _cross_modal_retrieval
    if _cross_modal_retrieval is None:
        _cross_modal_retrieval = CrossModalRetrieval()
    return _cross_modal_retrieval
