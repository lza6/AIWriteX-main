#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""测试SpiderRunner加载新爬虫"""
import sys
import os
import importlib.util

# 添加路径
sys.path.insert(0, os.path.join(os.path.dirname(__file__), 'src', 'ai_write_x'))
sys.path.insert(0, os.path.join(os.path.dirname(__file__), 'src', 'ai_write_x', 'scrapers'))

from tools.spider_runner import SpiderRunner

# 创建SpiderRunner实例
runner = SpiderRunner()
print("已加载的爬虫:")
for name, info in runner.spiders.items():
    print(f"  - {name}: {info['category']}")
