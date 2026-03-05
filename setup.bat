@echo off
setlocal enabledelayedexpansion
title AIWriteX Setup
echo AIWriteX One-Click Setup
echo.
cd /d "%~dp0"
set "PYTHON_EXE="
python --version >nul 2>&1
if !errorlevel! equ 0 (
    set "PYTHON_EXE=python"
) else (
    py --version >nul 2>&1
    if !errorlevel! equ 0 (
        set "PYTHON_EXE=py"
    ) else (
        if exist "%LOCALAPPDATA%\Programs\Python\Python310\python.exe" (
            set "PYTHON_EXE=%LOCALAPPDATA%\Programs\Python\Python310\python.exe"
        )
    )
)
if not defined PYTHON_EXE (
    echo Python not found! Install Python 3.10+ and add to PATH.
    pause
    exit /b 1
)
if not exist ".venv" (
    echo Creating virtual environment...
    "!PYTHON_EXE!" -m venv .venv
)
echo Installing/Updating dependencies...
".venv\Scripts\python.exe" -m pip install --upgrade pip
".venv\Scripts\python.exe" -m pip install -r requirements.txt
echo Installing Playwright browsers...
".venv\Scripts\playwright.exe" install chromium
if not exist ".env" (
    if exist ".env.example" (
        copy ".env.example" ".env" >nul
    )
)
echo.
echo Setup Complete! Run 启动.bat now.
pause
