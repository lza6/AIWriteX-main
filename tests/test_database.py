"""
AIWriteX 数据库模块单元测试
测试数据库连接、模型和仓库
"""
import os
import sys
import pytest
from unittest.mock import patch, MagicMock, Mock
from datetime import datetime

project_root = os.path.dirname(os.path.dirname(__file__))
if project_root not in sys.path:
    sys.path.insert(0, project_root)


class TestConnectionPool:
    """测试数据库连接池"""
    
    def test_connection_pool_singleton(self):
        """测试连接池单例模式"""
        from src.ai_write_x.database import ConnectionPool
        
        pool1 = ConnectionPool()
        pool2 = ConnectionPool()
        assert pool1 is pool2
        
    def test_get_connection(self):
        """测试获取连接"""
        from src.ai_write_x.database import ConnectionPool
        
        pool = ConnectionPool()
        # 模拟连接
        with patch.object(pool, '_engine') as mock_engine:
            mock_conn = MagicMock()
            mock_engine.connect.return_value = mock_conn
            
            conn = pool.get_connection()
            assert conn is not None
            
    def test_get_session(self):
        """测试获取会话"""
        from src.ai_write_x.database import ConnectionPool
        
        pool = ConnectionPool()
        with patch.object(pool, '_engine'):
            session = pool.get_session()
            assert session is not None


class TestDBManager:
    """测试数据库管理器"""
    
    def test_db_manager_initialization(self):
        """测试DBManager初始化"""
        from src.ai_write_x.database.db_manager import DBManager
        
        with patch('src.ai_write_x.database.db_manager.create_engine'):
            db = DBManager()
            assert db is not None
            
    def test_create_tables(self):
        """测试创建表"""
        from src.ai_write_x.database.db_manager import DBManager
        
        with patch('src.ai_write_x.database.db_manager.create_engine'):
            db = DBManager()
            with patch.object(db, 'Base') as mock_base:
                mock_base.metadata.create_all = MagicMock()
                db.create_tables()
                mock_base.metadata.create_all.assert_called_once()


class TestModels:
    """测试数据模型"""
    
    def test_article_model_creation(self):
        """测试文章模型创建"""
        from src.ai_write_x.database.models import Article
        
        article = Article(
            title="测试标题",
            content="测试内容",
            platform="wechat",
            status="draft"
        )
        assert article.title == "测试标题"
        assert article.platform == "wechat"
        
    def test_article_to_dict(self):
        """测试文章转字典"""
        from src.ai_write_x.database.models import Article
        
        article = Article(
            id=1,
            title="测试",
            content="内容",
            platform="wechat"
        )
        data = article.to_dict()
        assert isinstance(data, dict)
        assert data["title"] == "测试"
        
    def test_topic_model_creation(self):
        """测试话题模型"""
        from src.ai_write_x.database.models import Topic
        
        topic = Topic(
            title="测试话题",
            category="tech",
            source="weibo"
        )
        assert topic.title == "测试话题"
        assert topic.category == "tech"


class TestArticleRepository:
    """测试文章仓库"""
    
    def test_article_repo_initialization(self):
        """测试文章仓库初始化"""
        from src.ai_write_x.database.repository.article_repo import ArticleRepository
        
        with patch('src.ai_write_x.database.repository.article_repo.get_session'):
            repo = ArticleRepository()
            assert repo is not None
            
    def test_create_article(self):
        """测试创建文章"""
        from src.ai_write_x.database.repository.article_repo import ArticleRepository
        
        with patch('src.ai_write_x.database.repository.article_repo.get_session') as mock_get_session:
            mock_session = MagicMock()
            mock_get_session.return_value = mock_session
            
            repo = ArticleRepository()
            article_id = repo.create(
                title="测试",
                content="内容",
                platform="wechat"
            )
            
            mock_session.add.assert_called_once()
            mock_session.commit.assert_called_once()
            
    def test_get_article_by_id(self):
        """测试根据ID获取文章"""
        from src.ai_write_x.database.repository.article_repo import ArticleRepository
        
        with patch('src.ai_write_x.database.repository.article_repo.get_session') as mock_get_session:
            mock_session = MagicMock()
            mock_get_session.return_value = mock_session
            
            repo = ArticleRepository()
            result = repo.get_by_id(1)
            
            mock_session.query.assert_called_once()


class TestBaseRepository:
    """测试基础仓库"""
    
    def test_base_repo_exists(self):
        """测试基础仓库存在"""
        from src.ai_write_x.database.repository.base import BaseRepository
        assert BaseRepository is not None
        
    def test_repository_methods(self):
        """测试仓库方法"""
        from src.ai_write_x.database.repository.base import BaseRepository
        
        # 检查基本方法存在
        assert hasattr(BaseRepository, 'get_by_id')
        assert hasattr(BaseRepository, 'get_all')
        assert hasattr(BaseRepository, 'create')
        assert hasattr(BaseRepository, 'update')
        assert hasattr(BaseRepository, 'delete')


class TestMemoryRepository:
    """测试记忆仓库"""
    
    def test_memory_repo_initialization(self):
        """测试记忆仓库初始化"""
        from src.ai_write_x.database.repository.memory_repo import MemoryRepository
        
        with patch('src.ai_write_x.database.repository.memory_repo.get_session'):
            repo = MemoryRepository()
            assert repo is not None
            
    def test_add_memory(self):
        """测试添加记忆"""
        from src.ai_write_x.database.repository.memory_repo import MemoryRepository
        
        with patch('src.ai_write_x.database.repository.memory_repo.get_session') as mock_get_session:
            mock_session = MagicMock()
            mock_get_session.return_value = mock_session
            
            repo = MemoryRepository()
            memory_id = repo.add(
                content="测试记忆",
                memory_type="fact"
            )
            
            mock_session.add.assert_called_once()


class TestTopicRepository:
    """测试话题仓库"""
    
    def test_topic_repo_initialization(self):
        """测试话题仓库初始化"""
        from src.ai_write_x.database.repository.topic_repo import TopicRepository
        
        with patch('src.ai_write_x.database.repository.topic_repo.get_session'):
            repo = TopicRepository()
            assert repo is not None
            
    def test_get_topics_by_category(self):
        """测试按分类获取话题"""
        from src.ai_write_x.database.repository.topic_repo import TopicRepository
        
        with patch('src.ai_write_x.database.repository.topic_repo.get_session') as mock_get_session:
            mock_session = MagicMock()
            mock_get_session.return_value = mock_session
            
            repo = TopicRepository()
            topics = repo.get_by_category("tech")
            
            mock_session.query.assert_called_once()


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
