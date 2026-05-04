"""CLI/CI entry point: apply all pending migrations. Exits 0 on success, 1 on failure."""
from __future__ import annotations

import logging
import os
import sys

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", ".."))

logging.basicConfig(level=logging.INFO, format="%(levelname)s %(message)s")

from backend.db.connection import get_connection
from backend.migrations.run import run_migrations


def _mask_dsn(dsn: str) -> str:
    at = dsn.find("@")
    if at == -1:
        return "postgresql://***"
    scheme_end = dsn.find("://")
    prefix = dsn[: scheme_end + 3] if scheme_end != -1 else ""
    return f"{prefix}***{dsn[at:]}"


def main() -> None:
    dsn = os.getenv("DATABASE_URL")
    if not dsn:
        print("[migrations] ERROR: DATABASE_URL is not set", file=sys.stderr)
        sys.exit(1)

    print("[migrations] starting")
    print(f"[migrations] DATABASE_URL: {_mask_dsn(dsn)}")

    connection = None
    try:
        connection = get_connection()
        print("[migrations] database connection established")

        run_migrations(connection)
        print("[migrations] completed successfully")
        sys.exit(0)
    except Exception as exc:
        print(f"[migrations] FAILED: {exc}", file=sys.stderr)
        sys.exit(1)
    finally:
        if connection is not None:
            try:
                connection.close()
            except Exception:
                pass


if __name__ == "__main__":
    main()
