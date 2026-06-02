#!/bin/bash
set -e

SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"

VOLUMES_DIR="$SCRIPT_DIR/../StoreAssistant_volumes/data"

deploy_client() {
  local client_id="$1"
  local env_file="$VOLUMES_DIR/$client_id/.env"

  if [ ! -f "$env_file" ]; then
    echo "Warning: $env_file not found, skipping $client_id"
    return
  fi

  echo "==> Restarting $client_id..."
  docker compose -f "$SCRIPT_DIR/docker-compose.yml" --env-file "$env_file" up -d --build
}

if [ -z "$1" ]; then
  echo "Usage: $0 <CLIENT_ID>"
  echo "       $0 --all"
  exit 1
fi

echo "==> Pulling latest code..."
git -C "$SCRIPT_DIR" pull

if [ "$1" = "--all" ]; then
  for client_dir in "$VOLUMES_DIR"/*/; do
    deploy_client "$(basename "$client_dir")"
  done
else
  deploy_client "$1"
fi

echo "==> Done."
