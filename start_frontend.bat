@echo off
title GovFlow Connect - Frontend (Vite)
cd /d "%~dp0frontend\govflow-connect-main\govflow-connect-main"
echo ==========================================================
echo Starting GovFlow Frontend (Vite + React + TanStack Start)...
echo URL: http://localhost:3000 or http://localhost:5173
echo Proxies /api calls to backend at http://127.0.0.1:8000
echo ==========================================================
npm run dev
pause
