from __future__ import annotations

from collections import Counter, defaultdict
from datetime import date, datetime, timedelta
from decimal import Decimal, ROUND_HALF_UP
from typing import Any


def _to_decimal(value: Any) -> Decimal | None:
    if value is None:
        return None
    try:
        return Decimal(str(value)).quantize(Decimal("0.01"), rounding=ROUND_HALF_UP)
    except Exception:
        return None


def _to_date(value: Any) -> date | None:
    if value is None:
        return None
    try:
        # Accept ISO date or datetime.
        text = str(value)
        if "T" in text:
            return datetime.fromisoformat(text).date()
        return date.fromisoformat(text)
    except Exception:
        return None


def _in_range(value: date, start: date, end: date) -> bool:
    return start <= value <= end


def _round2(value: Decimal) -> float:
    return float(value.quantize(Decimal("0.01"), rounding=ROUND_HALF_UP))


def _product_sales_in_week(records: list[dict[str, Any]], week_start: date, week_end: date) -> Counter:
    sales = Counter()
    for rec in records:
        rec_date = _to_date(rec.get("sale_date"))
        line_total = _to_decimal(rec.get("line_total"))
        product = str(rec.get("product_name") or "").strip()
        if rec_date is None or line_total is None or not product:
            continue
        if not _in_range(rec_date, week_start, week_end):
            continue
        sales[product] += float(line_total)
    return sales


def _weekly_revenue(records: list[dict[str, Any]], week_start: date, week_end: date) -> Decimal:
    total = Decimal("0.00")
    for rec in records:
        rec_date = _to_date(rec.get("sale_date"))
        line_total = _to_decimal(rec.get("line_total"))
        if rec_date is None or line_total is None:
            continue
        if _in_range(rec_date, week_start, week_end):
            total += line_total
    return total.quantize(Decimal("0.01"), rounding=ROUND_HALF_UP)


def _customer_key(record: dict[str, Any]) -> str | None:
    phone = str(record.get("customer_phone") or "").strip()
    name = str(record.get("customer_name") or "").strip().lower()
    if phone:
        return f"phone:{phone}"
    if name:
        return f"name:{name}"
    return None


def compute_weekly_metrics(
    *,
    sales_records: list[dict[str, Any]],
    week_start: date,
    week_end: date,
    slow_mover_days: int = 14,
    top_n_products: int = 5,
) -> dict[str, Any]:
    """
    Deterministic weekly KPI engine.

    Input records are expected to be canonical normalized sales rows.
    All numeric outputs are computed deterministically in Python.
    """
    if week_end < week_start:
        raise ValueError("week_end must be on or after week_start")

    prev_week_end = week_start - timedelta(days=1)
    prev_week_start = prev_week_end - timedelta(days=6)

    this_revenue = _weekly_revenue(sales_records, week_start, week_end)
    prev_revenue = _weekly_revenue(sales_records, prev_week_start, prev_week_end)

    wow_delta_pct: float | str
    if prev_revenue == Decimal("0.00"):
        wow_delta_pct = "unavailable"
    else:
        wow_delta_pct = _round2(((this_revenue - prev_revenue) / prev_revenue) * Decimal("100"))

    product_sales = _product_sales_in_week(sales_records, week_start, week_end)
    total_for_products = sum(Decimal(str(v)) for v in product_sales.values())

    # Stable deterministic ordering: revenue desc, then product asc.
    ordered_products = sorted(product_sales.items(), key=lambda x: (-x[1], x[0]))
    top_products: list[dict[str, Any]] = []
    for product, revenue in ordered_products[:top_n_products]:
        revenue_d = Decimal(str(revenue)).quantize(Decimal("0.01"), rounding=ROUND_HALF_UP)
        if total_for_products == Decimal("0"):
            contribution_pct = Decimal("0.00")
        else:
            contribution_pct = (revenue_d / total_for_products) * Decimal("100")
        top_products.append(
            {
                "product_name": product,
                "revenue": _round2(revenue_d),
                "contribution_pct": _round2(contribution_pct),
            }
        )

    # Slow movers: products with no sale in last N days up to week_end.
    lookback_start = week_end - timedelta(days=slow_mover_days - 1)
    last_seen: dict[str, date] = {}
    for rec in sales_records:
        product = str(rec.get("product_name") or "").strip()
        rec_date = _to_date(rec.get("sale_date"))
        if not product or rec_date is None:
            continue
        if product not in last_seen or rec_date > last_seen[product]:
            last_seen[product] = rec_date

    slow_movers = sorted(
        [
            {
                "product_name": p,
                "last_sale_date": d.isoformat(),
                "days_since_last_sale": (week_end - d).days,
            }
            for p, d in last_seen.items()
            if d < lookback_start
        ],
        key=lambda x: (-x["days_since_last_sale"], x["product_name"]),
    )

    # Repeat customers heuristic: >=2 purchases in current week.
    customer_txn_count = defaultdict(int)
    for rec in sales_records:
        rec_date = _to_date(rec.get("sale_date"))
        if rec_date is None or not _in_range(rec_date, week_start, week_end):
            continue
        key = _customer_key(rec)
        if key is None:
            continue
        customer_txn_count[key] += 1

    repeat_customer_count = sum(1 for count in customer_txn_count.values() if count >= 2)

    weekly_txn_count = 0
    for rec in sales_records:
        rec_date = _to_date(rec.get("sale_date"))
        line_total = _to_decimal(rec.get("line_total"))
        if rec_date is None or line_total is None:
            continue
        if _in_range(rec_date, week_start, week_end):
            weekly_txn_count += 1

    avg_transaction_value: float | str
    if weekly_txn_count == 0:
        avg_transaction_value = "unavailable"
    else:
        avg_transaction_value = _round2(this_revenue / Decimal(weekly_txn_count))

    return {
        "week": {
            "start": week_start.isoformat(),
            "end": week_end.isoformat(),
            "previous_start": prev_week_start.isoformat(),
            "previous_end": prev_week_end.isoformat(),
        },
        "weekly_revenue": _round2(this_revenue),
        "previous_week_revenue": _round2(prev_revenue),
        "week_over_week_delta_pct": wow_delta_pct,
        "top_products": top_products,
        "slow_movers": slow_movers,
        "repeat_customers": repeat_customer_count,
        "avg_transaction_value": avg_transaction_value,
        "meta": {
            "slow_mover_days": slow_mover_days,
            "top_n_products": top_n_products,
            "records_processed": len(sales_records),
        },
    }
