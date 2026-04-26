#!/usr/bin/env bash
set -euo pipefail

ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"

if [[ -f "$ROOT_DIR/.env" ]]; then
  set -a
  # shellcheck disable=SC1091
  source "$ROOT_DIR/.env"
  set +a
fi

HOST="${BACKEND_HOST:-${HOST:-0.0.0.0}}"
PORT="${BACKEND_PORT:-${PORT:-8000}}"
RELOAD="${RELOAD:-1}"

if ! command -v uvicorn >/dev/null 2>&1; then
  echo "uvicorn is not installed. Install it with: pip install uvicorn fastapi"
  exit 1
fi

if [[ "$RELOAD" == "1" ]]; then
  exec uvicorn backend.main:app --host "$HOST" --port "$PORT" --reload
else
  exec uvicorn backend.main:app --host "$HOST" --port "$PORT"
fi
