"""
AI 回复质量检测器 - 简化版
"""

import re
from typing import List, Tuple


class RepetitionDetector:
    """重复内容检测器"""

    def __init__(self):
        self.max_consecutive_chars = 50
        self.min_repeat_length = 10
    
    def detect_consecutive_repetition(self, text: str) -> Tuple[bool, str]:
        """检测连续重复字符"""
        if len(text) < self.min_repeat_length:
            return False, ""
        
        # 检测连续相同字符
        pattern = r'(.)\1{49,}'
        matches = re.findall(pattern, text)
        
        if matches:
            char = matches[0]
            repeat_pattern = re.escape(char) + r'{50,}'
            repeat_match = re.search(repeat_pattern, text)
            if repeat_match:
                return True, f"检测到连续重复：{repeat_match.group(0)[:20]}..."
        
        return False, ""
    
    def check_chunk(self, chunk: str, full_content: str) -> Tuple[bool, str]:
        """检查新生成的 chunk 是否有重复"""
        is_rep, msg = self.detect_consecutive_repetition(chunk)
        if is_rep:
            return True, msg
        return False, ""
    
    def reset(self):
        """重置检测器"""
        pass


_global_detector = RepetitionDetector()


def get_detector() -> RepetitionDetector:
    """获取全局检测器"""
    return _global_detector


def check_generation_quality(chunk: str, full_content: str) -> Tuple[bool, str]:
    """检查生成内容的质量"""
    return _global_detector.check_chunk(chunk, full_content)
