from __future__ import annotations

import logging
from datetime import date, time
from typing import Any
from uuid import uuid4

from fastapi import APIRouter, Depends, Header, HTTPException
from pydantic import BaseModel, Field

from backend.db.connection import get_connection

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/schedules", tags=["schedules"])


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


class CreateScheduleRequest(BaseModel):
    organization_id: str = Field(default="default_org", min_length=1)
    business_id: str | None = None
    frequency: str = Field(min_length=1)
    time_of_day: str = Field(min_length=5, max_length=5)
    day_of_week: int | None = Field(default=None, ge=0, le=6)
    day_of_month: int | None = Field(default=None, ge=1, le=31)
    start_date: date
    end_date: date | None = None
    send_whatsapp: bool = True


class UpdateScheduleRequest(BaseModel):
    frequency: str | None = None
    time_of_day: str | None = None
    day_of_week: int | None = Field(default=None, ge=0, le=6)
    day_of_month: int | None = Field(default=None, ge=1, le=31)
    start_date: date | None = None
    end_date: date | None = None
    send_whatsapp: bool | None = None
    is_active: bool | None = None


@router.post("")
def create_schedule(
    payload: CreateScheduleRequest,
    _: None = Depends(_require_admin_token),
) -> dict[str, Any]:
    if payload.frequency not in ("daily", "weekly", "monthly"):
        raise HTTPException(status_code=400, detail="frequency must be daily, weekly, or monthly")
    if payload.frequency == "weekly" and payload.day_of_week is None:
        raise HTTPException(status_code=400, detail="day_of_week required for weekly schedules")
    if payload.frequency == "monthly" and payload.day_of_month is None:
        raise HTTPException(status_code=400, detail="day_of_month required for monthly schedules")

    schedule_id = uuid4().hex
    parsed_time = time.fromisoformat(payload.time_of_day)

    conn = get_connection()
    try:
        with conn.cursor() as cur:
            cur.execute("""
                INSERT INTO report_schedules
                    (id, organization_id, business_id, frequency, time_of_day,
                     day_of_week, day_of_month, start_date, end_date, send_whatsapp)
                VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
            """, (
                schedule_id,
                payload.organization_id,
                payload.business_id,
                payload.frequency,
                parsed_time,
                payload.day_of_week,
                payload.day_of_month,
                payload.start_date,
                payload.end_date,
                payload.send_whatsapp,
            ))
        conn.commit()
    except Exception as exc:
        conn.rollback()
        logger.error("Failed to create schedule: %s", exc)
        raise HTTPException(status_code=500, detail=str(exc)) from exc
    finally:
        conn.close()

    from backend.routes.analytics import log_activity
    log_activity(
        business_id=payload.business_id or "all",
        event_type="schedule",
        message=f"Schedule created: {payload.frequency} at {payload.time_of_day}",
        status="success",
        organization_id=payload.organization_id,
        metadata={"schedule_id": schedule_id},
    )

    return {
        "id": schedule_id,
        "organization_id": payload.organization_id,
        "business_id": payload.business_id,
        "frequency": payload.frequency,
        "time_of_day": payload.time_of_day,
        "day_of_week": payload.day_of_week,
        "day_of_month": payload.day_of_month,
        "start_date": payload.start_date.isoformat(),
        "end_date": payload.end_date.isoformat() if payload.end_date else None,
        "send_whatsapp": payload.send_whatsapp,
        "is_active": True,
    }


@router.get("")
def list_schedules(
    organization_id: str = "default_org",
    _: None = Depends(_require_admin_token),
) -> list[dict[str, Any]]:
    conn = get_connection()
    try:
        with conn.cursor() as cur:
            cur.execute(
                "SELECT 1 FROM information_schema.tables WHERE table_name = 'report_schedules' LIMIT 1"
            )
            if cur.fetchone() is None:
                return []
            cur.execute("""
                SELECT id, organization_id, business_id, frequency,
                       time_of_day, day_of_week, day_of_month,
                       start_date, end_date, send_whatsapp, is_active, created_at
                FROM report_schedules
                WHERE organization_id = %s
                ORDER BY created_at DESC
            """, (organization_id,))
            rows = cur.fetchall()

        return [
            {
                "id": row[0],
                "organization_id": row[1],
                "business_id": row[2],
                "frequency": row[3],
                "time_of_day": row[4].strftime("%H:%M") if hasattr(row[4], "strftime") else str(row[4])[:5],
                "day_of_week": row[5],
                "day_of_month": row[6],
                "start_date": row[7].isoformat() if hasattr(row[7], "isoformat") else str(row[7]),
                "end_date": row[8].isoformat() if row[8] and hasattr(row[8], "isoformat") else None,
                "send_whatsapp": row[9],
                "is_active": row[10],
                "created_at": row[11].isoformat() if hasattr(row[11], "isoformat") else str(row[11]),
            }
            for row in rows
        ]
    except HTTPException:
        raise
    except Exception as exc:
        logger.error("Failed to list schedules: %s", exc)
        raise HTTPException(status_code=500, detail=str(exc)) from exc
    finally:
        conn.close()


@router.patch("/{schedule_id}")
def update_schedule(
    schedule_id: str,
    payload: UpdateScheduleRequest,
    _: None = Depends(_require_admin_token),
) -> dict[str, Any]:
    updates: list[str] = []
    values: list[Any] = []

    if payload.frequency is not None:
        updates.append("frequency = %s")
        values.append(payload.frequency)
    if payload.time_of_day is not None:
        updates.append("time_of_day = %s")
        values.append(time.fromisoformat(payload.time_of_day))
    if payload.day_of_week is not None:
        updates.append("day_of_week = %s")
        values.append(payload.day_of_week)
    if payload.day_of_month is not None:
        updates.append("day_of_month = %s")
        values.append(payload.day_of_month)
    if payload.start_date is not None:
        updates.append("start_date = %s")
        values.append(payload.start_date)
    if payload.end_date is not None:
        updates.append("end_date = %s")
        values.append(payload.end_date)
    if payload.send_whatsapp is not None:
        updates.append("send_whatsapp = %s")
        values.append(payload.send_whatsapp)
    if payload.is_active is not None:
        updates.append("is_active = %s")
        values.append(payload.is_active)

    if not updates:
        raise HTTPException(status_code=400, detail="No fields to update")

    values.append(schedule_id)

    conn = get_connection()
    try:
        with conn.cursor() as cur:
            cur.execute(
                f"UPDATE report_schedules SET {', '.join(updates)} WHERE id = %s",
                values,
            )
            if cur.rowcount == 0:
                raise HTTPException(status_code=404, detail="Schedule not found")
        conn.commit()
    except HTTPException:
        raise
    except Exception as exc:
        conn.rollback()
        logger.error("Failed to update schedule: %s", exc)
        raise HTTPException(status_code=500, detail=str(exc)) from exc
    finally:
        conn.close()

    return {"id": schedule_id, "updated": True}


@router.delete("/{schedule_id}")
def delete_schedule(
    schedule_id: str,
    _: None = Depends(_require_admin_token),
) -> dict[str, Any]:
    conn = get_connection()
    try:
        with conn.cursor() as cur:
            cur.execute("DELETE FROM report_schedules WHERE id = %s", (schedule_id,))
            if cur.rowcount == 0:
                raise HTTPException(status_code=404, detail="Schedule not found")
        conn.commit()
    except HTTPException:
        raise
    except Exception as exc:
        conn.rollback()
        logger.error("Failed to delete schedule: %s", exc)
        raise HTTPException(status_code=500, detail=str(exc)) from exc
    finally:
        conn.close()

    return {"id": schedule_id, "deleted": True}
