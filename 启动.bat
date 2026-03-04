@echo off
setlocal enabledelayedexpansion

:: Simple Startup Script for AIWriteX
title AIWriteX Startup

echo ==========================================
echo           AIWriteX Startup
echo ==========================================
echo.

:: Set current directory to script directory
cd /d "%~dp0"

:: 1. Try local virtual environment first
if not exist ".venv\Scripts\python.exe" goto :try_system_python

echo [Status] Local virtual environment detected. Starting...
set "PYTHON_EXE=.venv\Scripts\python.exe"
goto :start_app

:try_system_python
:: 2. Try system python
python --version >nul 2>&1
if !errorlevel! equ 0 (
    echo [Warning] Local venv not found. Using system Python...
    set "PYTHON_EXE=python"
    goto :start_app
)

:: Environment not found
echo [Error] No Python environment found!
echo Please run setup.bat first to configure the project.
pause
exit /b 1

:start_app
:: Start application
echo [Run] !PYTHON_EXE! main.py
echo.
"!PYTHON_EXE!" main.py

if !errorlevel! neq 0 (
    echo.
    echo [Status] Application exited with error code: !errorlevel!
    pause
)