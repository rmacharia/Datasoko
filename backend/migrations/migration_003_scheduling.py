from __future__ import annotations

import logging
from typing import Any

logger = logging.getLogger(__name__)

_CREATE_TABLES = [
    """
    CREATE TABLE IF NOT EXISTS report_schedules (
        id              TEXT PRIMARY KEY,
        organization_id TEXT NOT NULL,
        business_id     TEXT,
        frequency       TEXT NOT NULL,
        time_of_day     TIME NOT NULL,
        day_of_week     INTEGER,
        day_of_month    INTEGER,
        start_date      DATE NOT NULL,
        end_date        DATE,
        send_whatsapp   BOOLEAN NOT NULL DEFAULT TRUE,
        is_active       BOOLEAN NOT NULL DEFAULT TRUE,
        created_at      TIMESTAMPTZ NOT NULL DEFAULT NOW()
    )
    """,
]

_INDEXES = [
    "CREATE INDEX IF NOT EXISTS idx_report_schedules_org ON report_schedules(organization_id)",
    "CREATE INDEX IF NOT EXISTS idx_report_schedules_active ON report_schedules(is_active, frequency)",
]

_ALTER_STATEMENTS = [
    "ALTER TABLE whatsapp_message_log ADD COLUMN IF NOT EXISTS cost_usd NUMERIC(10,4)",
]


def run(connection: Any) -> None:
    with connection.cursor() as cur:
        for sql in _CREATE_TABLES:
            cur.execute(sql.strip())
        logger.info("[migration_003] report_schedules table created")

        for sql in _INDEXES:
            cur.execute(sql)
        logger.info("[migration_003] indexes created")

        for sql in _ALTER_STATEMENTS:
            cur.execute(sql)
        logger.info("[migration_003] whatsapp_message_log cost_usd column added")
