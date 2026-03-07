# -*- coding: UTF-8 -*-
"""
记忆仓储 - Memory Repository
提供Agent记忆相关的数据库操作
"""

from typing import List, Optional, Dict, Any
from datetime import datetime, timedelta
from sqlmodel import select, and_, or_, desc, func

from src.ai_write_x.database import AgentMemory
from src.ai_write_x.database.repository.base import BaseRepository
from src.ai_write_x.core.exceptions import DatabaseError, RecordNotFoundError
from src.ai_write_x.utils import log


class MemoryRepository(BaseRepository[AgentMemory]):
    """记忆仓储"""
    
    @property
    def model(self) -> type[AgentMemory]:
        return AgentMemory
    
    def create_memory(
        self,
        agent_id: str,
        memory_type: str,
        content: str,
        metadata: Dict[str, Any] = None,
        **kwargs
    ) -> AgentMemory:
        """
        创建记忆
        """
        try:
            with self._get_session() as session:
                memory = AgentMemory(
                    agent_id=agent_id,
                    memory_type=memory_type,
                    content=content,
                    metadata=metadata,
                    **kwargs
                )
                session.add(memory)
                session.commit()
                session.refresh(memory)
                
                log.print_log(f"[MemoryRepository] 创建记忆: agent={agent_id}, type={memory_type}", "debug")
                return memory
        except DatabaseError:
            raise
        except Exception as e:
            log.print_log(f"[MemoryRepository] 创建记忆失败: {e}", "error")
            raise DatabaseError(f"创建记忆失败") from e
    
    def get_by_agent(
        self,
        agent_id: str,
        memory_type: str = None,
        limit: int = 50
    ) -> List[AgentMemory]:
        """
        获取Agent的记忆
        """
        try:
            with self._get_session() as session:
                statement = select(AgentMemory).where(AgentMemory.agent_id == agent_id)
                
                if memory_type:
                    statement = statement.where(AgentMemory.memory_type == memory_type)
                
                statement = statement.order_by(desc(AgentMemory.created_at)).limit(limit)
                return list(session.exec(statement).all())
        except DatabaseError:
            raise
        except Exception as e:
            log.print_log(f"[MemoryRepository] 获取记忆失败: {e}", "error")
            raise DatabaseError(f"获取记忆失败") from e
    
    def get_recent_memories(
        self,
        hours: int = 24,
        limit: int = 100
    ) -> List[AgentMemory]:
        """
        获取最近的记忆
        """
        try:
            with self._get_session() as session:
                cutoff = datetime.now() - timedelta(hours=hours)
                statement = (
                    select(AgentMemory)
                    .where(AgentMemory.created_at >= cutoff)
                    .order_by(desc(AgentMemory.created_at))
                    .limit(limit)
                )
                return list(session.exec(statement).all())
        except DatabaseError:
            raise
        except Exception as e:
            log.print_log(f"[MemoryRepository] 获取最近记忆失败: {e}", "error")
            raise DatabaseError(f"获取最近记忆失败") from e
    
    def search_memories(
        self,
        agent_id: str,
        keyword: str,
        limit: int = 20
    ) -> List[AgentMemory]:
        """
        搜索记忆
        """
        try:
            with self._get_session() as session:
                statement = (
                    select(AgentMemory)
                    .where(AgentMemory.agent_id == agent_id)
                    .where(AgentMemory.content.contains(keyword))
                    .order_by(desc(AgentMemory.created_at))
                    .limit(limit)
                )
                return list(session.exec(statement).all())
        except DatabaseError:
            raise
        except Exception as e:
            log.print_log(f"[MemoryRepository] 搜索记忆失败: {e}", "error")
            raise DatabaseError(f"搜索记忆失败") from e
    
    def get_statistics(self) -> Dict[str, Any]:
        """
        获取记忆统计
        """
        try:
            with self._get_session() as session:
                # 总数
                total_stmt = select(func.count(AgentMemory.id))
                total = session.exec(total_stmt).first() or 0
                
                # 按类型统计
                type_stmt = (
                    select(AgentMemory.memory_type, func.count(AgentMemory.id))
                    .group_by(AgentMemory.memory_type)
                )
                type_results = session.exec(type_stmt).all()
                by_type = {mtype: count for mtype, count in type_results}
                
                # 按Agent统计
                agent_stmt = (
                    select(AgentMemory.agent_id, func.count(AgentMemory.id))
                    .group_by(AgentMemory.agent_id)
                )
                agent_results = session.exec(agent_stmt).all()
                by_agent = {aid: count for aid, count in agent_results}
                
                return {
                    "total": total,
                    "by_type": by_type,
                    "by_agent": by_agent
                }
        except DatabaseError:
            raise
        except Exception as e:
            log.print_log(f"[MemoryRepository] 统计失败: {e}", "error")
            raise DatabaseError(f"获取记忆统计失败") from e
    
    def delete_by_agent(self, agent_id: str) -> int:
        """
        删除Agent的所有记忆
        """
        try:
            with self._get_session() as session:
                delete_stmt = AgentMemory.__table__.delete().where(
                    AgentMemory.agent_id == agent_id
                )
                result = session.exec(delete_stmt)
                session.commit()
                
                count = result.rowcount
                log.print_log(f"[MemoryRepository] 删除记忆: agent={agent_id}, count={count}", "debug")
                return count
        except DatabaseError:
            raise
        except Exception as e:
            log.print_log(f"[MemoryRepository] 删除记忆失败: {e}", "error")
            raise DatabaseError(f"删除记忆失败") from e
    
    def cleanup_old_memories(self, days: int = 30) -> int:
        """
        清理旧记忆
        """
        try:
            with self._get_session() as session:
                cutoff = datetime.now() - timedelta(days=days)
                
                delete_stmt = AgentMemory.__table__.delete().where(
                    AgentMemory.created_at < cutoff
                )
                result = session.exec(delete_stmt)
                session.commit()
                
                count = result.rowcount
                log.print_log(f"[MemoryRepository] 清理旧记忆: {count}条", "debug")
                return count
        except DatabaseError:
            raise
        except Exception as e:
            log.print_log(f"[MemoryRepository] 清理记忆失败: {e}", "error")
            raise DatabaseError(f"清理旧记忆失败") from e
