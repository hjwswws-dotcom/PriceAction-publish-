# PriceAction 启动器
Write-Host "============================================" -ForegroundColor Cyan
Write-Host "   PriceAction 启动器" -ForegroundColor Green
Write-Host "============================================" -ForegroundColor Cyan
Write-Host ""
Write-Host " [1] 启动前端 (Streamlit UI)"
Write-Host " [2] 启动后端 (API 服务)"
Write-Host " [3] 启动全部 (前后端)"
Write-Host " [4] 退出"
Write-Host ""
Write-Host "============================================" -ForegroundColor Cyan

$choice = Read-Host "请选择 (1-4)"

switch ($choice) {
    1 {
        Write-Host ""
        Write-Host "正在启动前端..." -ForegroundColor Yellow
        Write-Host "============================================" -ForegroundColor Cyan
        Set-Location -Path (Split-Path -Parent -Path $MyInvocation.MyCommand.Path)
        streamlit run frontend/app.py
    }
    2 {
        Write-Host ""
        Write-Host "正在启动后端..." -ForegroundColor Yellow
        Write-Host "============================================" -ForegroundColor Cyan
        Set-Location -Path (Split-Path -Parent -Path $MyInvocation.MyCommand.Path)
        python -m src.main
    }
    3 {
        Write-Host ""
        Write-Host "正在启动后端..." -ForegroundColor Yellow
        Start-Process -NoNewWindow "python" -ArgumentList "-m", "src.main"
        Start-Sleep -Seconds 3
        Write-Host "正在启动前端..." -ForegroundColor Yellow
        Set-Location -Path (Split-Path -Parent -Path $MyInvocation.MyCommand.Path)
        streamlit run frontend/app.py
    }
    4 {
        Exit
    }
    default {
        Write-Host "无效选择!" -ForegroundColor Red
        Pause
    }
}
