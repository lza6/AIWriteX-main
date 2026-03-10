"""
AIWriteX 测试运行器
运行所有测试并生成覆盖率报告
"""
import os
import sys
import subprocess
import argparse

project_root = os.path.dirname(os.path.dirname(__file__))
if project_root not in sys.path:
    sys.path.insert(0, project_root)


def run_tests(test_type="all", coverage=True, verbose=True):
    """
    运行测试
    
    Args:
        test_type: 测试类型 (all/unit/integration/performance)
        coverage: 是否生成覆盖率报告
        verbose: 是否详细输出
    """
    cmd = ["python", "-m", "pytest"]
    
    # 添加测试路径
    if test_type == "unit":
        cmd.extend([
            "tests/test_utils_tools.py",
            "tests/test_database.py",
            "tests/test_publishers_mock.py",
            "tests/test_core_modules.py"
        ])
    elif test_type == "integration":
        cmd.extend(["tests/test_integration.py", "-m", "integration"])
    elif test_type == "performance":
        cmd.extend([
            "tests/test_performance_detailed.py",
            "tests/test_performance_optimization.py"
        ])
    else:  # all
        cmd.append("tests/")
    
    # 添加覆盖率
    if coverage:
        cmd.extend([
            "--cov=src/ai_write_x",
            "--cov-report=term-missing",
            "--cov-report=html:htmlcov",
            "--cov-fail-under=90"
        ])
    
    # 添加详细输出
    if verbose:
        cmd.append("-v")
    
    print("=" * 70)
    print(f"运行测试: {test_type}")
    print("=" * 70)
    print(f"命令: {' '.join(cmd)}")
    print()
    
    # 执行测试
    result = subprocess.run(cmd, cwd=project_root)
    
    return result.returncode


def check_coverage():
    """检查覆盖率"""
    print("\n" + "=" * 70)
    print("检查测试覆盖率")
    print("=" * 70)
    
    cmd = [
        "python", "-m", "pytest",
        "tests/",
        "--cov=src/ai_write_x",
        "--cov-report=term",
        "--cov-report=html:htmlcov"
    ]
    
    result = subprocess.run(cmd, cwd=project_root)
    return result.returncode


def main():
    parser = argparse.ArgumentParser(description="AIWriteX 测试运行器")
    parser.add_argument(
        "--type",
        choices=["all", "unit", "integration", "performance"],
        default="all",
        help="测试类型"
    )
    parser.add_argument(
        "--no-coverage",
        action="store_true",
        help="不生成覆盖率报告"
    )
    parser.add_argument(
        "--quiet",
        action="store_true",
        help="静默模式"
    )
    
    args = parser.parse_args()
    
    # 运行测试
    exit_code = run_tests(
        test_type=args.type,
        coverage=not args.no_coverage,
        verbose=not args.quiet
    )
    
    sys.exit(exit_code)


if __name__ == "__main__":
    main()
