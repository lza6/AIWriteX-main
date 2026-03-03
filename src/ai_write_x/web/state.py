#!/usr/bin/env python
# -*- coding: UTF-8 -*-

from typing import Dict, Any


class AppState:
    def __init__(self):
        self.active_connections: Dict[str, Any] = {}
        self.current_process = None
        self.log_queue = None
        self.is_running = False
        self.config = None


# 全局状态实例
app_state = AppState()


def get_app_state():
    return app_state
