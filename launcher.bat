@echo off
chcp 65001 >nul
echo ============================================
echo    PriceAction Launcher
echo ============================================
echo.
echo  [1] Start Frontend (Streamlit UI)
echo  [2] Start Backend (API Service)
echo  [3] Start All (Frontend + Backend)
echo  [4] Exit
echo.
echo ============================================

set /p choice=Enter your choice (1-4):

if "%choice%"=="1" (
    echo.
    echo Starting frontend...
    echo ============================================
    cd /d "%~dp0"
    streamlit run frontend/app.py
) else if "%choice%"=="2" (
    echo.
    echo Starting backend...
    echo ============================================
    cd /d "%~dp0"
    python -m src.main
) else if "%choice%"=="3" (
    echo.
    echo Starting backend...
    start "PriceAction Backend" /B cmd /c "python -m src.main"
    timeout /t 3 /nobreak >nul
    echo Starting frontend...
    cd /d "%~dp0"
    streamlit run frontend/app.py
) else if "%choice%"=="4" (
    exit
) else (
    echo Invalid choice!
    pause
)
