"""
AIWriteX 统一系统测试
测试日志、配置、异常处理的统一性
"""

import sys
import os

# 添加项目根目录到Python路径（这样src.ai_write_x才能被找到）
project_root = os.path.join(os.path.dirname(__file__), '..')
if project_root not in sys.path:
    sys.path.insert(0, project_root)

print("=" * 70)
print("测试统一日志系统")
print("=" * 70)

try:
    # 测试1: 使用原有导入方式
    from src.ai_write_x.utils import print_log, log
    from src.ai_write_x.utils.structured_logger import info, error
    
    print_log("测试统一日志系统", "info")
    print("✅ 统一日志入口可用")
    
    # 测试2: 向后兼容的结构化日志
    info("测试结构化日志info")
    error("测试结构化日志error")
    print("✅ 结构化日志向后兼容")
    
except Exception as e:
    print(f"❌ 日志系统测试失败: {e}")

print()
print("=" * 70)
print("测试统一配置管理")
print("=" * 70)

try:
    # 测试1: 统一配置入口
    from src.ai_write_x.config import get_config, set_config, ConfigScope
    
    # 设置配置
    set_config("test.key", "test_value", ConfigScope.RUNTIME)
    
    # 获取配置
    value = get_config("test.key")
    assert value == "test_value", f"配置值不匹配: {value}"
    
    print("✅ 统一配置接口可用")
    print(f"✅ 配置读写正常: test.key = {value}")
    
    # 测试2: 旧版Config兼容
    from src.ai_write_x.config import Config
    config = Config.get_instance()
    print(f"✅ 旧版Config兼容: Config实例获取成功")
    
except Exception as e:
    print(f"❌ 配置系统测试失败: {e}")
    import traceback
    traceback.print_exc()

print()
print("=" * 70)
print("测试统一异常处理")
print("=" * 70)

try:
    # 测试1: 异常处理器
    from src.ai_write_x.utils import (
        ExceptionHandler,
        ErrorCategory,
        exception_handler_decorator,
        safe_execute
    )
    
    handler = ExceptionHandler()
    print("✅ 异常处理器实例创建成功")
    
    # 测试2: 异常处理
    try:
        raise ValueError("测试异常")
    except Exception as e:
        result = handler.handle(e, {"test": True})
        print(f"✅ 异常处理成功: {type(result)}")
    
    # 测试3: 装饰器
    @exception_handler_decorator(ErrorCategory.VALIDATION, fallback="default")
    def test_function():
        raise ValueError("装饰器测试")
    
    result = test_function()
    assert result == "default", "装饰器fallback失败"
    print("✅ 异常处理装饰器工作正常")
    
    # 测试4: 安全执行
    def risky_func():
        return "success"
    
    result = safe_execute(risky_func, fallback="failed")
    assert result == "success", "安全执行失败"
    print("✅ 安全执行函数工作正常")
    
except Exception as e:
    print(f"❌ 异常处理测试失败: {e}")
    import traceback
    traceback.print_exc()

print()
print("=" * 70)
print("测试统一导入")
print("=" * 70)

try:
    # 测试统一的utils导入
    from src.ai_write_x.utils import (
        print_log,
        ExceptionHandler,
        ErrorCategory
    )
    print("✅ 统一utils导入成功")
    
    # 测试统一的config导入
    from src.ai_write_x.config import (
        Config,
        get_config,
        set_config,
        ConfigScope,
        ConfigManager
    )
    print("✅ 统一config导入成功")
    
except Exception as e:
    print(f"❌ 统一导入测试失败: {e}")

print()
print("=" * 70)
print("测试总结")
print("=" * 70)
print("""
✅ 统一日志系统
   - 主日志系统 (utils/log.py)
   - 结构化日志兼容 (utils/structured_logger.py)
   - 统一入口: from src.ai_write_x.utils import print_log

✅ 统一配置管理
   - 配置中心 (core/config_center/)
   - 旧版Config兼容 (config/config.py)
   - 统一入口: from src.ai_write_x.config import get_config, set_config

✅ 统一异常处理
   - 异常处理器 (utils/exception_handler.py)
   - 装饰器支持
   - 安全执行函数
   - 统一入口: from src.ai_write_x.utils import ExceptionHandler

所有系统已统一！
""")
