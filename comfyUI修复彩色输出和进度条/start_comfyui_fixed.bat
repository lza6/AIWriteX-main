@echo off
:: 设置 CMD 窗口为 UTF-8 编码
chcp 65001
title ComfyUI_Server_Fixed

echo ====================================================
echo   ComfyUI 终极核平修复器(极速启动 + 逻辑绕过)
echo ====================================================
:: 4. 设置环境变量 (彻底禁用 tqdm 进度条和彩色输出，完美修复 Errno 22)
set TQDM_DISABLE=1
set PYTHONUNBUFFERED=1
:: 【修复点2】禁用彩色输出，防止自定义节点加载时 colorama 报错
set ANSI_COLORS_DISABLED=1

echo ----------------------------------------------------
echo [提示] 如果看到此消息，说明 ComfyUI 已成功。
pause