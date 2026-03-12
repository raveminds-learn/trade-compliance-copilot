#!/usr/bin/env bash
set -e
cd "$(dirname "$0")"

echo ""
echo "  Trade Compliance Copilot - Starting..."
echo ""

# Ensure .env exists
if [[ ! -f .env ]]; then
  if [[ -f .env.example ]]; then
    echo "  Creating .env from .env.example..."
    cp .env.example .env
  fi
fi

# Check Docker is available and daemon is running
if ! docker info &>/dev/null; then
  echo "  ERROR: Docker is not running or not installed."
  echo "  - Install Docker: https://docs.docker.com/get-docker/"
  echo "  - Start the Docker daemon, then run this script again."
  echo ""
  exit 1
fi

# Prefer "docker compose" (v2), fallback to "docker-compose" (v1)
if docker compose version &>/dev/null; then
  COMPOSE_CMD="docker compose"
else
  COMPOSE_CMD="docker-compose"
fi

echo "  Building and starting containers (first run may take a few minutes)..."
echo "  Dashboard: http://localhost:8501"
echo "  API docs:  http://localhost:8000/docs"
echo "  Ollama:    http://localhost:11434"
echo ""
echo "  Press Ctrl+C to stop."
echo "  ----------------------------------------------------------------------"
echo ""

$COMPOSE_CMD up --build
