#!/usr/bin/env bash
set -euo pipefail

MODE="${1:-all}"
ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"

run_unit() {
  echo "[tests] running unit tests"
  python3 -m unittest -q "$ROOT_DIR/tests/test_admin_settings_api.py"
  python3 -m unittest -q "$ROOT_DIR/tests/test_storage_and_runtime.py"
  python3 -m unittest -q "$ROOT_DIR/tests/test_metrics_contracts.py"
}

run_integration() {
  if [[ -z "${DATABASE_URL:-}" ]]; then
    echo "[tests] skipping integration tests: DATABASE_URL is not set"
    return 0
  fi

  echo "[tests] running integration tests"
  python3 -m unittest -q "$ROOT_DIR/tests/test_postgres_integration.py"
}

case "$MODE" in
  unit)
    run_unit
    ;;
  integration)
    run_integration
    ;;
  all)
    run_unit
    run_integration
    ;;
  *)
    echo "usage: $0 [unit|integration|all]"
    exit 2
    ;;
esac
