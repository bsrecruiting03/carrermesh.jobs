@echo off
echo ===================================================
echo     STARTING SERVER MODE (Exposure: 0.0.0.0)
echo ===================================================
echo WARNING: This will expose your App/API to the local network!
echo Ensure your Firewall allows ports 3000 and 8000.
echo.

echo [1/6] Checking Database...
call scripts\start_postgres_docker.bat

echo.
echo [2/6] Starting Backend API (Public Access)...
start "Job Board Backend (Server)" cmd /k "cd api && venv\Scripts\activate && python -m uvicorn main:app --host 0.0.0.0 --port 8000 --reload"

echo.
echo [3/6] Starting Frontend UI (Public Access)...
REM Passing -H 0.0.0.0 to Next.js via npm
start "Job Board Frontend (Server)" cmd /k "cd frontend && npm run dev -- -H 0.0.0.0"

echo.
echo [4/6] Starting Ingestion Engine...
start "Ingestion Engine" cmd /k "cd us_ats_jobs && ..\api\venv\Scripts\python main.py"

echo.
echo [5/6] Launching Enrichment Workers...
start "Enrichment Workers" cmd /k "cd scripts && ..\api\venv\Scripts\python launch_workers.py"

echo.
echo [6/6] Starting Monitoring Dashboard...
start "System Monitor" cmd /k "cd scripts && ..\api\venv\Scripts\python monitor_enrichment.py"

echo.
echo ===================================================
echo         SERVER MODE ACTIVE 🌐
echo ===================================================
echo.
echo  > Backend:    http://0.0.0.0:8000 (Access via IP)
echo  > Frontend:   http://0.0.0.0:3000 (Access via IP)
echo  > Workers:    Active
echo.
ipconfig | findstr "IPv4"
echo.
pause
