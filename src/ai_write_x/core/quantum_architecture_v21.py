# -*- coding: UTF-8 -*-
"""
V21 量子增强架构 - Quantum Enhanced Architecture

核心理念:
1. 异步流式处理 - Stream-First Design
2. 边缘计算支持 - Edge Computing Ready
3. 事件驱动架构 - Event Sourcing + CQRS
4. 服务网格集成 - Service Mesh Compatible

版本：V21.0.0
作者：AIWriteX Team
创建日期：2026-03-10
"""

from typing import AsyncIterator, Callable, Dict, Any, Optional
from dataclasses import dataclass, field
from enum import Enum
import asyncio
import time
import json
import hashlib
from collections import defaultdict
import logging
from pathlib import Path

logger = logging.getLogger(__name__)


class EventType(Enum):
    """事件类型枚举"""
    REQUEST_RECEIVED = "request_received"
    PROCESSING_STARTED = "processing_started"
    CACHE_HIT = "cache_hit"
    CACHE_MISS = "cache_miss"
    BATCH_CREATED = "batch_created"
    RESPONSE_SENT = "response_sent"
    ERROR_OCCURRED = "error_occurred"
    PERFORMANCE_THRESHOLD_BREACHED = "performance_threshold_breached"


@dataclass
class DomainEvent:
    """领域事件基类"""
    event_id: str = field(default_factory=lambda: hashlib.md5(
        f"{time.time()}".encode()).hexdigest())
    event_type: EventType = EventType.REQUEST_RECEIVED
    aggregate_id: str = ""
    timestamp: float = field(default_factory=lambda: time.time())
    payload: Dict[str, Any] = field(default_factory=dict)
    metadata: Dict[str, Any] = field(default_factory=dict)


class EventStore:
    """
    事件存储 - Event Store

    特性:
    - 事件溯源 (Event Sourcing)
    - 不可变事件日志
    - 支持事件重放
    - CQRS 模式支持
    - SQLite 持久化 (可选)

    设计意图:
    - 内存为主存储保证性能
    - SQLite 异步持久化防止数据丢失
    - 滑动窗口自动清理控制内存占用
    """

    def __init__(self, max_events: int = 100000, persistence_path: Optional[str] = None):
        self.max_events = max_events
        self.persistence_path = persistence_path
        self._events: list[DomainEvent] = []
        self._subscribers: Dict[EventType, list[Callable]] = defaultdict(list)
        self._lock = asyncio.Lock()
        self._db_lock = asyncio.Lock()  # 数据库操作锁

        # 索引优化 - O(1) 查询支持
        self._index_by_aggregate: Dict[str, List[int]] = defaultdict(list)
        self._index_by_type: Dict[EventType, List[int]] = defaultdict(list)

        # 持久化配置
        self._persist_interval = 60  # 秒
        self._last_persist_time = time.time()
        self._pending_persist_count = 0

    async def append(self, event: DomainEvent):
        """追加事件到存储（带索引更新和持久化）"""
        async with self._lock:
            idx = len(self._events)
            self._events.append(event)

            # 更新索引 - O(1) 复杂度
            self._index_by_aggregate[event.aggregate_id].append(idx)
            self._index_by_type[event.event_type].append(idx)

            # 超过最大限制时，删除最旧的事件
            if len(self._events) > self.max_events:
                old_count = len(self._events)
                self._events = self._events[-self.max_events:]
                # 重建索引（简化处理，实际可增量更新）
                await self._rebuild_indexes()
                logger.info(f"事件滑动窗口清理：{old_count} -> {len(self._events)}")

            # 通知订阅者
            await self._notify_subscribers(event)

            # 触发持久化检查
            self._pending_persist_count += 1
            if self._should_persist():
                await self._persist_events_async()

    async def get_events(
        self,
        aggregate_id: Optional[str] = None,
        event_type: Optional[EventType] = None,
        from_timestamp: Optional[float] = None,
        limit: int = 100
    ) -> list[DomainEvent]:
        """查询事件（使用索引优化）"""
        # 优先使用索引加速查询
        candidate_idxs = None

        if aggregate_id and aggregate_id in self._index_by_aggregate:
            candidate_idxs = set(self._index_by_aggregate[aggregate_id])

        if event_type and event_type in self._index_by_type:
            type_idxs = set(self._index_by_type[event_type])
            candidate_idxs = type_idxs if candidate_idxs is None else candidate_idxs & type_idxs

        # 使用索引或全量扫描
        if candidate_idxs is not None and len(candidate_idxs) < len(self._events) * 0.5:
            # 索引覆盖率高时使用索引
            events = [self._events[i]
                      for i in sorted(candidate_idxs) if i < len(self._events)]
        else:
            # 否则全量扫描
            events = self._events

        # 应用过滤条件
        if aggregate_id:
            events = [e for e in events if e.aggregate_id == aggregate_id]
        if event_type:
            events = [e for e in events if e.event_type == event_type]
        if from_timestamp:
            events = [e for e in events if e.timestamp >= from_timestamp]

        return events[-limit:]

    def subscribe(self, event_type: EventType, callback: Callable):
        """订阅事件"""
        self._subscribers[event_type].append(callback)

    async def _notify_subscribers(self, event: DomainEvent):
        """通知订阅者"""
        for callback in self._subscribers.get(event.event_type, []):
            try:
                if asyncio.iscoroutinefunction(callback):
                    await callback(event)
                else:
                    callback(event)
            except Exception as e:
                logger.error(f"事件回调执行失败：{e}")

    def _should_persist(self) -> bool:
        """判断是否应该持久化"""
        if not self.persistence_path:
            return False

        time_since_last = time.time() - self._last_persist_time
        return (time_since_last >= self._persist_interval or
                self._pending_persist_count >= 100)

    async def _rebuild_indexes(self):
        """重建所有索引（滑动窗口清理后调用）"""
        self._index_by_aggregate.clear()
        self._index_by_type.clear()

        for idx, event in enumerate(self._events):
            self._index_by_aggregate[event.aggregate_id].append(idx)
            self._index_by_type[event.event_type].append(idx)

    async def _persist_events_async(self):
        """异步持久化事件到 SQLite"""
        if not self.persistence_path:
            return

        async with self._db_lock:
            try:
                import aiosqlite

                # 确保目录存在
                Path(self.persistence_path).parent.mkdir(
                    parents=True, exist_ok=True)

                async with aiosqlite.connect(self.persistence_path) as db:
                    # 创建表结构
                    await db.execute('''
                        CREATE TABLE IF NOT EXISTS events (
                            id INTEGER PRIMARY KEY AUTOINCREMENT,
                            event_id TEXT UNIQUE NOT NULL,
                            event_type TEXT NOT NULL,
                            aggregate_id TEXT NOT NULL,
                            timestamp REAL NOT NULL,
                            payload TEXT,
                            metadata TEXT,
                            created_at REAL DEFAULT (strftime('%s', 'now'))
                        )
                    ''')

                    # 创建索引加速查询
                    await db.execute('CREATE INDEX IF NOT EXISTS idx_aggregate ON events(aggregate_id)')
                    await db.execute('CREATE INDEX IF NOT EXISTS idx_type ON events(event_type)')
                    await db.execute('CREATE INDEX IF NOT EXISTS idx_timestamp ON events(timestamp)')

                    # 批量插入未持久化的事件
                    events_to_persist = self._events[-self._pending_persist_count:
                                                     ] if self._pending_persist_count > 0 else self._events[-100:]

                    insert_data = [
                        (
                            e.event_id,
                            e.event_type.value,
                            e.aggregate_id,
                            e.timestamp,
                            json.dumps(e.payload),
                            json.dumps(e.metadata)
                        )
                        for e in events_to_persist
                    ]

                    await db.executemany(
                        '''INSERT OR IGNORE INTO events
                           (event_id, event_type, aggregate_id, timestamp, payload, metadata) 
                           VALUES (?, ?, ?, ?, ?, ?)''',
                        insert_data
                    )

                    await db.commit()

                    # 清理旧数据，保持表大小可控
                    await db.execute(
                        'DELETE FROM events WHERE rowid NOT IN ('
                        'SELECT rowid FROM events ORDER BY timestamp DESC LIMIT ?)',
                        (self.max_events,)
                    )
                    await db.commit()

                self._last_persist_time = time.time()
                self._pending_persist_count = 0
                logger.info(f"事件持久化完成：{len(events_to_persist)} 条记录")

            except ImportError:
                logger.warning("aiosqlite 未安装，跳过事件持久化")
            except Exception as e:
                logger.error(f"事件持久化失败：{e}")
                print(f"事件持久化失败：{e}")
                raise e

    async def load_events_from_db(self):
        """从数据库加载历史事件"""
        if not self.persistence_path:
            return []

        try:
            import aiosqlite

            async with aiosqlite.connect(self.persistence_path) as db:
                async with db.execute(
                    'SELECT event_id, event_type, aggregate_id, timestamp, payload, metadata '
                    'FROM events ORDER BY timestamp DESC LIMIT ?',
                    (self.max_events,)
                ) as cursor:
                    rows = await cursor.fetchall()

                    loaded_events = []
                    for row in reversed(rows):  # 按时间正序
                        event = DomainEvent(
                            event_id=row[0],
                            event_type=EventType(row[1]),
                            aggregate_id=row[2],
                            timestamp=row[3],
                            payload=json.loads(row[4]) if row[4] else {},
                            metadata=json.loads(row[5]) if row[5] else {}
                        )
                        loaded_events.append(event)

                    return loaded_events

        except Exception as e:
            logger.error(f"加载历史事件失败：{e}")
            return []


class StreamProcessor:
    """
    流式处理器 - Stream Processor

    特性:
    - 背压控制 (Backpressure)
    - 流式转换
    - 并行处理
    - 错误恢复
    """

    def __init__(
        self,
        buffer_size: int = 1000,
        parallelism: int = 4,
        timeout_seconds: float = 30.0
    ):
        self.buffer_size = buffer_size
        self.parallelism = parallelism
        self.timeout_seconds = timeout_seconds
        self._queue: asyncio.Queue = asyncio.Queue(maxsize=buffer_size)
        self._processors: list[Callable] = []
        self._running = False
        self._stats = {
            'processed': 0,
            'dropped': 0,
            'errors': 0,
            'avg_latency_ms': 0.0
        }

    def add_processor(self, processor: Callable):
        """添加处理器"""
        self._processors.append(processor)

    async def start(self):
        """启动流式处理器"""
        self._running = True
        asyncio.create_task(self._process_loop())
        logger.info(
            f"[StreamProcessor] 流式处理器已启动 (parallelism={self.parallelism})")

    async def stop(self):
        """停止流式处理器"""
        self._running = False
        await self._queue.join()
        logger.info("[StreamProcessor] 流式处理器已停止")

    async def push(self, item: Any) -> bool:
        """推送数据项到流"""
        try:
            await asyncio.wait_for(
                self._queue.put(item),
                timeout=self.timeout_seconds
            )
            return True
        except asyncio.TimeoutError:
            self._stats['dropped'] += 1
            logger.warning(f"[StreamProcessor] 队列已满，丢弃数据项")
            return False

    async def _process_loop(self):
        """处理循环"""
        semaphore = asyncio.Semaphore(self.parallelism)

        while self._running:
            try:
                item = await self._queue.get()

                async def process_item(data):
                    async with semaphore:
                        await self._execute_processors(data)
                    self._queue.task_done()

                asyncio.create_task(process_item(item))

            except asyncio.CancelledError:
                break
            except Exception as e:
                self._stats['errors'] += 1
                logger.error(f"[StreamProcessor] 处理错误：{e}")

    async def _execute_processors(self, item: Any):
        """执行所有处理器"""
        start_time = time.time()

        try:
            result = item
            for processor in self._processors:
                if asyncio.iscoroutinefunction(processor):
                    result = await processor(result)
                else:
                    result = processor(result)

            # 更新统计
            elapsed = (time.time() - start_time) * 1000
            self._update_stats(elapsed)

            return result

        except Exception as e:
            self._stats['errors'] += 1
            logger.error(f"[StreamProcessor] 处理器执行失败：{e}")
            raise

    def _update_stats(self, latency_ms: float):
        """更新统计信息"""
        processed = self._stats['processed']
        avg = self._stats['avg_latency_ms']

        # 移动平均
        self._stats['processed'] += 1
        self._stats['avg_latency_ms'] = (
            avg * processed + latency_ms) / (processed + 1)

    def get_stats(self) -> Dict[str, Any]:
        """获取统计信息"""
        return {
            **self._stats,
            'queue_size': self._queue.qsize(),
            'is_running': self._running
        }


class EdgeComputingNode:
    """
    边缘计算节点 - Edge Computing Node

    特性:
    - 本地缓存优先
    - 离线处理能力
    - 自动同步到云端
    - 低延迟响应
    """

    def __init__(self, node_id: str, location: str = "default"):
        self.node_id = node_id
        self.location = location
        self._local_cache: Dict[str, Any] = {}
        self._pending_sync: list[Dict] = []
        self._connected_to_cloud = True
        self._latency_ms: float = 0.0

    async def execute(self, task: Dict[str, Any]) -> Any:
        """执行边缘计算任务"""
        start_time = time.time()

        # 检查本地缓存
        cache_key = self._generate_cache_key(task)
        if cache_key in self._local_cache:
            self._update_latency(time.time() - start_time)
            return self._local_cache[cache_key]

        # 本地执行
        if self._connected_to_cloud:
            result = await self._execute_with_cloud(task)
        else:
            result = await self._execute_locally(task)
            # 标记为待同步
            self._pending_sync.append({
                'task': task,
                'result': result,
                'timestamp': time.time()
            })

        # 写入本地缓存
        self._local_cache[cache_key] = result

        self._update_latency(time.time() - start_time)
        return result

    async def _execute_with_cloud(self, task: Dict) -> Any:
        """通过云端执行"""
        # 模拟云端调用
        await asyncio.sleep(0.01)  # 网络延迟
        return {'source': 'cloud', 'task_id': task.get('id')}

    async def _execute_locally(self, task: Dict) -> Any:
        """本地执行"""
        # 模拟本地计算
        await asyncio.sleep(0.001)
        return {'source': 'local', 'task_id': task.get('id')}

    def _generate_cache_key(self, task: Dict) -> str:
        """生成缓存键"""
        return hashlib.md5(json.dumps(task, sort_keys=True).encode()).hexdigest()

    def _update_latency(self, seconds: float):
        """更新延迟统计"""
        ms = seconds * 1000
        self._latency_ms = self._latency_ms * 0.9 + ms * 0.1

    async def sync_to_cloud(self):
        """同步待处理数据到云端"""
        if not self._pending_sync:
            return

        logger.info(f"[EdgeNode] 同步 {len(self._pending_sync)} 条记录到云端")

        # 批量同步
        batch = self._pending_sync[:100]
        self._pending_sync = self._pending_sync[100:]

        # 模拟云端同步
        await asyncio.sleep(0.05)

        logger.info(f"[EdgeNode] 同步完成")

    def get_stats(self) -> Dict[str, Any]:
        """获取节点统计"""
        return {
            'node_id': self.node_id,
            'location': self.location,
            'cache_size': len(self._local_cache),
            'pending_sync': len(self._pending_sync),
            'connected': self._connected_to_cloud,
            'avg_latency_ms': self._latency_ms
        }


class QuantumArchitecture:
    """
    V21 量子增强架构核心

    整合:
    - Event Sourcing
    - Stream Processing
    - Edge Computing
    - CQRS 模式
    """

    def __init__(self, config: Optional[Dict] = None):
        self.config = config or {}

        # 核心组件
        self.event_store = EventStore()
        self.stream_processor = StreamProcessor(
            buffer_size=self.config.get('buffer_size', 1000),
            parallelism=self.config.get('parallelism', 8)
        )

        # 边缘节点
        self.edge_nodes: Dict[str, EdgeComputingNode] = {}

        # CQRS - 命令端
        self.command_handlers: Dict[str, Callable] = {}

        # CQRS - 查询端
        self.query_handlers: Dict[str, Callable] = {}

        logger.info("[QuantumArchitecture] V21 量子增强架构初始化完成")

    def register_edge_node(self, node: EdgeComputingNode):
        """注册边缘节点"""
        self.edge_nodes[node.node_id] = node
        logger.info(
            f"[QuantumArchitecture] 边缘节点已注册：{node.node_id}@{node.location}")

    def register_command(self, command_name: str, handler: Callable):
        """注册命令处理器"""
        self.command_handlers[command_name] = handler

    def register_query(self, query_name: str, handler: Callable):
        """注册查询处理器"""
        self.query_handlers[query_name] = handler

    async def execute_command(self, command: Dict[str, Any]) -> Any:
        """执行命令 (CQRS Command Side)"""
        command_name = command.get('type')

        if command_name not in self.command_handlers:
            raise ValueError(f"未知命令：{command_name}")

        # 记录事件
        await self.event_store.append(DomainEvent(
            event_type=EventType.PROCESSING_STARTED,
            aggregate_id=command.get('aggregate_id', ''),
            payload=command
        ))

        # 执行命令
        handler = self.command_handlers[command_name]
        result = await handler(command)

        # 记录完成事件
        await self.event_store.append(DomainEvent(
            event_type=EventType.RESPONSE_SENT,
            aggregate_id=command.get('aggregate_id', ''),
            payload={'result': result}
        ))

        return result

    async def execute_query(self, query: Dict[str, Any]) -> Any:
        """执行查询 (CQRS Query Side)"""
        query_name = query.get('type')

        if query_name not in self.query_handlers:
            raise ValueError(f"未知查询：{query_name}")

        # 记录事件
        await self.event_store.append(DomainEvent(
            event_type=EventType.REQUEST_RECEIVED,
            aggregate_id=query.get('aggregate_id', ''),
            payload=query
        ))

        # 执行查询
        handler = self.query_handlers[query_name]
        result = await handler(query)

        return result

    async def start(self):
        """启动架构"""
        await self.stream_processor.start()

        # 启动边缘节点同步
        asyncio.create_task(self._edge_sync_loop())

        logger.info("[QuantumArchitecture] V21 量子增强架构已启动")

    async def stop(self):
        """停止架构"""
        await self.stream_processor.stop()
        logger.info("[QuantumArchitecture] V21 量子增强架构已停止")

    async def _edge_sync_loop(self):
        """边缘节点同步循环"""
        while True:
            try:
                await asyncio.sleep(60)  # 每分钟同步一次

                for node in self.edge_nodes.values():
                    await node.sync_to_cloud()

            except Exception as e:
                logger.error(f"[QuantumArchitecture] 边缘同步失败：{e}")

    def get_architecture_stats(self) -> Dict[str, Any]:
        """获取架构统计"""
        return {
            'event_store_size': len(self.event_store._events),
            'stream_processor': self.stream_processor.get_stats(),
            'edge_nodes': {
                node_id: node.get_stats()
                for node_id, node in self.edge_nodes.items()
            },
            'commands': list(self.command_handlers.keys()),
            'queries': list(self.query_handlers.keys())
        }


# 示例用法
if __name__ == "__main__":
    async def test_quantum_architecture():
        # 初始化架构
        arch = QuantumArchitecture({
            'buffer_size': 500,
            'parallelism': 4
        })

        # 注册边缘节点
        edge_node = EdgeComputingNode("edge-001", "beijing")
        arch.register_edge_node(edge_node)

        # 注册命令处理器
        async def create_article(command):
            await asyncio.sleep(0.01)
            return {'article_id': '123', 'status': 'created'}

        arch.register_command("CreateArticle", create_article)

        # 注册查询处理器
        async def get_article(query):
            await asyncio.sleep(0.005)
            return {'article_id': query['article_id'], 'title': 'Test'}

        arch.register_query("GetArticle", get_article)

        # 启动
        await arch.start()

        # 执行命令
        result = await arch.execute_command({
            'type': 'CreateArticle',
            'aggregate_id': 'agg-001',
            'title': 'New Article'
        })
        print(f"命令执行结果：{result}")

        # 执行查询
        result = await arch.execute_query({
            'type': 'GetArticle',
            'aggregate_id': 'agg-002',
            'article_id': '123'
        })
        print(f"查询结果：{result}")

        # 查看统计
        stats = arch.get_architecture_stats()
        print(f"架构统计：{json.dumps(stats, indent=2)}")

        # 停止
        await arch.stop()

    asyncio.run(test_quantum_architecture())
