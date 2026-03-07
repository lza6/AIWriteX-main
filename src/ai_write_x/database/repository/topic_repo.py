# -*- coding: UTF-8 -*-
"""
主题仓储 - Topic Repository
提供主题相关的数据库操作
"""

from typing import List, Optional, Dict, Any
from datetime import datetime
from sqlmodel import select, and_, or_, desc

from src.ai_write_x.database import Topic, TopicStatus
from src.ai_write_x.database.repository.base import BaseRepository
from src.ai_write_x.core.exceptions import DatabaseError, RecordNotFoundError
from src.ai_write_x.utils import log


class TopicRepository(BaseRepository[Topic]):
    """主题仓储"""
    
    @property
    def model(self) -> type[Topic]:
        return Topic
    
    def _topic_to_dict(self, topic: Topic) -> Dict[str, Any]:
        """将Topic对象转换为字典"""
        if topic is None:
            return {}
        
        result = {}
        for col in Topic.__table__.columns:
            value = getattr(topic, col.name)
            # 处理枚举类型
            if isinstance(value, TopicStatus):
                value = value.value
            result[col.name] = value
        return result
    
    def _dict_to_topic(self, data: Dict[str, Any]) -> Topic:
        """从字典创建Topic对象"""
        # 过滤掉None值和不在模型中的键
        model_fields = {col.name for col in Topic.__table__.columns}
        filtered_data = {k: v for k, v in data.items() if k in model_fields}
        
        # 处理status字段
        if 'status' in filtered_data and isinstance(filtered_data['status'], str):
            filtered_data['status'] = TopicStatus(filtered_data['status'])
        
        return Topic(**filtered_data)
    
    def create_topic(
        self,
        title: str,
        source_platform: str = "unknown",
        hot_score: int = 0,
        **kwargs
    ) -> Topic:
        """
        创建主题
        """
        try:
            with self._get_session() as session:
                # 检查是否已存在
                statement = select(Topic).where(Topic.title == title)
                existing = session.exec(statement).first()
                
                if existing:
                    log.print_log(f"[TopicRepository] 主题已存在: {title}", "debug")
                    data = self._topic_to_dict(existing)
                    session.expunge(existing)
                    return self._dict_to_topic(data)
                
                # 创建新主题
                topic = Topic(
                    title=title,
                    source_platform=source_platform,
                    hot_score=hot_score,
                    status=TopicStatus.PENDING,
                    **kwargs
                )
                session.add(topic)
                session.flush()  # 获取ID
                
                data = self._topic_to_dict(topic)
                session.expunge(topic)
                
                log.print_log(f"[TopicRepository] 创建主题: {title}", "debug")
                return self._dict_to_topic(data)
        except DatabaseError:
            raise
        except Exception as e:
            log.print_log(f"[TopicRepository] 创建主题失败: {e}", "error")
            raise DatabaseError(f"创建主题失败: {title}") from e
    
    def get_by_title(self, title: str) -> Optional[Topic]:
        """
        根据标题获取主题
        """
        try:
            with self._get_session() as session:
                statement = select(Topic).where(Topic.title == title)
                result = session.exec(statement).first()
                
                if not result:
                    return None
                
                data = self._topic_to_dict(result)
                session.expunge(result)
                
                return self._dict_to_topic(data)
        except DatabaseError:
            raise
        except Exception as e:
            log.print_log(f"[TopicRepository] 获取主题失败: {e}", "error")
            raise DatabaseError(f"获取主题失败: {title}") from e
    
    def get_hot_topics(
        self,
        limit: int = 20,
        min_score: int = 0
    ) -> List[Topic]:
        """
        获取热门主题
        """
        try:
            with self._get_session() as session:
                statement = (
                    select(Topic)
                    .where(Topic.hot_score >= min_score)
                    .where(Topic.status == TopicStatus.APPROVED)
                    .order_by(desc(Topic.hot_score))
                    .limit(limit)
                )
                results = session.exec(statement).all()
                
                topics = []
                for r in results:
                    data = self._topic_to_dict(r)
                    session.expunge(r)
                    topics.append(self._dict_to_topic(data))
                
                return topics
        except DatabaseError:
            raise
        except Exception as e:
            log.print_log(f"[TopicRepository] 获取热门主题失败: {e}", "error")
            raise DatabaseError("获取热门主题失败") from e
    
    def get_pending_topics(self, limit: int = 50) -> List[Topic]:
        """
        获取待处理主题
        """
        try:
            with self._get_session() as session:
                statement = (
                    select(Topic)
                    .where(Topic.status == TopicStatus.PENDING)
                    .order_by(desc(Topic.hot_score))
                    .limit(limit)
                )
                results = session.exec(statement).all()
                
                topics = []
                for r in results:
                    data = self._topic_to_dict(r)
                    session.expunge(r)
                    topics.append(self._dict_to_topic(data))
                
                return topics
        except DatabaseError:
            raise
        except Exception as e:
            log.print_log(f"[TopicRepository] 获取待处理主题失败: {e}", "error")
            raise DatabaseError("获取待处理主题失败") from e
    
    def update_status(self, topic_id: int, status: TopicStatus) -> bool:
        """
        更新主题状态
        """
        try:
            with self._get_session() as session:
                statement = select(Topic).where(Topic.id == topic_id)
                topic = session.exec(statement).first()
                
                if not topic:
                    raise RecordNotFoundError(f"主题(id={topic_id})不存在")
                
                topic.status = status
                topic.updated_at = datetime.now()
                session.add(topic)
                session.commit()
                
                log.print_log(f"[TopicRepository] 更新主题状态: id={topic_id}, status={status}", "debug")
                return True
        except RecordNotFoundError:
            raise
        except DatabaseError:
            raise
        except Exception as e:
            log.print_log(f"[TopicRepository] 更新状态失败: {e}", "error")
            raise DatabaseError(f"更新主题状态失败") from e
    
    def increment_hot_score(self, topic_id: int, delta: int = 1) -> bool:
        """
        增加热度分数
        """
        try:
            with self._get_session() as session:
                statement = select(Topic).where(Topic.id == topic_id)
                topic = session.exec(statement).first()
                
                if not topic:
                    raise RecordNotFoundError(f"主题(id={topic_id})不存在")
                
                topic.hot_score = (topic.hot_score or 0) + delta
                topic.updated_at = datetime.now()
                session.add(topic)
                session.commit()
                
                return True
        except RecordNotFoundError:
            raise
        except DatabaseError:
            raise
        except Exception as e:
            log.print_log(f"[TopicRepository] 增加热度失败: {e}", "error")
            raise DatabaseError(f"增加热度分数失败") from e
    
    def search_topics(
        self,
        keyword: str,
        limit: int = 20
    ) -> List[Topic]:
        """
        搜索主题
        """
        try:
            with self._get_session() as session:
                statement = (
                    select(Topic)
                    .where(Topic.title.contains(keyword))
                    .order_by(desc(Topic.hot_score))
                    .limit(limit)
                )
                results = session.exec(statement).all()
                
                topics = []
                for r in results:
                    data = self._topic_to_dict(r)
                    session.expunge(r)
                    topics.append(self._dict_to_topic(data))
                
                return topics
        except DatabaseError:
            raise
        except Exception as e:
            log.print_log(f"[TopicRepository] 搜索主题失败: {e}", "error")
            raise DatabaseError(f"搜索主题失败") from e
    
    def bulk_update_status(
        self,
        topic_ids: List[int],
        status: TopicStatus
    ) -> int:
        """
        批量更新主题状态
        """
        try:
            with self._get_session() as session:
                updated_count = 0
                
                for topic_id in topic_ids:
                    statement = select(Topic).where(Topic.id == topic_id)
                    topic = session.exec(statement).first()
                    
                    if topic:
                        topic.status = status
                        topic.updated_at = datetime.now()
                        session.add(topic)
                        updated_count += 1
                
                session.commit()
                log.print_log(f"[TopicRepository] 批量更新状态: {updated_count}条", "debug")
                return updated_count
        except DatabaseError:
            raise
        except Exception as e:
            log.print_log(f"[TopicRepository] 批量更新失败: {e}", "error")
            raise DatabaseError(f"批量更新主题状态失败") from e