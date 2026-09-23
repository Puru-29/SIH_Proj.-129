# PowerShell Launcher for GovFlow Inter-Governmental Mesh
Write-Host "==========================================================" -ForegroundColor Cyan
Write-Host " Starting GovFlow Full Stack (Backend + Frontend)..." -ForegroundColor Green
Write-Host "==========================================================" -ForegroundColor Cyan

$root = Split-Path -Parent $MyInvocation.MyCommand.Definition
$backendPath = Join-Path $root "backend"
$frontendPath = Join-Path $root "frontend\govflow-connect-main\govflow-connect-main"

Write-Host "[1/2] Starting FastAPI Backend on http://127.0.0.1:8000 ..." -ForegroundColor Yellow
Start-Process powershell -ArgumentList "-NoExit", "-Command", "cd '$backendPath'; python -m uvicorn app.main:app --host 127.0.0.1 --port 8000 --reload"

Start-Sleep -Seconds 3

Write-Host "[2/2] Starting Vite Frontend on http://localhost:3000 ..." -ForegroundColor Yellow
Start-Process powershell -ArgumentList "-NoExit", "-Command", "cd '$frontendPath'; npm run dev"

Write-Host "`nAll services running!" -ForegroundColor Green
Write-Host "  -> Backend API Docs: http://127.0.0.1:8000/docs" -ForegroundColor Cyan
Write-Host "  -> Frontend Portal:  http://localhost:3000 (or http://localhost:5173)" -ForegroundColor Cyan
Write-Host "`nPress any key to close this launcher..." -ForegroundColor Gray
$null = $Host.UI.RawUI.ReadKey("NoEcho,IncludeKeyDown")
