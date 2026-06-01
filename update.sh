#!/bin/bash
set -e

SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"
CLIENTS_DIR="${CLIENTS_DIR:-/opt/clients}"
COMPOSE_FILE="$SCRIPT_DIR/docker-compose.yml"
TARGET_CLIENT="$1"

echo "==> Pulling latest code..."
git -C "$SCRIPT_DIR" pull

if [ -n "$TARGET_CLIENT" ]; then
    client_dirs=("$CLIENTS_DIR/$TARGET_CLIENT")
else
    client_dirs=("$CLIENTS_DIR"/*/)
fi

for client_dir in "${client_dirs[@]}"; do
    client_dir="${client_dir%/}"
    env_file="$client_dir/.env"

    if [ ! -f "$env_file" ]; then
        echo "[SKIP] $client_dir — .env not found"
        continue
    fi

    client_name="$(basename "$client_dir")"
    echo "==> Updating $client_name..."

    REPO_DIR="$SCRIPT_DIR" docker compose \
        -f "$COMPOSE_FILE" \
        --env-file "$env_file" \
        --project-directory "$client_dir" \
        up -d --build

    echo "[OK] $client_name updated"
done

echo "==> Done."
