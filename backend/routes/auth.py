from __future__ import annotations

import logging
from typing import Any
from uuid import uuid4

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel, Field

from backend.auth import AuthUser, get_current_user, hash_password, issue_token, verify_password
from backend.db.connection import get_connection

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/auth", tags=["auth"])


class RegisterRequest(BaseModel):
    email: str = Field(min_length=3)
    password: str = Field(min_length=6)
    organization_id: str = Field(default="default_org", min_length=1)
    role: str = Field(min_length=1)
    business_id: str | None = None


class LoginRequest(BaseModel):
    email: str = Field(min_length=1)
    password: str = Field(min_length=1)


@router.post("/register")
def register(payload: RegisterRequest) -> dict[str, Any]:
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
            """, (user_id, payload.email, pw_hash, payload.organization_id, payload.role, payload.business_id))
        conn.commit()
    except HTTPException:
        raise
    except Exception as exc:
        conn.rollback()
        logger.error("Registration failed: %s", exc)
        raise HTTPException(status_code=500, detail="Registration failed") from exc
    finally:
        conn.close()

    user = AuthUser(
        id=user_id,
        email=payload.email,
        organization_id=payload.organization_id,
        role=payload.role,
        business_id=payload.business_id,
    )
    token = issue_token(user)

    return {
        "access_token": token,
        "token_type": "bearer",
        "user": {
            "id": user.id,
            "email": user.email,
            "role": user.role,
            "organization_id": user.organization_id,
            "business_id": user.business_id,
        },
    }


@router.post("/login")
def login(payload: LoginRequest) -> dict[str, Any]:
    conn = get_connection()
    try:
        with conn.cursor() as cur:
            cur.execute(
                "SELECT id, email, password_hash, organization_id, role, business_id, is_active FROM users WHERE email = %s",
                (payload.email,),
            )
            row = cur.fetchone()
    except Exception as exc:
        logger.error("Login query failed: %s", exc)
        raise HTTPException(status_code=500, detail="Internal error") from exc
    finally:
        conn.close()

    if not row:
        raise HTTPException(status_code=401, detail="Invalid email or password")

    user_id, email, pw_hash, org_id, role, biz_id, is_active = row

    if not is_active:
        raise HTTPException(status_code=403, detail="Account is disabled")

    if not verify_password(payload.password, pw_hash):
        raise HTTPException(status_code=401, detail="Invalid email or password")

    user = AuthUser(
        id=user_id,
        email=email,
        organization_id=org_id,
        role=role,
        business_id=biz_id,
    )
    token = issue_token(user)

    return {
        "access_token": token,
        "token_type": "bearer",
        "user": {
            "id": user.id,
            "email": user.email,
            "role": user.role,
            "organization_id": user.organization_id,
            "business_id": user.business_id,
        },
    }


@router.get("/me")
def get_me(user: AuthUser = Depends(get_current_user)) -> dict[str, Any]:
    return {
        "id": user.id,
        "email": user.email,
        "role": user.role,
        "organization_id": user.organization_id,
        "business_id": user.business_id,
    }
