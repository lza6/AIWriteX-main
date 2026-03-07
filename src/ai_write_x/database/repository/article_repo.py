# -*- coding: UTF-8 -*-
"""
文章仓储 - Article Repository
提供文章相关的数据库操作
"""

from typing import List, Optional, Dict, Any
from datetime import datetime, timedelta
from sqlmodel import select, and_, or_, desc, func

from src.ai_write_x.database import Article
from src.ai_write_x.database.repository.base import BaseRepository
from src.ai_write_x.core.exceptions import DatabaseError, RecordNotFoundError
from src.ai_write_x.utils import log


class ArticleRepository(BaseRepository[Article]):
    """文章仓储"""
    
    @property
    def model(self) -> type[Article]:
        return Article
    
    def create_article(
        self,
        title: str,
        content: str,
        category: str = "unknown",
        source_url: str = None,
        **kwargs
    ) -> Article:
        """
        创建文章
        """
        try:
            with self._get_session() as session:
                article = Article(
                    title=title,
                    content=content,
                    category=category,
                    source_url=source_url,
                    **kwargs
                )
                session.add(article)
                session.commit()
                session.refresh(article)
                
                log.print_log(f"[ArticleRepository] 创建文章: {title}", "debug")
                return article
        except DatabaseError:
            raise
        except Exception as e:
            log.print_log(f"[ArticleRepository] 创建文章失败: {e}", "error")
            raise DatabaseError(f"创建文章失败") from e
    
    def get_by_title(self, title: str) -> Optional[Article]:
        """
        根据标题获取文章
        """
        try:
            with self._get_session() as session:
                statement = select(Article).where(Article.title == title)
                return session.exec(statement).first()
        except DatabaseError:
            raise
        except Exception as e:
            log.print_log(f"[ArticleRepository] 获取文章失败: {e}", "error")
            raise DatabaseError(f"获取文章失败") from e
    
    def get_by_category(
        self,
        category: str,
        limit: int = 20,
        offset: int = 0
    ) -> List[Article]:
        """
        根据分类获取文章
        """
        try:
            with self._get_session() as session:
                statement = (
                    select(Article)
                    .where(Article.category == category)
                    .order_by(desc(Article.created_at))
                    .limit(limit)
                    .offset(offset)
                )
                return list(session.exec(statement).all())
        except DatabaseError:
            raise
        except Exception as e:
            log.print_log(f"[ArticleRepository] 获取分类文章失败: {e}", "error")
            raise DatabaseError(f"获取分类文章失败") from e
    
    def get_recent_articles(
        self,
        hours: int = 24,
        limit: int = 50
    ) -> List[Article]:
        """
        获取最近的文章
        """
        try:
            with self._get_session() as session:
                cutoff = datetime.now() - timedelta(hours=hours)
                statement = (
                    select(Article)
                    .where(Article.created_at >= cutoff)
                    .order_by(desc(Article.created_at))
                    .limit(limit)
                )
                return list(session.exec(statement).all())
        except DatabaseError:
            raise
        except Exception as e:
            log.print_log(f"[ArticleRepository] 获取最近文章失败: {e}", "error")
            raise DatabaseError(f"获取最近文章失败") from e
    
    def search_articles(
        self,
        keyword: str,
        limit: int = 20
    ) -> List[Article]:
        """
        搜索文章
        """
        try:
            with self._get_session() as session:
                keyword_pattern = f"%{keyword}%"
                statement = (
                    select(Article)
                    .where(
                        or_(
                            Article.title.contains(keyword),
                            Article.content.contains(keyword)
                        )
                    )
                    .order_by(desc(Article.created_at))
                    .limit(limit)
                )
                return list(session.exec(statement).all())
        except DatabaseError:
            raise
        except Exception as e:
            log.print_log(f"[ArticleRepository] 搜索文章失败: {e}", "error")
            raise DatabaseError(f"搜索文章失败") from e
    
    def get_statistics(self) -> Dict[str, Any]:
        """
        获取文章统计信息
        """
        try:
            with self._get_session() as session:
                # 总数
                total_stmt = select(func.count(Article.id))
                total = session.exec(total_stmt).first() or 0
                
                # 分类统计
                category_stmt = (
                    select(Article.category, func.count(Article.id))
                    .group_by(Article.category)
                )
                category_results = session.exec(category_stmt).all()
                by_category = {cat: count for cat, count in category_results}
                
                # 今日新增
                today = datetime.now().replace(hour=0, minute=0, second=0, microsecond=0)
                today_stmt = select(func.count(Article.id)).where(Article.created_at >= today)
                today_count = session.exec(today_stmt).first() or 0
                
                return {
                    "total": total,
                    "by_category": by_category,
                    "today": today_count
                }
        except DatabaseError:
            raise
        except Exception as e:
            log.print_log(f"[ArticleRepository] 统计失败: {e}", "error")
            raise DatabaseError(f"获取文章统计失败") from e
    
    def update_published_status(
        self,
        article_id: int,
        is_published: bool = True
    ) -> bool:
        """
        更新文章发布状态
        """
        try:
            with self._get_session() as session:
                statement = select(Article).where(Article.id == article_id)
                article = session.exec(statement).first()
                
                if not article:
                    raise RecordNotFoundError(f"文章(id={article_id})不存在")
                
                article.is_published = is_published
                article.published_at = datetime.now() if is_published else None
                article.updated_at = datetime.now()
                session.add(article)
                session.commit()
                
                return True
        except RecordNotFoundError:
            raise
        except DatabaseError:
            raise
        except Exception as e:
            log.print_log(f"[ArticleRepository] 更新发布状态失败: {e}", "error")
            raise DatabaseError(f"更新发布状态失败") from e
    
    def delete_old_articles(self, days: int = 90) -> int:
        """
        删除旧文章
        """
        try:
            with self._get_session() as session:
                cutoff = datetime.now() - timedelta(days=days)
                
                # 获取要删除的文章ID
                select_stmt = select(Article.id).where(
                    and_(
                        Article.created_at < cutoff,
                        Article.is_published == False
                    )
                )
                article_ids = list(session.exec(select_stmt).all())
                
                if not article_ids:
                    return 0
                
                # 删除
                delete_stmt = Article.__table__.delete().where(
                    and_(
                        Article.created_at < cutoff,
                        Article.is_published == False
                    )
                )
                session.exec(delete_stmt)
                session.commit()
                
                log.print_log(f"[ArticleRepository] 删除旧文章: {len(article_ids)}条", "debug")
                return len(article_ids)
        except DatabaseError:
            raise
        except Exception as e:
            log.print_log(f"[ArticleRepository] 删除旧文章失败: {e}", "error")
            raise DatabaseError(f"删除旧文章失败") from e
