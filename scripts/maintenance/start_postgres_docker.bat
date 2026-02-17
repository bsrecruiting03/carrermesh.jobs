@echo off
echo Starting PostgreSQL in Docker...
echo.

echo Checking if container exists...
docker start job_board_postgres
if %errorlevel% neq 0 (
    echo Container not found. Creating new container...
    docker run --name job_board_postgres ^
      -e POSTGRES_PASSWORD=postgres ^
      -e POSTGRES_DB=job_board ^
      -p 5432:5432 ^
      -d postgres:16
) else (
    echo Container started - or was already running.
)

echo.
echo Waiting for PostgreSQL to start...
timeout /t 5 /nobreak >nul

echo.
echo Testing connection...
python scripts\setup_postgres.py

echo.
echo Postgres setup flow complete.
timeout /t 2 >nul
