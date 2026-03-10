"""
AIWriteX 工具模块单元测试
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
        assert pm.project_root is not None
        
    def test_get_data_dir(self):
        """测试获取数据目录"""
        from src.ai_write_x.utils.path_manager import PathManager
        
        pm = PathManager()
        data_dir = pm.get_data_dir()
        assert data_dir is not None
        assert os.path.exists(data_dir)
        
    def test_get_config_dir(self):
        """测试获取配置目录"""
        from src.ai_write_x.utils.path_manager import PathManager
        
        pm = PathManager()
        config_dir = pm.get_config_dir()
        assert config_dir is not None
        
    def test_ensure_dir(self):
        """测试确保目录存在"""
        from src.ai_write_x.utils.path_manager import PathManager
        
        pm = PathManager()
        test_dir = os.path.join(pm.project_root, "test_temp_dir")
        pm.ensure_dir(test_dir)
        assert os.path.exists(test_dir)
        os.rmdir(test_dir)


class TestContentParser:
    """测试内容解析器"""
    
    def test_extract_title(self):
        """测试提取标题"""
        from src.ai_write_x.utils.content_parser import extract_title
        
        content = "# 测试标题\n正文内容"
        title = extract_title(content)
        assert title == "测试标题"
        
    def test_extract_title_no_header(self):
        """测试提取无标题内容"""
        from src.ai_write_x.utils.content_parser import extract_title
        
        content = "正文内容"
        title = extract_title(content)
        assert title is not None
        
    def test_clean_html_tags(self):
        """测试清理HTML标签"""
        from src.ai_write_x.utils.content_parser import clean_html_tags
        
        html = "<p>测试内容</p><br>换行"
        text = clean_html_tags(html)
        assert "<p>" not in text
        assert "测试内容" in text
        
    def test_truncate_text(self):
        """测试截断文本"""
        from src.ai_write_x.utils.content_parser import truncate_text
        
        text = "这是一个很长的文本内容"
        truncated = truncate_text(text, max_length=5)
        assert len(truncated) <= 10  # 5 + "..."


class TestTopicDeduplicator:
    """测试话题去重器"""
    
    def test_similarity_calculation(self):
        """测试相似度计算"""
        from src.ai_write_x.utils.topic_deduplicator import calculate_similarity
        
        text1 = "测试文本一"
        text2 = "测试文本二"
        similarity = calculate_similarity(text1, text2)
        assert 0 <= similarity <= 1
        
    def test_is_duplicate(self):
        """测试重复检测"""
        from src.ai_write_x.utils.topic_deduplicator import is_duplicate
        
        existing = ["测试话题1", "测试话题2"]
        new_topic = "测试话题1"
        
        is_dup = is_duplicate(new_topic, existing, threshold=0.8)
        assert isinstance(is_dup, bool)
        
    def test_deduplicate_list(self):
        """测试列表去重"""
        from src.ai_write_x.utils.topic_deduplicator import deduplicate_list
        
        topics = ["话题A", "话题B", "话题A", "话题C"]
        unique = deduplicate_list(topics, threshold=0.9)
        assert isinstance(unique, list)


class TestComm:
    """测试通讯工具"""
    
    def test_safe_json_loads(self):
        """测试安全JSON加载"""
        from src.ai_write_x.utils.comm import safe_json_loads
        
        json_str = '{"key": "value"}'
        result = safe_json_loads(json_str, default={})
        assert result == {"key": "value"}
        
    def test_safe_json_loads_invalid(self):
        """测试无效JSON处理"""
        from src.ai_write_x.utils.comm import safe_json_loads
        
        invalid_json = "invalid"
        result = safe_json_loads(invalid_json, default={"default": True})
        assert result == {"default": True}
        
    def test_chunk_list(self):
        """测试列表分块"""
        from src.ai_write_x.utils.comm import chunk_list
        
        items = [1, 2, 3, 4, 5, 6, 7]
        chunks = list(chunk_list(items, 3))
        assert len(chunks) == 3
        assert chunks[0] == [1, 2, 3]


class TestUtils:
    """测试通用工具"""
    
    def test_generate_id(self):
        """测试ID生成"""
        from src.ai_write_x.utils.utils import generate_id
        
        id1 = generate_id()
        id2 = generate_id()
        assert id1 != id2
        assert len(id1) > 0
        
    def test_format_time(self):
        """测试时间格式化"""
        from src.ai_write_x.utils.utils import format_time
        from datetime import datetime
        
        dt = datetime(2024, 1, 1, 12, 0, 0)
        formatted = format_time(dt)
        assert "2024" in formatted
        
    def test_sanitize_filename(self):
        """测试文件名清理"""
        from src.ai_write_x.utils.utils import sanitize_filename
        
        filename = "test/file:name*.txt"
        sanitized = sanitize_filename(filename)
        assert "/" not in sanitized
        assert ":" not in sanitized
        
    def test_read_file_safe(self):
        """测试安全文件读取"""
        from src.ai_write_x.utils.utils import read_file_safe
        
        content = read_file_safe("non_existent_file.txt", default="default")
        assert content == "default"


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


if __name__ == "__main__":
    pytest.main([__file__, "-v"])