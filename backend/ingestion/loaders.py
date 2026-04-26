from __future__ import annotations

import logging
from pathlib import Path

import pandas as pd

from backend.validation.normalizers import normalize_excel_sales, normalize_mpesa
from backend.validation.schemas import (
    DatasetType,
    ErrorCode,
    NormalizationResult,
    QualityReport,
    Severity,
    ValidationIssue,
)

logger = logging.getLogger(__name__)

MAX_FILE_SIZE_MB = 25
EXCEL_EXTENSIONS = {".xlsx", ".xls"}
CSV_EXTENSIONS = {".csv"}


def _safe_file_meta(path: Path) -> dict[str, str | int]:
    """Return non-PII metadata safe for logs."""
    stat = path.stat() if path.exists() else None
    return {
        "file_name": path.name,
        "extension": path.suffix.lower(),
        "size_bytes": int(stat.st_size) if stat else 0,
    }


def _quality_for_file_error(dataset: DatasetType) -> QualityReport:
    # 100 - critical(20 for file error) = 80 (Medium) per documented formula.
    return QualityReport(
        dataset=dataset,
        quality_score=80,
        quality_band="Medium",
        row_count=0,
        valid_row_count=0,
        error_count=1,
        warning_count=0,
        top_issues=[],
    )


def _file_error_result(
    *,
    dataset: DatasetType,
    message: str,
    rule_id: str,
    suggestion: str | None = None,
) -> NormalizationResult:
    issue = ValidationIssue(
        error_code=ErrorCode.FILE_READ_ERROR,
        dataset=dataset,
        severity=Severity.ERROR,
        message=message,
        rule_id=rule_id,
        suggestion=suggestion,
    )
    return NormalizationResult(
        dataset=dataset,
        records=[],
        issues=[issue],
        quality=_quality_for_file_error(dataset),
    )


def _validate_file(path: Path, allowed_extensions: set[str], dataset: DatasetType) -> NormalizationResult | None:
    if not path.exists() or not path.is_file():
        return _file_error_result(
            dataset=dataset,
            message=f"Input file not found: {path}",
            rule_id="FILE_READ_002",
            suggestion="Provide a valid local file path.",
        )

    ext = path.suffix.lower()
    if ext not in allowed_extensions:
        return _file_error_result(
            dataset=dataset,
            message=f"Unsupported file extension: {ext}",
            rule_id="FILE_TYPE_001",
            suggestion=f"Use one of: {sorted(allowed_extensions)}",
        )

    size_mb = path.stat().st_size / (1024 * 1024)
    if size_mb > MAX_FILE_SIZE_MB:
        return _file_error_result(
            dataset=dataset,
            message=f"File exceeds max size of {MAX_FILE_SIZE_MB} MB.",
            rule_id="FILE_SIZE_001",
            suggestion="Split the file and upload smaller chunks.",
        )

    return None


def load_excel_sales(path: str | Path, business_currency: str = "KES") -> NormalizationResult:
    file_path = Path(path)
    file_error = _validate_file(file_path, EXCEL_EXTENSIONS, DatasetType.EXCEL_SALES)
    if file_error:
        logger.warning("excel_load_failed", extra={"meta": _safe_file_meta(file_path), "dataset": "excel_sales"})
        return file_error

    try:
        # Read as string first to preserve raw values for deterministic parsing in normalizer.
        df = pd.read_excel(file_path, dtype=str)
    except Exception:
        logger.exception("excel_read_exception", extra={"meta": _safe_file_meta(file_path), "dataset": "excel_sales"})
        return _file_error_result(
            dataset=DatasetType.EXCEL_SALES,
            message="Excel file could not be read.",
            rule_id="FILE_READ_003",
            suggestion="Ensure the file is a valid non-encrypted Excel workbook.",
        )

    result = normalize_excel_sales(df, business_currency=business_currency)
    logger.info(
        "excel_normalized",
        extra={
            "meta": _safe_file_meta(file_path),
            "dataset": "excel_sales",
            "rows": result.quality.row_count,
            "valid_rows": result.quality.valid_row_count,
            "quality_score": result.quality.quality_score,
        },
    )
    return result


def load_mpesa_csv(path: str | Path) -> NormalizationResult:
    file_path = Path(path)
    file_error = _validate_file(file_path, CSV_EXTENSIONS, DatasetType.MPESA)
    if file_error:
        logger.warning("mpesa_load_failed", extra={"meta": _safe_file_meta(file_path), "dataset": "mpesa"})
        return file_error

    try:
        # Keep raw text values for deterministic coercion in normalizer.
        df = pd.read_csv(file_path, dtype=str)
    except Exception:
        logger.exception("mpesa_read_exception", extra={"meta": _safe_file_meta(file_path), "dataset": "mpesa"})
        return _file_error_result(
            dataset=DatasetType.MPESA,
            message="M-Pesa CSV could not be read.",
            rule_id="FILE_READ_003",
            suggestion="Ensure the file is a valid UTF-8 CSV.",
        )

    result = normalize_mpesa(df)
    logger.info(
        "mpesa_normalized",
        extra={
            "meta": _safe_file_meta(file_path),
            "dataset": "mpesa",
            "rows": result.quality.row_count,
            "valid_rows": result.quality.valid_row_count,
            "quality_score": result.quality.quality_score,
        },
    )
    return result
