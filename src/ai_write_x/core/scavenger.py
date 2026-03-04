import os
import time
import asyncio
from pathlib import Path
from src.ai_write_x.utils import log
from src.ai_write_x.utils.path_manager import PathManager

class ScavengerEngine:
    """
    V3 清道夫守护进程 (Scavenger Engine)
    用于自动清理系统过期的缓存文件（HTML、图片、日志等）以及冗余资源。
    """
    
    def __init__(self, check_interval_hours=24):
        self.check_interval = check_interval_hours * 3600
        self.is_running = False
        
        # 定义各类别的过期时间(天数)
        self.expiry_rules = {
            "article": 30,  # 旧的文章产物(html, md)保留30天
            "image": 7,     # 缓存图片保留7天
            "temp": 1,      # 临时文件保留1天
            "logs": 7       # 日志保留7天
        }
        
    async def start_daemon(self):
        self.is_running = True
        log.print_log("🧹 V3 Scavenger Engine (清道夫守护进程) 已启动", "info")
        
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
        """执行全域深度清理"""
        log.print_log("🔍 Scavenger 正在开始全域冗余扫描与清理...", "info")
        
        cleaned_files = 0
        freed_space = 0
        
        # 1. 临时目录清理 (1天)
        temp_dir = PathManager.get_temp_dir()
        c, s = self._clean_directory(temp_dir, self.expiry_rules["temp"], [".tmp", ".temp", ".txt", ".json"])
        cleaned_files += c
        freed_space += s
        
        # 2. 图片缓存清理 (7天)
        # 很多时候图片只是临时生成配图，一旦文章定案可以清理不需要的旧原图
        img_dir = PathManager.get_image_dir()
        c, s = self._clean_directory(img_dir, self.expiry_rules["image"], [".png", ".jpg", ".jpeg", ".webp"])
        cleaned_files += c
        freed_space += s
        
        # 3. 日志清理 (7天)
        log_dir = PathManager.get_log_dir()
        c, s = self._clean_directory(log_dir, self.expiry_rules["logs"], [".log", ".txt"])
        cleaned_files += c
        freed_space += s
        
        # 4. 文章产物清理 (30天) - 可选，防止磁盘写满
        article_dir = PathManager.get_article_dir()
        c, s = self._clean_directory(article_dir, self.expiry_rules["article"], [".html", ".md", ".json"])
        cleaned_files += c
        freed_space += s
        
        # 5. 深层冗余扫描，清理一切不在版本控制规范内的脏文件和空目录
        c, s = self._deep_sweep_empty_dirs(PathManager.get_app_data_dir())
        cleaned_files += c
        
        if cleaned_files > 0:
            mb_freed = freed_space / (1024 * 1024)
            log.print_log(f"✨ Scavenger 清理完成: 删除了 {cleaned_files} 个过期/冗余项目，释放了 {mb_freed:.2f} MB 空间", "success")
        else:
            log.print_log("✨ Scavenger 清理完成: 环境非常纯净，无需清理", "info")

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
