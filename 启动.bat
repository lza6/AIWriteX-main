@echo off
setlocal enabledelayedexpansion
title AIWriteX Startup
echo AIWriteX Startup
echo.
cd /d "%~dp0"
if not exist ".venv\Scripts\python.exe" (
    python --version >nul 2>&1
    if !errorlevel! equ 0 (
        set "PYTHON_EXE=python"
    ) else (
        echo No Python environment found! Run setup.bat first.
        pause
        exit /b 1
    )
) else (
    set "PYTHON_EXE=.venv\Scripts\python.exe"
)
echo [Run] !PYTHON_EXE! main.py
"!PYTHON_EXE!" main.py
if !errorlevel! neq 0 (
    echo.
    echo Exited with error: !errorlevel!
    pause
)
