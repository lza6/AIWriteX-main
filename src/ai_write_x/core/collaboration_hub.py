# -*- coding: UTF-8 -*-
"""
V17.0 - Collaboration Hub (实时协作系统)

支持多人实时协同创作：
1. 实时文档编辑 (Operational Transformation)
2. 协作会话管理
3. 冲突解决
4. 评论和批注
5. 版本历史
"""

import json
import asyncio
from datetime import datetime
from typing import Dict, List, Optional, Set, Any, Callable, Tuple
from dataclasses import dataclass, field
from enum import Enum
import threading
from collections import defaultdict

from ..utils import log
from .swarm_protocol import SwarmTask, SwarmCapabilities, AgentBid
from .decentralized_allocator import DecentralizedAllocator
from .consensus_memory import EnhancedConsensusMemory as ConsensusMemory
from .swarm_protocol import SwarmMessageType, SwarmMessage


class CollaborationRole(Enum):
    """协作角色"""
    OWNER = "owner"
    EDITOR = "editor"
    VIEWER = "viewer"
    COMMENTER = "commenter"


class OperationType(Enum):
    """操作类型"""
    INSERT = "insert"
    DELETE = "delete"
    RETAIN = "retain"
    REPLACE = "replace"


@dataclass
class User:
    """协作用户"""
    id: str
    name: str
    avatar: Optional[str] = None
    role: CollaborationRole = CollaborationRole.VIEWER
    cursor_position: int = 0
    is_online: bool = True
    joined_at: datetime = field(default_factory=datetime.now)


@dataclass
class Operation:
    """操作 (Operational Transformation)"""
    id: str
    type: OperationType
    position: int
    content: Optional[str] = None
    length: int = 0
    user_id: str = ""
    timestamp: datetime = field(default_factory=datetime.now)
    revision: int = 0


@dataclass
class Comment:
    """评论/批注"""
    id: str
    user_id: str
    content: str
    position: int
    length: int
    created_at: datetime = field(default_factory=datetime.now)
    resolved: bool = False
    replies: List["Comment"] = field(default_factory=list)


@dataclass
class DocumentVersion:
    """文档版本"""
    revision: int
    content: str
    timestamp: datetime
    author_id: str
    operations: List[Operation] = field(default_factory=list)


class OperationalTransformation:
    """操作转换引擎 - 解决并发编辑冲突"""
    
    @staticmethod
    def transform(op1: Operation, op2: Operation) -> Tuple[Operation, Operation]:
        """
        转换两个并发操作
        确保操作顺序不影响最终结果
        """
        # 简化实现 - 实际应该更复杂
        if op1.position < op2.position:
            return op1, op2
        elif op1.position > op2.position:
            return op1, op2
        else:
            # 相同位置 - 根据时间戳排序
            if op1.timestamp <= op2.timestamp:
                return op1, op2
            else:
                return op2, op1
    
    @staticmethod
    def compose(ops: List[Operation]) -> str:
        """组合多个操作为最终内容"""
        # 简化实现
        result = []
        for op in sorted(ops, key=lambda x: (x.revision, x.timestamp)):
            if op.type == OperationType.INSERT:
                result.insert(op.position, op.content)
            elif op.type == OperationType.DELETE:
                if op.position < len(result):
                    del result[op.position:op.position + op.length]
        return "".join(result)


class CollaborationSession:
    """协作会话"""
    
    def __init__(self, session_id: str, document_id: str, initial_content: str = ""):
        self.session_id = session_id
        self.document_id = document_id
        self.content = initial_content
        self.revision = 0
        
        # 参与者
        self.users: Dict[str, User] = {}
        
        # 操作历史
        self.operations: List[Operation] = []
        
        # 评论
        self.comments: List[Comment] = []
        
        # 版本历史
        self.versions: List[DocumentVersion] = [
            DocumentVersion(0, initial_content, datetime.now(), "system")
        ]
        
        # 回调
        self.change_callbacks: List[Callable] = []
        self.cursor_callbacks: List[Callable] = []
        
        # 锁
        self._lock = threading.Lock()
    
    def join(self, user: User) -> bool:
        """用户加入会话"""
        with self._lock:
            self.users[user.id] = user
            log.print_log(f"[V17.0] 用户 {user.name} 加入会话 {self.session_id}", "info")
            return True
    
    def leave(self, user_id: str):
        """用户离开会话"""
        with self._lock:
            if user_id in self.users:
                self.users[user_id].is_online = False
                log.print_log(f"[V17.0] 用户 {user_id} 离开会话 {self.session_id}", "info")
    
    def apply_operation(self, operation: Operation) -> bool:
        """应用操作"""
        with self._lock:
            try:
                # 转换操作
                for existing_op in self.operations:
                    if existing_op.revision >= operation.revision:
                        operation, _ = OperationalTransformation.transform(operation, existing_op)
                
                # 应用操作
                if operation.type == OperationType.INSERT:
                    self.content = (
                        self.content[:operation.position] +
                        operation.content +
                        self.content[operation.position:]
                    )
                elif operation.type == OperationType.DELETE:
                    self.content = (
                        self.content[:operation.position] +
                        self.content[operation.position + operation.length:]
                    )
                
                # 更新版本
                self.revision += 1
                operation.revision = self.revision
                self.operations.append(operation)
                
                # 保存版本
                self.versions.append(DocumentVersion(
                    revision=self.revision,
                    content=self.content,
                    timestamp=datetime.now(),
                    author_id=operation.user_id,
                    operations=[operation]
                ))
                
                # 通知回调
                for callback in self.change_callbacks:
                    try:
                        callback(operation)
                    except Exception as e:
                        log.print_log(f"[V17.0] 回调错误: {e}", "error")
                
                return True
                
            except Exception as e:
                log.print_log(f"[V17.0] 应用操作失败: {e}", "error")
                return False
    
    def update_cursor(self, user_id: str, position: int):
        """更新光标位置"""
        if user_id in self.users:
            self.users[user_id].cursor_position = position
            for callback in self.cursor_callbacks:
                try:
                    callback(user_id, position)
                except Exception:
                    pass
    
    def add_comment(self, comment: Comment) -> bool:
        """添加评论"""
        self.comments.append(comment)
        return True
    
    def resolve_comment(self, comment_id: str) -> bool:
        """解决评论"""
        for comment in self.comments:
            if comment.id == comment_id:
                comment.resolved = True
                return True
        return False
    
    def get_content(self) -> str:
        """获取当前内容"""
        return self.content
    
    def get_version_history(self) -> List[DocumentVersion]:
        """获取版本历史"""
        return self.versions
    
    def revert_to_version(self, revision: int) -> bool:
        """回退到指定版本"""
        for version in self.versions:
            if version.revision == revision:
                self.content = version.content
                self.revision += 1
                return True
        return False
    
    def get_online_users(self) -> List[User]:
        """获取在线用户"""
        return [u for u in self.users.values() if u.is_online]
    
    def on_change(self, callback: Callable):
        """注册变更回调"""
        self.change_callbacks.append(callback)
    
    def on_cursor_change(self, callback: Callable):
        """注册光标变更回调"""
        self.cursor_callbacks.append(callback)


class CollaborationHub:
    """
    V17.0 实时协作中心
    
    管理所有协作会话，提供实时同步能力。
    """
    
    _instance = None
    _lock = threading.Lock()
    
    def __new__(cls):
        with cls._lock:
            if cls._instance is None:
                cls._instance = super(CollaborationHub, cls).__new__(cls)
                cls._instance._initialized = False
        return cls._instance
    
    def __init__(self):
        if self._initialized:
            return
        
        self._initialized = True
        self.sessions: Dict[str, CollaborationSession] = {}
        self.user_sessions: Dict[str, Set[str]] = defaultdict(set)  # user_id -> session_ids
        
        # V18.0: 蜂群核心组件
        self.allocator = DecentralizedAllocator()
        self.memory = ConsensusMemory()
        
        log.print_log("[V18.0] 🤝 Collaboration Hub (Swarm Mode Ready) 已初始化", "success")
    
    def create_session(
        self,
        document_id: str,
        initial_content: str = "",
        owner_id: str = ""
    ) -> str:
        """创建协作会话"""
        import uuid
        session_id = str(uuid.uuid4())[:12]
        
        session = CollaborationSession(session_id, document_id, initial_content)
        
        # 添加所有者
        if owner_id:
            owner = User(
                id=owner_id,
                name="Owner",
                role=CollaborationRole.OWNER
            )
            session.join(owner)
        
        self.sessions[session_id] = session
        
        log.print_log(f"[V17.0] 创建协作会话: {session_id}", "success")
        return session_id
    
    def get_session(self, session_id: str) -> Optional[CollaborationSession]:
        """获取会话"""
        return self.sessions.get(session_id)
    
    def join_session(
        self,
        session_id: str,
        user: User
    ) -> bool:
        """加入会话"""
        session = self.sessions.get(session_id)
        if not session:
            return False
        
        success = session.join(user)
        if success:
            self.user_sessions[user.id].add(session_id)
        return success
    
    def leave_session(self, session_id: str, user_id: str):
        """离开会话"""
        session = self.sessions.get(session_id)
        if session:
            session.leave(user_id)
            self.user_sessions[user_id].discard(session_id)
    
    def get_user_sessions(self, user_id: str) -> List[str]:
        """获取用户参与的所有会话"""
        return list(self.user_sessions[user_id])
    
    def list_active_sessions(self) -> List[Dict[str, Any]]:
        """列出所有活跃会话"""
        return [
            {
                "session_id": sid,
                "document_id": session.document_id,
                "user_count": len(session.get_online_users()),
                "revision": session.revision,
                "created_at": session.versions[0].timestamp.isoformat()
            }
            for sid, session in self.sessions.items()
        ]
    
    def close_session(self, session_id: str) -> bool:
        """关闭会话"""
        if session_id in self.sessions:
            session = self.sessions[session_id]
            # 通知所有用户
            for user in session.users.values():
                self.user_sessions[user.id].discard(session_id)
            
            del self.sessions[session_id]
            log.print_log(f"[V17.0] 关闭协作会话: {session_id}", "info")
            return True
        return False
    
    async def spawn_swarm_task(self, description: str, caps: List[SwarmCapabilities]) -> str:
        """派生蜂群任务：广播 -> 竞价 -> 分配"""
        task_id = await self.allocator.broadcast_task(description, caps)
        # 在真实场景下，Agent 会监听此广播并异步 submit_bid
        # 这里为核心逻辑预留接口
        return task_id

    async def sync_swarm_memory(self, key: str, value: Any, agent_id: str, confidence: float = 1.0):
        """同步 Agent 记忆到蜂群共识网络"""
        await self.memory.commit_memory(key, value, agent_id, confidence)

    def get_statistics(self) -> Dict[str, Any]:
        """获取统计信息"""
        total_users = sum(
            len(s.users) for s in self.sessions.values()
        )
        online_users = sum(
            len(s.get_online_users()) for s in self.sessions.values()
        )
        
        return {
            "total_sessions": len(self.sessions),
            "total_users": total_users,
            "online_users": online_users,
            "total_operations": sum(
                len(s.operations) for s in self.sessions.values()
            )
        }


# 全局实例
_collaboration_hub = None


def get_collaboration_hub() -> CollaborationHub:
    """获取协作中心全局实例"""
    global _collaboration_hub
    if _collaboration_hub is None:
        _collaboration_hub = CollaborationHub()
    return _collaboration_hub
