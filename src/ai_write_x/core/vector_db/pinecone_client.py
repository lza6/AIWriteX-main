"""
Pinecone 向量数据库客户端
支持十亿级向量检索
"""
from typing import Any, Dict, List, Optional
import asyncio

from src.ai_write_x.core.vector_db import (
    VectorDBBase, VectorEntry, SearchResult
)
from src.ai_write_x.utils import log


class PineconeClient(VectorDBBase):
    """Pinecone 向量数据库客户端"""
    
    def __init__(
        self,
        collection_name: str = "default",
        dimension: int = 768,
        metric_type: str = "COSINE",
        api_key: str = "",
        environment: str = "us-west1-gcp",
        pod_type: str = "p1",
        replicas: int = 1,
        shards: int = 1,
        **kwargs
    ):
        super().__init__(collection_name, dimension, metric_type)
        
        self.api_key = api_key
        self.environment = environment
        self.pod_type = pod_type
        self.replicas = replicas
        self.shards = shards
        
        self._index = None
        self._index_host = None
    
    async def connect(self) -> bool:
        """连接 Pinecone"""
        try:
            from pinecone import Pinecone
            
            # 初始化客户端
            self._client = Pinecone(api_key=self.api_key)
            
            # 获取或创建索引
            if self.collection_name in self._client.list_indexes().names():
                self._index = self._client.Index(self.collection_name)
                log.print_log(f"[Pinecone] 连接到现有索引: {self.collection_name}", "info")
            else:
                log.print_log(f"[Pinecone] 索引不存在: {self.collection_name}", "warning")
            
            self._connected = True
            return True
            
        except ImportError:
            log.print_log("[Pinecone] pinecone 未安装", "warning")
            return False
        except Exception as e:
            log.print_log(f"[Pinecone] 连接失败: {e}", "error")
            return False
    
    async def disconnect(self):
        """断开连接"""
        self._connected = False
        self._index = None
    
    async def create_collection(
        self,
        dimension: int = None,
        metric_type: str = "COSINE",
        index_type: str = "IVF_FLAT"
    ) -> bool:
        """创建索引"""
        try:
            from pinecone import ServerlessSpec, PodSpec
            
            dimension = dimension or self.dimension
            
            # 根据环境选择规格
            if "gcp" in self.environment:
                spec = ServerlessSpec(
                    cloud="gcp",
                    region=self.environment
                )
            elif "aws" in self.environment:
                spec = ServerlessSpec(
                    cloud="aws",
                    region=self.environment
                )
            else:
                # 使用 Pod 规格
                spec = PodSpec(
                    pod_type=self.pod_type,
                    replicas=self.replicas,
                    shards=self.shards
                )
            
            # 创建索引
            self._client.create_index(
                name=self.collection_name,
                dimension=dimension,
                metric=metric_type.lower(),
                spec=spec
            )
            
            # 等待索引就绪
            self._client.wait_for_index_ready(self.collection_name)
            
            self._index = self._client.Index(self.collection_name)
            
            log.print_log(f"[Pinecone] 索引已创建: {self.collection_name}", "info")
            return True
            
        except Exception as e:
            log.print_log(f"[Pinecone] 创建索引失败: {e}", "error")
            return False
    
    async def delete_collection(self) -> bool:
        """删除索引"""
        try:
            self._client.delete_index(self.collection_name)
            log.print_log(f"[Pinecone] 索引已删除: {self.collection_name}", "info")
            return True
        except Exception as e:
            log.print_log(f"[Pinecone] 删除索引失败: {e}", "error")
            return False
    
    async def insert(self, entries: List[VectorEntry]) -> List[str]:
        """插入向量"""
        try:
            if not self._index:
                await self.create_collection()
            
            # 准备数据
            vectors = []
            for entry in entries:
                vectors.append({
                    "id": entry.id,
                    "values": entry.vector,
                    "metadata": entry.payload
                })
            
            # 分批插入 (每批 1000 条)
            batch_size = 1000
            ids = []
            
            for i in range(0, len(vectors), batch_size):
                batch = vectors[i:i + batch_size]
                self._index.upsert(vectors=batch)
                ids.extend([v["id"] for v in batch])
            
            log.print_log(f"[Pinecone] 插入 {len(entries)} 条向量", "debug")
            return ids
            
        except Exception as e:
            log.print_log(f"[Pinecone] 插入失败: {e}", "error")
            return []
    
    async def search(
        self,
        query_vector: List[float],
        top_k: int = 10,
        filter_expr: str = None,
        output_fields: List[str] = None
    ) -> List[SearchResult]:
        """搜索向量"""
        try:
            if not self._index:
                return []
            
            # 准备查询参数
            query_params = {
                "top_k": top_k,
                "include_values": False,
                "include_metadata": True
            }
            
            # 添加过滤条件
            if filter_expr:
                # Pinecone 使用元数据过滤
                query_params["filter"] = self._parse_filter(filter_expr)
            
            # 添加输出字段
            if output_fields:
                query_params["include_metadata"] = "metadata" in output_fields
            
            # 执行搜索
            results = self._index.query(
                vector=query_vector,
                **query_params
            )
            
            # 解析结果
            search_results = []
            for match in results.get("matches", []):
                search_results.append(SearchResult(
                    id=match["id"],
                    score=match["score"],
                    payload=match.get("metadata", {})
                ))
            
            return search_results
            
        except Exception as e:
            log.print_log(f"[Pinecone] 搜索失败: {e}", "error")
            return []
    
    def _parse_filter(self, filter_expr: str) -> Dict:
        """解析过滤表达式"""
        # 简化实现：将简单表达式转为 Pinecone 格式
        # 例如: "status == 'active'" -> {"status": {"$eq": "active"}}
        import re
        
        # 简单解析
        match = re.match(r"(\w+)\s*==\s*'([^']+)'", filter_expr)
        if match:
            field, value = match.groups()
            return {field: {"$eq": value}}
        
        return {}
    
    async def delete(self, ids: List[str]) -> bool:
        """删除向量"""
        try:
            if not self._index:
                return False
            
            self._index.delete(ids=ids)
            
            log.print_log(f"[Pinecone] 删除 {len(ids)} 条向量", "debug")
            return True
            
        except Exception as e:
            log.print_log(f"[Pinecone] 删除失败: {e}", "error")
            return False
    
    async def get_by_id(self, id: str) -> Optional[VectorEntry]:
        """根据ID获取向量"""
        try:
            if not self._index:
                return None
            
            results = self._index.fetch(ids=[id])
            
            if id in results.vectors:
                vec = results.vectors[id]
                return VectorEntry(
                    id=id,
                    vector=vec.values,
                    payload=vec.metadata or {}
                )
            return None
            
        except Exception as e:
            log.print_log(f"[Pinecone] 查询失败: {e}", "error")
            return None
    
    async def upsert(self, entries: List[VectorEntry]) -> bool:
        """更新或插入"""
        try:
            await self.insert(entries)
            return True
        except Exception as e:
            log.print_log(f"[Pinecone] upsert 失败: {e}", "error")
            return False
    
    async def count(self) -> int:
        """获取向量数量"""
        try:
            if not self._index:
                return 0
            stats = self._index.describe_index_stats()
            return stats.get("total_vector_count", 0)
        except Exception as e:
            log.print_log(f"[Pinecone] count 失败: {e}", "error")
            return 0
    
    async def get_stats(self) -> Dict[str, Any]:
        """获取统计信息"""
        try:
            if not self._index:
                return {"status": "not connected"}
            
            stats = self._index.describe_index_stats()
            
            return {
                "collection": self.collection_name,
                "dimension": self.dimension,
                "metric_type": self.metric_type,
                "total_vectors": stats.get("total_vector_count", 0),
                "namespaces": list(stats.get("namespaces", {}).keys()),
                "connected": self._connected
            }
            
        except Exception as e:
            return {"error": str(e)}


# Pinecone 无服务器客户端 (Serverless)
class PineconeServerlessClient(PineconeClient):
    """Pinecone 无服务器客户端"""
    
    def __init__(
        self,
        collection_name: str = "default",
        dimension: int = 768,
        metric_type: str = "COSINE",
        api_key: str = "",
        cloud: str = "gcp",
        region: str = "us-west1",
        **kwargs
    ):
        super().__init__(
            collection_name=collection_name,
            dimension=dimension,
            metric_type=metric_type,
            api_key=api_key,
            environment=region,
            **kwargs
        )
        self.cloud = cloud
        self.region = region
    
    async def create_collection(
        self,
        dimension: int = None,
        metric_type: str = "COSINE",
        index_type: str = "IVF_FLAT"
    ) -> bool:
        """创建无服务器索引"""
        try:
            from pinecone import ServerlessSpec
            
            dimension = dimension or self.dimension
            
            spec = ServerlessSpec(
                cloud=self.cloud,
                region=self.region
            )
            
            self._client.create_index(
                name=self.collection_name,
                dimension=dimension,
                metric=metric_type.lower(),
                spec=spec
            )
            
            self._client.wait_for_index_ready(self.collection_name)
            self._index = self._client.Index(self.collection_name)
            
            log.print_log(f"[Pinecone Serverless] 索引已创建: {self.collection_name}", "info")
            return True
            
        except Exception as e:
            log.print_log(f"[Pinecone Serverless] 创建索引失败: {e}", "error")
            return False
