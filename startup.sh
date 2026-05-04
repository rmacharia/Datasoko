#!/bin/bash
set -e

echo "=== RUNNING DB MIGRATIONS ==="

python backend/scripts/run_migrations.py || echo "[migrations] WARNING: migration script failed but continuing app startup..."

echo "=== STARTING APP ==="

PORT="${PORT:-8000}"
exec gunicorn -k uvicorn.workers.UvicornWorker backend.main:app --bind=0.0.0.0:$PORT --timeout 120
