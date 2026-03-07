# -*- coding: UTF-8 -*-
"""
基础仓储类 - Base Repository
提供通用的数据库操作抽象
"""

from typing import TypeVar, Generic, List, Optional, Any, Dict
from abc import ABC, abstractmethod
from sqlmodel import SQLModel, Session, select
from contextlib import contextmanager

from src.ai_write_x.database import get_session
from src.ai_write_x.core.exceptions import DatabaseError, RecordNotFoundError
from src.ai_write_x.utils import log


T = TypeVar('T', bound=SQLModel)


def _detach_object(obj: T) -> T:
    """将SQLModel对象从session分离，使其在session关闭后可访问"""
    if obj is None:
        return None
    
    # 强制加载所有属性
    obj.__dict__  # 触发延迟加载
    
    # 使用make_transient将对象从session分离
    from sqlmodel import Session as SQLSession
    SQLSession.make_transient(obj)
    
    return obj


class BaseRepository(ABC, Generic[T]):
    """
    基础仓储类
    
    提供通用的 CRUD 操作:
    - create: 创建记录
    - get: 获取单条记录
    - get_all: 获取所有记录
    - update: 更新记录
    - delete: 删除记录
    - find: 条件查询
    """
    
    @property
    @abstractmethod
    def model(self) -> type[T]:
        """返回模型类"""
        pass
    
    @property
    def model_name(self) -> str:
        """返回模型名称"""
        return self.model.__name__ if self.model else "Unknown"
    
    @contextmanager
    def _get_session(self):
        """获取数据库会话"""
        session = get_session()
        try:
            yield session
            session.commit()
        except Exception:
            session.rollback()
            raise
        finally:
            session.close()
    
    def _to_dict(self, obj: T) -> Dict[str, Any]:
        """将SQLModel对象转换为字典"""
        if obj is None:
            return {}
        
        result = {}
        for col in obj.__table__.columns:
            result[col.name] = getattr(obj, col.name)
        return result
    
    def _from_dict(self, data: Dict[str, Any]) -> T:
        """从字典创建SQLModel对象"""
        # 过滤掉None值和不在模型中的键
        model_fields = {col.name for col in self.model.__table__.columns}
        filtered_data = {k: v for k, v in data.items() if k in model_fields}
        return self.model(**filtered_data)
    
    def create(self, **kwargs) -> Optional[T]:
        """
        创建记录
        """
        try:
            with self._get_session() as session:
                model_instance = self.model(**kwargs)
                session.add(model_instance)
                session.flush()  # 获取ID
                
                # 转换为字典再重建对象，避免session绑定问题
                data = self._to_dict(model_instance)
                session.expunge(model_instance)
                
                log.print_log(f"[{self.model_name}] 创建记录成功: {data.get('id', 'N/A')}", "debug")
                return self._from_dict(data)
        except DatabaseError:
            raise
        except Exception as e:
            log.print_log(f"[{self.model_name}] 创建记录失败: {e}", "error")
            raise DatabaseError(f"创建{self.model_name}失败") from e
    
    def get(self, id: int) -> Optional[T]:
        """
        根据ID获取记录
        """
        try:
            with self._get_session() as session:
                statement = select(self.model).where(self.model.id == id)
                result = session.exec(statement).first()
                
                if not result:
                    raise RecordNotFoundError(f"{self.model_name}(id={id})不存在")
                
                # 转换为字典再重建
                data = self._to_dict(result)
                session.expunge(result)
                
                return self._from_dict(data)
        except RecordNotFoundError:
            raise
        except DatabaseError:
            raise
        except Exception as e:
            log.print_log(f"[{self.model_name}] 获取记录失败: {e}", "error")
            raise DatabaseError(f"获取{self.model_name}失败") from e
    
    def get_all(self, limit: int = 100, offset: int = 0) -> List[T]:
        """
        获取所有记录
        """
        try:
            with self._get_session() as session:
                statement = select(self.model).offset(offset).limit(limit)
                results = session.exec(statement).all()
                
                # 批量转换
                return [self._from_dict(self._to_dict(r)) for r in results]
        except DatabaseError:
            raise
        except Exception as e:
            log.print_log(f"[{self.model_name}] 获取所有记录失败: {e}", "error")
            raise DatabaseError(f"获取所有{self.model_name}失败") from e
    
    def update(self, id: int, **kwargs) -> Optional[T]:
        """
        更新记录
        """
        try:
            with self._get_session() as session:
                statement = select(self.model).where(self.model.id == id)
                instance = session.exec(statement).first()
                
                if not instance:
                    raise RecordNotFoundError(f"{self.model_name}(id={id})不存在")
                
                for key, value in kwargs.items():
                    if hasattr(instance, key):
                        setattr(instance, key, value)
                
                session.add(instance)
                session.flush()
                
                # 转换为字典再重建
                data = self._to_dict(instance)
                session.expunge(instance)
                
                log.print_log(f"[{self.model_name}] 更新记录成功: id={id}", "debug")
                return self._from_dict(data)
        except RecordNotFoundError:
            raise
        except DatabaseError:
            raise
        except Exception as e:
            log.print_log(f"[{self.model_name}] 更新记录失败: {e}", "error")
            raise DatabaseError(f"更新{self.model_name}失败") from e
    
    def delete(self, id: int) -> bool:
        """
        删除记录
        """
        try:
            with self._get_session() as session:
                statement = select(self.model).where(self.model.id == id)
                instance = session.exec(statement).first()
                
                if not instance:
                    raise RecordNotFoundError(f"{self.model_name}(id={id})不存在")
                
                session.delete(instance)
                session.commit()
                
                log.print_log(f"[{self.model_name}] 删除记录成功: id={id}", "debug")
                return True
        except RecordNotFoundError:
            raise
        except DatabaseError:
            raise
        except Exception as e:
            log.print_log(f"[{self.model_name}] 删除记录失败: {e}", "error")
            raise DatabaseError(f"删除{self.model_name}失败") from e
    
    def find(self, conditions: Dict[str, Any], limit: int = 100) -> List[T]:
        """
        条件查询
        """
        try:
            with self._get_session() as session:
                statement = select(self.model)
                
                for key, value in conditions.items():
                    if hasattr(self.model, key):
                        if isinstance(value, (list, tuple)):
                            statement = statement.where(getattr(self.model, key).in_(value))
                        else:
                            statement = statement.where(getattr(self.model, key) == value)
                
                statement = statement.limit(limit)
                results = session.exec(statement).all()
                
                return [self._from_dict(self._to_dict(r)) for r in results]
        except DatabaseError:
            raise
        except Exception as e:
            log.print_log(f"[{self.model_name}] 条件查询失败: {e}", "error")
            raise DatabaseError(f"查询{self.model_name}失败") from e
    
    def count(self, conditions: Dict[str, Any] = None) -> int:
        """
        统计数量
        """
        try:
            with self._get_session() as session:
                statement = select(self.model)
                
                if conditions:
                    for key, value in conditions.items():
                        if hasattr(self.model, key):
                            if isinstance(value, (list, tuple)):
                                statement = statement.where(getattr(self.model, key).in_(value))
                            else:
                                statement = statement.where(getattr(self.model, key) == value)
                
                results = session.exec(statement).all()
                return len(list(results))
        except DatabaseError:
            raise
        except Exception as e:
            log.print_log(f"[{self.model_name}] 统计失败: {e}", "error")
            raise DatabaseError(f"统计{self.model_name}数量失败") from e
    
    def exists(self, id: int) -> bool:
        """
        检查记录是否存在
        """
        try:
            with self._get_session() as session:
                statement = select(self.model).where(self.model.id == id)
                result = session.exec(statement).first()
                return result is not None
        except Exception as e:
            log.print_log(f"[{self.model_name}] 检查存在性失败: {e}", "error")
            return False