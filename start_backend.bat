@echo off
chcp 65001 >nul
echo ============================================
echo    PriceAction Backend Starter
echo ============================================
echo.
echo  Starting backend service...
echo ============================================
cd /d "%~dp0"
python -m src.main --mode backend
pause
