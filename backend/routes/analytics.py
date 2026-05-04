from __future__ import annotations

import json
import logging
from typing import Any

from fastapi import APIRouter, Depends, Header, HTTPException

from backend.db.connection import get_connection

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/analytics", tags=["analytics"])


def _require_admin_token(authorization: str | None = Header(default=None, alias="Authorization")) -> None:
    import os
    admin_token = os.getenv("ADMIN_TOKEN", "").strip()
    if not admin_token:
        raise HTTPException(status_code=500, detail="ADMIN_TOKEN not configured.")
    if not authorization:
        raise HTTPException(status_code=401, detail="Authorization header required.")
    parts = authorization.split(" ", 1)
    if len(parts) != 2 or parts[0].lower() != "bearer" or parts[1].strip() != admin_token:
        raise HTTPException(status_code=401, detail="Invalid admin token.")


_METRICS_SQL = """
SELECT
    week_start,
    week_end,
    payload
FROM ingestion_weekly_payloads
WHERE business_id = %s
  AND dataset = 'excel_sales'
ORDER BY week_start ASC
LIMIT 52
""".strip()

_UPLOADS_SQL = """
SELECT
    business_id,
    dataset,
    week_start,
    week_end,
    payload->'quality'->>'row_count' AS row_count,
    payload->'quality'->>'quality_score' AS quality_score,
    payload->>'source_file' AS source_file,
    created_at
FROM ingestion_weekly_payloads
WHERE business_id = %s
ORDER BY created_at DESC
LIMIT 20
""".strip()

_WHATSAPP_STATS_SQL = """
SELECT
    COUNT(*) AS total_sent,
    MAX(created_at) AS last_sent,
    COUNT(*) FILTER (WHERE status = 'sent' OR status = 'delivered') AS success_count
FROM whatsapp_message_log
WHERE business_id = %s
""".strip()

_ACTIVITY_SQL = """
SELECT
    event_type,
    message,
    status,
    created_at
FROM activity_log
WHERE business_id = %s
ORDER BY created_at DESC
LIMIT 30
""".strip()


@router.get("/metrics")
def get_analytics_metrics(
    organization_id: str = "default_org",
    business_id: str = "biz_001",
    _: None = Depends(_require_admin_token),
) -> dict[str, Any]:
    connection = get_connection()
    try:
        with connection.cursor() as cur:
            cur.execute(_METRICS_SQL, (business_id,))
            rows = cur.fetchall()

        revenue_trend: list[dict[str, Any]] = []
        expenses_trend: list[dict[str, Any]] = []
        profit_trend: list[dict[str, Any]] = []
        total_revenue = 0.0
        total_expenses = 0.0

        for row in rows:
            week_start = row[0]
            payload_raw = row[2]
            payload = json.loads(payload_raw) if isinstance(payload_raw, str) else payload_raw

            records = payload.get("records", [])
            week_revenue = 0.0
            week_expenses = 0.0

            for record in records:
                line_total = float(record.get("line_total", 0) or 0)
                week_revenue += line_total

            # Expenses derived from M-Pesa outflows if available — for now revenue-only
            date_str = week_start.isoformat() if hasattr(week_start, "isoformat") else str(week_start)
            revenue_trend.append({"date": date_str, "value": round(week_revenue, 2)})
            expenses_trend.append({"date": date_str, "value": round(week_expenses, 2)})
            profit_trend.append({"date": date_str, "value": round(week_revenue - week_expenses, 2)})

            total_revenue += week_revenue
            total_expenses += week_expenses

        # Enrich expenses from M-Pesa data if available
        _enrich_expenses(connection, business_id, expenses_trend, profit_trend)
        recalc_total_expenses = sum(e["value"] for e in expenses_trend)

        return {
            "revenue_trend": revenue_trend,
            "expenses_trend": expenses_trend,
            "profit_trend": profit_trend,
            "totals": {
                "revenue": round(total_revenue, 2),
                "expenses": round(recalc_total_expenses, 2),
                "profit": round(total_revenue - recalc_total_expenses, 2),
            },
        }
    except HTTPException:
        raise
    except Exception as exc:
        logger.error("analytics/metrics error: %s", exc)
        raise HTTPException(status_code=500, detail=str(exc)) from exc
    finally:
        connection.close()


def _enrich_expenses(
    connection: Any,
    business_id: str,
    expenses_trend: list[dict[str, Any]],
    profit_trend: list[dict[str, Any]],
) -> None:
    """Enrich expenses from M-Pesa outflow data."""
    try:
        sql = """
        SELECT week_start, payload
        FROM ingestion_weekly_payloads
        WHERE business_id = %s AND dataset = 'mpesa'
        ORDER BY week_start ASC LIMIT 52
        """
        with connection.cursor() as cur:
            cur.execute(sql, (business_id,))
            rows = cur.fetchall()

        mpesa_by_date: dict[str, float] = {}
        for row in rows:
            week_start = row[0]
            payload_raw = row[1]
            payload = json.loads(payload_raw) if isinstance(payload_raw, str) else payload_raw
            records = payload.get("records", [])
            total_out = 0.0
            for record in records:
                direction = str(record.get("direction", "")).lower()
                if direction in ("out", "paid", "sent"):
                    total_out += abs(float(record.get("amount", 0) or 0))
            date_str = week_start.isoformat() if hasattr(week_start, "isoformat") else str(week_start)
            mpesa_by_date[date_str] = total_out

        for i, entry in enumerate(expenses_trend):
            mpesa_expense = mpesa_by_date.get(entry["date"], 0.0)
            expenses_trend[i]["value"] = round(entry["value"] + mpesa_expense, 2)
            # Recalculate profit for the same date
            if i < len(profit_trend):
                rev_val = profit_trend[i]["value"] + entry["value"]  # restore original revenue
                profit_trend[i]["value"] = round(rev_val - expenses_trend[i]["value"], 2)
    except Exception as exc:
        logger.warning("Could not enrich expenses from M-Pesa: %s", exc)


@router.get("/uploads")
def get_analytics_uploads(
    organization_id: str = "default_org",
    business_id: str = "biz_001",
    _: None = Depends(_require_admin_token),
) -> list[dict[str, Any]]:
    connection = get_connection()
    try:
        with connection.cursor() as cur:
            cur.execute(_UPLOADS_SQL, (business_id,))
            rows = cur.fetchall()

        result = []
        for row in rows:
            source_file = row[6] or f"{row[1]}_{row[2]}_{row[3]}"
            result.append({
                "file_name": source_file,
                "dataset": row[1],
                "rows": int(row[4]) if row[4] else 0,
                "quality_score": float(row[5]) if row[5] else None,
                "uploaded_at": row[7].isoformat() if hasattr(row[7], "isoformat") else str(row[7]),
                "status": "processed",
                "week_start": row[2].isoformat() if hasattr(row[2], "isoformat") else str(row[2]),
                "week_end": row[3].isoformat() if hasattr(row[3], "isoformat") else str(row[3]),
            })

        return result
    except HTTPException:
        raise
    except Exception as exc:
        logger.error("analytics/uploads error: %s", exc)
        raise HTTPException(status_code=500, detail=str(exc)) from exc
    finally:
        connection.close()


@router.get("/whatsapp")
def get_analytics_whatsapp(
    organization_id: str = "default_org",
    business_id: str = "biz_001",
    _: None = Depends(_require_admin_token),
) -> dict[str, Any]:
    connection = get_connection()
    try:
        with connection.cursor() as cur:
            # Table may not exist yet on older deployments
            cur.execute(
                "SELECT 1 FROM information_schema.tables WHERE table_name = 'whatsapp_message_log' LIMIT 1"
            )
            if cur.fetchone() is None:
                return {"total_sent": 0, "last_sent": None, "success_rate": 0.0}

            cur.execute(_WHATSAPP_STATS_SQL, (business_id,))
            row = cur.fetchone()

        total_sent = row[0] if row else 0
        last_sent = row[1] if row else None
        success_count = row[2] if row else 0
        success_rate = round((success_count / total_sent * 100), 1) if total_sent > 0 else 0.0

        return {
            "total_sent": total_sent,
            "last_sent": last_sent.isoformat() if last_sent and hasattr(last_sent, "isoformat") else last_sent,
            "success_rate": success_rate,
        }
    except HTTPException:
        raise
    except Exception as exc:
        logger.error("analytics/whatsapp error: %s", exc)
        raise HTTPException(status_code=500, detail=str(exc)) from exc
    finally:
        connection.close()


@router.get("/activity")
def get_analytics_activity(
    organization_id: str = "default_org",
    business_id: str = "biz_001",
    _: None = Depends(_require_admin_token),
) -> list[dict[str, Any]]:
    connection = get_connection()
    try:
        with connection.cursor() as cur:
            cur.execute(
                "SELECT 1 FROM information_schema.tables WHERE table_name = 'activity_log' LIMIT 1"
            )
            if cur.fetchone() is None:
                return []

            cur.execute(_ACTIVITY_SQL, (business_id,))
            rows = cur.fetchall()

        return [
            {
                "type": row[0],
                "message": row[1],
                "status": row[2],
                "timestamp": row[3].isoformat() if hasattr(row[3], "isoformat") else str(row[3]),
            }
            for row in rows
        ]
    except HTTPException:
        raise
    except Exception as exc:
        logger.error("analytics/activity error: %s", exc)
        raise HTTPException(status_code=500, detail=str(exc)) from exc
    finally:
        connection.close()


def log_activity(
    business_id: str,
    event_type: str,
    message: str,
    status: str = "success",
    organization_id: str = "default_org",
    metadata: dict[str, Any] | None = None,
) -> None:
    """Insert an activity log entry. Best-effort — swallows errors."""
    try:
        connection = get_connection()
        try:
            with connection.cursor() as cur:
                cur.execute(
                    "SELECT 1 FROM information_schema.tables WHERE table_name = 'activity_log' LIMIT 1"
                )
                if cur.fetchone() is None:
                    return
                cur.execute(
                    """
                    INSERT INTO activity_log (organization_id, business_id, event_type, message, status, metadata_json)
                    VALUES (%s, %s, %s, %s, %s, %s)
                    """,
                    (organization_id, business_id, event_type, message, status, json.dumps(metadata) if metadata else None),
                )
            connection.commit()
        finally:
            connection.close()
    except Exception as exc:
        logger.warning("Failed to log activity: %s", exc)


def log_whatsapp_message(
    business_id: str,
    phone: str,
    status: str = "sent",
    message_preview: str | None = None,
    provider: str = "twilio",
    provider_sid: str | None = None,
    error_detail: str | None = None,
    organization_id: str = "default_org",
) -> None:
    """Insert a WhatsApp message log entry. Best-effort — swallows errors."""
    try:
        connection = get_connection()
        try:
            with connection.cursor() as cur:
                cur.execute(
                    "SELECT 1 FROM information_schema.tables WHERE table_name = 'whatsapp_message_log' LIMIT 1"
                )
                if cur.fetchone() is None:
                    return
                cur.execute(
                    """
                    INSERT INTO whatsapp_message_log
                        (organization_id, business_id, phone, message_preview, status, provider, provider_sid, error_detail)
                    VALUES (%s, %s, %s, %s, %s, %s, %s, %s)
                    """,
                    (organization_id, business_id, phone, message_preview, status, provider, provider_sid, error_detail),
                )
            connection.commit()
        finally:
            connection.close()
    except Exception as exc:
        logger.warning("Failed to log WhatsApp message: %s", exc)
