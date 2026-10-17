@echo off
REM ==============================================================================
REM OpcHub: Windows Quickstart & Container Management Script
REM ==============================================================================

setlocal enabledelayedexpansion

cd /d "%~dp0\.."

if "%1"=="stop" goto stop_docker
if "%1"=="restart" goto restart_docker
if "%1"=="status" goto status_docker
if "%1"=="logs" goto logs_docker
if "%1"=="local" goto start_local
if "%1"=="help" goto show_help

:start_docker
echo ==================================================================
echo   OpcHub: Windows Quickstart
echo ==================================================================
if not exist .env (
    if exist .env.example (
        copy .env.example .env
    )
)
if not exist data mkdir data

docker compose up -d --build
echo.
echo [SUCCESS] OpcHub started successfully!
echo   Web Console : http://localhost:8000/
echo   API Docs    : http://localhost:8000/docs
echo   Health Probe: http://localhost:8000/health
goto end

:stop_docker
docker compose down
echo [SUCCESS] OpcHub containers stopped.
goto end

:restart_docker
docker compose down
docker compose up -d --build
goto end

:status_docker
docker compose ps
goto end

:logs_docker
docker compose logs -f --tail=100
goto end

:start_local
if not exist data mkdir data
set PYTHONPATH=%CD%\backend;%CD%
python -m uvicorn src.main:app --host 0.0.0.0 --port 8000 --app-dir "%CD%\backend"
goto end

:show_help
echo Usage: quickstart.bat [start^|stop^|restart^|status^|logs^|local]
goto end

:end
endlocal
