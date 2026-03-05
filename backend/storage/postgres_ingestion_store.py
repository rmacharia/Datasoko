from __future__ import annotations

import json
from datetime import date, datetime, timezone
from typing import Any, Protocol


class CursorLike(Protocol):
    def execute(self, query: str, params: tuple[Any, ...] | None = None) -> Any: ...
    def fetchone(self) -> Any: ...
    def fetchall(self) -> Any: ...

    def __enter__(self) -> "CursorLike": ...

    def __exit__(self, exc_type: Any, exc: Any, tb: Any) -> None: ...


class ConnectionLike(Protocol):
    def cursor(self) -> CursorLike: ...

    def commit(self) -> None: ...

    def rollback(self) -> None: ...


CREATE_TABLE_SQL = """
CREATE TABLE IF NOT EXISTS ingestion_weekly_payloads (
    id BIGSERIAL PRIMARY KEY,
    business_id TEXT NOT NULL,
    dataset TEXT NOT NULL,
    week_start DATE NOT NULL,
    week_end DATE NOT NULL,
    payload JSONB NOT NULL,
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    updated_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    UNIQUE (business_id, dataset, week_start, week_end)
);
""".strip()


UPSERT_WEEKLY_PAYLOAD_SQL = """
INSERT INTO ingestion_weekly_payloads (
    business_id,
    dataset,
    week_start,
    week_end,
    payload,
    created_at,
    updated_at
)
VALUES (%s, %s, %s, %s, %s::jsonb, %s, %s)
ON CONFLICT (business_id, dataset, week_start, week_end)
DO UPDATE SET
    payload = EXCLUDED.payload,
    updated_at = EXCLUDED.updated_at;
""".strip()

SELECT_WEEKLY_PAYLOAD_SQL = """
SELECT payload::text
FROM ingestion_weekly_payloads
WHERE business_id = %s
  AND dataset = %s
  AND week_start = %s
  AND week_end = %s
LIMIT 1;
""".strip()

SELECT_PAYLOADS_IN_RANGE_SQL = """
SELECT payload::text
FROM ingestion_weekly_payloads
WHERE business_id = %s
  AND dataset = %s
  AND week_end >= %s
  AND week_start <= %s
ORDER BY week_start ASC, week_end ASC;
""".strip()


class PostgresIngestionStore:
    """PostgreSQL adapter for storing normalized weekly ingestion payloads as JSONB."""

    def __init__(self, connection: ConnectionLike) -> None:
        self.connection = connection

    def ensure_table(self) -> None:
        try:
            with self.connection.cursor() as cur:
                cur.execute(CREATE_TABLE_SQL)
            self.connection.commit()
        except Exception:
            self.connection.rollback()
            raise

    def upsert_weekly_payload(
        self,
        *,
        business_id: str,
        dataset: str,
        week_start: date,
        week_end: date,
        payload: dict[str, Any],
    ) -> None:
        now_utc = datetime.now(timezone.utc)
        payload_json = self._to_json(payload)

        params: tuple[Any, ...] = (
            business_id,
            dataset,
            week_start,
            week_end,
            payload_json,
            now_utc,
            now_utc,
        )

        try:
            with self.connection.cursor() as cur:
                cur.execute(UPSERT_WEEKLY_PAYLOAD_SQL, params)
            self.connection.commit()
        except Exception:
            self.connection.rollback()
            raise

    def _to_json(self, payload: dict[str, Any]) -> str:
        return json.dumps(payload, separators=(",", ":"), ensure_ascii=False)

    def get_weekly_payload(
        self,
        *,
        business_id: str,
        dataset: str,
        week_start: date,
        week_end: date,
    ) -> dict[str, Any] | None:
        with self.connection.cursor() as cur:
            cur.execute(
                SELECT_WEEKLY_PAYLOAD_SQL,
                (business_id, dataset, week_start, week_end),
            )
            row = cur.fetchone()

        if not row:
            return None

        payload_value = row[0]
        if isinstance(payload_value, dict):
            return payload_value
        return json.loads(str(payload_value))

    def get_payloads_in_range(
        self,
        *,
        business_id: str,
        dataset: str,
        range_start: date,
        range_end: date,
    ) -> list[dict[str, Any]]:
        with self.connection.cursor() as cur:
            cur.execute(
                SELECT_PAYLOADS_IN_RANGE_SQL,
                (business_id, dataset, range_start, range_end),
            )
            rows = cur.fetchall()

        payloads: list[dict[str, Any]] = []
        for row in rows or []:
            payload_value = row[0]
            if isinstance(payload_value, dict):
                payloads.append(payload_value)
            else:
                payloads.append(json.loads(str(payload_value)))
        return payloads
