from __future__ import annotations

import json
import os
import unittest
import uuid
from datetime import date

from backend.storage.postgres_connection import create_postgres_connection
from backend.storage.postgres_ingestion_store import PostgresIngestionStore


@unittest.skipUnless(os.getenv("DATABASE_URL"), "Set DATABASE_URL to run live Postgres integration tests.")
class PostgresIntegrationTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        cls.connection = create_postgres_connection()
        cls.store = PostgresIngestionStore(cls.connection)
        cls.store.ensure_table()

    @classmethod
    def tearDownClass(cls) -> None:
        cls.connection.close()

    def setUp(self) -> None:
        self.business_id = f"it_{uuid.uuid4().hex[:10]}"
        self.dataset = "excel_sales"
        self.week_start = date(2026, 2, 23)
        self.week_end = date(2026, 3, 1)

    def tearDown(self) -> None:
        with self.connection.cursor() as cur:
            cur.execute(
                """
                DELETE FROM ingestion_weekly_payloads
                WHERE business_id = %s AND dataset = %s AND week_start = %s AND week_end = %s
                """.strip(),
                (self.business_id, self.dataset, self.week_start, self.week_end),
            )
        self.connection.commit()

    def _fetch_row(self) -> tuple[int, dict]:
        with self.connection.cursor() as cur:
            cur.execute(
                """
                SELECT COUNT(*)::int, COALESCE(MAX(payload::text), '{}')
                FROM ingestion_weekly_payloads
                WHERE business_id = %s AND dataset = %s AND week_start = %s AND week_end = %s
                """.strip(),
                (self.business_id, self.dataset, self.week_start, self.week_end),
            )
            row = cur.fetchone()

        count = int(row[0])
        payload_text = row[1]
        payload = json.loads(payload_text) if count else {}
        return count, payload

    def test_upsert_inserts_then_updates_on_conflict(self) -> None:
        first_payload = {
            "schema_version": "1.0",
            "normalizer_version": "1.0",
            "quality": {"quality_score": 81, "quality_band": "Medium"},
            "records": [{"invoice_id": "INV-001", "line_total": 100.0}],
            "issues": [],
        }
        second_payload = {
            "schema_version": "1.0",
            "normalizer_version": "1.0",
            "quality": {"quality_score": 94, "quality_band": "High"},
            "records": [{"invoice_id": "INV-001", "line_total": 300.0}],
            "issues": [{"rule_id": "LINE_TOTAL_DIFF_001", "severity": "warning"}],
        }

        self.store.upsert_weekly_payload(
            business_id=self.business_id,
            dataset=self.dataset,
            week_start=self.week_start,
            week_end=self.week_end,
            payload=first_payload,
        )

        count_after_first, payload_after_first = self._fetch_row()
        self.assertEqual(count_after_first, 1)
        self.assertEqual(payload_after_first, first_payload)

        self.store.upsert_weekly_payload(
            business_id=self.business_id,
            dataset=self.dataset,
            week_start=self.week_start,
            week_end=self.week_end,
            payload=second_payload,
        )

        count_after_second, payload_after_second = self._fetch_row()
        self.assertEqual(count_after_second, 1)
        self.assertEqual(payload_after_second, second_payload)

    def test_ensure_table_is_idempotent(self) -> None:
        self.store.ensure_table()
        self.store.ensure_table()

        # No exception is success condition; verify table still reachable.
        with self.connection.cursor() as cur:
            cur.execute("SELECT to_regclass('public.ingestion_weekly_payloads')")
            row = cur.fetchone()
        self.assertEqual(row[0], "ingestion_weekly_payloads")
