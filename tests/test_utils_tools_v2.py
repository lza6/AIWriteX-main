"""
AIWriteX 工具模块单元测试 (V2 - 基于实际代码结构)
测试utils目录下的各个工具函数
"""
import os
import sys
import pytest
from unittest.mock import patch, MagicMock, mock_open

project_root = os.path.dirname(os.path.dirname(__file__))
if project_root not in sys.path:
    sys.path.insert(0, project_root)


class TestPathManager:
    """测试路径管理器"""
    
    def test_path_manager_initialization(self):
        """测试路径管理器初始化"""
        from src.ai_write_x.utils.path_manager import PathManager
        
        pm = PathManager()
        assert pm is not None
        
    def test_get_app_data_dir(self):
        """测试获取应用数据目录"""
        from src.ai_write_x.utils.path_manager import PathManager
        
        data_dir = PathManager.get_app_data_dir()
        assert data_dir is not None
        
    def test_get_data_dir(self):
        """测试获取数据目录"""
        from src.ai_write_x.utils.path_manager import PathManager
        
        data_dir = PathManager.get_data_dir()
        assert data_dir is not None
        
    def test_get_config_dir(self):
        """测试获取配置目录"""
        from src.ai_write_x.utils.path_manager import PathManager
        
        config_dir = PathManager.get_config_dir()
        assert config_dir is not None


class TestContentParser:
    """测试内容解析器"""
    
    def test_content_parser_initialization(self):
        """测试内容解析器初始化"""
        from src.ai_write_x.utils.content_parser import ContentParser
        
        parser = ContentParser()
        assert parser is not None
        assert len(parser.title_patterns) > 0
        
    def test_parse_empty_content(self):
        """测试解析空内容"""
        from src.ai_write_x.utils.content_parser import ContentParser
        
        parser = ContentParser()
        result = parser.parse("")
        assert result.title == ""
        assert result.confidence == 0.0
        
    def test_parse_markdown_content(self):
        """测试解析Markdown内容"""
        from src.ai_write_x.utils.content_parser import ContentParser
        
        parser = ContentParser()
        content = "# 测试标题\n\n正文内容"
        result = parser.parse(content)
        
        assert isinstance(result.title, str)
        assert isinstance(result.content, str)
        
    def test_clean_content(self):
        """测试清理内容"""
        from src.ai_write_x.utils.content_parser import ContentParser
        
        parser = ContentParser()
        dirty_content = "  测试内容  \n\n"
        cleaned = parser._clean_content(dirty_content)
        
        assert isinstance(cleaned, str)
        
    def test_detect_content_type(self):
        """测试检测内容类型"""
        from src.ai_write_x.utils.content_parser import ContentParser
        
        parser = ContentParser()
        
        html_content = "<html><body>测试</body></html>"
        content_type = parser._detect_content_type(html_content)
        assert content_type == "html"
        
        markdown_content = "# 标题\n正文"
        content_type = parser._detect_content_type(markdown_content)
        assert content_type == "markdown"


class TestTopicDeduplicator:
    """测试话题去重器"""
    
    def test_deduplicator_initialization(self):
        """测试去重器初始化"""
        from src.ai_write_x.utils.topic_deduplicator import TopicDeduplicator
        
        with patch('src.ai_write_x.utils.topic_deduplicator.db_manager'):
            dedup = TopicDeduplicator(dedup_days=3)
            assert dedup.dedup_days == 3
            
    def test_is_duplicate(self):
        """测试重复检测"""
        from src.ai_write_x.utils.topic_deduplicator import TopicDeduplicator
        
        with patch('src.ai_write_x.utils.topic_deduplicator.db_manager') as mock_db:
            mock_db.is_topic_processed_recently.return_value = False
            
            dedup = TopicDeduplicator()
            result = dedup.is_duplicate("测试话题")
            
            assert isinstance(result, bool)
            assert result == False
            
    def test_add_topic(self):
        """测试添加话题"""
        from src.ai_write_x.utils.topic_deduplicator import TopicDeduplicator
        
        with patch('src.ai_write_x.utils.topic_deduplicator.db_manager') as mock_db:
            mock_db.add_topic.return_value = True
            
            dedup = TopicDeduplicator()
            dedup.add_topic("测试话题")
            
            mock_db.add_topic.assert_called_once()


class TestComm:
    """测试通讯工具"""
    
    def test_comm_module_import(self):
        """测试通讯模块导入"""
        from src.ai_write_x.utils import comm
        assert comm is not None


class TestLog:
    """测试日志模块"""
    
    def test_print_log(self):
        """测试打印日志"""
        from src.ai_write_x.utils.log import print_log
        
        # 不应抛出异常
        print_log("测试消息", "info")
        print_log("警告消息", "warning")
        print_log("错误消息", "error")
        print_log("成功消息", "success")
        
    def test_log_levels(self):
        """测试日志级别"""
        from src.ai_write_x.utils.log import LOG_LEVELS
        
        assert "info" in LOG_LEVELS
        assert "warning" in LOG_LEVELS
        assert "error" in LOG_LEVELS
        assert "success" in LOG_LEVELS


class TestUtils:
    """测试通用工具"""
    
    def test_utils_import(self):
        """测试工具模块导入"""
        from src.ai_write_x.utils import utils
        assert utils is not None
        
    def test_icon_manager_import(self):
        """测试图标管理器导入"""
        from src.ai_write_x.utils import icon_manager
        assert icon_manager is not None
        
    def test_llm_service_import(self):
        """测试LLM服务导入"""
        from src.ai_write_x.utils import llm_service
        assert llm_service is not None


class TestLLMService:
    """测试LLM服务"""
    
    def test_llm_service_initialization(self):
        """测试LLM服务初始化"""
        from src.ai_write_x.utils.llm_service import LLMService
        
        service = LLMService()
        assert service is not None


class TestIconManager:
    """测试图标管理器"""
    
    def test_icon_manager_initialization(self):
        """测试图标管理器初始化"""
        from src.ai_write_x.utils.icon_manager import IconManager
        
        manager = IconManager()
        assert manager is not None


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
