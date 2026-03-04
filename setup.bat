@echo off
setlocal enabledelayedexpansion

echo ==========================================
echo       AIWriteX 项目一键配置脚本
echo ==========================================
echo.

:: 1. 检查 Python 是否安装
python --version >nul 2>&1
if %errorlevel% neq 0 (
    echo [错误] 未在系统中找到 Python。请先安装 Python 3.10 或更高版本。
    echo 请访问: https://www.python.org/downloads/
    pause
    exit /b 1
)

:: 2. 创建虚拟环境
if not exist ".venv" (
    echo [状态] 正在创建虚拟环境 (.venv)...
    python -m venv .venv
    if %errorlevel% neq 0 (
        echo [错误] 创建虚拟环境失败。
        pause
        exit /b 1
    )
    echo [成功] 虚拟环境已创建。
) else (
    echo [状态] 虚拟环境已存在，跳过创建。
)

:: 3. 升级 pip 并安装依赖
echo [状态] 正在安装依赖项，请稍候...
echo.
.venv\Scripts\python.exe -m pip install --upgrade pip
.venv\Scripts\python.exe -m pip install -r requirements.txt
if %errorlevel% neq 0 (
    echo.
    echo [错误] 依赖项安装失败。请检查网络连接或 requirements.txt 文件。
    pause
    exit /b 1
)
echo.
echo [成功] 依赖项安装完成。

:: 4. 初始化 .env 文件
if not exist ".env" (
    if exist ".env.example" (
        echo [状态] 正在从 .env.example 生成 .env 文件...
        copy .env.example .env
        echo [提醒] .env 文件已生成，请在其中填入您的 API 密钥。
    ) else (
        echo [提醒] 未找到 .env.example 文件，请手动创建 .env 文件。
    )
) else (
    echo [状态] .env 文件已存在，跳过初始化。
)

echo.
echo ==========================================
echo       配置完成！现在可以运行 启动.bat
echo ==========================================
echo.
pause
