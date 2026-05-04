from __future__ import annotations

import logging
from typing import Any

logger = logging.getLogger(__name__)

_STATEMENTS = [
    """
    DO $$
    BEGIN
        IF NOT EXISTS (
            SELECT 1 FROM pg_constraint WHERE conname = 'unique_email'
        ) THEN
            ALTER TABLE users ADD CONSTRAINT unique_email UNIQUE(email);
        END IF;
    END $$
    """,
    """
    DO $$
    BEGIN
        IF NOT EXISTS (
            SELECT 1 FROM pg_constraint WHERE conname = 'users_role_check'
        ) THEN
            ALTER TABLE users ADD CONSTRAINT users_role_check CHECK (role IN ('admin', 'sme'));
        END IF;
    END $$
    """,
]


def run(connection: Any) -> None:
    with connection.cursor() as cur:
        for sql in _STATEMENTS:
            try:
                cur.execute(sql.strip())
            except Exception as exc:
                logger.warning("[migration_005] constraint may already exist: %s", exc)
                connection.rollback()
    connection.commit()
    logger.info("[migration_005] users constraints ensured")
