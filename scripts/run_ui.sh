#!/usr/bin/env bash
set -euo pipefail

ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
cd "$ROOT_DIR/frontend"

if [[ ! -d node_modules ]]; then
  echo "[ui] installing dependencies"
  npm install
fi

echo "[ui] starting dev server on http://localhost:3000"
npm run dev
