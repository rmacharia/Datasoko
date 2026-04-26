from __future__ import annotations

import json
import hmac
import os
import tempfile
from contextlib import suppress
from datetime import date, datetime, timedelta, timezone
from pathlib import Path
from typing import Any
from urllib import error as url_error
from urllib import request as url_request
from uuid import uuid4

from fastapi import Depends, FastAPI, File, Form, Header, HTTPException, UploadFile
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel, Field

app = FastAPI(title="DataSoko API", version="0.1.0")
APP_VERSION = "0.1.0"
SCHEMA_VERSION = "1.0"
NORMALIZER_VERSION = "1.0"
CONTRACT_VERSION = "1.0"

LAST_RUN_SUMMARY: dict[str, Any] | None = None
JOBS: dict[str, dict[str, Any]] = {}


def _cors_origins_from_env() -> list[str]:
    raw = os.getenv("BACKEND_CORS_ORIGINS", "http://localhost:3000")
    return [origin.strip() for origin in raw.split(",") if origin.strip()]


app.add_middleware(
    CORSMiddleware,
    allow_origins=_cors_origins_from_env(),
    allow_credentials=False,
    allow_methods=["GET", "POST", "PUT", "OPTIONS"],
    allow_headers=["Authorization", "Content-Type"],
)


class IngestWeeklyRequest(BaseModel):
    business_id: str = Field(min_length=1)
    week_start: date
    week_end: date
    excel_file_path: str | None = None
    mpesa_file_path: str | None = None
    business_currency: str = "KES"
    ensure_table: bool = True


class WeeklyMetricsRequest(BaseModel):
    business_id: str = Field(min_length=1)
    week_start: date
    week_end: date
    slow_mover_days: int = Field(default=14, ge=1)
    top_n_products: int = Field(default=5, ge=1, le=20)


class AdminGenerateReportRequest(BaseModel):
    business_id: str | None = None
    week_start: date
    week_end: date
    slow_mover_days: int = Field(default=14, ge=1)
    top_n_products: int = Field(default=5, ge=1, le=20)
    business_name: str = "Your Business"
    sme_type: str = "retail"
    currency: str = "KES"
    all_businesses: bool = False


class OperationalSettingsUpdate(BaseModel):
    default_business_id: str | None = Field(default=None, min_length=1)
    default_currency: str | None = Field(default=None, min_length=1, max_length=8)
    timezone: str | None = Field(default=None, min_length=1)
    report_schedule_day: str | None = Field(default=None, min_length=1)
    report_schedule_time: str | None = Field(default=None, pattern=r"^\d{2}:\d{2}$")


class AiNarratorSettingsUpdate(BaseModel):
    provider: str | None = Field(default=None, min_length=1)
    model: str | None = Field(default=None, min_length=1)
    temperature: float | None = Field(default=None, ge=0.0, le=1.0)
    max_output_tokens: int | None = Field(default=None, ge=64, le=4096)
    strict_json_only: bool | None = None
    metrics_only_fallback: bool | None = None
    azure_endpoint: str | None = None
    azure_deployment: str | None = None
    api_key: str | None = Field(default=None, repr=False)


class WhatsAppSettingsUpdate(BaseModel):
    provider: str | None = Field(default=None, min_length=1)
    phone_number_id: str | None = None
    business_account_id: str | None = None
    sender_display_name: str | None = None
    webhook_callback_url: str | None = None
    access_token: str | None = Field(default=None, repr=False)
    webhook_verify_token: str | None = Field(default=None, repr=False)


class AdminSettingsUpdateRequest(BaseModel):
    operational: OperationalSettingsUpdate | None = None
    ai: AiNarratorSettingsUpdate | None = None
    whatsapp: WhatsAppSettingsUpdate | None = None


class WhatsAppTestSendRequest(BaseModel):
    to_phone: str = Field(min_length=6, max_length=24)
    message: str | None = Field(default=None, min_length=1, max_length=800)


def _version_payload() -> dict[str, str]:
    return {
        "app_version": APP_VERSION,
        "schema_version": SCHEMA_VERSION,
        "normalizer_version": NORMALIZER_VERSION,
        "contract_version": CONTRACT_VERSION,
    }


def _require_admin_token(authorization: str | None = Header(default=None, alias="Authorization")) -> None:
    admin_token = os.getenv("ADMIN_TOKEN", "").strip()
    if not admin_token:
        raise HTTPException(status_code=503, detail="ADMIN_TOKEN is not configured.")

    if not authorization or not authorization.startswith("Bearer "):
        raise HTTPException(status_code=401, detail="Missing bearer token.")

    provided = authorization.removeprefix("Bearer ").strip()
    if not hmac.compare_digest(provided, admin_token):
        raise HTTPException(status_code=401, detail="Invalid admin token.")


def _summary_from_quality(
    *,
    business_id: str,
    dataset: str,
    week_start: date,
    week_end: date,
    quality: dict[str, Any],
    persisted: bool,
) -> dict[str, Any]:
    return {
        "business_id": business_id,
        "dataset": dataset,
        "week_start": week_start.isoformat(),
        "week_end": week_end.isoformat(),
        "row_count": int(quality.get("row_count", 0)),
        "valid_row_count": int(quality.get("valid_row_count", 0)),
        "error_count": int(quality.get("error_count", 0)),
        "warning_count": int(quality.get("warning_count", 0)),
        "quality_score": int(quality.get("quality_score", 0)),
        "quality_band": str(quality.get("quality_band", "Low")),
        "persisted": persisted,
    }


def _redact_issues(issues: list[dict[str, Any]]) -> list[dict[str, Any]]:
    # Return actionable validation issues without exposing raw offending values.
    redacted: list[dict[str, Any]] = []
    for issue in issues:
        redacted.append(
            {
                "error_code": issue.get("error_code"),
                "severity": issue.get("severity"),
                "message": issue.get("message"),
                "row_number": issue.get("row_number"),
                "field": issue.get("field"),
                "rule_id": issue.get("rule_id"),
                "suggestion": issue.get("suggestion"),
            }
        )
    return redacted


def _update_last_run(summary: dict[str, Any]) -> None:
    global LAST_RUN_SUMMARY
    LAST_RUN_SUMMARY = {
        **summary,
        "timestamp": datetime.now(timezone.utc).isoformat(),
    }


def _compute_and_format_report(
    *,
    business_id: str,
    week_start: date,
    week_end: date,
    slow_mover_days: int,
    top_n_products: int,
    business_name: str,
    sme_type: str,
    currency: str,
) -> dict[str, Any]:
    payload = WeeklyMetricsRequest(
        business_id=business_id,
        week_start=week_start,
        week_end=week_end,
        slow_mover_days=slow_mover_days,
        top_n_products=top_n_products,
    )
    metrics = _compute_weekly_metrics(payload)

    from backend.messaging import format_weekly_whatsapp_message
    from backend.ai import generate_llm_narration

    whatsapp_message = format_weekly_whatsapp_message(
        metrics=metrics,
        business_name=business_name,
        currency=currency,
        sme_type=sme_type,
    )
    llm_narration_json: dict[str, Any] | None
    try:
        llm_narration_json = generate_llm_narration(
            metrics_json=metrics,
            business_profile={
                "business_name": business_name,
                "business_type": sme_type,
                "currency": currency,
            },
            retrieved_summaries=[],
        )
    except Exception:
        llm_narration_json = {
            "summary": "Narration unavailable; falling back to metrics-only WhatsApp preview.",
            "insights": [],
            "recommendations": [],
            "source": "narration_error",
        }

    return {
        "metrics_json": metrics,
        "llm_narration_json": llm_narration_json,
        "whatsapp_preview": {"message": whatsapp_message},
    }


def _mask_phone(phone: str) -> str:
    normalized = "".join(ch for ch in phone if ch.isdigit() or ch == "+")
    if len(normalized) <= 4:
        return "***"
    return f"{normalized[:3]}***{normalized[-2:]}"


def _settings_response() -> dict[str, Any]:
    from backend.admin_settings_store import SETTINGS_STORE

    non_secret = SETTINGS_STORE.get_non_secret_settings()
    ai = dict(non_secret.get("ai", {}))
    whatsapp = dict(non_secret.get("whatsapp", {}))

    ai["has_api_key"] = SETTINGS_STORE.has_secret("ai_api_key")
    whatsapp["has_access_token"] = SETTINGS_STORE.has_secret("whatsapp_access_token")
    whatsapp["has_webhook_verify_token"] = SETTINGS_STORE.has_secret("whatsapp_verify_token")

    return {
        "operational": non_secret.get("operational", {}),
        "ai": ai,
        "whatsapp": whatsapp,
    }


@app.get("/health")
def health() -> dict[str, str]:
    return {"status": "ok"}


@app.get("/version")
def version() -> dict[str, str]:
    return _version_payload()


@app.post("/ingest/weekly")
def ingest_weekly(payload: IngestWeeklyRequest) -> dict[str, Any]:
    if payload.week_end < payload.week_start:
        raise HTTPException(status_code=400, detail="week_end must be on or after week_start")

    if not payload.excel_file_path and not payload.mpesa_file_path:
        raise HTTPException(status_code=400, detail="Provide at least one of excel_file_path or mpesa_file_path")

    if payload.excel_file_path and not Path(payload.excel_file_path).exists():
        raise HTTPException(status_code=400, detail=f"Excel file not found: {payload.excel_file_path}")

    if payload.mpesa_file_path and not Path(payload.mpesa_file_path).exists():
        raise HTTPException(status_code=400, detail=f"M-Pesa file not found: {payload.mpesa_file_path}")

    try:
        from backend.ingestion.factory import create_ingestion_runtime

        runtime = create_ingestion_runtime(ensure_table=payload.ensure_table)
    except Exception as exc:
        raise HTTPException(status_code=500, detail=f"Failed to initialize ingestion runtime: {exc}") from exc

    try:
        result = runtime.service.ingest_weekly_bundle(
            business_id=payload.business_id,
            week_start=payload.week_start,
            week_end=payload.week_end,
            excel_file_path=payload.excel_file_path,
            mpesa_file_path=payload.mpesa_file_path,
            business_currency=payload.business_currency,
        )
        response = {
            "excel": result.excel.__dict__ if result.excel else None,
            "mpesa": result.mpesa.__dict__ if result.mpesa else None,
        }

        _update_last_run(
            {
                "source": "ingest_weekly",
                "business_id": payload.business_id,
                "week_start": payload.week_start.isoformat(),
                "week_end": payload.week_end.isoformat(),
                "excel": response["excel"],
                "mpesa": response["mpesa"],
            }
        )

        return response
    except Exception as exc:
        raise HTTPException(status_code=500, detail=f"Ingestion failed: {exc}") from exc
    finally:
        runtime.close()


@app.post("/metrics/weekly")
def weekly_metrics(payload: WeeklyMetricsRequest) -> dict[str, Any]:
    if payload.week_end < payload.week_start:
        raise HTTPException(status_code=400, detail="week_end must be on or after week_start")

    return _compute_weekly_metrics(payload)


@app.get("/metrics/weekly")
def weekly_metrics_get(
    business_id: str,
    week_start: date,
    week_end: date,
    slow_mover_days: int = 14,
    top_n_products: int = 5,
) -> dict[str, Any]:
    payload = WeeklyMetricsRequest(
        business_id=business_id,
        week_start=week_start,
        week_end=week_end,
        slow_mover_days=slow_mover_days,
        top_n_products=top_n_products,
    )
    return _compute_weekly_metrics(payload)


@app.get("/whatsapp/weekly")
def whatsapp_weekly_message(
    business_id: str,
    week_start: date,
    week_end: date,
    business_name: str = "Your Business",
    sme_type: str = "retail",
    currency: str = "KES",
    slow_mover_days: int = 14,
    top_n_products: int = 5,
) -> dict[str, str]:
    report = _compute_and_format_report(
        business_id=business_id,
        week_start=week_start,
        week_end=week_end,
        slow_mover_days=slow_mover_days,
        top_n_products=top_n_products,
        business_name=business_name,
        sme_type=sme_type,
        currency=currency,
    )
    return report["whatsapp_preview"]


@app.get("/admin/status")
def admin_status(_: None = Depends(_require_admin_token)) -> dict[str, Any]:
    db_connected = False
    db_error: str | None = None
    connection: Any | None = None

    try:
        from backend.storage import create_postgres_connection
        from backend.storage.postgres_ingestion_store import PostgresIngestionStore

        connection = create_postgres_connection()
        store = PostgresIngestionStore(connection)
        store.ensure_table()
        db_connected = True
    except Exception as exc:
        db_error = str(exc)
    finally:
        if connection is not None:
            connection.close()

    return {
        "backend_health": "ok",
        "version": _version_payload(),
        "db": {
            "connected": db_connected,
            "error": db_error,
        },
        "last_run": LAST_RUN_SUMMARY,
    }


@app.post("/admin/upload/weekly")
async def admin_upload_weekly(
    business_id: str = Form(...),
    week_start: date = Form(...),
    week_end: date = Form(...),
    business_currency: str = Form("KES"),
    excel_file: UploadFile | None = File(None),
    mpesa_file: UploadFile | None = File(None),
    _: None = Depends(_require_admin_token),
) -> dict[str, Any]:
    if week_end < week_start:
        raise HTTPException(status_code=400, detail="week_end must be on or after week_start")

    if not excel_file and not mpesa_file:
        raise HTTPException(status_code=400, detail="Provide at least one of excel_file or mpesa_file")

    try:
        from backend.ingestion.loaders import load_excel_sales, load_mpesa_csv
        from backend.storage import create_postgres_connection
        from backend.storage.postgres_ingestion_store import PostgresIngestionStore
    except Exception as exc:
        raise HTTPException(status_code=500, detail=f"Failed to initialize upload runtime: {exc}") from exc

    temporary_paths: list[str] = []

    def _persisted_payload(
        *,
        dataset: str,
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

    def _save_temp_file(upload: UploadFile) -> str:
        suffix = Path(upload.filename or "").suffix
        with tempfile.NamedTemporaryFile(delete=False, suffix=suffix) as tmp:
            data = upload.file.read()
            tmp.write(data)
            tmp_path = tmp.name
        temporary_paths.append(tmp_path)
        return tmp_path

    connection: Any | None = None
    store: Any | None = None

    excel_response: dict[str, Any] | None = None
    mpesa_response: dict[str, Any] | None = None

    try:
        connection = create_postgres_connection()
        store = PostgresIngestionStore(connection)
        store.ensure_table()

        if excel_file:
            excel_path = _save_temp_file(excel_file)
            excel_result = load_excel_sales(excel_path, business_currency=business_currency)
            excel_dump = excel_result.model_dump(mode="json")
            store.upsert_weekly_payload(
                business_id=business_id,
                dataset="excel_sales",
                week_start=week_start,
                week_end=week_end,
                payload=_persisted_payload(
                    dataset="excel_sales",
                    source_file=excel_file.filename or Path(excel_path).name,
                    result=excel_dump,
                ),
            )
            excel_response = {
                "summary": _summary_from_quality(
                    business_id=business_id,
                    dataset="excel_sales",
                    week_start=week_start,
                    week_end=week_end,
                    quality=excel_dump["quality"],
                    persisted=True,
                ),
                "quality": excel_dump["quality"],
                "schema_fields": sorted(list(excel_dump["records"][0].keys())) if excel_dump["records"] else [],
                "issues": _redact_issues(excel_dump["issues"]),
            }

        if mpesa_file:
            mpesa_path = _save_temp_file(mpesa_file)
            mpesa_result = load_mpesa_csv(mpesa_path)
            mpesa_dump = mpesa_result.model_dump(mode="json")
            store.upsert_weekly_payload(
                business_id=business_id,
                dataset="mpesa",
                week_start=week_start,
                week_end=week_end,
                payload=_persisted_payload(
                    dataset="mpesa",
                    source_file=mpesa_file.filename or Path(mpesa_path).name,
                    result=mpesa_dump,
                ),
            )
            mpesa_response = {
                "summary": _summary_from_quality(
                    business_id=business_id,
                    dataset="mpesa",
                    week_start=week_start,
                    week_end=week_end,
                    quality=mpesa_dump["quality"],
                    persisted=True,
                ),
                "quality": mpesa_dump["quality"],
                "schema_fields": sorted(list(mpesa_dump["records"][0].keys())) if mpesa_dump["records"] else [],
                "issues": _redact_issues(mpesa_dump["issues"]),
            }

        response = {
            "business_id": business_id,
            "week_start": week_start.isoformat(),
            "week_end": week_end.isoformat(),
            "excel": excel_response,
            "mpesa": mpesa_response,
        }
        _update_last_run(
            {
                "source": "admin_upload_weekly",
                "business_id": business_id,
                "week_start": week_start.isoformat(),
                "week_end": week_end.isoformat(),
                "excel": excel_response["summary"] if excel_response else None,
                "mpesa": mpesa_response["summary"] if mpesa_response else None,
            }
        )
        return response
    except HTTPException:
        raise
    except Exception as exc:
        raise HTTPException(status_code=500, detail=f"Admin upload failed: {exc}") from exc
    finally:
        for path in temporary_paths:
            try:
                os.unlink(path)
            except OSError:
                pass
        if connection is not None:
            connection.close()


@app.get("/admin/reports")
def admin_reports(
    business_id: str,
    week_start: date,
    week_end: date,
    slow_mover_days: int = 14,
    top_n_products: int = 5,
    business_name: str = "Your Business",
    sme_type: str = "retail",
    currency: str = "KES",
    _: None = Depends(_require_admin_token),
) -> dict[str, Any]:
    if week_end < week_start:
        raise HTTPException(status_code=400, detail="week_end must be on or after week_start")

    report = _compute_and_format_report(
        business_id=business_id,
        week_start=week_start,
        week_end=week_end,
        slow_mover_days=slow_mover_days,
        top_n_products=top_n_products,
        business_name=business_name,
        sme_type=sme_type,
        currency=currency,
    )
    return {
        "business_id": business_id,
        "week_start": week_start.isoformat(),
        "week_end": week_end.isoformat(),
        **report,
    }


@app.post("/admin/reports/generate")
def admin_generate_report(payload: AdminGenerateReportRequest, _: None = Depends(_require_admin_token)) -> dict[str, Any]:
    if payload.week_end < payload.week_start:
        raise HTTPException(status_code=400, detail="week_end must be on or after week_start")

    if payload.all_businesses:
        raise HTTPException(status_code=400, detail="all_businesses is not yet supported in this MVP.")

    if not payload.business_id:
        raise HTTPException(status_code=400, detail="business_id is required when all_businesses is false.")

    job_id = uuid4().hex
    job = {
        "job_id": job_id,
        "status": "queued",
        "requested_at": datetime.now(timezone.utc).isoformat(),
        "started_at": None,
        "finished_at": None,
        "error": None,
        "business_id": payload.business_id,
        "week_start": payload.week_start.isoformat(),
        "week_end": payload.week_end.isoformat(),
        "result_summary": None,
    }
    JOBS[job_id] = job

    try:
        job["status"] = "running"
        job["started_at"] = datetime.now(timezone.utc).isoformat()

        report = _compute_and_format_report(
            business_id=payload.business_id,
            week_start=payload.week_start,
            week_end=payload.week_end,
            slow_mover_days=payload.slow_mover_days,
            top_n_products=payload.top_n_products,
            business_name=payload.business_name,
            sme_type=payload.sme_type,
            currency=payload.currency,
        )

        metrics = report["metrics_json"]
        job["status"] = "completed"
        job["finished_at"] = datetime.now(timezone.utc).isoformat()
        job["result_summary"] = {
            "weekly_revenue": metrics.get("weekly_revenue"),
            "repeat_customers": metrics.get("repeat_customers"),
            "records_processed": metrics.get("meta", {}).get("records_processed"),
        }

        _update_last_run(
            {
                "source": "admin_generate_report",
                "business_id": payload.business_id,
                "week_start": payload.week_start.isoformat(),
                "week_end": payload.week_end.isoformat(),
                "job_id": job_id,
                "result_summary": job["result_summary"],
            }
        )
    except Exception as exc:
        job["status"] = "failed"
        job["finished_at"] = datetime.now(timezone.utc).isoformat()
        job["error"] = str(exc)

    return {
        "job_id": job_id,
        "status": job["status"],
    }


@app.get("/admin/jobs/{job_id}")
def admin_job_status(job_id: str, _: None = Depends(_require_admin_token)) -> dict[str, Any]:
    job = JOBS.get(job_id)
    if not job:
        raise HTTPException(status_code=404, detail="Job not found.")
    return job


@app.get("/admin/settings")
def admin_get_settings(_: None = Depends(_require_admin_token)) -> dict[str, Any]:
    return _settings_response()


@app.put("/admin/settings")
def admin_update_settings(payload: AdminSettingsUpdateRequest, _: None = Depends(_require_admin_token)) -> dict[str, Any]:
    from backend.admin_settings_store import SETTINGS_STORE

    updates: dict[str, Any] = {}

    if payload.operational is not None:
        updates["operational"] = payload.operational.model_dump(exclude_none=True)

    if payload.ai is not None:
        ai_updates = payload.ai.model_dump(exclude_none=True)
        api_key = ai_updates.pop("api_key", None)
        updates["ai"] = ai_updates
        SETTINGS_STORE.set_secret("ai_api_key", api_key)

    if payload.whatsapp is not None:
        whatsapp_updates = payload.whatsapp.model_dump(exclude_none=True)
        access_token = whatsapp_updates.pop("access_token", None)
        verify_token = whatsapp_updates.pop("webhook_verify_token", None)
        updates["whatsapp"] = whatsapp_updates
        SETTINGS_STORE.set_secret("whatsapp_access_token", access_token)
        SETTINGS_STORE.set_secret("whatsapp_verify_token", verify_token)

    if updates:
        SETTINGS_STORE.update_non_secret_settings(updates)

    return _settings_response()


@app.post("/admin/whatsapp/test-send")
def admin_whatsapp_test_send(payload: WhatsAppTestSendRequest, _: None = Depends(_require_admin_token)) -> dict[str, Any]:
    from backend.admin_settings_store import SETTINGS_STORE

    settings = SETTINGS_STORE.get_non_secret_settings()
    whatsapp_cfg = settings.get("whatsapp", {})
    provider = str(whatsapp_cfg.get("provider") or "meta_cloud_api")
    phone_number_id = str(whatsapp_cfg.get("phone_number_id") or os.getenv("WHATSAPP_PHONE_NUMBER_ID") or "").strip()
    access_token = SETTINGS_STORE.get_secret("whatsapp_access_token")

    if provider != "meta_cloud_api":
        return {
            "status": "not_supported",
            "provider_response_summary": {
                "provider": provider,
                "detail": "Test send is only implemented for meta_cloud_api in this MVP.",
            },
        }

    if not phone_number_id or not access_token:
        return {
            "status": "not_configured",
            "provider_response_summary": {
                "provider": provider,
                "detail": "WhatsApp phone_number_id/access token is not configured.",
            },
        }

    safe_template = "DataSoko internal integration test message. No business data included."
    outbound_payload = {
        "messaging_product": "whatsapp",
        "to": payload.to_phone.strip(),
        "type": "text",
        "text": {"preview_url": False, "body": safe_template},
    }
    request_body = json.dumps(outbound_payload).encode("utf-8")
    req = url_request.Request(
        url=f"https://graph.facebook.com/v20.0/{phone_number_id}/messages",
        data=request_body,
        headers={
            "Authorization": f"Bearer {access_token}",
            "Content-Type": "application/json",
        },
        method="POST",
    )

    try:
        with url_request.urlopen(req, timeout=8) as response:  # noqa: S310
            raw = response.read().decode("utf-8")
            parsed: dict[str, Any] | None = None
            with suppress(Exception):
                parsed = json.loads(raw)
            messages = parsed.get("messages") if isinstance(parsed, dict) else None
            return {
                "status": "sent",
                "provider_response_summary": {
                    "provider": provider,
                    "to_phone_masked": _mask_phone(payload.to_phone),
                    "http_status": getattr(response, "status", 200),
                    "message_count": len(messages) if isinstance(messages, list) else 0,
                },
            }
    except url_error.HTTPError as exc:
        return {
            "status": "failed",
            "provider_response_summary": {
                "provider": provider,
                "to_phone_masked": _mask_phone(payload.to_phone),
                "http_status": exc.code,
                "detail": "Provider rejected test message.",
            },
        }
    except Exception:
        return {
            "status": "failed",
            "provider_response_summary": {
                "provider": provider,
                "to_phone_masked": _mask_phone(payload.to_phone),
                "detail": "Could not reach WhatsApp provider endpoint.",
            },
        }


def _compute_weekly_metrics(payload: WeeklyMetricsRequest) -> dict[str, Any]:
    try:
        from backend.metrics import compute_weekly_metrics
        from backend.storage import create_postgres_connection
        from backend.storage.postgres_ingestion_store import PostgresIngestionStore

        connection = create_postgres_connection()
        store = PostgresIngestionStore(connection)
        store.ensure_table()
    except Exception as exc:
        raise HTTPException(status_code=500, detail=f"Failed to initialize metrics runtime: {exc}") from exc

    try:
        prev_week_end = payload.week_start - timedelta(days=1)
        prev_week_start = prev_week_end - timedelta(days=6)

        # Range-based retrieval allows arbitrary report windows while keeping
        # previous-period computations available to the metrics engine.
        range_start = min(prev_week_start, payload.week_start)
        range_end = max(prev_week_end, payload.week_end)

        payloads: list[dict[str, Any]] = []
        if hasattr(store, "get_payloads_in_range"):
            payloads = store.get_payloads_in_range(
                business_id=payload.business_id,
                dataset="excel_sales",
                range_start=range_start,
                range_end=range_end,
            )
        else:
            # Backward compatibility with older store stubs.
            weekly_payload = store.get_weekly_payload(
                business_id=payload.business_id,
                dataset="excel_sales",
                week_start=payload.week_start,
                week_end=payload.week_end,
            )
            previous_week_payload = store.get_weekly_payload(
                business_id=payload.business_id,
                dataset="excel_sales",
                week_start=prev_week_start,
                week_end=prev_week_end,
            )
            payloads = [p for p in [weekly_payload, previous_week_payload] if p]

        if not payloads:
            raise HTTPException(
                status_code=404,
                detail="No normalized excel_sales payload found for this business/date range",
            )

        records: list[Any] = []
        for payload_obj in payloads:
            current_records = payload_obj.get("records")
            if not isinstance(current_records, list):
                raise HTTPException(status_code=500, detail="Stored payload is invalid: records must be a list")
            records.extend(current_records)

        metrics = compute_weekly_metrics(
            sales_records=records,
            week_start=payload.week_start,
            week_end=payload.week_end,
            slow_mover_days=payload.slow_mover_days,
            top_n_products=payload.top_n_products,
        )
        return metrics
    except HTTPException:
        raise
    except Exception as exc:
        raise HTTPException(status_code=500, detail=f"Metrics computation failed: {exc}") from exc
    finally:
        connection.close()
