from __future__ import annotations

import logging
from typing import Any

logger = logging.getLogger(__name__)

_CREATE_TABLES = [
    """
    CREATE TABLE IF NOT EXISTS whatsapp_message_log (
        id              BIGSERIAL PRIMARY KEY,
        organization_id TEXT NOT NULL DEFAULT 'default_org',
        business_id     TEXT NOT NULL,
        phone           TEXT NOT NULL,
        message_preview TEXT,
        status          TEXT NOT NULL DEFAULT 'sent',
        provider        TEXT NOT NULL DEFAULT 'twilio',
        provider_sid    TEXT,
        error_detail    TEXT,
        created_at      TIMESTAMPTZ NOT NULL DEFAULT NOW()
    )
    """,
    """
    CREATE TABLE IF NOT EXISTS activity_log (
        id              BIGSERIAL PRIMARY KEY,
        organization_id TEXT NOT NULL DEFAULT 'default_org',
        business_id     TEXT NOT NULL,
        event_type      TEXT NOT NULL,
        message         TEXT NOT NULL,
        status          TEXT NOT NULL DEFAULT 'success',
        metadata_json   JSONB,
        created_at      TIMESTAMPTZ NOT NULL DEFAULT NOW()
    )
    """,
]

_INDEXES = [
    "CREATE INDEX IF NOT EXISTS idx_whatsapp_log_biz ON whatsapp_message_log (business_id, created_at DESC)",
    "CREATE INDEX IF NOT EXISTS idx_whatsapp_log_org ON whatsapp_message_log (organization_id, created_at DESC)",
    "CREATE INDEX IF NOT EXISTS idx_activity_log_biz ON activity_log (business_id, created_at DESC)",
    "CREATE INDEX IF NOT EXISTS idx_activity_log_org ON activity_log (organization_id, created_at DESC)",
]


def run(connection: Any) -> None:
    with connection.cursor() as cur:
        for sql in _CREATE_TABLES:
            cur.execute(sql.strip())
        logger.info("[migration_002] analytics tables created")

        for sql in _INDEXES:
            cur.execute(sql)
        logger.info("[migration_002] indexes created")
