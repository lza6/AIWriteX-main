@echo off
setlocal enabledelayedexpansion
title AIWriteX Environment Setup
echo AIWriteX Environment Setup
echo.
cd /d "%~dp0"
if not exist ".venv" (
    echo Creating virtual environment...
    python -m venv .venv
)
echo Installing dependencies...
.venv\Scripts\python.exe -m pip install --upgrade pip
.venv\Scripts\python.exe -m pip install -r requirements.txt
echo.
echo Setup completed!
pause
