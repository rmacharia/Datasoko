from __future__ import annotations

import argparse
import os
from dataclasses import dataclass
from typing import Any
from urllib.parse import urlsplit

from backend.storage.postgres_connection import create_postgres_connection


TENANT_TABLE_DELETE_ORDER = [
    "ingestion_weekly_payloads",
    "whatsapp_message_log",
    "activity_log",
    "report_schedules",
    "users",
    "subscriptions",
    "businesses",
    "organizations",
]


@dataclass(frozen=True)
class CleanupResult:
    dry_run: bool
    before_counts: dict[str, int]
    after_counts: dict[str, int]


def _existing_tables(connection: Any) -> set[str]:
    with connection.cursor() as cur:
        cur.execute(
            """
            SELECT table_name
            FROM information_schema.tables
            WHERE table_schema = 'public'
              AND table_name = ANY(%s)
            """.strip(),
            (TENANT_TABLE_DELETE_ORDER,),
        )
        return {row[0] for row in cur.fetchall()}


def _table_counts(connection: Any, tables: list[str]) -> dict[str, int]:
    counts: dict[str, int] = {}
    with connection.cursor() as cur:
        for table in tables:
            cur.execute(f"SELECT COUNT(*) FROM {table}")
            row = cur.fetchone()
            counts[table] = int(row[0] if row else 0)
    return counts


def cleanup_database(connection: Any, *, dry_run: bool = True) -> CleanupResult:
    existing = _existing_tables(connection)
    tables = [table for table in TENANT_TABLE_DELETE_ORDER if table in existing]
    before_counts = _table_counts(connection, tables)

    try:
        if not dry_run:
            with connection.cursor() as cur:
                for table in tables:
                    if table == "users":
                        cur.execute("DELETE FROM users WHERE role <> %s", ("super_admin",))
                    else:
                        cur.execute(f"DELETE FROM {table}")

        after_counts = _table_counts(connection, tables)
        if dry_run:
            connection.rollback()
        else:
            connection.commit()
        return CleanupResult(dry_run=dry_run, before_counts=before_counts, after_counts=after_counts)
    except Exception:
        connection.rollback()
        raise


def _target_label() -> str:
    dsn = os.getenv("DATABASE_URL", "").strip()
    if dsn:
        parsed = urlsplit(dsn)
        host = parsed.hostname or "unknown-host"
        database = parsed.path.lstrip("/") or "unknown-db"
        return f"{host}/{database}"
    host = os.getenv("PGHOST", "localhost")
    database = os.getenv("PGDATABASE", "datasoko")
    return f"{host}/{database}"


def _print_result(result: CleanupResult) -> None:
    mode = "DRY RUN" if result.dry_run else "APPLIED"
    print(f"{mode}: {_target_label()}")
    for table in TENANT_TABLE_DELETE_ORDER:
        if table not in result.before_counts:
            continue
        before = result.before_counts[table]
        after = result.after_counts.get(table, before)
        print(f"{table}: {before} -> {after}")


def main() -> int:
    parser = argparse.ArgumentParser(
        description="Clear tenant data while preserving super_admin users."
    )
    parser.add_argument(
        "--yes",
        action="store_true",
        help="Apply deletes. Without this flag the script only reports current counts.",
    )
    args = parser.parse_args()

    connection = create_postgres_connection()
    try:
        result = cleanup_database(connection, dry_run=not args.yes)
        _print_result(result)
    finally:
        connection.close()
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
