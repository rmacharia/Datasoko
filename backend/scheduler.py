from __future__ import annotations

import calendar
import logging
import os
import threading
from datetime import date, datetime, timedelta, timezone
from typing import Any
from uuid import uuid4

logger = logging.getLogger(__name__)

_SCHEDULER_THREAD: threading.Thread | None = None
_STOP_EVENT = threading.Event()

# Two schedule firings within this window are treated as the same firing.
# 55 minutes leaves enough slack to survive loop drift and DB retries
# without re-running a schedule that has already fired this hour.
_DEDUPE_WINDOW = timedelta(minutes=55)


def start_scheduler() -> None:
    global _SCHEDULER_THREAD
    if _SCHEDULER_THREAD is not None and _SCHEDULER_THREAD.is_alive():
        logger.info("[scheduler] already running")
        return

    _STOP_EVENT.clear()
    _SCHEDULER_THREAD = threading.Thread(target=_run_loop, daemon=True, name="datasoko-scheduler")
    _SCHEDULER_THREAD.start()
    logger.info("[scheduler] started background scheduler thread")


def stop_scheduler() -> None:
    _STOP_EVENT.set()
    logger.info("[scheduler] stop signal sent")


def _run_loop() -> None:
    logger.info("[scheduler] loop started — checking every 60s")
    while not _STOP_EVENT.is_set():
        try:
            run_scheduled_reports()
        except Exception as exc:
            logger.error("[scheduler] error in run cycle: %s", exc)
        _STOP_EVENT.wait(timeout=60)


def run_scheduled_reports() -> int:
    now = datetime.now(timezone.utc)
    tz_name = os.getenv("TZ", "Africa/Nairobi")
    try:
        import zoneinfo
        local_now = now.astimezone(zoneinfo.ZoneInfo(tz_name))
    except Exception:
        local_now = now

    schedules = _fetch_active_schedules()
    triggered = 0

    for s in schedules:
        if _already_ran_in_window(s, now):
            continue
        if _should_run(s, local_now):
            status = "success"
            try:
                _trigger_schedule(s, local_now)
                triggered += 1
            except Exception as exc:
                status = "failed"
                logger.error("[scheduler] failed to trigger schedule %s: %s", s["id"], exc)
            _record_run(s["id"], now, status, _compute_next_run(s, local_now))
        else:
            # Keep next_run_at fresh even when the schedule did not fire
            # this cycle, so the UI can show a live countdown.
            _record_next_run(s["id"], _compute_next_run(s, local_now))

    if triggered > 0:
        logger.info("[scheduler] triggered %d schedule(s) at %s", triggered, local_now.isoformat())

    return triggered


def _already_ran_in_window(s: dict[str, Any], now_utc: datetime) -> bool:
    last_run = s.get("last_run_at")
    if last_run is None:
        return False
    if last_run.tzinfo is None:
        last_run = last_run.replace(tzinfo=timezone.utc)
    return (now_utc - last_run) < _DEDUPE_WINDOW


def _fetch_active_schedules() -> list[dict[str, Any]]:
    try:
        from backend.db.connection import get_connection
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
                           start_date, end_date, send_whatsapp,
                           last_run_at
                    FROM report_schedules
                    WHERE is_active = TRUE
                """)
                rows = cur.fetchall()
            return [
                {
                    "id": row[0],
                    "organization_id": row[1],
                    "business_id": row[2],
                    "frequency": row[3],
                    "time_of_day": row[4],
                    "day_of_week": row[5],
                    "day_of_month": row[6],
                    "start_date": row[7],
                    "end_date": row[8],
                    "send_whatsapp": row[9],
                    "last_run_at": row[10],
                }
                for row in rows
            ]
        finally:
            conn.close()
    except Exception as exc:
        logger.warning("[scheduler] could not fetch schedules: %s", exc)
        return []


def _should_run(s: dict[str, Any], now: datetime) -> bool:
    current_date = now.date()
    current_time_hm = now.strftime("%H:%M")

    if current_date < s["start_date"]:
        return False
    if s["end_date"] and current_date > s["end_date"]:
        return False

    schedule_time_hm = s["time_of_day"].strftime("%H:%M") if hasattr(s["time_of_day"], "strftime") else str(s["time_of_day"])[:5]

    if current_time_hm != schedule_time_hm:
        return False

    freq = s["frequency"]
    if freq == "daily":
        return True
    elif freq == "weekly":
        return now.weekday() == (s["day_of_week"] or 0)
    elif freq == "monthly":
        return now.day == (s["day_of_month"] or 1)

    return False


def _compute_next_run(s: dict[str, Any], from_local: datetime) -> datetime | None:
    """Project the next firing of a schedule in the scheduler's local timezone."""
    tod = s["time_of_day"]
    hour = tod.hour if hasattr(tod, "hour") else int(str(tod)[:2])
    minute = tod.minute if hasattr(tod, "minute") else int(str(tod)[3:5])

    freq = s["frequency"]
    candidate = from_local.replace(hour=hour, minute=minute, second=0, microsecond=0)

    if freq == "daily":
        if candidate <= from_local:
            candidate += timedelta(days=1)
    elif freq == "weekly":
        target_dow = s["day_of_week"] or 0
        days_ahead = (target_dow - from_local.weekday()) % 7
        candidate = (from_local + timedelta(days=days_ahead)).replace(
            hour=hour, minute=minute, second=0, microsecond=0,
        )
        if candidate <= from_local:
            candidate += timedelta(days=7)
    elif freq == "monthly":
        target_dom = s["day_of_month"] or 1
        year, month = from_local.year, from_local.month
        last_day = calendar.monthrange(year, month)[1]
        day = min(target_dom, last_day)
        candidate = from_local.replace(year=year, month=month, day=day, hour=hour, minute=minute, second=0, microsecond=0)
        if candidate <= from_local:
            month += 1
            if month > 12:
                month = 1
                year += 1
            last_day = calendar.monthrange(year, month)[1]
            day = min(target_dom, last_day)
            candidate = from_local.replace(year=year, month=month, day=day, hour=hour, minute=minute, second=0, microsecond=0)
    else:
        return None

    if s["end_date"] and candidate.date() > s["end_date"]:
        return None

    return candidate.astimezone(timezone.utc)


def _record_run(schedule_id: str, ran_at_utc: datetime, status: str, next_run_utc: datetime | None) -> None:
    try:
        from backend.db.connection import get_connection
        conn = get_connection()
        try:
            with conn.cursor() as cur:
                cur.execute(
                    """
                    UPDATE report_schedules
                    SET last_run_at = %s,
                        last_status = %s,
                        next_run_at = %s
                    WHERE id = %s
                    """,
                    (ran_at_utc, status, next_run_utc, schedule_id),
                )
            conn.commit()
        finally:
            conn.close()
    except Exception as exc:
        logger.warning("[scheduler] could not record run for %s: %s", schedule_id, exc)


def _record_next_run(schedule_id: str, next_run_utc: datetime | None) -> None:
    try:
        from backend.db.connection import get_connection
        conn = get_connection()
        try:
            with conn.cursor() as cur:
                cur.execute(
                    "UPDATE report_schedules SET next_run_at = %s WHERE id = %s",
                    (next_run_utc, schedule_id),
                )
            conn.commit()
        finally:
            conn.close()
    except Exception as exc:
        logger.warning("[scheduler] could not record next_run for %s: %s", schedule_id, exc)


def _trigger_schedule(s: dict[str, Any], now: datetime) -> None:
    from backend.routes.analytics import log_activity

    businesses = _get_businesses_for_schedule(s)

    for biz in businesses:
        _create_scheduled_job(
            organization_id=s["organization_id"],
            business_id=biz["id"],
            send_whatsapp=s["send_whatsapp"],
            schedule_id=s["id"],
        )

    log_activity(
        business_id=s["business_id"] or (businesses[0]["id"] if businesses else "unknown"),
        event_type="schedule",
        message=f"Schedule triggered: {s['frequency']} — {len(businesses)} business(es)",
        status="success",
        organization_id=s["organization_id"],
        metadata={"schedule_id": s["id"], "businesses": [b["id"] for b in businesses]},
    )


def _get_businesses_for_schedule(s: dict[str, Any]) -> list[dict[str, str]]:
    if s["business_id"]:
        return [{"id": s["business_id"]}]

    try:
        from backend.db.connection import get_connection
        conn = get_connection()
        try:
            with conn.cursor() as cur:
                cur.execute(
                    "SELECT id FROM businesses WHERE organization_id = %s",
                    (s["organization_id"],),
                )
                rows = cur.fetchall()
            return [{"id": row[0]} for row in rows]
        finally:
            conn.close()
    except Exception as exc:
        logger.warning("[scheduler] could not fetch businesses for org %s: %s", s["organization_id"], exc)
        return []


def _create_scheduled_job(
    organization_id: str,
    business_id: str,
    send_whatsapp: bool,
    schedule_id: str,
) -> str:
    from backend.main import JOBS, _compute_and_format_report, _format_whatsapp_report, _get_business_whatsapp_phone, _send_whatsapp_report

    job_id = uuid4().hex
    now_iso = datetime.now(timezone.utc).isoformat()

    today = date.today()
    week_start = today - timedelta(days=today.weekday())
    week_end = week_start + timedelta(days=6)

    job = {
        "job_id": job_id,
        "status": "queued",
        "requested_at": now_iso,
        "started_at": None,
        "finished_at": None,
        "error": None,
        "business_id": business_id,
        "week_start": week_start.isoformat(),
        "week_end": week_end.isoformat(),
        "result_summary": None,
        "source": "scheduler",
        "schedule_id": schedule_id,
    }
    JOBS[job_id] = job

    try:
        job["status"] = "running"
        job["started_at"] = datetime.now(timezone.utc).isoformat()

        report = _compute_and_format_report(
            business_id=business_id,
            week_start=week_start,
            week_end=week_end,
            slow_mover_days=14,
            top_n_products=5,
            business_name="Your Business",
            sme_type="retail",
            currency="KES",
        )

        metrics = report["metrics_json"]
        job["status"] = "completed"
        job["finished_at"] = datetime.now(timezone.utc).isoformat()
        job["result_summary"] = {
            "weekly_revenue": metrics.get("weekly_revenue"),
            "repeat_customers": metrics.get("repeat_customers"),
            "records_processed": metrics.get("meta", {}).get("records_processed"),
        }

        if send_whatsapp:
            phone = _get_business_whatsapp_phone(business_id)
            if phone:
                wa_message = _format_whatsapp_report(metrics, week_start.isoformat(), week_end.isoformat())
                wa_result = _send_whatsapp_report(phone, wa_message, business_id, job_id)
            else:
                wa_result = {"sent": False, "sid": None, "error": "No WhatsApp phone configured"}
            job["whatsapp"] = wa_result
        else:
            job["whatsapp"] = {"sent": False, "sid": None, "error": "WhatsApp disabled"}

        from backend.routes.analytics import log_activity
        log_activity(
            business_id=business_id,
            event_type="report",
            message=f"Scheduled report — revenue: {metrics.get('weekly_revenue')}",
            status="success",
            organization_id=organization_id,
            metadata={"job_id": job_id, "schedule_id": schedule_id},
        )
    except Exception as exc:
        job["status"] = "failed"
        job["finished_at"] = datetime.now(timezone.utc).isoformat()
        job["error"] = str(exc)
        logger.error("[scheduler] job %s failed: %s", job_id, exc)

    return job_id
