import sys
import os
import time

# Ensure project root is in path
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from src.ai_write_x.utils import log

class MockTask:
    def __init__(self, name):
        self.name = name
    def __repr__(self):
        return f"MockTask({self.name})"

def test_rich_logging():
    print("\n--- 验证 print_ai_log 对不可序列化对象的兼容性 ---")
    
    # 测试包含 Task 对象的请求载荷
    test_payload = {
        "model": "gpt-4o",
        "task_object": MockTask("Complex Generation"),
        "messages": [
            {"role": "system", "content": "你是一个 AI 写作助手。"},
            {"role": "user", "content": "请写一篇关于人工智能的文章。"}
        ]
    }
    log.print_ai_log("AI Request (gpt-4o)", test_payload, log_type="payload", req_id="test-json-fix")
    
    time.sleep(1) # 模拟处理延迟
    
    # 测试响应内容记录
    test_response = "人工智能（AI）正在深刻改变我们的世界。从自动驾驶到医疗诊断，AI 的应用无处不在..."
    log.print_ai_log("AI Response (gpt-4o)", test_response, log_type="response", req_id="test-123")
    
    print("\n--- 验证结束 ---")

if __name__ == "__main__":
    test_rich_logging()
