"""
AIWriteX V18.1 - Config Center
统一配置管理中心 - 集中式配置管理

功能:
1. 集中配置: 统一存储和管理所有配置
2. 热更新: 配置修改实时生效
3. 版本管理: 配置版本控制和回滚
4. 多环境: 支持开发、测试、生产环境
"""

import json
import yaml
from typing import Dict, List, Optional, Any, Callable
from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum
from pathlib import Path
import threading
import hashlib


class ConfigScope(Enum):
    """配置作用域"""
    SYSTEM = "system"       # 系统级
    USER = "user"          # 用户级
    PROJECT = "project"    # 项目级
    RUNTIME = "runtime"    # 运行时


@dataclass
class ConfigEntry:
    """配置项"""
    key: str
    value: Any
    scope: ConfigScope
    description: str = ""
    updated_at: datetime = field(default_factory=datetime.now)
    version: int = 1
    encrypted: bool = False


class ConfigManager:
    """
    配置管理器
    
    集中管理所有配置项
    """
    
    _instance = None
    _lock = threading.Lock()
    
    def __new__(cls):
        if cls._instance is None:
            with cls._lock:
                if cls._instance is None:
                    cls._instance = super().__new__(cls)
                    cls._instance._initialized = False
        return cls._instance
    
    def __init__(self):
        if self._initialized:
            return
            
        self._initialized = True
        self._configs: Dict[str, ConfigEntry] = {}
        self._watchers: Dict[str, List[Callable]] = {}
        self._history: Dict[str, List[ConfigEntry]] = {}
        self._config_file: Optional[Path] = None
    
    def load_from_file(self, config_path: str):
        """从文件加载配置"""
        path = Path(config_path)
        if not path.exists():
            return
        
        self._config_file = path
        
        with open(path, 'r', encoding='utf-8') as f:
            if path.suffix == '.json':
                data = json.load(f)
            elif path.suffix in ['.yaml', '.yml']:
                data = yaml.safe_load(f)
            else:
                return
        
        # 导入配置
        for key, value in data.items():
            self.set(key, value, ConfigScope.PROJECT)
    
    def save_to_file(self, config_path: Optional[str] = None):
        """保存配置到文件"""
        path = Path(config_path) if config_path else self._config_file
        if not path:
            return
        
        data = {
            key: entry.value
            for key, entry in self._configs.items()
            if entry.scope in [ConfigScope.PROJECT, ConfigScope.USER]
        }
        
        with open(path, 'w', encoding='utf-8') as f:
            if path.suffix == '.json':
                json.dump(data, f, indent=2, ensure_ascii=False)
            else:
                yaml.dump(data, f, allow_unicode=True)
                
    def _load_config(self, *args, **kwargs):
        """兼容老版本接口"""
        return self.load_from_file(*args, **kwargs)

    def _save_config(self, *args, **kwargs):
        """兼容老版本接口"""
        return self.save_to_file(*args, **kwargs)
    
    def get(self, key: str, default: Any = None) -> Any:
        """获取配置值"""
        if key in self._configs:
            return self._configs[key].value
        return default
    
    def set(
        self,
        key: str,
        value: Any,
        scope: ConfigScope = ConfigScope.RUNTIME,
        description: str = ""
    ):
        """设置配置值"""
        # 保存历史
        if key in self._configs:
            if key not in self._history:
                self._history[key] = []
            self._history[key].append(self._configs[key])
            # 限制历史数量
            if len(self._history[key]) > 10:
                self._history[key] = self._history[key][-10:]
        
        # 创建或更新配置项
        if key in self._configs:
            entry = self._configs[key]
            entry.value = value
            entry.scope = scope
            entry.version += 1
            entry.updated_at = datetime.now()
        else:
            entry = ConfigEntry(
                key=key,
                value=value,
                scope=scope,
                description=description
            )
            self._configs[key] = entry
        
        # 通知监听器
        self._notify_watchers(key, value)
    
    def delete(self, key: str):
        """删除配置"""
        if key in self._configs:
            del self._configs[key]
    
    def rollback(self, key: str, version: int):
        """回滚到指定版本"""
        if key not in self._history:
            return False
        
        for entry in reversed(self._history[key]):
            if entry.version == version:
                self._configs[key] = entry
                self._notify_watchers(key, entry.value)
                return True
        
        return False
    
    def watch(self, key: str, callback: Callable):
        """监听配置变化"""
        if key not in self._watchers:
            self._watchers[key] = []
        self._watchers[key].append(callback)
    
    def unwatch(self, key: str, callback: Callable):
        """取消监听"""
        if key in self._watchers and callback in self._watchers[key]:
            self._watchers[key].remove(callback)
    
    def _notify_watchers(self, key: str, value: Any):
        """通知监听器"""
        if key in self._watchers:
            for callback in self._watchers[key]:
                try:
                    callback(key, value)
                except:
                    pass
    
    def get_all(self, scope: Optional[ConfigScope] = None) -> Dict[str, Any]:
        """获取所有配置"""
        if scope:
            return {
                k: v.value for k, v in self._configs.items()
                if v.scope == scope
            }
        return {k: v.value for k, v in self._configs.items()}
    
    def export(self) -> Dict:
        """导出配置"""
        return {
            key: {
                "value": entry.value,
                "scope": entry.scope.value,
                "version": entry.version,
                "updated_at": entry.updated_at.isoformat()
            }
            for key, entry in self._configs.items()
        }


# 全局配置管理器
config_manager = ConfigManager()


def get_config(key: str, default: Any = None) -> Any:
    """
    获取配置值 - 统一配置接口
    
    优先从ConfigManager获取，如果不存在则从旧版Config获取
    
    Args:
        key: 配置键名 (支持嵌套，如 'api.timeout')
        default: 默认值
        
    Returns:
        配置值
    """
    # 首先尝试从新的配置中心获取
    value = config_manager.get(key)
    if value is not None:
        return value
    
    # 兼容旧版Config
    try:
        from src.ai_write_x.config.config import Config
        old_config = Config.get_instance()
        
        # 支持嵌套键 (如 'api.timeout')
        keys = key.split('.')
        current = old_config.config
        
        for k in keys:
            if isinstance(current, dict) and k in current:
                current = current[k]
            else:
                return default
        
        return current if current is not None else default
    except Exception:
        return default


def set_config(
    key: str,
    value: Any,
    scope: ConfigScope = ConfigScope.RUNTIME,
    persist: bool = False
):
    """
    设置配置值 - 统一配置接口
    
    Args:
        key: 配置键名
        value: 配置值
        scope: 配置作用域
        persist: 是否持久化到文件
    """
    config_manager.set(key, value, scope)
    
    # 同时更新旧版Config以保持兼容
    if scope in [ConfigScope.PROJECT, ConfigScope.USER]:
        try:
            from src.ai_write_x.config.config import Config
            old_config = Config.get_instance()
            
            # 支持嵌套键
            keys = key.split('.')
            current = old_config.config
            
            for k in keys[:-1]:
                if k not in current:
                    current[k] = {}
                current = current[k]
            
            current[keys[-1]] = value
            
            # 如果需要持久化
            if persist:
                old_config.save_config()
        except Exception:
            pass


def migrate_old_config():
    """
    迁移旧版配置到新的配置中心
    
    在系统启动时调用一次
    """
    try:
        from src.ai_write_x.config.config import Config
        old_config = Config.get_instance()
        
        # 迁移关键配置
        for key, value in old_config.config.items():
            if key not in config_manager._configs:
                config_manager.set(
                    key,
                    value,
                    ConfigScope.PROJECT,
                    f"Migrated from old config"
                )
        
        print_log("配置迁移完成", "info")
    except Exception as e:
        print_log(f"配置迁移失败: {e}", "warning")


# 启动时自动迁移（可选）
# migrate_old_config()
