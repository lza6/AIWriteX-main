import os
import time
import shutil
import asyncio
from pathlib import Path
from dataclasses import dataclass, field
from typing import Dict
from src.ai_write_x.utils import log
from src.ai_write_x.utils.path_manager import PathManager


@dataclass
class CleanupReport:
    """V3.1: 结构化清理报告"""
    total_files: int = 0
    total_freed_bytes: int = 0
    duration_seconds: float = 0.0
    categories: Dict[str, int] = field(default_factory=dict)
    disk_free_mb: float = 0.0
    emergency_triggered: bool = False

    @property
    def freed_mb(self):
        return round(self.total_freed_bytes / (1024 * 1024), 2)

    def to_dict(self):
        return {
            "total_files": self.total_files,
            "freed_mb": self.freed_mb,
            "duration_seconds": round(self.duration_seconds, 2),
            "categories": self.categories,
            "disk_free_mb": round(self.disk_free_mb, 1),
            "emergency_triggered": self.emergency_triggered
        }

class CosmicScavenger:
    """
    V10.0 宇宙清道夫 (Cosmic Scavenger)
    治理系统的终极形态。基于“系统熵 (System Entropy)”健康评估模型，实现星系级的冗余坍缩与自平衡。
    """
    
    def __init__(self, check_interval_hours=24):
        self.check_interval = check_interval_hours * 3600
        self.is_running = False
        self.last_report = None  # V3.1: 上次清理报告
        
        # V10.0: 宇宙治理规则 (Cosmic Protocols)
        self.expiry_rules = {
            "article": 7,   # 维持在一周内
            "image": 1,     # 图片仅保留24小时
            "temp": 0.1,    # 2.4小时清理临时文件
            "logs": 2,      # 2天滚动日志
            "ai_models": 3   # 3天清理模型碎片
        }
        self.system_entropy = 0.0  # 系统熵值 (0-100)
        
        try:
            from src.ai_write_x.config.config import Config
            cfg = Config.get_instance()
            custom_rules = cfg.get("scavenger_rules", {})
            if isinstance(custom_rules, dict):
                for key in self.expiry_rules:
                    if key in custom_rules and isinstance(custom_rules[key], (int, float)):
                        self.expiry_rules[key] = int(custom_rules[key])
        except Exception:
            pass  # 配置不可用时使用默认值
        
    async def start_daemon(self):
        self.is_running = True
        log.print_log("🌌 V10.0 Cosmic Scavenger (宇宙清道夫) 已接管星系资源", "info")
        
        # 启动时延时后执行一次清理，避免阻塞首次抢占资源
        await asyncio.sleep(10)
        await self._sweep()
        
        while self.is_running:
            await asyncio.sleep(self.check_interval)
            await self._sweep()
            
    def stop_daemon(self):
        self.is_running = False
        log.print_log("🧹 V3 Scavenger Engine 已停止", "info")
        
    async def _sweep(self):
        """V11.0: 执行宇宙级清理与熵健康评估"""
        from src.ai_write_x.core.monitoring import WorkflowMonitor
        monitor = WorkflowMonitor.get_instance()
        
        start_time = time.time()
        report = CleanupReport()
        log.print_log("🔭 Cosmic Scavenger 正在测量星系红移并调节平衡系数...", "info")
        
        # V11: 获取全局系统熵
        self.system_entropy = monitor.calculate_system_entropy()
        
        # 根据系统熵动态调整清理强度 (Entropy-Driven Thresholds)
        # 熵值越高，清理越激进
        intensity_factor = 1.0
        if self.system_entropy > 80:
            intensity_factor = 0.3 # 仅保留原定时间的 30%
            log.print_log(f"🔥 系统熵值过高 ({self.system_entropy:.1f}%)，清理强度提升至 300%", "warning")
        elif self.system_entropy > 60:
            intensity_factor = 0.6
            
        # 临时映射过期规则，不修改原始 self.expiry_rules(保持配置持久性)
        current_expiry = {k: max(0.1, v * intensity_factor) for k, v in self.expiry_rules.items()}
        
        # V3.1: 磁盘使用监控 — 可用空间<500MB时触发紧急清理
        try:
            disk_usage = shutil.disk_usage(PathManager.get_app_data_dir())
            report.disk_free_mb = disk_usage.free / (1024 * 1024)
            if report.disk_free_mb < 500:
                report.emergency_triggered = True
                log.print_log(f"🚨 空间告急 ({report.disk_free_mb:.1f}MB)，宇宙常数强行坍缩！", "error")
                current_expiry = {k: 0.1 for k in current_expiry} # 强行全部坍缩至 2.4 小时
        except Exception:
            pass
        
        cleaned_files = 0
        freed_space = 0
        
        # 1. 临时目录清理
        temp_dir = PathManager.get_temp_dir()
        c, s = self._clean_directory(temp_dir, current_expiry["temp"], [".tmp", ".temp", ".txt", ".json"])
        cleaned_files += c; freed_space += s
        report.categories["temp"] = c
        
        # 2. 图片缓存清理
        img_dir = PathManager.get_image_dir()
        c, s = self._clean_directory(img_dir, current_expiry["image"], [".png", ".jpg", ".jpeg", ".webp"])
        cleaned_files += c; freed_space += s
        report.categories["image"] = c
        
        # 3. 日志清理
        log_dir = PathManager.get_log_dir()
        c, s = self._clean_directory(log_dir, current_expiry["logs"], [".log", ".txt"])
        cleaned_files += c; freed_space += s
        report.categories["logs"] = c
        
        # 4. 文章产物清理
        article_dir = PathManager.get_article_dir()
        c, s = self._clean_directory(article_dir, current_expiry["article"], [".html", ".md", ".json"])
        cleaned_files += c; freed_space += s
        report.categories["article"] = c
        
        # 5. 深层冗余扫描
        c, s = self._deep_sweep_empty_dirs(PathManager.get_app_data_dir())
        cleaned_files += c
        report.categories["empty_dirs"] = c
        
        report.total_files = cleaned_files
        report.total_freed_bytes = freed_space
        report.duration_seconds = time.time() - start_time
        self.last_report = report
        
        if cleaned_files > 0:
            log.print_log(f"✨ 星系平衡已恢复: 坍缩了 {cleaned_files} 个冗余粒子，系统熵降至预期范围", "success")
        else:
            log.print_log("✨ 星系处于 Zen Mode，无需执行冗余坍缩", "info")
        
        self._evaluate_entropy(report)
        return report

    def _evaluate_entropy(self, report: CleanupReport):
        """V11.0: 系统熵健康评估与持久化治理 (Entropy Stability)"""
        # 计算系统熵：基于清理出的资源量与磁盘剩余空间
        raw_entropy = (report.freed_mb / 500) * 100  # 假设 500MB 为阈值
        self.system_entropy = min(100, raw_entropy + (100 - min(100, report.disk_free_mb / 10)))
        
        # V11: 持久化熵值记录到数据库
        try:
            from src.ai_write_x.database.db_manager import db_manager
            db_manager.save_system_entropy(
                entropy_value=self.system_entropy,
                reasoning_load=report.freed_mb,
                active_agents=report.total_files
            )
        except Exception as e:
            log.print_log(f"Failed to persist entropy state via db_manager: {e}", "warning")
        
        if self.system_entropy > 75:
            log.print_log(f"🌌 [意识枢纽警告] 系统熵值偏高 ({self.system_entropy:.1f}%)，启动星系级自动平衡协议", "warning")
            # V11: 这里可以触发更深层次的自动平衡逻辑，例如压缩旧日志或减少非核心缓存

    def _clean_directory(self, directory: Path, max_age_days: int, extensions: list) -> tuple:
        """清理指定目录中的过期文件"""
        count = 0
        size_saved = 0
        
        if not directory.exists() or not directory.is_dir():
            return count, size_saved
            
        current_time = time.time()
        max_age_seconds = max_age_days * 24 * 3600
        
        for file_path in directory.rglob("*"):
            if file_path.is_file() and file_path.suffix.lower() in extensions:
                try:
                    stats = file_path.stat()
                    # 检查修改时间
                    if current_time - stats.st_mtime > max_age_seconds:
                        size = stats.st_size
                        file_path.unlink()
                        count += 1
                        size_saved += size
                except Exception as e:
                    pass
                    
        return count, size_saved
        
    def _deep_sweep_empty_dirs(self, root_dir: Path) -> tuple:
        """从底向上清理所有空目录（脏数据遗留）"""
        count = 0
        if not root_dir.exists() or not root_dir.is_dir():
            return count, 0
            
        # os.walk bottom-up 模式
        for dirpath, dirnames, filenames in os.walk(root_dir, topdown=False):
            try:
                path_str = str(dirpath)
                
                # 排除根自身以及重要目录结构
                if path_str == str(root_dir):
                    continue
                
                if "\\.git\\" in path_str or "/.git/" in path_str or "templates" in path_str or "config" in path_str:
                    continue
                    
                # 检查目录是否为空
                if not os.listdir(dirpath):
                    os.rmdir(dirpath)
                    count += 1
            except Exception:
                pass
                
        return count, 0
