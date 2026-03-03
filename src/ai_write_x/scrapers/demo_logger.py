#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
日志输出演示脚本
展示美化后的日志输出效果
"""

import asyncio
from logger_utils import logger
import time


def demo_logger_output():
    """演示各种类型的日志输出"""

    # 标题
    logger.header("爬虫系统日志输出演示")

    # 普通信息
    logger.info("系统初始化中...")
    time.sleep(0.5)

    # 成功信息
    logger.success("数据库连接池创建成功")
    logger.success("数据表初始化完成")
    time.sleep(0.5)

    # 进度信息
    logger.progress("开始爬取IT之家新闻...")
    time.sleep(0.5)

    # 跳过信息
    logger.skip("文章已存在: Python 3.12 正式发布")
    logger.skip("文章已存在: 微软发布新版 Windows")
    time.sleep(0.5)

    # 警告信息
    logger.warning("网络连接不稳定，正在重试...")
    time.sleep(0.5)

    # 错误信息
    logger.error("获取新闻详情失败: 连接超时")
    logger.error("保存文章失败: 数据库连接中断")
    time.sleep(0.5)

    # 分隔线
    logger.separator()

    # 更多成功信息
    logger.success("IT之家爬虫执行完成，保存了 15 篇文章")
    logger.success("澎湃新闻爬虫执行完成，保存了 23 篇文章")
    logger.success("网易新闻爬虫执行完成，保存了 18 篇文章")

    # 分隔线
    logger.separator()

    # 系统信息
    logger.info("总共处理了 56 篇文章")
    logger.info("跳过重复文章 12 篇")
    logger.info("成功保存新文章 44 篇")

    # 最终成功
    logger.success("所有爬虫执行完成，系统正常退出")


if __name__ == "__main__":
    print("\n" + "=" * 80)
    print(" " * 30 + "日志输出效果演示")
    print("=" * 80)
    print("\n以下是美化后的日志输出效果：\n")

    demo_logger_output()

    print("\n" + "=" * 80)
    print(" " * 25 + "演示完成 - 日志已保存到 spider.log")
    print("=" * 80)
