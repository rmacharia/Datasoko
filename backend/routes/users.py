from __future__ import annotations

import logging
from typing import Any
from uuid import uuid4

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel, Field

from backend.auth import AuthUser, get_current_user, hash_password
from backend.db.connection import get_connection

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/users", tags=["users"])


def _require_admin(user: AuthUser = Depends(get_current_user)) -> AuthUser:
    if user.role != "admin":
        raise HTTPException(status_code=403, detail="Admin access required")
    return user


class CreateUserRequest(BaseModel):
    email: str = Field(min_length=3)
    password: str = Field(min_length=6)
    role: str = Field(min_length=1)
    business_id: str | None = None


class UpdateUserRequest(BaseModel):
    role: str | None = None
    business_id: str | None = None
    is_active: bool | None = None


@router.post("")
def create_user(
    payload: CreateUserRequest,
    admin: AuthUser = Depends(_require_admin),
) -> dict[str, Any]:
    if payload.role not in ("admin", "sme"):
        raise HTTPException(status_code=400, detail="role must be 'admin' or 'sme'")
    if payload.role == "sme" and not payload.business_id:
        raise HTTPException(status_code=400, detail="business_id is required for SME users")

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
            """, (user_id, payload.email, pw_hash, admin.organization_id, payload.role, payload.business_id))
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
        "organization_id": admin.organization_id,
        "business_id": payload.business_id,
        "is_active": True,
    }


@router.get("")
def list_users(
    admin: AuthUser = Depends(_require_admin),
) -> list[dict[str, Any]]:
    conn = get_connection()
    try:
        with conn.cursor() as cur:
            cur.execute("""
                SELECT id, email, role, business_id, is_active, created_at
                FROM users
                WHERE organization_id = %s
                ORDER BY created_at DESC
            """, (admin.organization_id,))
            rows = cur.fetchall()

        return [
            {
                "id": row[0],
                "email": row[1],
                "role": row[2],
                "business_id": row[3],
                "is_active": row[4],
                "created_at": row[5].isoformat() if hasattr(row[5], "isoformat") else str(row[5]),
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
    admin: AuthUser = Depends(_require_admin),
) -> dict[str, Any]:
    updates: list[str] = []
    values: list[Any] = []

    if payload.role is not None:
        if payload.role not in ("admin", "sme"):
            raise HTTPException(status_code=400, detail="role must be 'admin' or 'sme'")
        updates.append("role = %s")
        values.append(payload.role)
    if payload.business_id is not None:
        updates.append("business_id = %s")
        values.append(payload.business_id)
    if payload.is_active is not None:
        updates.append("is_active = %s")
        values.append(payload.is_active)

    if not updates:
        raise HTTPException(status_code=400, detail="No fields to update")

    values.append(user_id)
    values.append(admin.organization_id)

    conn = get_connection()
    try:
        with conn.cursor() as cur:
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
    admin: AuthUser = Depends(_require_admin),
) -> dict[str, Any]:
    if user_id == admin.id:
        raise HTTPException(status_code=400, detail="Cannot disable your own account")

    conn = get_connection()
    try:
        with conn.cursor() as cur:
            cur.execute(
                "UPDATE users SET is_active = FALSE WHERE id = %s AND organization_id = %s",
                (user_id, admin.organization_id),
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
