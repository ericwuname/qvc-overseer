@echo off
echo ============================================
echo   QVC One-Click Installer (Windows)
echo ============================================
echo.
echo Checking Python...
python --version >nul 2>&1
if errorlevel 1 (
    echo Python not found! Please install Python 3.11+ from https://python.org
    echo Make sure to check "Add Python to PATH" during installation.
    pause
    exit /b 1
)
echo Python found!
echo.
echo Installing QVC...
pip install qvc-overseer
if errorlevel 1 (
    echo Installation failed. Try: pip install qvc-overseer --user
    pause
    exit /b 1
)
echo.
echo ============================================
echo   QVC installed successfully!
echo.
echo   Quick start:
echo   1. cd your-project
echo   2. qvc scan .
echo   3. qvc fix
echo.
echo   Need help?   qvc guide
echo ============================================
pause
