#!/bin/bash
set -e

SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"

echo "==> Pulling latest code..."
git -C "$SCRIPT_DIR" pull

echo "==> Rebuilding and restarting..."
docker compose -f "$SCRIPT_DIR/docker-compose.yml" up -d --build

echo "==> Done."
