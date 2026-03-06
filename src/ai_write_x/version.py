# -*- coding: UTF-8 -*-
"""AIWriteX 版本信息 (V12.0.0 "Cosmic Singularity Evolution")"""

from datetime import datetime

__version__ = "12.0.2"
__author__ = "本地开发版 (Cosmic Singularity)"
__build_time__ = datetime.now().strftime("%Y-%m-%d %H:%M:%S")


def get_version():
    return __version__


def get_author():
    return __author__


def get_version_with_prefix():
    return f"v{__version__}"


def get_build_info():
    """V3: 返回完整构建信息字典"""
    return {
        "version": __version__,
        "version_display": f"v{__version__}",
        "author": __author__,
        "build_time": __build_time__,
    }