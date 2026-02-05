@echo off
chcp 65001 >nul
echo ============================================
echo    PriceAction 启动器
echo ============================================
echo.
echo  [1] 启动前端 (Streamlit UI)
echo  [2] 启动后端 (API 服务)
echo  [3] 启动全部 (前后端)
echo  [4] 退出
echo.
echo ============================================

set /p choice=请选择 (1-4):

if "%choice%"=="1" (
    echo.
    echo 正在启动前端...
    echo ============================================
    cd /d "%~dp0"
    streamlit run frontend/app.py
) else if "%choice%"=="2" (
    echo.
    echo 正在启动后端...
    echo ============================================
    cd /d "%~dp0"
    python -m src.main
) else if "%choice%"=="3" (
    echo.
    echo 正在启动后端...
    start "PriceAction Backend" /B cmd /c "python -m src.main"
    timeout /t 3 /nobreak >nul
    echo 正在启动前端...
    cd /d "%~dp0"
    streamlit run frontend/app.py
) else if "%choice%"=="4" (
    exit
) else (
    echo 无效选择!
    pause
)
