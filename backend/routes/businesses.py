from __future__ import annotations

from typing import Any

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel, Field

from backend.auth import (
    AuthUser,
    is_org_admin,
    is_super_admin,
    require_any_authenticated,
    require_org_admin_or_platform,
)
from backend.db.connection import get_connection

router = APIRouter()

_CHECK_ORG_SQL = "SELECT 1 FROM organizations WHERE id = %s LIMIT 1"
_CHECK_BIZ_SQL = "SELECT 1 FROM businesses WHERE id = %s LIMIT 1"
_INSERT_BIZ_SQL = """
INSERT INTO businesses (id, organization_id, name, whatsapp_phone)
VALUES (%s, %s, %s, %s)
RETURNING id, organization_id, name, whatsapp_phone, created_at
""".strip()
_LIST_BIZ_SQL = """
SELECT id, name, whatsapp_phone, created_at
FROM businesses
WHERE organization_id = %s
ORDER BY created_at ASC
""".strip()


class CreateBusinessRequest(BaseModel):
    id: str = Field(min_length=1)
    organization_id: str | None = None
    name: str | None = None
    whatsapp_phone: str | None = None


def _do_create_business(
    *,
    connection: Any,
    business_id: str,
    organization_id: str,
    name: str | None,
    whatsapp_phone: str | None,
) -> dict[str, Any]:
    with connection.cursor() as cur:
        cur.execute(_CHECK_ORG_SQL, (organization_id,))
        if cur.fetchone() is None:
            raise HTTPException(status_code=400, detail=f"organization '{organization_id}' not found")

        cur.execute(_CHECK_BIZ_SQL, (business_id,))
        if cur.fetchone() is not None:
            raise HTTPException(status_code=409, detail=f"business '{business_id}' already exists")

        cur.execute(_INSERT_BIZ_SQL, (business_id, organization_id, name, whatsapp_phone))
        row = cur.fetchone()

    connection.commit()

    created_at = row[4]
    return {
        "id": row[0],
        "organization_id": row[1],
        "name": row[2],
        "whatsapp_phone": row[3],
        "created_at": created_at.isoformat() if hasattr(created_at, "isoformat") else str(created_at),
    }


def _do_list_businesses(*, connection: Any, organization_id: str) -> dict[str, Any]:
    with connection.cursor() as cur:
        cur.execute(_CHECK_ORG_SQL, (organization_id,))
        if cur.fetchone() is None:
            raise HTTPException(status_code=404, detail=f"organization '{organization_id}' not found")

        cur.execute(_LIST_BIZ_SQL, (organization_id,))
        rows = cur.fetchall()

    businesses = [
        {
            "id": r[0],
            "name": r[1],
            "whatsapp_phone": r[2],
            "created_at": r[3].isoformat() if hasattr(r[3], "isoformat") else str(r[3]),
        }
        for r in rows
    ]
    return {"organization_id": organization_id, "businesses": businesses}


@router.post("/businesses", status_code=201)
def create_business(
    payload: CreateBusinessRequest,
    actor: AuthUser = Depends(require_org_admin_or_platform),
) -> dict[str, Any]:
    if is_org_admin(actor):
        if payload.organization_id and payload.organization_id != actor.organization_id:
            raise HTTPException(status_code=403, detail="Cannot create business in another organization")
        target_org = actor.organization_id
    else:
        if not payload.organization_id:
            raise HTTPException(status_code=400, detail="organization_id is required for super_admin")
        target_org = payload.organization_id

    if not target_org:
        raise HTTPException(status_code=400, detail="organization_id could not be resolved from token")

    connection = get_connection()
    try:
        return _do_create_business(
            connection=connection,
            business_id=payload.id,
            organization_id=target_org,
            name=payload.name,
            whatsapp_phone=payload.whatsapp_phone,
        )
    except HTTPException:
        raise
    except Exception as exc:
        connection.rollback()
        raise HTTPException(status_code=500, detail=str(exc)) from exc
    finally:
        connection.close()


@router.get("/businesses")
def list_businesses(
    organization_id: str | None = None,
    actor: AuthUser = Depends(require_any_authenticated),
) -> dict[str, Any]:
    # Tenant users can only see their own org. Super admins may pass an
    # explicit organization_id.
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
        return _do_list_businesses(connection=connection, organization_id=target_org)
    except HTTPException:
        raise
    except Exception as exc:
        raise HTTPException(status_code=500, detail=str(exc)) from exc
    finally:
        connection.close()
