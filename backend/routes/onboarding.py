from __future__ import annotations

from datetime import datetime, timedelta, timezone
from typing import Any

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel, Field

from backend.auth import (
    AuthUser,
    is_org_admin,
    is_super_admin,
    require_org_admin_or_platform,
)
from backend.db.connection import get_connection

router = APIRouter()

_CHECK_SUB_SQL = """
SELECT organization_id, plan, status, expiry_date
FROM subscriptions
WHERE organization_id = %s
LIMIT 1
""".strip()

_INSERT_ORG_SQL = """
INSERT INTO organizations (id, name)
VALUES (%s, %s)
ON CONFLICT DO NOTHING
""".strip()

_INSERT_SUB_SQL = """
INSERT INTO subscriptions (organization_id, plan, status, expiry_date)
VALUES (%s, %s, %s, %s)
""".strip()


class OnboardRequest(BaseModel):
    organization_id: str | None = Field(default=None, min_length=1)
    name: str = Field(min_length=1)
    plan: str = Field(min_length=1)


def _do_onboard(*, connection: Any, organization_id: str, name: str, plan: str) -> dict[str, Any]:
    with connection.cursor() as cur:
        cur.execute(_CHECK_SUB_SQL, (organization_id,))
        existing = cur.fetchone()

    if existing is not None:
        expiry = existing[3]
        raise HTTPException(status_code=409, detail={
            "organization_id": existing[0],
            "plan": existing[1],
            "status": existing[2],
            "expiry_date": expiry.isoformat() if hasattr(expiry, "isoformat") else str(expiry),
        })

    expiry = datetime.now(timezone.utc) + timedelta(days=30)
    try:
        with connection.cursor() as cur:
            cur.execute(_INSERT_ORG_SQL, (organization_id, name))
            cur.execute(_INSERT_SUB_SQL, (organization_id, plan, "active", expiry))
        connection.commit()
    except Exception:
        connection.rollback()
        raise

    return {
        "organization_id": organization_id,
        "name": name,
        "plan": plan,
        "status": "active",
        "expiry_date": expiry.isoformat(),
    }


@router.post("/onboard", status_code=201)
def onboard(
    payload: OnboardRequest,
    actor: AuthUser = Depends(require_org_admin_or_platform),
) -> dict[str, Any]:
    # Tenant admins onboard their own org; super_admins may onboard any org
    # (but typically use /admin/organizations instead).
    if is_org_admin(actor):
        if payload.organization_id and payload.organization_id != actor.organization_id:
            raise HTTPException(status_code=403, detail="Cannot onboard another organization")
        organization_id = actor.organization_id
    else:
        if not payload.organization_id:
            raise HTTPException(status_code=400, detail="organization_id is required")
        organization_id = payload.organization_id

    if not organization_id:
        raise HTTPException(status_code=400, detail="organization_id could not be resolved from token")

    connection = get_connection()
    try:
        return _do_onboard(
            connection=connection,
            organization_id=organization_id,
            name=payload.name,
            plan=payload.plan,
        )
    except HTTPException:
        raise
    except Exception as exc:
        raise HTTPException(status_code=500, detail=str(exc)) from exc
    finally:
        connection.close()
