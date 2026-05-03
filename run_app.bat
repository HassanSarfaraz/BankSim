@echo off
echo ============================================
echo   SecureBank Management System - Launcher
echo ============================================
echo.

REM Check Python
python --version >nul 2>&1
if errorlevel 1 (
    echo [ERROR] Python not found. Install Python 3.11+ first.
    pause
    exit /b 1
)

echo [1/3] Installing dependencies...
pip install -r requirements.txt -q
pip install -r requirements-gui.txt -q
echo      Done.
echo.

echo [2/3] Starting Flask API on port 5000...
start "SecureBank API" cmd /k "python -m backend.app"

echo      Waiting 4 seconds for API to start...
timeout /t 4 /nobreak >nul
echo.

echo [3/3] Launching Tkinter GUI...
start "SecureBank GUI" cmd /k "python -m frontend.main"

echo.
echo ============================================
echo   SecureBank is running!
echo   API: http://localhost:5000/api/health
echo ============================================
echo.
pause
