@echo off
setlocal
chcp 65001 >nul
title AIWriteX

echo ==========================================
echo           AIWriteX 启动程序
echo ==========================================
echo.

:: 设置当前目录为脚本目录
cd /d %~dp0

:: 1. 优先尝试本地虚拟环境
if exist ".venv\Scripts\python.exe" (
    echo [状态] 检测到本地虚拟环境，正在启动...
    set PYTHON_EXE=.venv\Scripts\python.exe
) else (
    :: 2. 尝试系统路径中的 python
    python --version >nul 2>&1
    if %errorlevel% equ 0 (
        echo [提醒] 未检测到本地虚拟环境，尝试使用系统 Python 启动...
        set PYTHON_EXE=python
    ) else (
        echo [错误] 未找到可用的 Python 环境！
        echo 请先运行 setup.bat 进行一键配置。
        pause
        exit /b 1
    )
)

:: 启动程序
echo [运行] %PYTHON_EXE% main.py
echo.
%PYTHON_EXE% main.py

if %errorlevel% neq 0 (
    echo.
    echo [提示] 程序异常退出。
    pause
)