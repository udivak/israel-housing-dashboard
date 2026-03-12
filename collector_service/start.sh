#!/usr/bin/env bash
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
cd "$SCRIPT_DIR"

# ── MongoDB ──────────────────────────────────────────────────────────────────

echo "[mongodb] Starting MongoDB via docker compose..."
docker compose up mongo -d

echo "[mongodb] Waiting for MongoDB to be ready..."
until docker compose exec mongo mongosh --quiet --eval "db.adminCommand('ping')" &>/dev/null; do
  sleep 1
done
echo "[mongodb] MongoDB is ready."

# ── FastAPI ──────────────────────────────────────────────────────────────────

if [[ ! -d "$SCRIPT_DIR/venv" ]]; then
  echo "[api] No venv found — creating and installing dependencies..."
  python3 -m venv "$SCRIPT_DIR/venv"
  "$SCRIPT_DIR/venv/bin/pip" install -r "$SCRIPT_DIR/requirements.txt"
  "$SCRIPT_DIR/venv/bin/playwright" install chromium
fi

source "$SCRIPT_DIR/venv/bin/activate"

echo "[api] Starting collector_service on http://localhost:8000 ..."
echo "[api] Docs available at http://localhost:8000/docs"

uvicorn app.main:app --host 0.0.0.0 --port 8000 --reload
