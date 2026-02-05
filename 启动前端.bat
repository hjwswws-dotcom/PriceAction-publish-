@echo off
chcp 65001 >nul
echo ============================================
echo    PriceAction 前端启动器
echo ============================================
echo.
echo  正在启动 Streamlit 前端...
echo  访问地址: http://localhost:8501
echo ============================================
cd /d "%~dp0"
streamlit run frontend/app.py
pause
