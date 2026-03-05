from __future__ import annotations

import logging
from dataclasses import dataclass
from datetime import date
from pathlib import Path
from typing import Any, Protocol

from .loaders import load_excel_sales, load_mpesa_csv

logger = logging.getLogger(__name__)


class NormalizedPayloadStore(Protocol):
    def upsert_weekly_payload(
        self,
        *,
        business_id: str,
        dataset: str,
        week_start: date,
        week_end: date,
        payload: dict[str, Any],
    ) -> None:
        """Persist a normalized JSONB-ready payload."""


@dataclass(frozen=True)
class IngestionSummary:
    business_id: str
    dataset: str
    week_start: date
    week_end: date
    row_count: int
    valid_row_count: int
    error_count: int
    warning_count: int
    quality_score: int
    quality_band: str
    persisted: bool


@dataclass(frozen=True)
class IngestionBundleResult:
    excel: IngestionSummary | None
    mpesa: IngestionSummary | None


class IngestionService:
    def __init__(self, store: NormalizedPayloadStore | None = None) -> None:
        self.store = store

    def ingest_excel_sales(
        self,
        *,
        business_id: str,
        file_path: str | Path,
        week_start: date,
        week_end: date,
        business_currency: str = "KES",
    ) -> IngestionSummary:
        result = load_excel_sales(file_path, business_currency=business_currency)
        payload = self._build_jsonb_payload(
            business_id=business_id,
            dataset="excel_sales",
            week_start=week_start,
            week_end=week_end,
            source_file=Path(file_path).name,
            result=result.model_dump(mode="json"),
        )
        persisted = self._persist_if_configured(
            business_id=business_id,
            dataset="excel_sales",
            week_start=week_start,
            week_end=week_end,
            payload=payload,
        )
        summary = self._to_summary(
            business_id=business_id,
            dataset="excel_sales",
            week_start=week_start,
            week_end=week_end,
            quality=result.quality.model_dump(mode="json"),
            persisted=persisted,
        )
        self._log_summary_event(summary)
        return summary

    def ingest_mpesa(
        self,
        *,
        business_id: str,
        file_path: str | Path,
        week_start: date,
        week_end: date,
    ) -> IngestionSummary:
        result = load_mpesa_csv(file_path)
        payload = self._build_jsonb_payload(
            business_id=business_id,
            dataset="mpesa",
            week_start=week_start,
            week_end=week_end,
            source_file=Path(file_path).name,
            result=result.model_dump(mode="json"),
        )
        persisted = self._persist_if_configured(
            business_id=business_id,
            dataset="mpesa",
            week_start=week_start,
            week_end=week_end,
            payload=payload,
        )
        summary = self._to_summary(
            business_id=business_id,
            dataset="mpesa",
            week_start=week_start,
            week_end=week_end,
            quality=result.quality.model_dump(mode="json"),
            persisted=persisted,
        )
        self._log_summary_event(summary)
        return summary

    def ingest_weekly_bundle(
        self,
        *,
        business_id: str,
        week_start: date,
        week_end: date,
        excel_file_path: str | Path | None = None,
        mpesa_file_path: str | Path | None = None,
        business_currency: str = "KES",
    ) -> IngestionBundleResult:
        excel_summary: IngestionSummary | None = None
        mpesa_summary: IngestionSummary | None = None

        if excel_file_path:
            excel_summary = self.ingest_excel_sales(
                business_id=business_id,
                file_path=excel_file_path,
                week_start=week_start,
                week_end=week_end,
                business_currency=business_currency,
            )

        if mpesa_file_path:
            mpesa_summary = self.ingest_mpesa(
                business_id=business_id,
                file_path=mpesa_file_path,
                week_start=week_start,
                week_end=week_end,
            )

        return IngestionBundleResult(excel=excel_summary, mpesa=mpesa_summary)

    def _build_jsonb_payload(
        self,
        *,
        business_id: str,
        dataset: str,
        week_start: date,
        week_end: date,
        source_file: str,
        result: dict[str, Any],
    ) -> dict[str, Any]:
        return {
            "business_id": business_id,
            "dataset": dataset,
            "week_start": week_start.isoformat(),
            "week_end": week_end.isoformat(),
            "source_file": source_file,
            "schema_version": result.get("schema_version"),
            "normalizer_version": result.get("normalizer_version"),
            "quality": result.get("quality"),
            "issues": result.get("issues"),
            "records": result.get("records"),
        }

    def _persist_if_configured(
        self,
        *,
        business_id: str,
        dataset: str,
        week_start: date,
        week_end: date,
        payload: dict[str, Any],
    ) -> bool:
        if not self.store:
            return False

        self.store.upsert_weekly_payload(
            business_id=business_id,
            dataset=dataset,
            week_start=week_start,
            week_end=week_end,
            payload=payload,
        )
        return True

    def _to_summary(
        self,
        *,
        business_id: str,
        dataset: str,
        week_start: date,
        week_end: date,
        quality: dict[str, Any],
        persisted: bool,
    ) -> IngestionSummary:
        return IngestionSummary(
            business_id=business_id,
            dataset=dataset,
            week_start=week_start,
            week_end=week_end,
            row_count=int(quality["row_count"]),
            valid_row_count=int(quality["valid_row_count"]),
            error_count=int(quality["error_count"]),
            warning_count=int(quality["warning_count"]),
            quality_score=int(quality["quality_score"]),
            quality_band=str(quality["quality_band"]),
            persisted=persisted,
        )

    def _log_summary_event(self, summary: IngestionSummary) -> None:
        # Safe summary event: no row-level values, names, phone, or transaction details.
        logger.info(
            "ingestion_summary",
            extra={
                "business_id": summary.business_id,
                "dataset": summary.dataset,
                "week_start": summary.week_start.isoformat(),
                "week_end": summary.week_end.isoformat(),
                "row_count": summary.row_count,
                "valid_row_count": summary.valid_row_count,
                "error_count": summary.error_count,
                "warning_count": summary.warning_count,
                "quality_score": summary.quality_score,
                "quality_band": summary.quality_band,
                "persisted": summary.persisted,
            },
        )
