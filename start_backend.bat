@echo off
title GovFlow Mesh Backend - FastAPI (Port 8000)
cd /d "%~dp0backend"
echo ==========================================================
echo Starting SIH26129 Inter-Governmental Mesh API Backend...
echo FastAPI + EasyOCR + LayoutLMv3 + spaCy + XGBoost + LightGBM
echo Endpoint: http://127.0.0.1:8000
echo Docs:     http://127.0.0.1:8000/docs
echo ==========================================================
python -m uvicorn app.main:app --host 127.0.0.1 --port 8000 --reload
pause
