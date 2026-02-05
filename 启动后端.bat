@echo off
chcp 65001 >nul
echo ============================================
echo    PriceAction 后端启动器
echo ============================================
echo.
echo  正在启动后端服务...
echo ============================================
cd /d "%~dp0"
python -m src.main
pause
