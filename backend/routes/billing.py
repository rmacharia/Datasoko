from __future__ import annotations

from datetime import datetime, timezone
from typing import Any

from fastapi import APIRouter, Depends, HTTPException

from backend.auth import (
    AuthUser,
    is_super_admin,
    require_any_authenticated,
)
from backend.db.connection import get_connection

router = APIRouter()

_CHECK_ORG_SQL = "SELECT 1 FROM organizations WHERE id = %s LIMIT 1"
_GET_SUB_SQL = """
SELECT plan, status, expiry_date
FROM subscriptions
WHERE organization_id = %s
LIMIT 1
""".strip()


def _do_billing_current(*, connection: Any, organization_id: str) -> dict[str, Any]:
    with connection.cursor() as cur:
        cur.execute(_CHECK_ORG_SQL, (organization_id,))
        if cur.fetchone() is None:
            raise HTTPException(status_code=404, detail="organization not found")

        cur.execute(_GET_SUB_SQL, (organization_id,))
        row = cur.fetchone()

    if row is None:
        raise HTTPException(status_code=404, detail="subscription not found")

    plan, status, expiry_date = row
    now = datetime.now(timezone.utc)

    if expiry_date is not None and expiry_date.tzinfo is None:
        expiry_date = expiry_date.replace(tzinfo=timezone.utc)

    active = (status == "active") and (expiry_date is not None) and (expiry_date > now)
    days_remaining = max(0, (expiry_date - now).days) if expiry_date and expiry_date > now else 0

    return {
        "organization_id": organization_id,
        "plan": plan,
        "status": status,
        "expiry_date": expiry_date.isoformat() if expiry_date else None,
        "active": active,
        "days_remaining": days_remaining,
    }


@router.get("/billing/current")
def billing_current(
    organization_id: str | None = None,
    actor: AuthUser = Depends(require_any_authenticated),
) -> dict[str, Any]:
    # Super admins query any org explicitly; tenant users are pinned to
    # their own org regardless of the query string.
    if is_super_admin(actor):
        if not organization_id:
            raise HTTPException(status_code=400, detail="organization_id is required for super_admin")
        target_org = organization_id
    else:
        target_org = actor.organization_id
        if organization_id and organization_id != target_org:
            raise HTTPException(status_code=403, detail="Cross-organization access denied")

    if not target_org:
        raise HTTPException(status_code=400, detail="organization_id could not be resolved from token")

    connection = get_connection()
    try:
        return _do_billing_current(connection=connection, organization_id=target_org)
    except HTTPException:
        raise
    except Exception as exc:
        raise HTTPException(status_code=500, detail=str(exc)) from exc
    finally:
        connection.close()
