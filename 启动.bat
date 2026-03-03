@echo off
chcp 65001 >nul
title AIWriteX
cd /d %~dp0
echo ========================================
echo     AIWriteX
echo ========================================
echo.
"%LOCALAPPDATA%\Programs\Python\Python310\python.exe" main.py
pause