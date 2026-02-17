@echo off
echo ===================================================
echo     STARTING FULL ATS SYSTEM (Version 2)
echo ===================================================

echo.
echo [1/6] Checking Database...
call scripts\start_postgres_docker.bat

echo.
echo [2/6] Starting Backend API (Port 8000)...
start "Job Board Backend" cmd /k "cd api && venv\Scripts\activate && python -m uvicorn main:app --host 127.0.0.1 --port 8000 --reload"

echo.
echo [3/6] Starting Frontend UI (Port 3000)...
start "Job Board Frontend" cmd /k "cd frontend && npm run dev"

echo.
echo [4/6] Starting Ingestion Engine (Job Scraper)...
start "Ingestion Engine" cmd /k "cd us_ats_jobs && ..\api\venv\Scripts\python main.py"

echo.
echo [5/6] Launching Enrichment Workers (AI)...
start "Enrichment Workers" cmd /k "cd scripts && ..\api\venv\Scripts\python launch_workers.py"

echo.
echo [6/6] Starting Monitoring Dashboard...
start "System Monitor" cmd /k "cd scripts && ..\api\venv\Scripts\python monitor_enrichment.py"

echo.
echo ===================================================
echo         ALL SYSTEMS LAUNCHED 🚀
echo ===================================================
echo.
echo  > Backend:    http://127.0.0.1:8000/docs
echo  > Frontend:   http://localhost:3000
echo  > Workers:    5 Parallel Processes (Background)
echo  > Dashboard:  Active in separate window
echo.
pause
