"""
AIWriteX 多平台发布模块
支持小红书、抖音、知乎、今日头条、百家号等平台发布
"""

# 基础发布器
from src.ai_write_x.tools.publishers.base_publisher import PlaywrightPublisher

# 各平台发布器
from src.ai_write_x.tools.publishers.xiaohongshu_publisher import XiaohongshuPublisher
from src.ai_write_x.tools.publishers.douyin_publisher import DouyinPublisher
from src.ai_write_x.tools.publishers.zhihu_publisher import ZhihuPublisher
from src.ai_write_x.tools.publishers.toutiao_publisher import ToutiaoPublisher
from src.ai_write_x.tools.publishers.baijiahao_publisher import BaijiahaoPublisher

# 多平台发布中心
from src.ai_write_x.tools.publishers.multi_platform_hub import (
    MultiPlatformHub,
    PlatformType,
    PlatformConfig,
    PublishTask,
    get_multi_platform_hub,
    quick_publish
)

__all__ = [
    # 基础类
    'PlaywrightPublisher',
    
    # 平台发布器
    'XiaohongshuPublisher',
    'DouyinPublisher',
    'ZhihuPublisher',
    'ToutiaoPublisher',
    'BaijiahaoPublisher',
    
    # 多平台中心
    'MultiPlatformHub',
    'PlatformType',
    'PlatformConfig',
    'PublishTask',
    'get_multi_platform_hub',
    'quick_publish'
]
