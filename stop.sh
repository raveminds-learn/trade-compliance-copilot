#!/usr/bin/env bash
cd "$(dirname "$0")"
docker compose down 2>/dev/null || docker-compose down
echo "Containers stopped."
