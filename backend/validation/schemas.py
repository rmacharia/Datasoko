from __future__ import annotations

from datetime import date, datetime
from enum import Enum
from typing import Any

from pydantic import BaseModel, Field


class DatasetType(str, Enum):
    EXCEL_SALES = "excel_sales"
    MPESA = "mpesa"


class Severity(str, Enum):
    ERROR = "error"
    WARNING = "warning"


class ErrorCode(str, Enum):
    FILE_READ_ERROR = "FILE_READ_ERROR"
    MISSING_REQUIRED_COLUMN = "MISSING_REQUIRED_COLUMN"
    INVALID_DATE = "INVALID_DATE"
    NUMERIC_PARSE_ERROR = "NUMERIC_PARSE_ERROR"
    NEGATIVE_NOT_ALLOWED = "NEGATIVE_NOT_ALLOWED"
    CONFLICTING_AMOUNT_FIELDS = "CONFLICTING_AMOUNT_FIELDS"
    DUPLICATE_ROW = "DUPLICATE_ROW"
    SCHEMA_MISMATCH = "SCHEMA_MISMATCH"


class ValidationIssue(BaseModel):
    error_code: ErrorCode
    dataset: DatasetType
    severity: Severity
    message: str
    row_number: int | None = None
    field: str | None = None
    value: str | None = None
    rule_id: str
    suggestion: str | None = None


class ExcelSalesRecord(BaseModel):
    sale_date: date
    product_name: str
    quantity: float
    unit_price: float
    line_total: float
    customer_name: str | None = None
    customer_phone: str | None = None
    invoice_id: str | None = None
    channel: str | None = None
    currency: str = "KES"


class MpesaRecord(BaseModel):
    txn_date: datetime
    txn_code: str
    details: str
    direction: str
    amount: float
    balance: float | None = None
    party: str | None = None
    party_phone: str | None = None
    currency: str = "KES"


class TopIssue(BaseModel):
    rule_id: str
    count: int


class QualityReport(BaseModel):
    dataset: DatasetType
    quality_score: int = Field(ge=0, le=100)
    quality_band: str
    row_count: int = Field(ge=0)
    valid_row_count: int = Field(ge=0)
    error_count: int = Field(ge=0)
    warning_count: int = Field(ge=0)
    top_issues: list[TopIssue]


class NormalizationResult(BaseModel):
    dataset: DatasetType
    records: list[dict[str, Any]]
    issues: list[ValidationIssue]
    quality: QualityReport
    schema_version: str = "1.0"
    normalizer_version: str = "1.0"
