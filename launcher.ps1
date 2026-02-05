# PriceAction Launcher
Write-Host "============================================" -ForegroundColor Cyan
Write-Host "   PriceAction Launcher" -ForegroundColor Green
Write-Host "============================================" -ForegroundColor Cyan
Write-Host ""
Write-Host " [1] Start Frontend (Streamlit UI)"
Write-Host " [2] Start Backend (API Service)"
Write-Host " [3] Start All (Frontend + Backend)"
Write-Host " [4] Exit"
Write-Host ""
Write-Host "============================================" -ForegroundColor Cyan

$choice = Read-Host "Enter your choice (1-4)"

switch ($choice) {
    1 {
        Write-Host ""
        Write-Host "Starting frontend..." -ForegroundColor Yellow
        Write-Host "============================================" -ForegroundColor Cyan
        Set-Location -Path (Split-Path -Parent -Path $MyInvocation.MyCommand.Path)
        streamlit run frontend/app.py
    }
    2 {
        Write-Host ""
        Write-Host "Starting backend..." -ForegroundColor Yellow
        Write-Host "============================================" -ForegroundColor Cyan
        Set-Location -Path (Split-Path -Parent -Path $MyInvocation.MyCommand.Path)
        python -m src.main
    }
    3 {
        Write-Host ""
        Write-Host "Starting backend..." -ForegroundColor Yellow
        Start-Process -NoNewWindow "python" -ArgumentList "-m", "src.main"
        Start-Sleep -Seconds 3
        Write-Host "Starting frontend..." -ForegroundColor Yellow
        Set-Location -Path (Split-Path -Parent -Path $MyInvocation.MyCommand.Path)
        streamlit run frontend/app.py
    }
    4 {
        Exit
    }
    default {
        Write-Host "Invalid choice!" -ForegroundColor Red
        Pause
    }
}
