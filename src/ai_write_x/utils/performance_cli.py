"""
AIWriteX 性能诊断命令行工具
Usage: python -m src.ai_write_x.utils.performance_cli [command]
"""
import argparse
import asyncio
import sys
import time
from typing import List

from src.ai_write_x.utils.performance_optimizer import (
    memory_optimizer,
    browser_pool,
    performance_monitor,
    initialize_performance_system,
    shutdown_performance_system
)
from src.ai_write_x.utils import log as lg


def cmd_monitor(args):
    """启动性能监控"""
    lg.print_log("启动性能监控...", "info")
    initialize_performance_system()
    
    try:
        while True:
            time.sleep(10)
            metrics = performance_monitor.get_latest_metrics()
            if metrics:
                lg.print_log(
                    f"[监控] 内存: {metrics.memory_mb:.1f}MB | "
                    f"CPU: {metrics.cpu_percent:.1f}% | "
                    f"浏览器: {metrics.browser_instances}",
                    "info"
                )
    except KeyboardInterrupt:
        lg.print_log("停止监控", "info")
        shutdown_performance_system()


def cmd_status(args):
    """显示当前性能状态"""
    lg.print_log("=" * 60, "info")
    lg.print_log("系统性能状态", "info")
    lg.print_log("=" * 60, "info")
    
    # 内存信息
    memory_mb = memory_optimizer.get_memory_usage_mb()
    system_mem = memory_optimizer.get_system_memory()
    lg.print_log(f"进程内存使用: {memory_mb:.1f} MB", "info")
    lg.print_log(f"系统内存: {system_mem['used_mb']:.0f}/{system_mem['total_mb']:.0f} MB ({system_mem['percent']}%)", "info")
    
    # 浏览器池状态
    pool_stats = browser_pool.get_stats()
    lg.print_log(f"浏览器池: {pool_stats['in_use']}/{pool_stats['max_instances']} 使用中, {pool_stats['pool_size']} 可用", "info")
    
    # 性能报告
    report = performance_monitor.get_report()
    print(report)


def cmd_gc(args):
    """执行垃圾回收"""
    lg.print_log("执行垃圾回收...", "info")
    before = memory_optimizer.get_memory_usage_mb()
    memory_optimizer.force_gc()
    after = memory_optimizer.get_memory_usage_mb()
    freed = before - after
    lg.print_log(f"垃圾回收完成，释放 {freed:.1f} MB", "success" if freed > 0 else "info")


def cmd_test(args):
    """性能测试"""
    lg.print_log("=" * 60, "info")
    lg.print_log("性能测试", "info")
    lg.print_log("=" * 60, "info")
    
    # 测试1: 内存分配测试
    lg.print_log("\n测试1: 内存分配测试", "info")
    before = memory_optimizer.get_memory_usage_mb()
    
    # 分配和释放大对象
    large_list = [i for i in range(1000000)]
    del large_list
    memory_optimizer.force_gc()
    
    after = memory_optimizer.get_memory_usage_mb()
    lg.print_log(f"内存变化: {before:.1f} -> {after:.1f} MB", "info")
    
    # 测试2: 浏览器池测试
    lg.print_log("\n测试2: 浏览器池测试", "info")
    stats = browser_pool.get_stats()
    lg.print_log(f"当前池状态: {stats}", "info")
    
    # 测试3: 多平台发布中心测试
    lg.print_log("\n测试3: 多平台发布中心测试", "info")
    from src.ai_write_x.tools.publishers.multi_platform_hub import MultiPlatformHub
    
    hub = MultiPlatformHub()
    task = hub.create_publish_task(
        title="性能测试",
        content="测试内容",
        images=[]
    )
    lg.print_log(f"创建任务成功: {task.id}", "success")
    
    stats = hub.get_publish_stats()
    lg.print_log(f"发布统计: {stats}", "info")
    
    lg.print_log("\n性能测试完成", "success")


def main():
    """主入口"""
    parser = argparse.ArgumentParser(description="AIWriteX 性能诊断工具")
    subparsers = parser.add_subparsers(dest="command", help="可用命令")
    
    # monitor 命令
    subparsers.add_parser("monitor", help="启动实时性能监控")
    
    # status 命令
    subparsers.add_parser("status", help="显示当前性能状态")
    
    # gc 命令
    subparsers.add_parser("gc", help="执行垃圾回收")
    
    # test 命令
    subparsers.add_parser("test", help="运行性能测试")
    
    args = parser.parse_args()
    
    if args.command == "monitor":
        cmd_monitor(args)
    elif args.command == "status":
        cmd_status(args)
    elif args.command == "gc":
        cmd_gc(args)
    elif args.command == "test":
        cmd_test(args)
    else:
        parser.print_help()


if __name__ == "__main__":
    main()
