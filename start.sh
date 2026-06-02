#!/bin/bash
set -e

SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"
VOLUMES_DIR="$SCRIPT_DIR/../StoreAssistant_volumes/data"

if [ -z "$1" ]; then
  echo "Usage: $0 <CLIENT_ID>"
  exit 1
fi

CLIENT_ID="$1"
ENV_FILE="$VOLUMES_DIR/$CLIENT_ID/.env"

if [ ! -f "$ENV_FILE" ]; then
  echo "Error: $ENV_FILE not found"
  exit 1
fi

echo "==> Starting $CLIENT_ID..."
docker compose -f "$SCRIPT_DIR/docker-compose.yml" --env-file "$ENV_FILE" up -d

echo "==> Done."
