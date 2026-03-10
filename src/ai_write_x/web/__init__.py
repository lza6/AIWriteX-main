#!/usr/bin/env python
# -*- coding: UTF-8 -*-

"""
AIWriteX 新架构
基于FastAPI + PyWebView
"""
try:
    from src.ai_write_x.version import get_version, get_author
    __version__ = get_version()
    __author__ = get_author()
except ImportError:
    try:
        from ..version import get_version, get_author
        __version__ = get_version()
        __author__ = get_author()
    except ImportError:
        __version__ = "18.0.0"
        __author__ = "AIWriteX"
