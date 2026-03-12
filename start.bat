@echo off
setlocal enabledelayedexpansion
cd /d "%~dp0"

echo.
echo  Trade Compliance Copilot - Starting...
echo.

:: Ensure .env exists
if not exist ".env" (
    if exist ".env.example" (
        echo  Creating .env from .env.example...
        copy /y ".env.example" ".env" >nul
    )
)

:: Check Docker is available and daemon is running
docker info >nul 2>&1
if errorlevel 1 goto docker_not_running
goto start_containers

:docker_not_running
set "DOCKER_EXE=C:\Program Files\Docker\Docker\Docker Desktop.exe"
:: Ask user with a popup whether to start Docker Desktop
powershell -NoProfile -Command "[Reflection.Assembly]::LoadWithPartialName('System.Windows.Forms') | Out-Null; $r = [System.Windows.Forms.MessageBox]::Show('Docker Desktop is not running. Start it now?', 'Trade Compliance Copilot', [System.Windows.Forms.MessageBoxButtons]::YesNo); if ($r -eq [System.Windows.Forms.DialogResult]::Yes) { exit 0 } else { exit 1 }"
if errorlevel 1 goto user_declined
if not exist "%DOCKER_EXE%" (
    echo  Docker Desktop not found at expected path. Please start it manually.
    echo  Install: https://docker.com/products/docker-desktop
    echo.
    pause
    exit /b 1
)
echo  Starting Docker Desktop...
start "" "%DOCKER_EXE%"
echo  Waiting for Docker to be ready (up to 2 minutes)...
set wait_count=0
:wait_docker
timeout /t 5 /nobreak >nul
docker info >nul 2>&1
if not errorlevel 1 goto docker_ready
set /a wait_count+=1
if !wait_count! geq 24 (
    echo  Docker did not start in time. Please wait for Docker Desktop to finish starting, then run this script again.
    pause
    exit /b 1
)
goto wait_docker

:docker_ready
echo  Docker is ready.
echo.
goto start_containers

:user_declined
echo  Docker was not started. Start Docker Desktop manually, then run this script again.
echo  Install: https://docker.com/products/docker-desktop
echo.
pause
exit /b 1

:start_containers
:: Prefer "docker compose" (v2), fallback to "docker-compose" (v1)
where docker compose >nul 2>&1
if errorlevel 1 (
    set "COMPOSE_CMD=docker-compose"
) else (
    set "COMPOSE_CMD=docker compose"
)

echo  Building and starting containers...
echo  Dashboard: http://localhost:8501
echo  API docs:  http://localhost:8000/docs
echo  Ollama:    http://localhost:11434
echo.
echo  First run: Ollama downloads Mistral (~4 GB). Can take 3-5 min with little output.
echo  Wait for "mistral ready" and API/dashboard logs, then open the Dashboard URL.
echo.
echo  Press Ctrl+C to stop.
echo  ----------------------------------------------------------------------
echo.

%COMPOSE_CMD% up --build

endlocal
