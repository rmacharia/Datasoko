from __future__ import annotations

import logging
from typing import Any

logger = logging.getLogger(__name__)

_CREATE_TABLES = [
    """
    CREATE TABLE IF NOT EXISTS users (
        id              TEXT PRIMARY KEY,
        email           TEXT UNIQUE NOT NULL,
        password_hash   TEXT NOT NULL,
        organization_id TEXT NOT NULL,
        role            TEXT NOT NULL CHECK (role IN ('admin', 'sme')),
        business_id     TEXT,
        is_active       BOOLEAN NOT NULL DEFAULT TRUE,
        created_at      TIMESTAMPTZ NOT NULL DEFAULT NOW()
    )
    """,
]

_INDEXES = [
    "CREATE INDEX IF NOT EXISTS idx_users_org ON users (organization_id)",
    "CREATE INDEX IF NOT EXISTS idx_users_email ON users (email)",
]


def run(connection: Any) -> None:
    with connection.cursor() as cur:
        for sql in _CREATE_TABLES:
            cur.execute(sql.strip())
        logger.info("[migration_004] users table created")

        for sql in _INDEXES:
            cur.execute(sql)
        logger.info("[migration_004] indexes created")
