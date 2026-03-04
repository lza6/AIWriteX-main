@echo off
setlocal enabledelayedexpansion

:: Simple Setup Script for AIWriteX
title AIWriteX Setup

echo ==========================================
echo       AIWriteX One-Click Setup
echo ==========================================
echo.

:: Set current directory to script directory
cd /d "%~dp0"

:: 1. Check for Python
echo [Status] Looking for Python environment...

set "PYTHON_EXE="

:: Try Method 1: direct command
python --version >nul 2>&1
if !errorlevel! equ 0 (
    set "PYTHON_EXE=python"
    goto :python_found
)

:: Try Method 2: py launcher
py --version >nul 2>&1
if !errorlevel! equ 0 (
    set "PYTHON_EXE=py"
    goto :python_found
)

:: Try Method 3: common install path
if exist "%LOCALAPPDATA%\Programs\Python\Python310\python.exe" (
    set "PYTHON_EXE=%LOCALAPPDATA%\Programs\Python\Python310\python.exe"
    goto :python_found
)

:: Not found
echo [Error] Python not found! Please install Python 3.10 or higher.
echo Make sure to check "Add Python to PATH" during installation.
echo Download: https://www.python.org/downloads/
pause
exit /b 1

:python_found
echo [Status] Using Python: !PYTHON_EXE!

:: 2. Create virtual environment
if exist ".venv" (
    echo [Status] Virtual environment already exists.
    goto :venv_done
)

echo [Status] Creating virtual environment (.venv)...
"!PYTHON_EXE!" -m venv .venv
if !errorlevel! neq 0 (
    echo [Error] Failed to create virtual environment.
    pause
    exit /b 1
)
echo [Success] Virtual environment created.

:venv_done

:: 3. Install dependencies
echo [Status] Installing/Updating dependencies (this may take a few minutes)...
echo.
".venv\Scripts\python.exe" -m pip install --upgrade pip
".venv\Scripts\python.exe" -m pip install -r requirements.txt
if !errorlevel! neq 0 (
    echo.
    echo [Error] Failed to install dependencies. Please check your internet connection.
    pause
    exit /b 1
)
echo.
echo [Success] Dependencies installed successfully.

:: 4. Initialize configuration
if not exist ".env" (
    if exist ".env.example" (
        echo [Status] Initializing .env file...
        copy ".env.example" ".env" >nul
        echo [Note] .env file created. Please remember to add your API keys.
    )
)

echo.
echo ==========================================
echo       Setup Complete!
echo       You can now run "启动.bat" to start.
echo ==========================================
echo.
pause
