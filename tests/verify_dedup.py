import unittest
from unittest.mock import MagicMock, patch
import sys
import os

# 确保导入路径正确
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from src.ai_write_x.tools import hotnews
from src.ai_write_x.utils.topic_deduplicator import TopicDeduplicator

class TestTopicDeduplication(unittest.TestCase):
    
    @patch('src.ai_write_x.tools.hotnews.get_platform_news')
    def test_select_platform_topic_deduplication(self, mock_get_news):
        # 模拟返回的话题列表
        mock_get_news.side_effect = lambda p, c, exclude=None: [
            t for t in ["Topic 1", "Topic 2", "Topic 3", "Topic 4"] 
            if exclude is None or t not in exclude
        ]
        
        used_topics = []
        
        # 第一次选择
        topic1 = hotnews.select_platform_topic("微博", exclude_topics=used_topics)
        used_topics.append(topic1)
        
        # 第二次选择，应该排除第一个
        topic2 = hotnews.select_platform_topic("微博", exclude_topics=used_topics)
        used_topics.append(topic2)
        
        self.assertNotEqual(topic1, topic2)
        self.assertIn(topic1, ["Topic 1", "Topic 2", "Topic 3", "Topic 4"])
        self.assertIn(topic2, ["Topic 1", "Topic 2", "Topic 3", "Topic 4"])
        print(f"Selected topics: {topic1}, {topic2}")

    @patch('src.ai_write_x.database.db_manager.is_topic_processed_recently')
    @patch('src.ai_write_x.database.db_manager.add_topic')
    def test_deduplicator_integration(self, mock_add, mock_is_recent):
        mock_is_recent.return_value = False
        dedup = TopicDeduplicator(dedup_days=3)
        
        # 测试添加新话题
        dedup.add_topic("Unique Topic X")
        mock_add.assert_called_with("Unique Topic X")
        
        # 测试查重
        mock_is_recent.return_value = True
        self.assertTrue(dedup.is_duplicate("Recent Topic"))
        
        mock_is_recent.return_value = False
        self.assertFalse(dedup.is_duplicate("New Topic"))

if __name__ == '__main__':
    unittest.main()
