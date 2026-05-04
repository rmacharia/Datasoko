# backend/db/connection.py
from __future__ import annotations

from typing import Any

from backend.storage.postgres_connection import create_postgres_connection


def get_connection() -> Any:
    """Return a psycopg/psycopg2 connection with autocommit=False (default)."""
    conn = create_postgres_connection()
    conn.autocommit = False
    return conn


__all__ = ["create_postgres_connection", "get_connection"]
