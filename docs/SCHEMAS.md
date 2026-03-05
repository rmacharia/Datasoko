# docs/SCHEMAS.md

## Purpose
Canonical input schemas and deterministic validation/normalization rules for DataSoko weekly analytics.

## 1) Canonical Excel Sales Schema

### 1.1 Accepted Source Columns (raw)
At ingest time, map aliases to canonical names.

| Canonical Field | Required | Type | Accepted Aliases |
|---|---|---|---|
| `sale_date` | Yes | date | date, transaction_date, sold_on |
| `product_name` | Yes | string | product, item, sku_name |
| `quantity` | Yes | number | qty, units, pieces |
| `unit_price` | Yes | number | price, unit_cost, selling_price |
| `line_total` | No | number | total, amount, gross_amount |
| `customer_name` | No | string | customer, client_name, buyer |
| `customer_phone` | No | string | phone, msisdn, mobile |
| `invoice_id` | No | string | receipt_no, order_id, ref |
| `channel` | No | string | payment_channel, source |
| `currency` | No | string | ccy |

### 1.2 Canonical Output Record (post-normalization)
```json
{
  "sale_date": "YYYY-MM-DD",
  "product_name": "string",
  "quantity": 0.0,
  "unit_price": 0.0,
  "line_total": 0.0,
  "customer_name": "string|null",
  "customer_phone": "string|null",
  "invoice_id": "string|null",
  "channel": "string|null",
  "currency": "KES"
}
```

## 2) Canonical M-Pesa CSV Schema

### 2.1 Accepted Source Columns (raw)

| Canonical Field | Required | Type | Accepted Aliases |
|---|---|---|---|
| `txn_date` | Yes | datetime | completion_time, date, transaction_date |
| `txn_code` | Yes | string | receipt_no, transaction_id, code |
| `details` | Yes | string | description, narrative |
| `paid_in` | No | number | credit, paid_in_amount, in |
| `withdrawn` | No | number | debit, withdrawn_amount, out |
| `balance` | No | number | running_balance |
| `party` | No | string | other_party, counterparty |
| `party_phone` | No | string | msisdn, phone |

### 2.2 Canonical Output Record (post-normalization)
```json
{
  "txn_date": "YYYY-MM-DDTHH:MM:SS",
  "txn_code": "string",
  "details": "string",
  "direction": "in|out",
  "amount": 0.0,
  "balance": 0.0,
  "party": "string|null",
  "party_phone": "string|null",
  "currency": "KES"
}
```

## 3) Validation Rules (Deterministic)

## 3.1 File-Level
- Reject file if unreadable, encrypted, empty, or row count = 0.
- Reject if required canonical columns cannot be mapped.
- Max file size default: 25 MB (configurable).

## 3.2 Field-Level
- Dates: parse strictly with configured timezone (`Africa/Nairobi`). Invalid dates => row error.
- Numeric fields (`quantity`, `unit_price`, `line_total`, `paid_in`, `withdrawn`, `balance`): must parse as finite decimal.
- Negative rules:
  - `quantity` must be `> 0`.
  - `unit_price` must be `>= 0`.
  - `line_total` must be `>= 0` when present.
  - M-Pesa `amount` must be `> 0` after direction derivation.
- String fields: trim, collapse inner spaces, UTF-8 safe, max 255 chars for identifiers.
- Phone: normalize to E.164 KE format when possible; otherwise set null and add warning.

## 3.3 Cross-Field Rules
- Excel: if `line_total` missing, compute `quantity * unit_price`.
- Excel: if `line_total` present and differs from `quantity * unit_price` by >1 KES, keep provided value and log warning.
- M-Pesa: exactly one of `paid_in` or `withdrawn` must be positive; derive:
  - `direction = in`, `amount = paid_in` when `paid_in > 0`
  - `direction = out`, `amount = withdrawn` when `withdrawn > 0`
- Duplicate detection keys:
  - Excel: (`sale_date`, `product_name`, `invoice_id`, `line_total`)
  - M-Pesa: (`txn_code`) primary, fallback (`txn_date`, `amount`, `details`)

## 4) Normalization Logic

## 4.1 Excel
1. Header normalize: lowercase snake_case.
2. Alias-map raw headers to canonical names.
3. Parse `sale_date` to `YYYY-MM-DD`.
4. Convert numeric fields to decimal(18,2).
5. Backfill `line_total` if null.
6. Standardize `currency` to business profile currency, default `KES`.
7. Clean product naming (`strip`, title-preserve internal acronyms).
8. Remove exact duplicate rows after canonicalization.

## 4.2 M-Pesa
1. Header normalize and alias map.
2. Parse `txn_date` to ISO datetime in `Africa/Nairobi`.
3. Parse `paid_in`/`withdrawn` numeric.
4. Derive `direction` and unified `amount`.
5. Normalize transaction code to uppercase.
6. Strip PII from `details` for logs (store raw only in secured table if needed).
7. Set `currency = KES` unless explicit valid override.

## 5) Error Message Format

All validation/normalization errors must be machine-readable JSON.

```json
{
  "error_code": "VALIDATION_ERROR",
  "dataset": "excel_sales|mpesa",
  "severity": "error|warning",
  "message": "Human-readable summary",
  "row_number": 12,
  "field": "unit_price",
  "value": "KES -",
  "rule_id": "NUMERIC_PARSE_001",
  "suggestion": "Provide a numeric unit_price, e.g. 250.00"
}
```

### 5.1 Standard `error_code` values
- `FILE_READ_ERROR`
- `MISSING_REQUIRED_COLUMN`
- `INVALID_DATE`
- `NUMERIC_PARSE_ERROR`
- `NEGATIVE_NOT_ALLOWED`
- `CONFLICTING_AMOUNT_FIELDS`
- `DUPLICATE_ROW`
- `SCHEMA_MISMATCH`

## 6) Data Quality Scoring

Score each upload `0-100` deterministically.

`quality_score = 100 - (critical_penalty + major_penalty + minor_penalty)`

### 6.1 Penalties
- Critical (20 each): missing required column, unreadable file, >20% invalid dates.
- Major (5 each): invalid numeric row, duplicate rate >5%, unknown currency values.
- Minor (1 each): optional-field null rate >60%, phone normalization failures.

### 6.2 Bands
- `90-100` = High (safe for weekly insights)
- `70-89` = Medium (insights with warnings)
- `<70` = Low (block automated insight send; request cleanup)

### 6.3 Quality Output JSON
```json
{
  "dataset": "excel_sales",
  "quality_score": 86,
  "quality_band": "Medium",
  "row_count": 1240,
  "valid_row_count": 1178,
  "error_count": 42,
  "warning_count": 18,
  "top_issues": [
    {"rule_id": "NUMERIC_PARSE_001", "count": 21},
    {"rule_id": "DUPLICATE_ROW_001", "count": 11}
  ]
}
```

## 7) Guardrails for Deterministic Analytics
- Only normalized canonical tables feed metric engine.
- Invalid rows excluded from metrics; exclusion counts must be reported.
- No LLM access to raw rows or PII fields.
- All transformations versioned (`schema_version`, `normalizer_version`).
