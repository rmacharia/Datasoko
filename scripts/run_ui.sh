#!/usr/bin/env bash
set -euo pipefail

ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"

if [[ -f "$ROOT_DIR/.env" ]]; then
  set -a
  # shellcheck disable=SC1091
  source "$ROOT_DIR/.env"
  set +a
fi

cd "$ROOT_DIR/frontend"

if [[ ! -d node_modules ]]; then
  echo "[ui] installing dependencies"
  npm install
fi

HOST="${FRONTEND_HOST:-${HOST:-0.0.0.0}}"
PORT="${FRONTEND_PORT:-${PORT:-3000}}"

echo "[ui] starting dev server on http://${HOST}:${PORT}"
npm run dev -- --hostname "$HOST" --port "$PORT"
