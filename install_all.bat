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

echo [3/3] Applying database migrations...
cd /d "%~dp0backend"
python -m alembic upgrade head
if %ERRORLEVEL% NEQ 0 (
    echo [ERROR] Could not reach DATABASE_URL or apply migrations.
    echo Configure backend\.env from backend\.env.example and start PostgreSQL.
    pause
    exit /b %ERRORLEVEL%
)

echo ==========================================================
echo Dependencies installed and database schema migrated successfully!
echo You can now run start_all.bat to launch the application.
echo Development fixtures are optional: run python seed_db.py from backend.
echo ==========================================================
pause
