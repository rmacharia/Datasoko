from __future__ import annotations

import logging
from typing import Any

logger = logging.getLogger(__name__)

# Phase 1: create tables with minimal primary-key-only structure.
# On a fresh DB these create the full schema; on a drifted DB where the table
# already exists, CREATE TABLE IF NOT EXISTS is a no-op — that's fine because
# phase 2 adds any missing columns.
_CREATE_TABLES = [
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
]

# Phase 2: ensure every expected column exists. Runs unconditionally so that
# partially-created tables (schema drift) get repaired before anything
# references those columns.
_ALTER_COLUMNS = [
    "ALTER TABLE organizations ADD COLUMN IF NOT EXISTS name TEXT",
    "ALTER TABLE organizations ADD COLUMN IF NOT EXISTS created_at TIMESTAMPTZ DEFAULT NOW()",
    "ALTER TABLE subscriptions ADD COLUMN IF NOT EXISTS plan TEXT",
    "ALTER TABLE subscriptions ADD COLUMN IF NOT EXISTS status TEXT",
    "ALTER TABLE subscriptions ADD COLUMN IF NOT EXISTS expiry_date TIMESTAMPTZ",
    "ALTER TABLE subscriptions ADD COLUMN IF NOT EXISTS created_at TIMESTAMPTZ DEFAULT NOW()",
    "ALTER TABLE businesses ADD COLUMN IF NOT EXISTS organization_id TEXT NOT NULL DEFAULT 'default_org'",
    "ALTER TABLE businesses ADD COLUMN IF NOT EXISTS name TEXT",
    "ALTER TABLE businesses ADD COLUMN IF NOT EXISTS whatsapp_phone TEXT",
    "ALTER TABLE businesses ADD COLUMN IF NOT EXISTS created_at TIMESTAMPTZ DEFAULT NOW()",
]

# Phase 3: indexes and seed data — only safe to run AFTER all columns exist.
_POST_ALTER = [
    "CREATE INDEX IF NOT EXISTS idx_businesses_org ON businesses (organization_id)",
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
        for sql in _CREATE_TABLES:
            cur.execute(sql.strip())
        logger.info("[migration_001] phase 1: tables created/verified")

        for sql in _ALTER_COLUMNS:
            cur.execute(sql)
        logger.info("[migration_001] phase 2: %d ALTER statements applied", len(_ALTER_COLUMNS))

        for sql in _POST_ALTER:
            cur.execute(sql.strip())
        logger.info("[migration_001] phase 3: indexes and seed data applied")

        cur.execute(_TABLE_EXISTS_SQL)
        if cur.fetchone() is not None:
            cur.execute(_BACKFILL_SQL)
            logger.info("[migration_001] backfilled businesses from ingestion_weekly_payloads")
        else:
            logger.info("[migration_001] skipped backfill — ingestion_weekly_payloads does not exist yet")
