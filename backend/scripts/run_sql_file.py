"""Execute a SQL file against the database. Useful for manual schema setup.

Usage:
    DATABASE_URL=postgresql://... python backend/scripts/run_sql_file.py backend/migrations/manual_001_multitenancy.sql
"""
from __future__ import annotations

import os
import sys

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", ".."))


def main() -> None:
    dsn = os.getenv("DATABASE_URL")
    if not dsn:
        print("ERROR: DATABASE_URL environment variable is not set", file=sys.stderr)
        sys.exit(1)

    if len(sys.argv) < 2:
        print("Usage: python backend/scripts/run_sql_file.py <path-to-sql-file>", file=sys.stderr)
        sys.exit(1)

    sql_path = sys.argv[1]
    try:
        with open(sql_path, "r") as f:
            sql = f.read()
    except FileNotFoundError:
        print(f"ERROR: file not found: {sql_path}", file=sys.stderr)
        sys.exit(1)

    try:
        import psycopg2
        conn = psycopg2.connect(dsn)
    except ImportError:
        import psycopg
        conn = psycopg.connect(dsn)

    cur = conn.cursor()
    try:
        cur.execute(sql)
        conn.commit()
        print(f"SQL executed successfully from {sql_path}")
    except Exception as exc:
        conn.rollback()
        print(f"SQL execution failed: {exc}", file=sys.stderr)
        sys.exit(1)
    finally:
        cur.close()
        conn.close()


if __name__ == "__main__":
    main()
