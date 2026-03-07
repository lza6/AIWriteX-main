@echo off
setlocal enabledelayedexpansion
chcp 65001 > nul

cd /d "%~dp0"
set "BASE_DIR=%CD%"
if "%BASE_DIR:~-1%" neq "\" set "BASE_DIR=%BASE_DIR%\"
set "TEMP_DIR=%BASE_DIR%_update_temp"

if not exist "%TEMP_DIR%" mkdir "%TEMP_DIR%"

echo ======================================================
echo           AIWriteX 智能更新助手 (Robust Dual-Mode)
echo ======================================================
echo [Debug] Script path: %~dp0
echo [Debug] Working dir: %BASE_DIR%
echo.

if exist "%TEMP_DIR%\extracted" (
    echo [Status] UI triggered update detected, applying...
    for /d %%i in ("%TEMP_DIR%\extracted\*") do set "SRC_DIR=%%~fi"
    goto APPLY_UPDATE
)

echo [Status] Checking for updates (Standalone Mode)...

set "VERSION_FILE="
if exist "%BASE_DIR%src\ai_write_x\version.py" (
    set "VERSION_FILE=%BASE_DIR%src\ai_write_x\version.py"
) else if exist "src\ai_write_x\version.py" (
    set "VERSION_FILE=src\ai_write_x\version.py"
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
echo [Info] Current local version: %LOCAL_V%

echo [Info] Fetching latest version from GitHub...

powershell -command "$ProgressPreference = 'SilentlyContinue'; try { $resp = Invoke-WebRequest -Uri 'https://github.com/lza6/AIWriteX-main/releases' -UseBasicParsing -TimeoutSec 15; if ($resp.Content -match '/lza6/AIWriteX-main/releases/tag/(v?[\d\.]+)') { $matches[1].TrimStart('v') } else { 'PARSE_ERROR' } } catch { 'NET_ERROR' }" > "%TEMP_DIR%\remote_raw.txt"

set /p REMOTE_V=<"%TEMP_DIR%\remote_raw.txt"
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
powershell -command "$l = [version]'!LOCAL_V!'; $r = [version]'!REMOTE_V!'; if ($r -gt $l) { 1 } else { 0 }" > "%TEMP_DIR%\comp_res.txt"
set /p NEEDS_UPDATE=<"%TEMP_DIR%\comp_res.txt"

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
if exist "%TEMP_DIR%\zip" rd /s /q "%TEMP_DIR%\zip"
mkdir "%TEMP_DIR%\zip"

echo [1/4] Downloading update package (Please wait)...
set "DL_URL=https://github.com/lza6/AIWriteX-main/archive/refs/tags/v!REMOTE_V!.zip"
powershell -command "$ProgressPreference = 'SilentlyContinue'; try { Invoke-WebRequest -Uri '%DL_URL%' -OutFile '%TEMP_DIR%\update.zip' -UseBasicParsing } catch { exit 1 }"
if errorlevel 1 (
    echo [Error] Download failed. Check your network.
    pause & exit /b 1
)

echo [2/4] Extracting update files...
if exist "%TEMP_DIR%\extracted" rd /s /q "%TEMP_DIR%\extracted"
powershell -command "Expand-Archive -Path '%TEMP_DIR%\update.zip' -DestinationPath '%TEMP_DIR%\extracted' -Force"
for /d %%i in ("%TEMP_DIR%\extracted\*") do set "SRC_DIR=%%~fi"

:APPLY_UPDATE
echo.
echo [3/4] Replacing files (Ensuring AIWriteX is closed)...
echo.
timeout /t 2 /nobreak > nul
xcopy "%SRC_DIR%\*" "%BASE_DIR%" /E /Y /I /Q
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
