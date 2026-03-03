#!/usr/bin/python
# -*- coding: UTF-8 -*-
# @author:anning
# @email:anningforchina@gmail.com

import asyncio
import logging
import os
import time
from datetime import datetime
from dotenv import load_dotenv

# 导入数据库管理器
from database import db_manager
from logger_utils import logger

# 导入所有爬虫
from ithome import ITHome
from pengpai import PengPai
from wangyi import WangYi
from souhu import SouHu
from tengxunxinwen import TenXuNews
from tengxuntiyu import TenXun
from xinlang import XinLangGuoJi
from zhongguoribao import ChineseDayNews

# 加载.env文件
load_dotenv()

# 配置日志已在logger_utils中完成

# 爬虫列表及其间隔时间
spiders = {
    "ithome": {
        # 爬虫类
        "spider": ITHome(),
        # 运行间隔时间，单位为秒，这里设置为5分钟，即180秒
        "interval": int(os.getenv("ITHOME_INTERVAL", 360)),
        # 上次运行时间，初始化为0，表示还没有运行过
        "last_run": 0,
        # 类别的间隔时间，单位为秒，这里设置为0，表示无间隔
        "class_sleep_time": 0,
        # 文章详情的间隔时间，单位为秒，这里设置为0，表示无间隔
        "info_sleep_time": 0,
    },
    "pengpai": {
        "spider": PengPai(),
        "interval": int(os.getenv("PENGPAI_INTERVAL", 360)),
        "last_run": 0,
        # 类别的间隔时间，单位为秒，这里设置为0，表示无间隔
        "class_sleep_time": 2,
        # 文章详情的间隔时间，单位为秒，这里设置为0，表示无间隔
        "info_sleep_time": 2,
    },
    "wangyi": {
        "spider": WangYi(),
        "interval": int(os.getenv("WANGYI_INTERVAL", 180)),
        "last_run": 0,
        # 类别的间隔时间，单位为秒，这里设置为0，表示无间隔
        "class_sleep_time": 2,
        # 文章详情的间隔时间，单位为秒，这里设置为0，表示无间隔
        "info_sleep_time": 2,
    },
    "souhu": {
        "spider": SouHu(),
        "interval": int(os.getenv("SOUHU_INTERVAL", 180)),
        "last_run": 0,
        # 类别的间隔时间，单位为秒，这里设置为0，表示无间隔
        "class_sleep_time": 2,
        # 文章详情的间隔时间，单位为秒，这里设置为0，表示无间隔
        "info_sleep_time": 5,
    },
    "tengxunxinwen": {
        "spider": TenXuNews(),
        "interval": int(os.getenv("TENGXUNXINWEN_INTERVAL", 180)),
        "last_run": 0,
        # 类别的间隔时间，单位为秒，这里设置为0，表示无间隔
        "class_sleep_time": 0,
        # 文章详情的间隔时间，单位为秒，这里设置为0，表示无间隔
        "info_sleep_time": 0,
    },
    "tengxuntiyu": {
        "spider": TenXun(),
        "interval": int(os.getenv("TENGXUNTIYU_INTERVAL", 180)),
        "last_run": 0,
        # 类别的间隔时间，单位为秒，这里设置为0，表示无间隔
        "class_sleep_time": 0,
        # 文章详情的间隔时间，单位为秒，这里设置为0，表示无间隔
        "info_sleep_time": 0,
    },
    "xinlang": {
        "spider": XinLangGuoJi(),
        "interval": int(os.getenv("XINLANG_INTERVAL", 180)),
        "last_run": 0,
        # 类别的间隔时间，单位为秒，这里设置为0，表示无间隔
        "class_sleep_time": 0,
        # 文章详情的间隔时间，单位为秒，这里设置为0，表示无间隔
        "info_sleep_time": 0,
    },
    "zhongguoribao": {
        "spider": ChineseDayNews(),
        "interval": int(os.getenv("ZHONGGUORIBAO_INTERVAL", 180)),
        "last_run": 0,
        # 类别的间隔时间，单位为秒，这里设置为0，表示无间隔
        "class_sleep_time": 5,
        # 文章详情的间隔时间，单位为秒，这里设置为0，表示无间隔
        "info_sleep_time": 5,
    },
}

# 默认爬取数量限制 None 代表不限制
DEFAULT_LIMIT = int(os.getenv("DEFAULT_LIMIT", 10))


async def init_database():
    """初始化数据库连接"""
    # 使用环境变量配置数据库连接
    db_manager.host = os.getenv("DB_HOST", "localhost")
    db_manager.port = int(os.getenv("DB_PORT", 5432))
    db_manager.user = os.getenv("DB_USER", "anning")
    db_manager.password = os.getenv("DB_PASSWORD", "123456")
    db_manager.database = os.getenv("DB_DATABASE", "article_spider")

    # 创建连接池
    await db_manager.create_pool()
    await db_manager.init_tables()
    logger.success("数据库连接池已创建，数据表已初始化")


async def run_spider(name, spider_info):
    """运行单个爬虫"""
    try:
        logger.info(f"开始运行爬虫: {name}")
        spider = spider_info["spider"]
        saved_count = await spider.crawl_and_save(
            limit=DEFAULT_LIMIT,
            class_sleep_time=spider_info["class_sleep_time"],
            info_sleep_time=spider_info["info_sleep_time"],
        )
        logger.success(f"{name} 爬取完成，保存了 {saved_count} 篇文章")
        # 更新最后运行时间
        spider_info["last_run"] = time.time()
    except Exception as e:
        logger.error(f"{name} 爬取失败: {e}")


async def spider_worker(name, spider_info):
    """爬虫工作协程，负责独立运行和管理单个爬虫"""
    while True:
        current_time = time.time()
        # 检查是否需要运行爬虫
        if current_time - spider_info["last_run"] >= spider_info["interval"]:
            await run_spider(name, spider_info)
            # 运行完爬虫后，直接等待设定的间隔时间
            wait_time = spider_info["interval"]
            logger.progress(f"{name} 下一次运行将在 {wait_time:.2f} 秒后进行")
            await asyncio.sleep(wait_time)
        else:
            # 计算距离下次运行还需要等待的时间
            remaining_time = spider_info["interval"] - (
                current_time - spider_info["last_run"]
            )
            wait_time = max(1, remaining_time)  # 至少等待1秒
            logger.progress(f"{name} 下一次运行将在 {wait_time:.2f} 秒后进行")
            await asyncio.sleep(wait_time)


async def main():
    """主函数，创建并管理所有爬虫协程任务"""
    # 初始化数据库
    await init_database()

    logger.info("开始并发执行爬虫任务")

    try:
        # 创建所有爬虫的工作协程
        tasks = []
        for name, spider_info in spiders.items():
            task = asyncio.create_task(spider_worker(name, spider_info))
            tasks.append(task)

        # 等待所有任务完成（实际上不会完成，因为是无限循环）
        await asyncio.gather(*tasks)

    except (KeyboardInterrupt, SystemExit):
        logger.info("收到退出信号，正在关闭程序...")
    finally:
        # 关闭数据库连接
        await db_manager.close_pool()
        logger.success("数据库连接池已关闭")


if __name__ == "__main__":
    # 打印启动信息
    logger.header("文章爬虫系统启动")
    logger.info(f"当前时间: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    logger.info(f"数据库: {os.getenv('DB_DATABASE')}")
    logger.info(f"爬虫列表: {', '.join(spiders.keys())}")
    logger.separator()

    # 运行主函数
    asyncio.run(main())
