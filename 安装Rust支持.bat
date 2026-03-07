@echo off
chcp 65001 >nul
echo ========================================
echo   Rust Toolchain Installer (for PyO3)
echo ========================================
echo.

rustc --version >nul 2>&1
if %errorlevel% equ 0 (
    echo [OK] Rust is installed
    rustc --version
    echo.
    goto :install_maturin
)

echo [!] Rust not found, downloading...
echo.
echo [*] Downloading rustup-init.exe...
powershell -Command "Invoke-WebRequest -Uri 'https://win.rustup.rs/x86_64' -OutFile 'rustup-init.exe'"

echo [*] Running installer...
rustup-init.exe -y --default-toolchain stable
del rustup-init.exe

echo.
echo [OK] Rust installed!
rustc --version
echo.

:install_maturin
echo [*] Installing maturin...
.venv\Scripts\pip.exe install maturin --upgrade

echo.
echo ========================================
echo   Done!
echo ========================================
echo.
echo Optional: Build PyO3 extension
echo   maturin develop --release
echo.
pause