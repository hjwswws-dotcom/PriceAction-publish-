@echo off
chcp 65001 >nul
echo ============================================
echo    PriceAction Frontend Starter
echo ============================================
echo.
echo  Starting Streamlit frontend...
echo  Access URL: http://localhost:8501
echo ============================================
cd /d "%~dp0"
streamlit run frontend/app.py
pause
