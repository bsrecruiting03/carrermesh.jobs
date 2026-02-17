@echo off
echo ===================================================
echo       STARTING JOB BOARD APPLICATION
echo ===================================================

echo.
echo [1/3] Checking Database...
call scripts\start_postgres_docker.bat

echo.
echo [2/3] Starting Backend API (Port 8000)...
start "Job Board Backend" cmd /k "cd api && venv\Scripts\activate && python -m uvicorn main:app --host 127.0.0.1 --port 8000 --reload"

echo.
echo [3/3] Starting Frontend UI (Port 3000)...
start "Job Board Frontend" cmd /k "cd frontend && npm run dev"

echo.
echo [4/4] Starting Discovery Engine (Job Scraper)...
start "Discovery Engine" cmd /k "cd us_ats_jobs && ..\api\venv\Scripts\python main.py && pause"

echo.
echo ===================================================
echo       ALL SYSTEMS GO!
echo ===================================================
echo Backend:  http://127.0.0.1:8000/docs
echo Frontend: http://localhost:3000
echo.
pause
