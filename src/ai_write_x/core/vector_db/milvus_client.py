"""
Milvus 向量数据库客户端
支持十亿级向量检索
"""
from typing import Any, Dict, List, Optional
import asyncio

from src.ai_write_x.core.vector_db import (
    VectorDBBase, VectorEntry, SearchResult
)
from src.ai_write_x.utils import log


class MilvusClient(VectorDBBase):
    """Milvus 向量数据库客户端"""
    
    def __init__(
        self,
        collection_name: str = "default",
        dimension: int = 768,
        metric_type: str = "COSINE",
        host: str = "localhost",
        port: int = 19530,
        user: str = "",
        password: str = "",
        index_type: str = "IVF_FLAT",
        nlist: int = 1024,
        nprobe: int = 16,
        use_ssl: bool = False,
        **kwargs
    ):
        super().__init__(collection_name, dimension, metric_type)
        
        self.host = host
        self.port = port
        self.user = user
        self.password = password
        self.index_type = index_type
        self.nlist = nlist
        self.nprobe = nprobe
        self.use_ssl = use_ssl
        
        self._client = None
        self._collection = None
    
    async def connect(self) -> bool:
        """连接 Milvus"""
        try:
            from pymilvus import connections, Collection
            
            # 连接 Milvus
            alias = f"milvus_{self.collection_name}"
            connections.connect(
                alias=alias,
                host=self.host,
                port=self.port,
                user=self.user,
                password=self.password,
                secure=self.use_ssl
            )
            
            self._client = Collection(self.collection_name, using=alias)
            self._connected = True
            
            log.print_log(f"[Milvus] 已连接到 {self.host}:{self.port}", "info")
            return True
            
        except ImportError:
            log.print_log("[Milvus] pymilvus 未安装", "warning")
            return False
        except Exception as e:
            log.print_log(f"[Milvus] 连接失败: {e}", "error")
            return False
    
    async def disconnect(self):
        """断开连接"""
        if self._client:
            try:
                from pymilvus import connections
                alias = f"milvus_{self.collection_name}"
                connections.disconnect(alias=alias)
            except Exception as e:
                log.print_log(f"[Milvus] 断开连接失败: {e}", "error")
            finally:
                self._connected = False
    
    async def create_collection(
        self,
        dimension: int = None,
        metric_type: str = "COSINE",
        index_type: str = "IVF_FLAT"
    ) -> bool:
        """创建集合"""
        try:
            from pymilvus import Collection, CollectionSchema, FieldSchema, DataType
            
            dimension = dimension or self.dimension
            
            # 定义字段
            fields = [
                FieldSchema(name="id", dtype=DataType.VARCHAR, max_length=256, is_primary=True),
                FieldSchema(name="vector", dtype=DataType.FLOAT_VECTOR, dim=dimension),
                FieldSchema(name="payload", dtype=DataType.JSON, is_nullable=True),
            ]
            
            # 创建 schema
            schema = CollectionSchema(fields=fields, description=f"AIWriteX {self.collection_name}")
            
            # 创建集合
            self._collection = Collection(
                name=self.collection_name,
                schema=schema,
                using=f"milvus_{self.collection_name}"
            )
            
            # 创建索引
            await self._create_index(index_type, metric_type)
            
            log.print_log(f"[Milvus] 集合 {self.collection_name} 已创建", "info")
            return True
            
        except Exception as e:
            log.print_log(f"[Milvus] 创建集合失败: {e}", "error")
            return False
    
    async def _create_index(self, index_type: str, metric_type: str):
        """创建索引"""
        from pymilvus import Index
        
        if index_type == "IVF_FLAT":
            index_params = {
                "index_type": "IVF_FLAT",
                "metric_type": metric_type,
                "params": {"nlist": self.nlist}
            }
        elif index_type == "HNSW":
            index_params = {
                "index_type": "HNSW",
                "metric_type": metric_type,
                "params": {"M": 16, "efConstruction": 256}
            }
        elif index_type == "DISKANN":
            index_params = {
                "index_type": "DISKANN",
                "metric_type": metric_type,
                "params": {}
            }
        else:
            index_params = {
                "index_type": "IVF_FLAT",
                "metric_type": metric_type,
                "params": {"nlist": self.nlist}
            }
        
        index = Index(self.collection_name, index_params)
        index.build()
        
        log.print_log(f"[Milvus] 索引已创建: {index_type}", "info")
    
    async def delete_collection(self) -> bool:
        """删除集合"""
        try:
            from pymilvus import Collection
            collection = Collection(self.collection_name, using=f"milvus_{self.collection_name}")
            collection.drop()
            log.print_log(f"[Milvus] 集合已删除: {self.collection_name}", "info")
            return True
        except Exception as e:
            log.print_log(f"[Milvus] 删除集合失败: {e}", "error")
            return False
    
    async def insert(self, entries: List[VectorEntry]) -> List[str]:
        """插入向量"""
        try:
            if not self._collection:
                await self.create_collection()
            
            # 准备数据
            ids = []
            vectors = []
            payloads = []
            
            for entry in entries:
                ids.append(entry.id)
                vectors.append(entry.vector)
                payloads.append(entry.payload)
            
            # 插入数据
            data = [ids, vectors, payloads]
            result = self._collection.insert(data)
            
            # 刷新
            self._collection.flush()
            
            log.print_log(f"[Milvus] 插入 {len(entries)} 条向量", "debug")
            return [str(r) for r in result.primary_keys]
            
        except Exception as e:
            log.print_log(f"[Milvus] 插入失败: {e}", "error")
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
            if not self._collection:
                return []
            
            # 加载集合到内存
            self._collection.load()
            
            # 搜索参数
            search_params = {
                "metric_type": self.metric_type,
                "params": {"nprobe": self.nprobe}
            }
            
            # 执行搜索
            results = self._collection.search(
                data=[query_vector],
                anns_field="vector",
                param=search_params,
                limit=top_k,
                expr=filter_expr,
                output_fields=output_fields or ["id", "payload"]
            )
            
            # 解析结果
            search_results = []
            for hits in results:
                for hit in hits:
                    search_results.append(SearchResult(
                        id=hit.entity.get("id"),
                        score=hit.distance,
                        payload=hit.entity.get("payload", {})
                    ))
            
            return search_results
            
        except Exception as e:
            log.print_log(f"[Milvus] 搜索失败: {e}", "error")
            return []
    
    async def delete(self, ids: List[str]) -> bool:
        """删除向量"""
        try:
            if not self._collection:
                return False
            
            # 构建删除表达式
            id_list = ",".join([f'"{id}"' for id in ids])
            expr = f'id in [{id_list}]'
            self._collection.delete(expr)
            self._collection.flush()
            
            log.print_log(f"[Milvus] 删除 {len(ids)} 条向量", "debug")
            return True
            
        except Exception as e:
            log.print_log(f"[Milvus] 删除失败: {e}", "error")
            return False
    
    async def get_by_id(self, id: str) -> Optional[VectorEntry]:
        """根据ID获取向量"""
        try:
            if not self._collection:
                return None
            
            results = self._collection.query(
                expr=f'id == "{id}"',
                output_fields=["id", "vector", "payload"]
            )
            
            if results:
                r = results[0]
                return VectorEntry(
                    id=r["id"],
                    vector=r["vector"],
                    payload=r.get("payload", {})
                )
            return None
            
        except Exception as e:
            log.print_log(f"[Milvus] 查询失败: {e}", "error")
            return None
    
    async def upsert(self, entries: List[VectorEntry]) -> bool:
        """更新或插入"""
        try:
            # 先删除
            ids = [e.id for e in entries]
            await self.delete(ids)
            
            # 再插入
            await self.insert(entries)
            
            return True
            
        except Exception as e:
            log.print_log(f"[Milvus] upsert 失败: {e}", "error")
            return False
    
    async def count(self) -> int:
        """获取向量数量"""
        try:
            if not self._collection:
                return 0
            return self._collection.num_entities
        except Exception as e:
            log.print_log(f"[Milvus] count 失败: {e}", "error")
            return 0
    
    async def get_stats(self) -> Dict[str, Any]:
        """获取统计信息"""
        try:
            if not self._collection:
                return {"status": "not connected"}
            
            return {
                "collection": self.collection_name,
                "dimension": self.dimension,
                "metric_type": self.metric_type,
                "index_type": self.index_type,
                "entities": self._collection.num_entities,
                "connected": self._connected
            }
            
        except Exception as e:
            return {"error": str(e)}


# 分布式 Milvus 集群客户端
class MilvusClusterClient(MilvusClient):
    """Milvus 分布式集群客户端"""
    
    def __init__(
        self,
        collection_name: str = "default",
        dimension: int = 768,
        metric_type: str = "COSINE",
        nodes: List[Dict[str, Any]] = None,
        **kwargs
    ):
        super().__init__(collection_name, dimension, metric_type, **kwargs)
        self.nodes = nodes or []
    
    async def connect(self) -> bool:
        """连接集群"""
        try:
            from pymilvus import connections, ClusterNode
            
            # 连接 root coord
            connections.connect(
                alias=f"cluster_{self.collection_name}",
                host=self.host,
                port=self.port,
                secure=self.use_ssl
            )
            
            self._connected = True
            
            log.print_log(f"[Milvus Cluster] 已连接到集群", "info")
            return True
            
        except Exception as e:
            log.print_log(f"[Milvus Cluster] 连接失败: {e}", "error")
            return False
