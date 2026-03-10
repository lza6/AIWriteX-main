"""
AIWriteX 配置模块 - 统一配置入口

使用方式:
    from src.ai_write_x.config import Config, get_config, set_config
    
    # 获取配置
    timeout = get_config('api.timeout', default=30)
    
    # 设置配置
    set_config('user.theme', 'dark', scope=ConfigScope.USER)
"""

# 导出原有Config类
from src.ai_write_x.config.config import Config, DEFAULT_TEMPLATE_CATEGORIES

# 导出配置中心
from src.ai_write_x.core.config_center.config_manager import (
    ConfigManager,
    ConfigEntry,
    ConfigScope,
    get_config,
    set_config
)

__all__ = [
    'Config',
    'DEFAULT_TEMPLATE_CATEGORIES',
    'ConfigManager',
    'ConfigEntry',
    'ConfigScope',
    'get_config',
    'set_config'
]
