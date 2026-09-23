@echo off
title Install All Requirements - GovFlow
echo ==========================================================
echo Installing / Verifying All Requirements for GovFlow Mesh
echo ==========================================================

echo [1/3] Checking Python Dependencies...
pip install -r "%~dp0requirements.txt"
if %ERRORLEVEL% NEQ 0 (
    echo [ERROR] Failed installing Python requirements.
    pause
    exit /b %ERRORLEVEL%
)

echo [2/3] Checking Node.js Dependencies...
cd /d "%~dp0frontend\govflow-connect-main\govflow-connect-main"
call npm install
if %ERRORLEVEL% NEQ 0 (
    echo [ERROR] Failed installing Node requirements.
    pause
    exit /b %ERRORLEVEL%
)

echo [3/3] Initializing and Seeding Database...
cd /d "%~dp0backend"
python seed_db.py

echo ==========================================================
echo All requirements installed and verified successfully!
echo You can now run start_all.bat to launch the application.
echo ==========================================================
pause
