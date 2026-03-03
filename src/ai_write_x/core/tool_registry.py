import threading
from typing import Dict, Any


class GlobalToolRegistry:
    _instance = None
    _lock = threading.Lock()

    def __init__(self):
        self._tools = {}
        self._tool_lock = threading.Lock()

    @classmethod
    def get_instance(cls):
        if cls._instance is None:
            with cls._lock:
                if cls._instance is None:
                    cls._instance = cls()
        return cls._instance

    def register_tool(self, name: str, tool_class):
        with self._tool_lock:
            self._tools[name] = tool_class

    def get_tool(self, name: str):
        with self._tool_lock:
            return self._tools.get(name)

    def keys(self):
        """获取所有已注册工具的名称"""
        with self._tool_lock:
            return list(self._tools.keys())

    def has_tool(self, name: str) -> bool:
        """检查工具是否已注册"""
        with self._tool_lock:
            return name in self._tools

    def get_all_tools(self) -> Dict[str, Any]:
        """获取所有已注册的工具"""
        return self._tools.copy()
