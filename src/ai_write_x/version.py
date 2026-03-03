# -*- coding: UTF-8 -*-

__version__ = "1.0.0"
__author__ = "本地开发版"


def get_version():
    return __version__


def get_author():
    return __author__


def get_version_with_prefix():
    return f"v{__version__}"