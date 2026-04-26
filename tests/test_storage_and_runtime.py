from __future__ import annotations

import json
import sys
import types
import unittest
from datetime import date
from unittest.mock import patch

# Provide a lightweight pandas stub for import-time dependency gaps in this environment.
if "pandas" not in sys.modules:
    sys.modules["pandas"] = types.SimpleNamespace(
        read_excel=lambda *args, **kwargs: None,
        read_csv=lambda *args, **kwargs: None,
    )

if "pydantic" not in sys.modules:
    class _BaseModel:
        def __init__(self, **kwargs):
            for key, value in kwargs.items():
                setattr(self, key, value)

        def model_dump(self, mode=None):  # noqa: ARG002
            return dict(self.__dict__)

    def _field(*args, **kwargs):  # noqa: ARG001, ANN001, ANN003
        return None

    sys.modules["pydantic"] = types.SimpleNamespace(BaseModel=_BaseModel, Field=_field)

if "fastapi" not in sys.modules:
    class _HTTPException(Exception):
        def __init__(self, status_code: int, detail: str) -> None:
            super().__init__(detail)
            self.status_code = status_code
            self.detail = detail

    class _FastAPI:
        def __init__(self, *args, **kwargs) -> None:  # noqa: ARG002, ANN001
            return None

        def get(self, *args, **kwargs):  # noqa: ARG002, ANN001
            def _decorator(fn):
                return fn

            return _decorator

        def post(self, *args, **kwargs):  # noqa: ARG002, ANN001
            def _decorator(fn):
                return fn

            return _decorator

        def put(self, *args, **kwargs):  # noqa: ARG002, ANN001
            def _decorator(fn):
                return fn

            return _decorator

        def add_middleware(self, *args, **kwargs) -> None:  # noqa: ARG002, ANN001
            return None

    class _UploadFile:
        filename = "stub"
        file = types.SimpleNamespace(read=lambda: b"")

    def _identity(*args, **kwargs):  # noqa: ARG001, ANN001
        return None

    sys.modules["fastapi"] = types.SimpleNamespace(
        Depends=_identity,
        FastAPI=_FastAPI,
        File=_identity,
        Form=_identity,
        Header=_identity,
        HTTPException=_HTTPException,
        UploadFile=_UploadFile,
    )
    sys.modules["fastapi.middleware"] = types.SimpleNamespace()
    sys.modules["fastapi.middleware.cors"] = types.SimpleNamespace(CORSMiddleware=object)

from backend.ingestion.factory import create_ingestion_runtime
from backend.ingestion.service import IngestionService
from backend.main import WeeklyMetricsRequest, _compute_weekly_metrics
from backend.storage.postgres_ingestion_store import (
    CREATE_TABLE_SQL,
    UPSERT_WEEKLY_PAYLOAD_SQL,
    PostgresIngestionStore,
)


class RecordingCursor:
    def __init__(self, connection: "RecordingConnection") -> None:
        self.connection = connection

    def __enter__(self) -> "RecordingCursor":
        return self

    def __exit__(self, exc_type, exc, tb) -> None:  # type: ignore[no-untyped-def]
        return None

    def execute(self, query: str, params=None) -> None:  # type: ignore[no-untyped-def]
        self.connection.executed.append((query, params))

        if query == UPSERT_WEEKLY_PAYLOAD_SQL and params is not None:
            key = (params[0], params[1], params[2], params[3])
            payload_json = params[4]
            self.connection.rows[key] = payload_json


class RecordingConnection:
    def __init__(self) -> None:
        self.executed: list[tuple[str, tuple | None]] = []
        self.rows: dict[tuple[object, object, object, object], str] = {}
        self.commit_count = 0
        self.rollback_count = 0

    def cursor(self) -> RecordingCursor:
        return RecordingCursor(self)

    def commit(self) -> None:
        self.commit_count += 1

    def rollback(self) -> None:
        self.rollback_count += 1


class StubConnection:
    def __init__(self) -> None:
        self.closed = False

    def close(self) -> None:
        self.closed = True


class StubStore:
    def __init__(self, connection) -> None:  # type: ignore[no-untyped-def]
        self.connection = connection
        self.ensure_table_called = 0

    def ensure_table(self) -> None:
        self.ensure_table_called += 1

    def upsert_weekly_payload(self, **kwargs) -> None:  # type: ignore[no-untyped-def]
        return None


class StubMetricsConnection:
    def __init__(self) -> None:
        self.closed = False

    def close(self) -> None:
        self.closed = True


class StubMetricsStore:
    def __init__(self, payloads: dict[tuple[str, str, date, date], dict]) -> None:
        self.payloads = payloads
        self.ensure_table_called = 0
        self.calls: list[tuple[str, str, date, date]] = []

    def ensure_table(self) -> None:
        self.ensure_table_called += 1

    def get_weekly_payload(
        self,
        *,
        business_id: str,
        dataset: str,
        week_start: date,
        week_end: date,
    ) -> dict | None:
        key = (business_id, dataset, week_start, week_end)
        self.calls.append(key)
        return self.payloads.get(key)


class StorageAndRuntimeTests(unittest.TestCase):
    def test_ensure_table_executes_create_sql_and_commits(self) -> None:
        conn = RecordingConnection()
        store = PostgresIngestionStore(conn)

        store.ensure_table()

        self.assertEqual(conn.commit_count, 1)
        self.assertEqual(conn.rollback_count, 0)
        self.assertEqual(conn.executed[0][0], CREATE_TABLE_SQL)

    def test_upsert_weekly_payload_is_idempotent_on_unique_key(self) -> None:
        conn = RecordingConnection()
        store = PostgresIngestionStore(conn)

        key = ("biz_001", "excel_sales", date(2026, 2, 23), date(2026, 3, 1))

        first_payload = {"records": [{"line_total": 100.0}], "quality": {"quality_score": 90}}
        second_payload = {"records": [{"line_total": 250.0}], "quality": {"quality_score": 95}}

        store.upsert_weekly_payload(
            business_id=key[0],
            dataset=key[1],
            week_start=key[2],
            week_end=key[3],
            payload=first_payload,
        )
        store.upsert_weekly_payload(
            business_id=key[0],
            dataset=key[1],
            week_start=key[2],
            week_end=key[3],
            payload=second_payload,
        )

        self.assertEqual(conn.commit_count, 2)
        self.assertEqual(conn.rollback_count, 0)
        self.assertEqual(len(conn.rows), 1)
        self.assertIn(key, conn.rows)
        self.assertEqual(json.loads(conn.rows[key]), second_payload)
        self.assertIn("ON CONFLICT (business_id, dataset, week_start, week_end)", UPSERT_WEEKLY_PAYLOAD_SQL)

    def test_create_ingestion_runtime_wires_service_and_store_with_ensure_table(self) -> None:
        stub_conn = StubConnection()

        with patch("backend.ingestion.factory.create_postgres_connection", return_value=stub_conn), patch(
            "backend.ingestion.factory.PostgresIngestionStore", StubStore
        ):
            runtime = create_ingestion_runtime(ensure_table=True)

        self.assertIsInstance(runtime.service, IngestionService)
        self.assertIsInstance(runtime.service.store, StubStore)
        self.assertIs(runtime.service.store.connection, stub_conn)
        self.assertEqual(runtime.service.store.ensure_table_called, 1)

        runtime.close()
        self.assertTrue(stub_conn.closed)

    def test_create_ingestion_runtime_skips_ensure_table_when_disabled(self) -> None:
        stub_conn = StubConnection()

        with patch("backend.ingestion.factory.create_postgres_connection", return_value=stub_conn), patch(
            "backend.ingestion.factory.PostgresIngestionStore", StubStore
        ):
            runtime = create_ingestion_runtime(ensure_table=False)

        self.assertIsInstance(runtime.service.store, StubStore)
        self.assertEqual(runtime.service.store.ensure_table_called, 0)

    def test_compute_weekly_metrics_uses_previous_week_payload_when_present(self) -> None:
        week_start = date(2026, 3, 2)
        week_end = date(2026, 3, 8)
        prev_week_start = date(2026, 2, 23)
        prev_week_end = date(2026, 3, 1)
        business_id = "biz_123"

        current_records = [{"sale_date": "2026-03-03", "product_name": "Milk", "line_total": 100.0}]
        previous_records = [{"sale_date": "2026-02-26", "product_name": "Bread", "line_total": 80.0}]

        payloads = {
            (business_id, "excel_sales", week_start, week_end): {"records": current_records},
            (business_id, "excel_sales", prev_week_start, prev_week_end): {"records": previous_records},
        }
        stub_store = StubMetricsStore(payloads=payloads)
        stub_conn = StubMetricsConnection()

        captured_sales_records: list[dict] = []

        def _fake_compute_weekly_metrics(**kwargs):  # type: ignore[no-untyped-def]
            captured_sales_records.extend(kwargs["sales_records"])
            return {
                "week": {
                    "start": kwargs["week_start"].isoformat(),
                    "end": kwargs["week_end"].isoformat(),
                    "previous_start": prev_week_start.isoformat(),
                    "previous_end": prev_week_end.isoformat(),
                },
                "weekly_revenue": 100.0,
                "previous_week_revenue": 80.0,
                "week_over_week_delta_pct": 25.0,
                "top_products": [],
                "slow_movers": [],
                "repeat_customers": 0,
                "avg_transaction_value": 100.0,
                "meta": {"slow_mover_days": 14, "top_n_products": 5, "records_processed": 2},
            }

        request = WeeklyMetricsRequest(
            business_id=business_id,
            week_start=week_start,
            week_end=week_end,
            slow_mover_days=14,
            top_n_products=5,
        )

        with patch("backend.storage.create_postgres_connection", return_value=stub_conn), patch(
            "backend.storage.postgres_ingestion_store.PostgresIngestionStore", return_value=stub_store
        ), patch("backend.metrics.compute_weekly_metrics", side_effect=_fake_compute_weekly_metrics):
            metrics = _compute_weekly_metrics(request)

        self.assertEqual(stub_store.ensure_table_called, 1)
        self.assertTrue(stub_conn.closed)
        self.assertEqual(len(stub_store.calls), 2)
        self.assertEqual(captured_sales_records, current_records + previous_records)
        self.assertEqual(metrics["previous_week_revenue"], 80.0)
