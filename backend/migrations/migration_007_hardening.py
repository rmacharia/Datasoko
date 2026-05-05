from __future__ import annotations

import logging
from typing import Any

logger = logging.getLogger(__name__)

# Scheduler hardening: track last execution and next projected run per
# schedule so the background worker can dedupe and expose health in the UI.
_SCHEDULE_ALTERS = [
    "ALTER TABLE report_schedules ADD COLUMN IF NOT EXISTS last_run_at TIMESTAMPTZ",
    "ALTER TABLE report_schedules ADD COLUMN IF NOT EXISTS last_status TEXT",
    "ALTER TABLE report_schedules ADD COLUMN IF NOT EXISTS next_run_at TIMESTAMPTZ",
]

# Cost tracking consistency: ensure every WhatsApp row carries a cost we
# can sum in /analytics/costs, even when the provider didn't report one.
_WHATSAPP_DEFAULT_COST = [
    "ALTER TABLE whatsapp_message_log ALTER COLUMN cost_usd SET DEFAULT 0",
    "UPDATE whatsapp_message_log SET cost_usd = 0 WHERE cost_usd IS NULL",
]


def run(connection: Any) -> None:
    with connection.cursor() as cur:
        for sql in _SCHEDULE_ALTERS:
            cur.execute(sql)
        logger.info("[migration_007] report_schedules last_run/next_run columns added")

        for sql in _WHATSAPP_DEFAULT_COST:
            cur.execute(sql)
        logger.info("[migration_007] whatsapp_message_log cost_usd default set to 0")
