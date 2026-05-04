"""CLI/CI entry point: apply all pending migrations. Exits 0 on success, 1 on failure."""
from __future__ import annotations

import logging
import os
import sys

# Ensure repo root is on sys.path when run as `python backend/scripts/run_migrations.py`
sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", ".."))

logging.basicConfig(level=logging.INFO, format="%(levelname)s %(message)s")

from backend.db.connection import get_connection
from backend.migrations.run import run_migrations


def main() -> None:
    if not os.getenv("DATABASE_URL"):
        print("[migrations] ERROR: DATABASE_URL environment variable is not set", file=sys.stderr)
        sys.exit(1)

    print("[migrations] starting")
    connection = get_connection()
    try:
        run_migrations(connection)
        print("[migrations] all migrations applied successfully")
        sys.exit(0)
    except Exception as exc:
        print(f"[migrations] FAILED: {exc}", file=sys.stderr)
        sys.exit(1)
    finally:
        try:
            connection.close()
        except Exception:
            pass


if __name__ == "__main__":
    main()
