from __future__ import annotations

import logging
from typing import Any

logger = logging.getLogger(__name__)

_DDL = [
    """
    CREATE TABLE IF NOT EXISTS organizations (
        id          TEXT PRIMARY KEY,
        name        TEXT,
        created_at  TIMESTAMPTZ DEFAULT NOW()
    )
    """,
    """
    CREATE TABLE IF NOT EXISTS subscriptions (
        organization_id  TEXT PRIMARY KEY NOT NULL,
        plan             TEXT,
        status           TEXT,
        expiry_date      TIMESTAMPTZ,
        created_at       TIMESTAMPTZ DEFAULT NOW()
    )
    """,
    """
    CREATE TABLE IF NOT EXISTS businesses (
        id               TEXT PRIMARY KEY,
        organization_id  TEXT NOT NULL DEFAULT 'default_org',
        name             TEXT,
        whatsapp_phone   TEXT,
        created_at       TIMESTAMPTZ DEFAULT NOW()
    )
    """,
    """
    CREATE INDEX IF NOT EXISTS idx_businesses_org ON businesses (organization_id)
    """,
    """
    INSERT INTO organizations (id, name)
    VALUES ('default_org', 'Default Organization')
    ON CONFLICT DO NOTHING
    """,
]

_BACKFILL_SQL = """
INSERT INTO businesses (id, organization_id)
SELECT DISTINCT business_id, 'default_org'
FROM ingestion_weekly_payloads
WHERE business_id IS NOT NULL
ON CONFLICT (id) DO NOTHING
""".strip()

_TABLE_EXISTS_SQL = """
SELECT 1 FROM information_schema.tables
WHERE table_schema = 'public' AND table_name = 'ingestion_weekly_payloads'
LIMIT 1
""".strip()


def run(connection: Any) -> None:
    """Apply all DDL for multi-tenancy. Caller (runner) owns commit/rollback."""
    with connection.cursor() as cur:
        for sql in _DDL:
            cur.execute(sql.strip())

        cur.execute(_TABLE_EXISTS_SQL)
        if cur.fetchone() is not None:
            cur.execute(_BACKFILL_SQL)
            logger.info("[migration_001] backfilled businesses from ingestion_weekly_payloads")
        else:
            logger.info("[migration_001] skipped backfill — ingestion_weekly_payloads does not exist yet")
