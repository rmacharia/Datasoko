from __future__ import annotations

import logging
from typing import Any

logger = logging.getLogger(__name__)

_STATEMENTS = [
    "ALTER TABLE ingestion_weekly_payloads ADD COLUMN IF NOT EXISTS organization_id TEXT",
    """
    UPDATE ingestion_weekly_payloads p
    SET organization_id = b.organization_id
    FROM businesses b
    WHERE p.business_id = b.id
      AND p.organization_id IS NULL
    """,
    """
    UPDATE ingestion_weekly_payloads
    SET organization_id = 'default_org'
    WHERE organization_id IS NULL
    """,
    "CREATE INDEX IF NOT EXISTS idx_ingestion_payloads_org_biz ON ingestion_weekly_payloads (organization_id, business_id)",
    "CREATE INDEX IF NOT EXISTS idx_ingestion_payloads_org_dataset_week ON ingestion_weekly_payloads (organization_id, dataset, week_start, week_end)",
]


def run(connection: Any) -> None:
    """Add tenant context to payload storage without tightening constraints yet."""
    with connection.cursor() as cur:
        cur.execute(
            "SELECT 1 FROM information_schema.tables "
            "WHERE table_schema = 'public' AND table_name = 'ingestion_weekly_payloads' LIMIT 1"
        )
        if cur.fetchone() is None:
            logger.info("[migration_008] skipped: ingestion_weekly_payloads does not exist yet")
            return

        for sql in _STATEMENTS:
            cur.execute(sql.strip())
    logger.info("[migration_008] ingestion payload tenant columns backfilled/indexed")
