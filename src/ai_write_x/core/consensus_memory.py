import asyncio
from typing import Dict, List, Any, Optional
from datetime import datetime
import hashlib
import json

from src.ai_write_x.utils import log

class ConsensusMemory:
    """
    V18.0 共识记忆网络
    
    实现蜂群 Agent 之间的记忆同步与事实一致性：
    1. 分布式知识存储
    2. 冲突消解机制
    3. 记忆权重演化 (基于使用频率和准确度反馈)
    """
    
    def __init__(self):
        self.memories: Dict[str, Dict[str, Any]] = {}  # key -> {value, confidence, sources, last_update}
        self._lock = asyncio.Lock()

    async def commit_memory(self, key: str, value: Any, agent_id: str, confidence: float = 1.0):
        """Agent 提交一段记忆/知识点"""
        async with self._lock:
            if key in self.memories:
                existing = self.memories[key]
                # 冲突消解：加权合并或权重竞争
                # 简单实现：新提交若置信度更高则覆盖，否则作为来源记录
                if confidence > existing['confidence']:
                    existing['value'] = value
                    existing['confidence'] = confidence
                
                if agent_id not in existing['sources']:
                    existing['sources'].append(agent_id)
                existing['last_update'] = datetime.now()
            else:
                self.memories[key] = {
                    'value': value,
                    'confidence': confidence,
                    'sources': [agent_id],
                    'last_update': datetime.now()
                }
            
            log.print_log(f"[Swarm] 共识记忆更新: {key} | 来自: {agent_id} | 置信度: {confidence}", "info")

    async def query_memory(self, key: str) -> Optional[Any]:
        """查询共识记忆"""
        async with self._lock:
            data = self.memories.get(key)
            if data and data['confidence'] > 0.5:  # 只返回高置信度记忆
                return data['value']
            return None

    def get_topology_digest(self) -> str:
        """生成当前记忆网络的哈希摘要，用于蜂群同步校验"""
        mem_str = json.dumps(self.memories, sort_keys=True, default=str)
        return hashlib.sha256(mem_str.encode()).hexdigest()
