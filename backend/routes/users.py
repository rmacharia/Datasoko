from __future__ import annotations

import logging
from typing import Any
from uuid import uuid4

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel, Field

from backend.auth import (
    ROLE_ORG_ADMIN,
    ROLE_SME_USER,
    ROLE_SUPER_ADMIN,
    AuthUser,
    hash_password,
    is_org_admin,
    is_super_admin,
    require_role,
)
from backend.db.connection import get_connection

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/users", tags=["users"])


_ALLOWED_NEW_ROLES = (ROLE_SUPER_ADMIN, ROLE_ORG_ADMIN, ROLE_SME_USER)


class CreateUserRequest(BaseModel):
    email: str = Field(min_length=3)
    password: str = Field(min_length=6)
    role: str = Field(min_length=1)
    organization_id: str | None = None
    business_id: str | None = None


class UpdateUserRequest(BaseModel):
    role: str | None = None
    organization_id: str | None = None
    business_id: str | None = None
    is_active: bool | None = None


def _validate_role_placement(role: str, organization_id: str | None, business_id: str | None) -> tuple[str | None, str | None]:
    if role not in _ALLOWED_NEW_ROLES:
        raise HTTPException(
            status_code=400,
            detail=f"role must be one of {_ALLOWED_NEW_ROLES}",
        )
    if role == ROLE_SUPER_ADMIN:
        return None, None
    if role == ROLE_ORG_ADMIN:
        if not organization_id:
            raise HTTPException(status_code=400, detail="organization_id is required for admin")
        return organization_id, None
    # sme_user
    if not organization_id:
        raise HTTPException(status_code=400, detail="organization_id is required for sme_user")
    if not business_id:
        raise HTTPException(status_code=400, detail="business_id is required for sme_user")
    return organization_id, business_id


@router.post("")
def create_user(
    payload: CreateUserRequest,
    actor: AuthUser = Depends(require_role(ROLE_SUPER_ADMIN, ROLE_ORG_ADMIN)),
) -> dict[str, Any]:
    # Org admins can only create sme_users inside their own org.
    # Super admins can create admin or sme_user for any org (platform
    # super_admins are created via /auth/bootstrap or /auth/register, not
    # through the tenant-user endpoint).
    if is_org_admin(actor):
        if payload.role != ROLE_SME_USER:
            raise HTTPException(status_code=403, detail="Org admins can only create sme_user accounts")
        if payload.organization_id and payload.organization_id != actor.organization_id:
            raise HTTPException(status_code=403, detail="Cannot create users in another organization")
        target_org = actor.organization_id
    else:
        if payload.role == ROLE_SUPER_ADMIN:
            raise HTTPException(
                status_code=400,
                detail="super_admin accounts are created via /auth/register, not /users",
            )
        target_org = payload.organization_id

    organization_id, business_id = _validate_role_placement(payload.role, target_org, payload.business_id)

    user_id = uuid4().hex
    pw_hash = hash_password(payload.password)

    conn = get_connection()
    try:
        with conn.cursor() as cur:
            cur.execute("SELECT 1 FROM users WHERE email = %s", (payload.email,))
            if cur.fetchone():
                raise HTTPException(status_code=409, detail="Email already registered")
            cur.execute("""
                INSERT INTO users (id, email, password_hash, organization_id, role, business_id)
                VALUES (%s, %s, %s, %s, %s, %s)
            """, (user_id, payload.email, pw_hash, organization_id, payload.role, business_id))
        conn.commit()
    except HTTPException:
        raise
    except Exception as exc:
        conn.rollback()
        logger.error("Create user failed: %s", exc)
        raise HTTPException(status_code=500, detail="Failed to create user") from exc
    finally:
        conn.close()

    return {
        "id": user_id,
        "email": payload.email,
        "role": payload.role,
        "organization_id": organization_id,
        "business_id": business_id,
        "is_active": True,
    }


@router.get("")
def list_users(
    actor: AuthUser = Depends(require_role(ROLE_SUPER_ADMIN, ROLE_ORG_ADMIN)),
) -> list[dict[str, Any]]:
    conn = get_connection()
    try:
        with conn.cursor() as cur:
            if is_super_admin(actor):
                cur.execute("""
                    SELECT id, email, role, organization_id, business_id, is_active, created_at
                    FROM users
                    ORDER BY created_at DESC
                """)
            else:
                cur.execute("""
                    SELECT id, email, role, organization_id, business_id, is_active, created_at
                    FROM users
                    WHERE organization_id = %s
                    ORDER BY created_at DESC
                """, (actor.organization_id,))
            rows = cur.fetchall()

        return [
            {
                "id": row[0],
                "email": row[1],
                "role": row[2],
                "organization_id": row[3],
                "business_id": row[4],
                "is_active": row[5],
                "created_at": row[6].isoformat() if hasattr(row[6], "isoformat") else str(row[6]),
            }
            for row in rows
        ]
    except Exception as exc:
        logger.error("List users failed: %s", exc)
        raise HTTPException(status_code=500, detail=str(exc)) from exc
    finally:
        conn.close()


@router.patch("/{user_id}")
def update_user(
    user_id: str,
    payload: UpdateUserRequest,
    actor: AuthUser = Depends(require_role(ROLE_SUPER_ADMIN, ROLE_ORG_ADMIN)),
) -> dict[str, Any]:
    updates: list[str] = []
    values: list[Any] = []

    if payload.role is not None:
        if payload.role not in _ALLOWED_NEW_ROLES:
            raise HTTPException(status_code=400, detail=f"role must be one of {_ALLOWED_NEW_ROLES}")
        if is_org_admin(actor) and payload.role == ROLE_SUPER_ADMIN:
            raise HTTPException(status_code=403, detail="Org admins cannot promote to super_admin")
        updates.append("role = %s")
        values.append(payload.role)
    if payload.organization_id is not None:
        if is_org_admin(actor) and payload.organization_id != actor.organization_id:
            raise HTTPException(status_code=403, detail="Cannot reassign users to another organization")
        updates.append("organization_id = %s")
        values.append(payload.organization_id)
    if payload.business_id is not None:
        updates.append("business_id = %s")
        values.append(payload.business_id)
    if payload.is_active is not None:
        updates.append("is_active = %s")
        values.append(payload.is_active)

    if not updates:
        raise HTTPException(status_code=400, detail="No fields to update")

    conn = get_connection()
    try:
        with conn.cursor() as cur:
            if is_super_admin(actor):
                values.append(user_id)
                cur.execute(
                    f"UPDATE users SET {', '.join(updates)} WHERE id = %s",
                    values,
                )
            else:
                values.append(user_id)
                values.append(actor.organization_id)
                cur.execute(
                    f"UPDATE users SET {', '.join(updates)} WHERE id = %s AND organization_id = %s",
                    values,
                )
            if cur.rowcount == 0:
                raise HTTPException(status_code=404, detail="User not found")
        conn.commit()
    except HTTPException:
        raise
    except Exception as exc:
        conn.rollback()
        logger.error("Update user failed: %s", exc)
        raise HTTPException(status_code=500, detail=str(exc)) from exc
    finally:
        conn.close()

    return {"id": user_id, "updated": True}


@router.delete("/{user_id}")
def delete_user(
    user_id: str,
    actor: AuthUser = Depends(require_role(ROLE_SUPER_ADMIN, ROLE_ORG_ADMIN)),
) -> dict[str, Any]:
    if user_id == actor.id:
        raise HTTPException(status_code=400, detail="Cannot disable your own account")

    conn = get_connection()
    try:
        with conn.cursor() as cur:
            if is_super_admin(actor):
                cur.execute(
                    "UPDATE users SET is_active = FALSE WHERE id = %s",
                    (user_id,),
                )
            else:
                cur.execute(
                    "UPDATE users SET is_active = FALSE WHERE id = %s AND organization_id = %s",
                    (user_id, actor.organization_id),
                )
            if cur.rowcount == 0:
                raise HTTPException(status_code=404, detail="User not found")
        conn.commit()
    except HTTPException:
        raise
    except Exception as exc:
        conn.rollback()
        logger.error("Delete user failed: %s", exc)
        raise HTTPException(status_code=500, detail=str(exc)) from exc
    finally:
        conn.close()

    return {"id": user_id, "disabled": True}
