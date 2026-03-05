from __future__ import annotations

import math
import re
from collections import Counter
from decimal import Decimal, InvalidOperation, ROUND_HALF_UP
from zoneinfo import ZoneInfo

import pandas as pd

from .schemas import (
    DatasetType,
    ErrorCode,
    NormalizationResult,
    QualityReport,
    Severity,
    TopIssue,
    ValidationIssue,
)

KENYA_TZ = ZoneInfo("Africa/Nairobi")
DEFAULT_CURRENCY = "KES"


EXCEL_ALIASES = {
    "sale_date": {"sale_date", "date", "transaction_date", "sold_on"},
    "product_name": {"product_name", "product", "item", "sku_name"},
    "quantity": {"quantity", "qty", "units", "pieces"},
    "unit_price": {"unit_price", "price", "unit_cost", "selling_price"},
    "line_total": {"line_total", "total", "amount", "gross_amount"},
    "customer_name": {"customer_name", "customer", "client_name", "buyer"},
    "customer_phone": {"customer_phone", "phone", "msisdn", "mobile"},
    "invoice_id": {"invoice_id", "receipt_no", "order_id", "ref"},
    "channel": {"channel", "payment_channel", "source"},
    "currency": {"currency", "ccy"},
}

MPESA_ALIASES = {
    "txn_date": {"txn_date", "completion_time", "date", "transaction_date"},
    "txn_code": {"txn_code", "receipt_no", "transaction_id", "code"},
    "details": {"details", "description", "narrative"},
    "paid_in": {"paid_in", "credit", "paid_in_amount", "in"},
    "withdrawn": {"withdrawn", "debit", "withdrawn_amount", "out"},
    "balance": {"balance", "running_balance"},
    "party": {"party", "other_party", "counterparty"},
    "party_phone": {"party_phone", "msisdn", "phone"},
}


def _to_snake_case(value: str) -> str:
    value = value.strip().lower()
    value = re.sub(r"[^a-z0-9]+", "_", value)
    value = re.sub(r"_+", "_", value)
    return value.strip("_")


def _normalize_headers(df: pd.DataFrame) -> pd.DataFrame:
    out = df.copy()
    out.columns = [_to_snake_case(str(col)) for col in out.columns]
    return out


def _apply_alias_map(df: pd.DataFrame, aliases: dict[str, set[str]]) -> pd.DataFrame:
    out = df.copy()
    columns = set(out.columns)
    rename_map: dict[str, str] = {}

    for canonical, names in aliases.items():
        found = [c for c in columns if c in names]
        if found:
            rename_map[found[0]] = canonical

    return out.rename(columns=rename_map)


def _issue(
    dataset: DatasetType,
    severity: Severity,
    error_code: ErrorCode,
    message: str,
    rule_id: str,
    row_number: int | None = None,
    field: str | None = None,
    value: object | None = None,
    suggestion: str | None = None,
) -> ValidationIssue:
    return ValidationIssue(
        error_code=error_code,
        dataset=dataset,
        severity=severity,
        message=message,
        row_number=row_number,
        field=field,
        value=None if value is None else str(value),
        rule_id=rule_id,
        suggestion=suggestion,
    )


def _clean_string(value: object, max_len: int = 255) -> str | None:
    if value is None or (isinstance(value, float) and math.isnan(value)):
        return None
    text = re.sub(r"\s+", " ", str(value)).strip()
    if not text:
        return None
    return text[:max_len]


def _parse_decimal(value: object) -> Decimal | None:
    if value is None or (isinstance(value, float) and math.isnan(value)):
        return None

    text = str(value).strip().replace(",", "")
    if not text:
        return None

    try:
        parsed = Decimal(text)
    except InvalidOperation:
        return None

    if not parsed.is_finite():
        return None

    return parsed.quantize(Decimal("0.01"), rounding=ROUND_HALF_UP)


def _parse_date(value: object) -> datetime | None:
    if value is None or (isinstance(value, float) and math.isnan(value)):
        return None
    ts = pd.to_datetime(value, errors="coerce")
    if pd.isna(ts):
        return None

    dt = ts.to_pydatetime()
    if dt.tzinfo is None:
        return dt.replace(tzinfo=KENYA_TZ)
    return dt.astimezone(KENYA_TZ)


def _normalize_ke_phone(value: object) -> str | None:
    raw = _clean_string(value)
    if not raw:
        return None

    digits = re.sub(r"\D", "", raw)
    if digits.startswith("0") and len(digits) == 10:
        return f"+254{digits[1:]}"
    if digits.startswith("254") and len(digits) == 12:
        return f"+{digits}"
    if digits.startswith("7") and len(digits) == 9:
        return f"+254{digits}"
    return None


def _derive_quality(
    dataset: DatasetType,
    total_rows: int,
    valid_rows: int,
    issues: list[ValidationIssue],
    invalid_date_rows: int,
    duplicate_count: int,
    optional_null_rate: float,
    phone_failures: int,
    unknown_currency_count: int,
) -> QualityReport:
    critical = 0
    major = 0
    minor = 0

    required_column_errors = any(i.error_code == ErrorCode.MISSING_REQUIRED_COLUMN for i in issues)
    file_read_errors = any(i.error_code == ErrorCode.FILE_READ_ERROR for i in issues)

    if required_column_errors:
        critical += 20
    if file_read_errors:
        critical += 20
    if total_rows > 0 and (invalid_date_rows / total_rows) > 0.20:
        critical += 20

    numeric_errors = sum(1 for i in issues if i.error_code == ErrorCode.NUMERIC_PARSE_ERROR)
    major += numeric_errors * 5

    if total_rows > 0 and (duplicate_count / total_rows) > 0.05:
        major += 5

    if unknown_currency_count > 0:
        major += 5

    if optional_null_rate > 0.60:
        minor += 1

    minor += phone_failures

    score = max(0, 100 - (critical + major + minor))
    if score >= 90:
        band = "High"
    elif score >= 70:
        band = "Medium"
    else:
        band = "Low"

    counter = Counter(i.rule_id for i in issues)
    top_issues = [TopIssue(rule_id=k, count=v) for k, v in counter.most_common(5)]

    return QualityReport(
        dataset=dataset,
        quality_score=score,
        quality_band=band,
        row_count=total_rows,
        valid_row_count=valid_rows,
        error_count=sum(1 for i in issues if i.severity == Severity.ERROR),
        warning_count=sum(1 for i in issues if i.severity == Severity.WARNING),
        top_issues=top_issues,
    )


def normalize_excel_sales(df: pd.DataFrame, business_currency: str = DEFAULT_CURRENCY) -> NormalizationResult:
    dataset = DatasetType.EXCEL_SALES
    issues: list[ValidationIssue] = []

    if df is None or df.empty:
        issues.append(
            _issue(
                dataset=dataset,
                severity=Severity.ERROR,
                error_code=ErrorCode.FILE_READ_ERROR,
                message="Excel sales file is empty or unreadable.",
                rule_id="FILE_READ_001",
            )
        )
        quality = _derive_quality(dataset, 0, 0, issues, 0, 0, 1.0, 0, 0)
        return NormalizationResult(dataset=dataset, records=[], issues=issues, quality=quality)

    raw = _apply_alias_map(_normalize_headers(df), EXCEL_ALIASES)

    required = ["sale_date", "product_name", "quantity", "unit_price"]
    missing = [col for col in required if col not in raw.columns]
    for col in missing:
        issues.append(
            _issue(
                dataset=dataset,
                severity=Severity.ERROR,
                error_code=ErrorCode.MISSING_REQUIRED_COLUMN,
                message=f"Missing required column: {col}",
                field=col,
                rule_id="SCHEMA_REQUIRED_001",
                suggestion=f"Add a column that maps to {col}.",
            )
        )

    if missing:
        quality = _derive_quality(dataset, len(raw), 0, issues, 0, 0, 1.0, 0, 0)
        return NormalizationResult(dataset=dataset, records=[], issues=issues, quality=quality)

    records: list[dict[str, object]] = []
    invalid_date_rows = 0
    phone_failures = 0
    unknown_currency_count = 0
    optional_nulls = 0
    optional_total = 0

    for idx, row in raw.iterrows():
        row_number = idx + 2

        parsed_date = _parse_date(row.get("sale_date"))
        if not parsed_date:
            invalid_date_rows += 1
            issues.append(
                _issue(
                    dataset=dataset,
                    severity=Severity.ERROR,
                    error_code=ErrorCode.INVALID_DATE,
                    message="Invalid sale_date format.",
                    row_number=row_number,
                    field="sale_date",
                    value=row.get("sale_date"),
                    rule_id="DATE_PARSE_001",
                )
            )
            continue

        quantity = _parse_decimal(row.get("quantity"))
        unit_price = _parse_decimal(row.get("unit_price"))
        line_total = _parse_decimal(row.get("line_total"))

        if quantity is None or unit_price is None:
            issues.append(
                _issue(
                    dataset=dataset,
                    severity=Severity.ERROR,
                    error_code=ErrorCode.NUMERIC_PARSE_ERROR,
                    message="quantity and unit_price must be numeric.",
                    row_number=row_number,
                    rule_id="NUMERIC_PARSE_001",
                )
            )
            continue

        if quantity <= 0 or unit_price < 0:
            issues.append(
                _issue(
                    dataset=dataset,
                    severity=Severity.ERROR,
                    error_code=ErrorCode.NEGATIVE_NOT_ALLOWED,
                    message="quantity must be > 0 and unit_price must be >= 0.",
                    row_number=row_number,
                    rule_id="VALUE_RANGE_001",
                )
            )
            continue

        computed_total = (quantity * unit_price).quantize(Decimal("0.01"), rounding=ROUND_HALF_UP)

        if line_total is None:
            line_total = computed_total
        else:
            if line_total < 0:
                issues.append(
                    _issue(
                        dataset=dataset,
                        severity=Severity.ERROR,
                        error_code=ErrorCode.NEGATIVE_NOT_ALLOWED,
                        message="line_total must be >= 0.",
                        row_number=row_number,
                        field="line_total",
                        value=str(line_total),
                        rule_id="VALUE_RANGE_002",
                    )
                )
                continue
            if abs(line_total - computed_total) > Decimal("1.00"):
                issues.append(
                    _issue(
                        dataset=dataset,
                        severity=Severity.WARNING,
                        error_code=ErrorCode.SCHEMA_MISMATCH,
                        message="line_total differs from quantity * unit_price by > 1 KES; provided value retained.",
                        row_number=row_number,
                        field="line_total",
                        value=str(line_total),
                        rule_id="LINE_TOTAL_DIFF_001",
                    )
                )

        product_name = _clean_string(row.get("product_name"))
        if not product_name:
            issues.append(
                _issue(
                    dataset=dataset,
                    severity=Severity.ERROR,
                    error_code=ErrorCode.SCHEMA_MISMATCH,
                    message="product_name is required.",
                    row_number=row_number,
                    field="product_name",
                    rule_id="REQUIRED_VALUE_001",
                )
            )
            continue

        customer_phone = _normalize_ke_phone(row.get("customer_phone"))
        if row.get("customer_phone") is not None and customer_phone is None:
            phone_failures += 1
            issues.append(
                _issue(
                    dataset=dataset,
                    severity=Severity.WARNING,
                    error_code=ErrorCode.SCHEMA_MISMATCH,
                    message="customer_phone could not be normalized to KE E.164; set to null.",
                    row_number=row_number,
                    field="customer_phone",
                    value=row.get("customer_phone"),
                    rule_id="PHONE_NORMALIZE_001",
                )
            )

        currency = _clean_string(row.get("currency")) or business_currency or DEFAULT_CURRENCY
        currency = currency.upper()
        if len(currency) != 3:
            unknown_currency_count += 1
            currency = DEFAULT_CURRENCY

        optional_fields = [
            _clean_string(row.get("customer_name")),
            _clean_string(row.get("customer_phone")),
            _clean_string(row.get("invoice_id")),
            _clean_string(row.get("channel")),
        ]
        optional_total += len(optional_fields)
        optional_nulls += sum(1 for value in optional_fields if value is None)

        records.append(
            {
                "sale_date": parsed_date.date().isoformat(),
                "product_name": product_name,
                "quantity": float(quantity),
                "unit_price": float(unit_price),
                "line_total": float(line_total),
                "customer_name": _clean_string(row.get("customer_name")),
                "customer_phone": customer_phone,
                "invoice_id": _clean_string(row.get("invoice_id")),
                "channel": _clean_string(row.get("channel")),
                "currency": currency,
            }
        )

    # Deterministic duplicate removal on canonical key.
    dedupe_keys = ("sale_date", "product_name", "invoice_id", "line_total")
    seen = set()
    deduped: list[dict[str, object]] = []
    duplicate_count = 0

    for rec in records:
        key = tuple(rec.get(k) for k in dedupe_keys)
        if key in seen:
            duplicate_count += 1
            issues.append(
                _issue(
                    dataset=dataset,
                    severity=Severity.WARNING,
                    error_code=ErrorCode.DUPLICATE_ROW,
                    message="Duplicate Excel row removed after canonicalization.",
                    rule_id="DUPLICATE_ROW_001",
                )
            )
            continue
        seen.add(key)
        deduped.append(rec)

    optional_null_rate = (optional_nulls / optional_total) if optional_total else 1.0

    quality = _derive_quality(
        dataset=dataset,
        total_rows=len(raw),
        valid_rows=len(deduped),
        issues=issues,
        invalid_date_rows=invalid_date_rows,
        duplicate_count=duplicate_count,
        optional_null_rate=optional_null_rate,
        phone_failures=phone_failures,
        unknown_currency_count=unknown_currency_count,
    )

    return NormalizationResult(dataset=dataset, records=deduped, issues=issues, quality=quality)


def normalize_mpesa(df: pd.DataFrame) -> NormalizationResult:
    dataset = DatasetType.MPESA
    issues: list[ValidationIssue] = []

    if df is None or df.empty:
        issues.append(
            _issue(
                dataset=dataset,
                severity=Severity.ERROR,
                error_code=ErrorCode.FILE_READ_ERROR,
                message="M-Pesa CSV is empty or unreadable.",
                rule_id="FILE_READ_001",
            )
        )
        quality = _derive_quality(dataset, 0, 0, issues, 0, 0, 1.0, 0, 0)
        return NormalizationResult(dataset=dataset, records=[], issues=issues, quality=quality)

    raw = _apply_alias_map(_normalize_headers(df), MPESA_ALIASES)

    required = ["txn_date", "txn_code", "details"]
    missing = [col for col in required if col not in raw.columns]
    for col in missing:
        issues.append(
            _issue(
                dataset=dataset,
                severity=Severity.ERROR,
                error_code=ErrorCode.MISSING_REQUIRED_COLUMN,
                message=f"Missing required column: {col}",
                field=col,
                rule_id="SCHEMA_REQUIRED_001",
                suggestion=f"Add a column that maps to {col}.",
            )
        )

    if missing:
        quality = _derive_quality(dataset, len(raw), 0, issues, 0, 0, 1.0, 0, 0)
        return NormalizationResult(dataset=dataset, records=[], issues=issues, quality=quality)

    records: list[dict[str, object]] = []
    invalid_date_rows = 0
    phone_failures = 0
    optional_nulls = 0
    optional_total = 0

    for idx, row in raw.iterrows():
        row_number = idx + 2

        txn_date = _parse_date(row.get("txn_date"))
        if not txn_date:
            invalid_date_rows += 1
            issues.append(
                _issue(
                    dataset=dataset,
                    severity=Severity.ERROR,
                    error_code=ErrorCode.INVALID_DATE,
                    message="Invalid txn_date format.",
                    row_number=row_number,
                    field="txn_date",
                    value=row.get("txn_date"),
                    rule_id="DATE_PARSE_001",
                )
            )
            continue

        paid_in = _parse_decimal(row.get("paid_in"))
        withdrawn = _parse_decimal(row.get("withdrawn"))

        paid_positive = paid_in is not None and paid_in > 0
        withdrawn_positive = withdrawn is not None and withdrawn > 0

        if paid_positive == withdrawn_positive:
            issues.append(
                _issue(
                    dataset=dataset,
                    severity=Severity.ERROR,
                    error_code=ErrorCode.CONFLICTING_AMOUNT_FIELDS,
                    message="Exactly one of paid_in or withdrawn must be positive.",
                    row_number=row_number,
                    rule_id="MPESA_DIRECTION_001",
                )
            )
            continue

        if paid_positive:
            direction = "in"
            amount = paid_in
        else:
            direction = "out"
            amount = withdrawn

        if amount is None or amount <= 0:
            issues.append(
                _issue(
                    dataset=dataset,
                    severity=Severity.ERROR,
                    error_code=ErrorCode.NEGATIVE_NOT_ALLOWED,
                    message="Derived M-Pesa amount must be > 0.",
                    row_number=row_number,
                    field="amount",
                    rule_id="VALUE_RANGE_003",
                )
            )
            continue

        txn_code = (_clean_string(row.get("txn_code")) or "").upper()
        details = _clean_string(row.get("details"))

        if not txn_code or not details:
            issues.append(
                _issue(
                    dataset=dataset,
                    severity=Severity.ERROR,
                    error_code=ErrorCode.SCHEMA_MISMATCH,
                    message="txn_code and details are required.",
                    row_number=row_number,
                    rule_id="REQUIRED_VALUE_002",
                )
            )
            continue

        party_phone = _normalize_ke_phone(row.get("party_phone"))
        if row.get("party_phone") is not None and party_phone is None:
            phone_failures += 1
            issues.append(
                _issue(
                    dataset=dataset,
                    severity=Severity.WARNING,
                    error_code=ErrorCode.SCHEMA_MISMATCH,
                    message="party_phone could not be normalized to KE E.164; set to null.",
                    row_number=row_number,
                    field="party_phone",
                    value=row.get("party_phone"),
                    rule_id="PHONE_NORMALIZE_001",
                )
            )

        optional_fields = [
            _clean_string(row.get("balance")),
            _clean_string(row.get("party")),
            _clean_string(row.get("party_phone")),
        ]
        optional_total += len(optional_fields)
        optional_nulls += sum(1 for value in optional_fields if value is None)

        balance = _parse_decimal(row.get("balance"))

        records.append(
            {
                "txn_date": txn_date.replace(microsecond=0).isoformat(),
                "txn_code": txn_code,
                "details": details,
                "direction": direction,
                "amount": float(amount),
                "balance": float(balance) if balance is not None else None,
                "party": _clean_string(row.get("party")),
                "party_phone": party_phone,
                "currency": DEFAULT_CURRENCY,
            }
        )

    # De-dup: primary txn_code, fallback tuple for missing codes.
    seen_primary = set()
    deduped: list[dict[str, object]] = []
    duplicate_count = 0

    for rec in records:
        primary_key = rec.get("txn_code")
        fallback_key = (rec.get("txn_date"), rec.get("amount"), rec.get("details"))
        key = ("primary", primary_key) if primary_key else ("fallback", fallback_key)

        if key in seen_primary:
            duplicate_count += 1
            issues.append(
                _issue(
                    dataset=dataset,
                    severity=Severity.WARNING,
                    error_code=ErrorCode.DUPLICATE_ROW,
                    message="Duplicate M-Pesa row removed after canonicalization.",
                    rule_id="DUPLICATE_ROW_001",
                )
            )
            continue

        seen_primary.add(key)
        deduped.append(rec)

    optional_null_rate = (optional_nulls / optional_total) if optional_total else 1.0

    quality = _derive_quality(
        dataset=dataset,
        total_rows=len(raw),
        valid_rows=len(deduped),
        issues=issues,
        invalid_date_rows=invalid_date_rows,
        duplicate_count=duplicate_count,
        optional_null_rate=optional_null_rate,
        phone_failures=phone_failures,
        unknown_currency_count=0,
    )

    return NormalizationResult(dataset=dataset, records=deduped, issues=issues, quality=quality)
