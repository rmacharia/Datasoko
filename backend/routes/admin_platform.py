from __future__ import annotations

import logging
import re
from typing import Any
from uuid import uuid4

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel, Field

from backend.auth import (
    ROLE_ORG_ADMIN,
    AuthUser,
    hash_password,
    require_platform_admin,
)
from backend.db.connection import get_connection

logger = logging.getLogger(__name__)

# Platform-scoped routes — these are strictly super_admin only and never
# leak into the tenant layer. Mounted under /admin to match existing
# guard conventions in main.py.
router = APIRouter(prefix="/admin", tags=["admin-platform"])


_ORG_ID_PATTERN = re.compile(r"^[a-z0-9_\-]{2,64}$")


class CreateOrganizationRequest(BaseModel):
    name: str = Field(min_length=1, max_length=120)
    organization_id: str | None = Field(default=None, min_length=2, max_length=64)
    admin_email: str = Field(min_length=3)
    admin_password: str = Field(min_length=6)


def _slugify(name: str) -> str:
    base = re.sub(r"[^a-z0-9]+", "_", name.lower()).strip("_")
    return (base or "org")[:40]


def _unique_org_id(cur: Any, desired: str) -> str:
    candidate = desired
    suffix = 0
    while True:
        cur.execute("SELECT 1 FROM organizations WHERE id = %s", (candidate,))
        if cur.fetchone() is None:
            return candidate
        suffix += 1
        candidate = f"{desired}_{suffix}"


@router.post("/organizations", status_code=201)
def create_organization(
    payload: CreateOrganizationRequest,
    _actor: AuthUser = Depends(require_platform_admin),
) -> dict[str, Any]:
    if payload.organization_id and not _ORG_ID_PATTERN.match(payload.organization_id):
        raise HTTPException(
            status_code=400,
            detail="organization_id must be lowercase alphanumeric, dash, or underscore (2–64 chars)",
        )

    desired_id = payload.organization_id or _slugify(payload.name)
    admin_id = uuid4().hex
    pw_hash = hash_password(payload.admin_password)

    conn = get_connection()
    try:
        with conn.cursor() as cur:
            cur.execute("SELECT 1 FROM users WHERE email = %s", (payload.admin_email,))
            if cur.fetchone() is not None:
                raise HTTPException(status_code=409, detail="Admin email already registered")

            org_id = _unique_org_id(cur, desired_id)

            cur.execute(
                "INSERT INTO organizations (id, name) VALUES (%s, %s)",
                (org_id, payload.name),
            )
            cur.execute(
                """
                INSERT INTO users (id, email, password_hash, organization_id, role, business_id)
                VALUES (%s, %s, %s, %s, %s, NULL)
                """,
                (admin_id, payload.admin_email, pw_hash, org_id, ROLE_ORG_ADMIN),
            )
        conn.commit()
    except HTTPException:
        conn.rollback()
        raise
    except Exception as exc:
        conn.rollback()
        logger.error("create_organization failed: %s", exc)
        raise HTTPException(status_code=500, detail="Failed to create organization") from exc
    finally:
        conn.close()

    return {
        "organization_id": org_id,
        "name": payload.name,
        "admin": {
            "id": admin_id,
            "email": payload.admin_email,
            "role": ROLE_ORG_ADMIN,
        },
    }


@router.get("/organizations")
def list_organizations(
    _actor: AuthUser = Depends(require_platform_admin),
) -> list[dict[str, Any]]:
    conn = get_connection()
    try:
        with conn.cursor() as cur:
            cur.execute(
                """
                SELECT
                    o.id,
                    o.name,
                    o.created_at,
                    (SELECT COUNT(*) FROM users u WHERE u.organization_id = o.id) AS user_count,
                    (SELECT COUNT(*) FROM businesses b WHERE b.organization_id = o.id) AS business_count,
                    s.plan,
                    s.status,
                    s.expiry_date
                FROM organizations o
                LEFT JOIN subscriptions s ON s.organization_id = o.id
                ORDER BY o.created_at DESC
                """
            )
            rows = cur.fetchall()
        return [
            {
                "id": row[0],
                "name": row[1],
                "created_at": row[2].isoformat() if hasattr(row[2], "isoformat") else str(row[2]),
                "user_count": int(row[3] or 0),
                "business_count": int(row[4] or 0),
                "plan": row[5],
                "status": row[6],
                "expiry_date": row[7].isoformat() if row[7] and hasattr(row[7], "isoformat") else None,
            }
            for row in rows
        ]
    except Exception as exc:
        logger.error("list_organizations failed: %s", exc)
        raise HTTPException(status_code=500, detail=str(exc)) from exc
    finally:
        conn.close()


@router.get("/businesses")
def list_all_businesses(
    _actor: AuthUser = Depends(require_platform_admin),
) -> list[dict[str, Any]]:
    conn = get_connection()
    try:
        with conn.cursor() as cur:
            cur.execute(
                """
                SELECT id, organization_id, name, whatsapp_phone, created_at
                FROM businesses
                ORDER BY created_at DESC
                """
            )
            rows = cur.fetchall()
        return [
            {
                "id": row[0],
                "organization_id": row[1],
                "name": row[2],
                "whatsapp_phone": row[3],
                "created_at": row[4].isoformat() if hasattr(row[4], "isoformat") else str(row[4]),
            }
            for row in rows
        ]
    except Exception as exc:
        logger.error("list_all_businesses failed: %s", exc)
        raise HTTPException(status_code=500, detail=str(exc)) from exc
    finally:
        conn.close()
