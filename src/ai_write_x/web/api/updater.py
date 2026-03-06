import os
import shutil
import zipfile
import tempfile
import asyncio
import httpx
from pathlib import Path
from fastapi import APIRouter, HTTPException
from pydantic import BaseModel

from src.ai_write_x.version import get_version
from src.ai_write_x.utils import log

router = APIRouter(prefix="/api/system", tags=["System Update"])

# 全局更新状态跟踪
_update_progress = {
    "status": "idle",  # idle, downloading, extracting, success, error
    "progress": 0,    # 0-100
    "message": "",
    "error": ""
}

class Version:
    """语义化版本号比对类"""
    def __init__(self, version_str):
        self.version_str = str(version_str).strip().lower().lstrip('v')
        self.parts = [int(p) if p.isdigit() else 0 for p in self.version_str.split('.')]
    
    def __lt__(self, other):
        for i in range(max(len(self.parts), len(other.parts))):
            v1 = self.parts[i] if i < len(self.parts) else 0
            v2 = other.parts[i] if i < len(other.parts) else 0
            if v1 < v2: return True
            if v1 > v2: return False
        return False

    def __ne__(self, other):
        return self.version_str != other.version_str

    def __gt__(self, other):
        return other < self

class UpdateCheckResponse(BaseModel):
    has_update: bool
    current_version: str
    latest_version: str
    release_notes: str
    download_url: str

class UpdateRequest(BaseModel):
    download_url: str

GITHUB_RELEASES_URL = "https://github.com/lza6/AIWriteX-main/releases"

@router.get("/check-update", response_model=UpdateCheckResponse)
async def check_update():
    """检查是否有新版本 (通过爬取 HTML 绕过 API 限制)"""
    current_version = get_version()
    
    try:
        async with httpx.AsyncClient(timeout=15.0, follow_redirects=True) as client:
            # 直接抓取 Releases 页面
            response = await client.get(GITHUB_RELEASES_URL)
            response.raise_for_status()
            html_content = response.text
            
            # 使用正则表达式从 HTML 中提取版本号和下载链接
            # 匹配模式：/lza6/AIWriteX-main/releases/tag/v3.0 或 /lza6/AIWriteX-main/releases/tag/3.0
            import re
            tag_match = re.search(r'\/lza6\/AIWriteX-main\/releases\/tag\/(v?[\d\.]+)', html_content)
            if not tag_match:
                raise Exception("无法从页面中解析到最新版本号")
            
            latest_version = tag_match.group(1).lstrip("v")
            
            # 提取 zipball 链接
            zip_match = re.search(r'\/lza6\/AIWriteX-main\/archive\/refs\/tags\/(v?[\d\.]+)\.zip', html_content)
            if zip_match:
                download_url = f"https://github.com/lza6/AIWriteX-main/archive/refs/tags/{zip_match.group(1)}.zip"
            else:
                # 备选方案：构建链接
                download_url = f"https://github.com/lza6/AIWriteX-main/archive/refs/tags/{tag_match.group(1)}.zip"
            
            # 使用 Version 类进行健壮的版本比对
            try:
                v_current = Version(current_version)
                v_latest = Version(latest_version)
                has_update = v_latest > v_current
            except Exception as ve:
                log.print_log(f"版本解析失败: {ve}", "warning")
                has_update = latest_version and latest_version != current_version
            
            return UpdateCheckResponse(
                has_update=has_update,
                current_version=current_version,
                latest_version=latest_version,
                release_notes="详情请见 GitHub Releases 页面",
                download_url=download_url
            )
    except Exception as e:
        log.print_log(f"版本检测失败 (Scraping): {str(e)}", "error")
        raise HTTPException(status_code=500, detail=f"检查更新失败: {str(e)}")
    except Exception as e:
        log.print_log(f"版本检测失败: {str(e)}", "error")
        raise HTTPException(status_code=500, detail=f"检查更新失败: {str(e)}")

@router.get("/update-progress")
async def get_update_progress():
    """获取当前的下载进度"""
    return _update_progress

@router.post("/update")
async def apply_update(req: UpdateRequest):
    """下载并准备更新 (解压到临时目录)"""
    download_url = req.download_url
    if not download_url:
        raise HTTPException(status_code=400, detail="缺少下载链接")
        
    log.print_log(f"开始更新流程: {download_url}", "info")
    
    try:
        # 使用项目根目录下的临时文件夹，以便让外部批处理脚本访问
        from src.ai_write_x.utils.path_manager import PathManager
        base_dir = PathManager.get_base_dir()
        update_temp_dir = base_dir / "_update_temp"
        
        # 清理旧的更新临时文件夹
        if update_temp_dir.exists():
            shutil.rmtree(update_temp_dir)
        update_temp_dir.mkdir(parents=True, exist_ok=True)
        
        zip_path = update_temp_dir / "update.zip"
        
        # 1. 下载阶段
        global _update_progress
        # 全局更新进度状态
        _update_progress = {
            "status": "idle",
            "progress": 0,
            "message": "",
            "error": None,
            "logs": []  # 新增日志列表
        }
        _update_progress["status"] = "downloading"
        _update_progress["message"] = "正在连接更新服务器..."
        _update_progress["logs"].append("🚀 开始更新流程...")
        _update_progress["logs"].append(f"🔗 下载地址: {download_url}")
        
        async with httpx.AsyncClient(timeout=60.0, follow_redirects=True) as client:
            async with client.stream("GET", download_url) as response:
                response.raise_for_status()
                total_size = int(response.headers.get("content-length", 0))
                downloaded = 0
                
                with open(zip_path, "wb") as f:
                    async for chunk in response.aiter_bytes():
                        f.write(chunk)
                        downloaded += len(chunk)
                        if total_size > 0:
                            progress = int((downloaded / total_size) * 100)
                            if progress != _update_progress["progress"]:
                                _update_progress["progress"] = progress
                                _update_progress["message"] = f"正在下载: {progress}%"
                                if progress % 10 == 0: # 每10%记录一次日志
                                    _update_progress["logs"].append(f"⬇️ 下载进度: {progress}%")
                        else:
                            _update_progress["message"] = f"下载中: {downloaded//1024} KB"
                            
        _update_progress["logs"].append("✅ 下载完成。")
        # 2. 解压阶段
        _update_progress.update({"status": "extracting", "progress": 100, "message": "正在准备更新文件..."})
        _update_progress["logs"].append("📦 正在解压更新包...")
        extract_dir = update_temp_dir / "extracted"
        extract_dir.mkdir(exist_ok=True)
        
        with zipfile.ZipFile(zip_path, 'r') as zip_ref:
            zip_ref.extractall(extract_dir)
            
        # 获取解压后的目录 (GitHub zipball 会嵌套一层目录)
        contents = list(extract_dir.iterdir())
        if not contents or not contents[0].is_dir():
            raise Exception("无法识别的更新包结构")
        source_dir = contents[0]
        _update_progress["logs"].append(f"📂 解压完成，源目录: {source_dir.name}")
        
        # 3. 生成增强型外部更新脚本 (支持双重模式：UI触发 vs 独立运行)
        helper_script_path = base_dir / "一键更新.bat"
        
        # 我们在脚本中动态寻找提取目录下唯一的文件夹
        
        script_content = f"""@echo off
setlocal enabledelayedexpansion
chcp 65001 > nul

cd /d "%~dp0"
set "BASE_DIR=%CD%"
if "%BASE_DIR:~-1%" neq "\\" set "BASE_DIR=%BASE_DIR%\\"
set "TEMP_DIR=%BASE_DIR%_update_temp"

if not exist "%TEMP_DIR%" mkdir "%TEMP_DIR%"

echo ======================================================
echo           AIWriteX 智能更新助手 (Robust Dual-Mode)
echo ======================================================
echo [Debug] Script path: %~dp0
echo [Debug] Working dir: %BASE_DIR%
echo.

if exist "%TEMP_DIR%\\extracted" (
    echo [Status] UI triggered update detected, applying...
    for /d %%i in ("%TEMP_DIR%\\extracted\\*") do set "SRC_DIR=%%~fi"
    goto APPLY_UPDATE
)

echo [Status] Checking for updates (Standalone Mode)...

set "VERSION_FILE="
if exist "%BASE_DIR%src\\ai_write_x\\version.py" (
    set "VERSION_FILE=%BASE_DIR%src\\ai_write_x\\version.py"
) else if exist "src\\ai_write_x\\version.py" (
    set "VERSION_FILE=src\\ai_write_x\\version.py"
)

if "%VERSION_FILE%"=="" (
    echo [Error] Cannot find version.py.
    pause & exit /b 1
)

echo [Check] Found version file: %VERSION_FILE%
for /f "tokens=2 delims==" %%i in ('findstr "__version__" "%VERSION_FILE%"') do set "L_V=%%i"
set "L_V=%L_V:"=%"
set "L_V=%L_V: =%"
set "L_V=%L_V:'=%"
set "LOCAL_V=%L_V%"
echo [Info] Current local version: !LOCAL_V!

echo [Info] Fetching latest version from GitHub...

powershell -command "$ProgressPreference = 'SilentlyContinue'; try {{ $resp = Invoke-WebRequest -Uri 'https://github.com/lza6/AIWriteX-main/releases' -UseBasicParsing -TimeoutSec 15; if ($resp.Content -match '/lza6/AIWriteX-main/releases/tag/(v?[\\d\\.]+)') {{ $matches[1].TrimStart('v') }} else {{ 'PARSE_ERROR' }} }} catch {{ 'NET_ERROR' }}" > "%TEMP_DIR%\\remote_raw.txt"

set /p REMOTE_V=<"%TEMP_DIR%\\remote_raw.txt"
if "!REMOTE_V!"=="" (
    echo [Error] Remote version is empty.
    pause & exit /b 1
)

echo [Debug] Remote info fetched: "!REMOTE_V!"

if "!REMOTE_V!"=="NET_ERROR" (
    echo [Error] Network request failed. Please check your proxy.
    pause & exit /b 1
)

if "!REMOTE_V!"=="PARSE_ERROR" (
    echo [Warning] HTML parsing failed to find version tag.
    pause & exit /b 1
)

echo [Info] Latest remote version: !REMOTE_V!

:: 调用 PowerShell 进行语义化版本对比，只返回 1 或 0
set "NEEDS_UPDATE=0"
powershell -command "$l = [version]'!LOCAL_V!'; $r = [version]'!REMOTE_V!'; if ($r -gt $l) { 1 } else { 0 }" > "%TEMP_DIR%\\comp_res.txt"
set /p NEEDS_UPDATE=<"%TEMP_DIR%\\comp_res.txt"

:: 必须去除空格
set "NEEDS_UPDATE=!NEEDS_UPDATE: =!"

if "!NEEDS_UPDATE!"=="0" (
    echo [Result] You are already on the latest or newer version.
    echo.
    echo ======================================================
    echo           Update process finished.
    echo ======================================================
    pause
    exit /b 0
)

echo.
echo ------------------------------------------------------
echo   New version found: v!REMOTE_V!  (Current: v!LOCAL_V!)
echo ------------------------------------------------------
echo.
set /p "CHOICE=Do you want to start the update process? (Y/N): "
if /i "!CHOICE!" neq "Y" exit /b 0

echo [Info] Preparing workspace...
if exist "%TEMP_DIR%\\zip" rd /s /q "%TEMP_DIR%\\zip"
mkdir "%TEMP_DIR%\\zip"

echo [1/4] Downloading update package (Please wait)...
set "DL_URL=https://github.com/lza6/AIWriteX-main/archive/refs/tags/v!REMOTE_V!.zip"
powershell -command "$ProgressPreference = 'SilentlyContinue'; try {{ Invoke-WebRequest -Uri '%DL_URL%' -OutFile '%TEMP_DIR%\\update.zip' -UseBasicParsing }} catch {{ exit 1 }}"
if errorlevel 1 (
    echo [Error] Download failed. Check your network.
    pause & exit /b 1
)

echo [2/4] Extracting update files...
if exist "%TEMP_DIR%\\extracted" rd /s /q "%TEMP_DIR%\\extracted"
powershell -command "Expand-Archive -Path '%TEMP_DIR%\\update.zip' -DestinationPath '%TEMP_DIR%\\extracted' -Force"
for /d %%i in ("%TEMP_DIR%\\extracted\\*") do set "SRC_DIR=%%~fi"

:APPLY_UPDATE
echo.
echo [3/4] Replacing files (Ensuring AIWriteX is closed)...
echo.
timeout /t 2 /nobreak > nul
xcopy "%SRC_DIR%\\*" "%BASE_DIR%" /E /Y /I /Q
if errorlevel 1 (
    echo [Error] File replacement failed. Process might be locked.
    echo Please close AIWriteX manually and try again.
    pause & exit /b 1
)

echo [4/4] Cleaning up...
rd /s /q "%TEMP_DIR%"

echo.
echo ======================================================
echo           Update Success! Restarting AIWriteX...
echo ======================================================
echo.
if exist "%BASE_DIR%启动.bat" (
    start "" "%BASE_DIR%启动.bat"
) else (
    start "" "%BASE_DIR%start.bat"
)

echo.
echo ======================================================
echo           Update process finished.
echo ======================================================
pause
exit /b 0
"""
        with open(helper_script_path, "w", encoding="utf-8-sig") as f:
            f.write(script_content)

        _update_progress["logs"].append("✨ 核心更新逻辑注入成功")
        _update_progress["logs"].append("🎉 准备就绪，等待用户确认重启...")
            
        _update_progress.update({"status": "ready_to_restart", "progress": 100, "message": "准备就绪，请点击重启完成更新。"})
        return {"status": "success", "message": "文件已准备就绪。"}
        
    except Exception as e:
        _update_progress["logs"].append(f"❌ 更新中断: {str(e)}")
        _update_progress.update({"status": "error", "error": str(e), "message": f"更新失败: {str(e)}"})
        log.print_log(f"更新准备失败: {str(e)}", "error")
        raise HTTPException(status_code=500, detail=f"更新过程发生错误: {str(e)}")

@router.post("/restart-and-update")
async def restart_and_update():
    """退出当前程序并启动外部更新脚本"""
    try:
        from src.ai_write_x.utils.path_manager import PathManager
        base_dir = PathManager.get_base_dir()        # 获取一键更新脚本路径
        helper_script = PathManager.get_app_dir() / "一键更新.bat"
        
        if not helper_script.exists():
            raise HTTPException(status_code=404, detail="更新脚本不存在，请重新执行一键更新")
            
        log.print_log("用户请求重启并完成更新，正在移交控制权...", "info")
        
        # 在 Windows 上启动新进程并立即退出
        import subprocess
        import sys
        
        subprocess.Popen([str(helper_script)], 
                         shell=True, 
                         creationflags=subprocess.CREATE_NEW_CONSOLE)
        
        # 延迟一小会儿后强制退出
        import os
        os._exit(0)
        
    except Exception as e:
        log.print_log(f"重启失败: {e}", "error")
        raise HTTPException(status_code=500, detail=str(e))

