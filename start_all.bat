@echo off
title GovFlow Mesh - Full Stack Launcher
echo ==========================================================
echo Launching GovFlow Inter-Governmental Mesh Full Stack...
echo 1. Starting FastAPI Backend (Port 8000)...
echo 2. Starting Vite Frontend...
echo ==========================================================
start "GovFlow Backend (FastAPI)" cmd /k "cd /d "%~dp0backend" && python -m uvicorn app.main:app --host 127.0.0.1 --port 8000 --reload"
timeout /t 3 /nobreak >nul
start "GovFlow Frontend (Vite)" cmd /k "cd /d "%~dp0frontend\govflow-connect-main\govflow-connect-main" && npm run dev"
echo Both services launched in separate windows!
echo Backend:  http://127.0.0.1:8000 (API Docs: http://127.0.0.1:8000/docs)
echo Frontend: http://localhost:3000 (or http://localhost:5173)
echo ==========================================================
pause
