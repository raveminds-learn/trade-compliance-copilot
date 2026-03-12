@echo off
cd /d "%~dp0"
if docker compose version >nul 2>&1 (docker compose down) else (docker-compose down)
echo Containers stopped.
