"""
Qdrant 向量数据库客户端 (简化版)
支持高性能分布式向量检索
"""
from typing import Any, Dict, List, Optional
from datetime import datetime

from src.ai_write_x.core.vector_db import (
    VectorDBBase, VectorEntry, SearchResult
)
from src.ai_write_x.utils import log


class QdrantClient(VectorDBBase):
    """Qdrant 向量数据库客户端"""

    def __init__(
        self,
        collection_name: str = "aiwritex",
        dimension: int = 768,
        metric_type: str = "Cosine",
        host: str = "localhost",
        port: int = 6333,
        grpc_port: int = 6334,
        api_key: str = None,
        https: bool = False,
        **kwargs
    ):
        super().__init__(collection_name, dimension, metric_type.upper())

        self.host = host
        self.port = port
        self.grpc_port = grpc_port
        self.api_key = api_key
        self.https = https
        
        self._client = None
        self._async_client = None
        self._collection_exists = False
    
    async def connect(self) -> bool:
        """连接到 Qdrant 服务器"""
        try:
            from qdrant_client import QdrantClient, AsyncQdrantClient
            
            # 同步客户端
            if self.https:
                self._client = QdrantClient(
                    url=f"https://{self.host}:{self.port}",
                    api_key=self.api_key,
                    timeout=60
                )
            else:
                self._client = QdrantClient(
                    host=self.host,
                    port=self.port,
                    timeout=60
                )
            
            # 异步客户端
            if self.https:
                self._async_client = AsyncQdrantClient(
                    url=f"https://{self.host}:{self.port}",
                    api_key=self.api_key,
                    timeout=60
                )
            else:
                self._async_client = AsyncQdrantClient(
                    host=self.host,
                    port=self.port,
                    timeout=60
                )
            
            # 测试连接
            await self._async_client.get_collections()
            
            self._connected = True
            log.print_log(
                f"[Qdrant] 已连接到 {self.host}:{self.port}",
                "success"
            )
            return True
            
        except ImportError as e:
            log.print_log(f"[Qdrant] qdrant-client 未安装：{e}", "warning")
            return False
        except Exception as e:
            log.print_log(f"[Qdrant] 连接失败：{e}", "error")
            return False
    
    async def disconnect(self):
        """断开连接"""
        if self._async_client:
            try:
                await self._async_client.close()
            except Exception as e:
                log.print_log(f"[Qdrant] 关闭异步客户端失败：{e}", "error")
        
        if self._client:
            try:
                self._client.close()
            except Exception as e:
                log.print_log(f"[Qdrant] 关闭同步客户端失败：{e}", "error")
        
        self._connected = False
        log.print_log("[Qdrant] 已断开连接", "info")
    
    async def create_collection(
        self,
        dimension: int = None,
        metric_type: str = None,
        **kwargs
    ) -> bool:
        """创建集合"""
        try:
            from qdrant_client.http.models import Distance, VectorParams
            
            dimension = dimension or self.dimension
            metric_type = metric_type or self.metric_type
            
            # 检查是否已存在
            collections = await self._async_client.get_collections()
            if self.collection_name in [col.name for col in collections.collections]:
                self._collection_exists = True
                log.print_log(f"[Qdrant] 集合 '{self.collection_name}' 已存在", "info")
                return True
            
            # 距离度量映射
            distance_map = {
                "COSINE": Distance.COSINE,
                "EUCLID": Distance.EUCLID,
                "DOT": Distance.DOT
            }
            distance = distance_map.get(metric_type.upper(), Distance.COSINE)
            
            # 创建集合
            await self._async_client.create_collection(
                collection_name=self.collection_name,
                vectors_config=VectorParams(size=dimension, distance=distance)
            )
            
            self._collection_exists = True
            log.print_log(
                f"[Qdrant] 集合 '{self.collection_name}' 创建成功 (dim={dimension})",
                "success"
            )
            return True
            
        except Exception as e:
            log.print_log(f"[Qdrant] 创建集合失败：{e}", "error")
            return False
    
    async def delete_collection(self) -> bool:
        """删除集合"""
        try:
            await self._async_client.delete_collection(self.collection_name)
            self._collection_exists = False
            log.print_log(f"[Qdrant] 集合 '{self.collection_name}' 已删除", "success")
            return True
        except Exception as e:
            log.print_log(f"[Qdrant] 删除集合失败：{e}", "error")
            return False
    
    async def insert(self, entries: List[VectorEntry]) -> List[str]:
        """插入向量"""
        if not self._async_client:
            raise RuntimeError("[Qdrant] 客户端未连接")
        
        if not self._collection_exists:
            await self.create_collection()
        
        try:
            from qdrant_client.http.models import PointStruct
            
            points = []
            ids = []
            
            for entry in entries:
                point = PointStruct(
                    id=entry.id,
                    vector=entry.vector,
                    payload=entry.payload or {}
                )
                points.append(point)
                ids.append(entry.id)
            
            # 批量上传
            await self._async_client.upsert(
                collection_name=self.collection_name,
                points=points,
                wait=True
            )
            
            log.print_log(f"[Qdrant] 成功插入 {len(points)} 个向量", "info")
            return ids
            
        except Exception as e:
            log.print_log(f"[Qdrant] 插入向量失败：{e}", "error")
            return []
    
    async def search(
        self,
        query_vector: List[float],
        top_k: int = 10,
        filter_expr: str = None,
        **kwargs
    ) -> List[SearchResult]:
        """搜索相似向量"""
        if not self._async_client:
            raise RuntimeError("[Qdrant] 客户端未连接")
        
        try:
            from qdrant_client.http.models import Filter, FieldCondition, MatchValue
            
            # 构建过滤器
            scroll_filter = None
            if filter_expr:
                conditions = []
                for condition in filter_expr.split(" AND "):
                    if "=" in condition:
                        key, value = condition.split("=", 1)
                        conditions.append(
                            FieldCondition(
                                key=key.strip(),
                                match=MatchValue(value=value.strip())
                            )
                        )
                if conditions:
                    scroll_filter= Filter(must=conditions)
            
            # 执行搜索
            results = await self._async_client.search(
                collection_name=self.collection_name,
                query_vector=query_vector,
                limit=top_k,
                query_filter=scroll_filter,
                with_payload=True,
                with_vector=False
            )
            
            # 转换结果
            search_results = []
            for result in results:
                search_results.append(SearchResult(
                    id=str(result.id),
                    score=result.score,
                    payload=result.payload or {},
                    vector=None
                ))
            
            return search_results
            
        except Exception as e:
            log.print_log(f"[Qdrant] 搜索失败：{e}", "error")
            return []
    
    async def delete(self, ids: List[str]) -> bool:
        """删除向量"""
        if not self._async_client:
            raise RuntimeError("[Qdrant] 客户端未连接")
        
        try:
            from qdrant_client.http.models import PointIdsList
            
            await self._async_client.delete(
                collection_name=self.collection_name,
                points=PointIdsList(points=ids)
            )
            
            log.print_log(f"[Qdrant] 成功删除 {len(ids)} 个向量", "info")
            return True
            
        except Exception as e:
            log.print_log(f"[Qdrant] 删除向量失败：{e}", "error")
            return False
    
    async def get_by_id(self, id: str) -> Optional[VectorEntry]:
        """根据 ID 获取向量"""
        if not self._async_client:
            raise RuntimeError("[Qdrant] 客户端未连接")
        
        try:
            records = await self._async_client.retrieve(
                collection_name=self.collection_name,
                ids=[id],
                with_payload=True,
                with_vector=True
            )
            
            if records and len(records) > 0:
                record = records[0]
                return VectorEntry(
                    id=str(record.id),
                    vector=record.vector,
                    payload=record.payload or {}
                )
            return None
            
        except Exception as e:
            log.print_log(f"[Qdrant] 获取向量失败：{e}", "error")
            return None
    
    async def upsert(self, entries: List[VectorEntry]) -> bool:
        """更新或插入"""
        ids = await self.insert(entries)
        return len(ids) == len(entries)
    
    async def count(self) -> int:
        """获取向量数量"""
        if not self._async_client:
            return 0
        try:
            count_result = await self._async_client.count(
                collection_name=self.collection_name
            )
            return count_result.count if count_result else 0
        except Exception:
            return 0
    
    async def get_stats(self) -> Dict[str, Any]:
        """获取统计信息"""
        if not self._async_client:
            return {"status": "not connected"}
        
        try:
            info = await self._async_client.get_collection(self.collection_name)
            
            return {
                "status": "connected",
                "collection_name": self.collection_name,
                "vectors_count": info.points_count if hasattr(info, 'points_count') else 0,
                "dimension": info.config.params.vectors.size if hasattr(info.config.params.vectors, 'size') else self.dimension,
                "metric_type": str(info.config.params.vectors.distance),
                "timestamp": datetime.now().isoformat()
            }
        except Exception as e:
            return {
                "status": "error",
                "error": str(e),
                "collection_name": self.collection_name
            }
