"""
AIWriteX 完整测试套件运行器
运行所有测试并生成详细报告
"""
import os
import sys
import subprocess
import json
from datetime import datetime

# 添加项目根目录到路径
project_root = os.path.dirname(os.path.abspath(__file__))
if project_root not in sys.path:
    sys.path.insert(0, project_root)


def run_tests():
    """运行所有测试"""
    print("=" * 80)
    print("AIWriteX 完整测试套件")
    print("=" * 80)
    print(f"开始时间：{datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    print()
    
    # 测试文件列表
    test_files = [
        # 核心模块测试
        "tests/test_core_basic.py",
        "tests/test_comprehensive_core.py",
        
        # 发布器测试
        "tests/test_publishers_mock.py",
        
        # 数据库测试
        "tests/test_database.py",
        
        # 爬虫和新闻聚合测试
        "tests/test_scrapers_news.py",
        
        # Swarm 智能测试
        "tests/test_swarm_intelligence.py",
        
        # 认知和多模态测试
        "tests/test_cognitive_multimodal.py",
        
        # Web API 测试
        "tests/test_web_api.py",
        
        # 前端 UI 测试
        "tests/test_frontend_ui.py",
        
        # 端到端测试
        "tests/test_end_to_end.py",
        
        # 性能测试
        "tests/test_performance_stress.py",
        
        # 现有测试
        "tests/test_publishers_mock.py",
        "tests/test_performance_detailed.py",
        "tests/test_core_modules.py",
        "tests/test_integration.py",
        "tests/test_utils_tools.py",
        "tests/test_utils_tools_v2.py",
        "tests/test_multi_platform.py",
        "tests/test_v17_features.py",
        "tests/test_v18_features.py",
    ]
    
    # 过滤存在的测试文件
    existing_tests = [f for f in test_files if os.path.exists(os.path.join(project_root, f))]
    
    print(f"找到 {len(existing_tests)} 个测试文件")
    print()
    
    # 运行测试
    cmd = [
        sys.executable, "-m", "pytest",
        *existing_tests,
        "-v",
        "--tb=short",
        f"--cov=src/ai_write_x",
        "--cov-report=term-missing",
        "--cov-report=html:htmlcov",
        "--html=report.html",
        "--self-contained-html",
        "-n", "auto"  # 并行执行
    ]
    
    print("运行测试...")
    print()
    
    result = subprocess.run(cmd, cwd=project_root)
    
    print()
    print("=" * 80)
    print(f"测试完成时间：{datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    print("=" * 80)
    
    return result.returncode


def generate_summary():
    """生成测试摘要"""
    print("\n生成测试摘要...")
    
    summary = {
        "project": "AIWriteX",
        "version": "V19.0",
        "test_date": datetime.now().strftime('%Y-%m-%d %H:%M:%S'),
        "test_files": [],
        "coverage_report": "htmlcov/index.html",
        "html_report": "report.html"
    }
    
    # 统计测试文件
    tests_dir = os.path.join(project_root, "tests")
    for f in os.listdir(tests_dir):
        if f.startswith("test_") and f.endswith(".py"):
            summary["test_files"].append(f)
    
    summary["total_test_files"] = len(summary["test_files"])
    
    # 保存摘要
    summary_file = os.path.join(project_root, "test_summary.json")
    with open(summary_file, 'w', encoding='utf-8') as f:
        json.dump(summary, f, indent=2, ensure_ascii=False)
    
    print(f"测试摘要已保存到：{summary_file}")
    return summary


if __name__ == "__main__":
    exit_code = run_tests()
    generate_summary()
    
    print("\n测试报告已生成:")
    print("- HTML 报告：report.html")
    print("- 覆盖率报告：htmlcov/index.html")
    print("- 测试摘要：test_summary.json")
    
    sys.exit(exit_code)
