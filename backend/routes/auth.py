from __future__ import annotations

import logging
import os
from typing import Any
from uuid import uuid4

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel, Field

from backend.auth import (
    ROLE_ORG_ADMIN,
    ROLE_SME_USER,
    ROLE_SUPER_ADMIN,
    AuthUser,
    get_current_user,
    hash_password,
    issue_token,
    is_super_admin,
    optional_current_user,
    verify_password,
)
from backend.db.connection import get_connection

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/auth", tags=["auth"])


class BootstrapRequest(BaseModel):
    email: str = Field(min_length=3)
    password: str = Field(min_length=6)
    # organization_id is accepted for backwards compatibility with older
    # frontends but is ignored — bootstrap always creates a platform
    # super_admin with no tenant scope.
    organization_id: str | None = None


class RegisterRequest(BaseModel):
    email: str = Field(min_length=3)
    password: str = Field(min_length=6)
    organization_id: str | None = None
    role: str = Field(min_length=1)
    business_id: str | None = None


class LoginRequest(BaseModel):
    email: str = Field(min_length=1)
    password: str = Field(min_length=1)


def _bootstrap_enabled() -> bool:
    return os.getenv("ALLOW_BOOTSTRAP_ADMIN", "").strip().lower() in {"1", "true", "yes", "on"}


def _super_admin_count(cur: Any) -> int:
    cur.execute("SELECT COUNT(*) FROM users WHERE role = %s", (ROLE_SUPER_ADMIN,))
    row = cur.fetchone()
    return int(row[0] if row else 0)


def _audit_auth_event(event_type: str, message: str, *, status: str = "success", email: str | None = None) -> None:
    try:
        from backend.routes.analytics import log_activity

        log_activity(
            business_id="system",
            event_type=event_type,
            message=message if email is None else f"{message}: {email}",
            status=status,
            organization_id="system",
        )
    except Exception:
        logger.info("auth audit event=%s status=%s email=%s", event_type, status, email)


@router.get("/status")
def auth_status() -> dict[str, Any]:
    """Check setup state for the first-admin flow."""
    conn = get_connection()
    try:
        with conn.cursor() as cur:
            cur.execute("SELECT 1 FROM information_schema.tables WHERE table_name = 'users' LIMIT 1")
            if cur.fetchone() is None:
                return {
                    "initialized": False,
                    "user_count": 0,
                    "bootstrap_allowed": False,
                }
            cur.execute("SELECT COUNT(*) FROM users")
            count = cur.fetchone()[0]
        return {
            "initialized": count > 0,
            "user_count": count,
            "bootstrap_allowed": count == 0 and _bootstrap_enabled(),
        }
    except Exception as exc:
        logger.warning("auth/status check failed: %s", exc)
        return {
            "initialized": False,
            "user_count": 0,
            "bootstrap_allowed": False,
        }
    finally:
        conn.close()


@router.post("/bootstrap")
def bootstrap(payload: BootstrapRequest) -> dict[str, Any]:
    """Create the first admin user. Only works when no users exist."""
    if not _bootstrap_enabled():
        _audit_auth_event(
            "auth_blocked",
            "Blocked bootstrap attempt while ALLOW_BOOTSTRAP_ADMIN is disabled",
            status="failed",
            email=payload.email,
        )
        raise HTTPException(status_code=403, detail="Bootstrap is disabled.")

    conn = get_connection()
    try:
        with conn.cursor() as cur:
            cur.execute("SELECT 1 FROM information_schema.tables WHERE table_name = 'users' LIMIT 1")
            if cur.fetchone() is None:
                raise HTTPException(status_code=500, detail="Users table not initialized. Run migrations first.")
            cur.execute("SELECT COUNT(*) FROM users")
            count = cur.fetchone()[0]
        if count > 0:
            raise HTTPException(status_code=403, detail="Bootstrap already completed. Use /auth/login instead.")
    except HTTPException:
        raise
    except Exception as exc:
        logger.error("Bootstrap check failed: %s", exc)
        raise HTTPException(status_code=500, detail="Database error") from exc
    finally:
        conn.close()

    user_id = uuid4().hex
    pw_hash = hash_password(payload.password)

    conn = get_connection()
    try:
        with conn.cursor() as cur:
            cur.execute("""
                INSERT INTO users (id, email, password_hash, organization_id, role, business_id)
                VALUES (%s, %s, %s, NULL, %s, NULL)
            """, (user_id, payload.email, pw_hash, ROLE_SUPER_ADMIN))
        conn.commit()
    except Exception as exc:
        conn.rollback()
        logger.error("Bootstrap insert failed: %s", exc)
        raise HTTPException(status_code=500, detail="Failed to create admin user") from exc
    finally:
        conn.close()

    from backend.routes.analytics import log_activity
    log_activity(
        business_id="system",
        event_type="bootstrap",
        message=f"Platform bootstrapped by {payload.email}",
        status="success",
        organization_id="system",
    )

    user = AuthUser(
        id=user_id,
        email=payload.email,
        organization_id=None,
        role=ROLE_SUPER_ADMIN,
        business_id=None,
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


@router.post("/register")
def register(
    payload: RegisterRequest,
    actor: AuthUser | None = Depends(optional_current_user),
) -> dict[str, Any]:
    if payload.role not in (ROLE_SUPER_ADMIN, ROLE_ORG_ADMIN, ROLE_SME_USER):
        raise HTTPException(
            status_code=400,
            detail=f"role must be one of '{ROLE_SUPER_ADMIN}', '{ROLE_ORG_ADMIN}', '{ROLE_SME_USER}'",
        )
    if payload.role == ROLE_SME_USER and not payload.business_id:
        raise HTTPException(status_code=400, detail="business_id is required for sme_user")
    if payload.role == ROLE_ORG_ADMIN and not payload.organization_id:
        raise HTTPException(status_code=400, detail="organization_id is required for admin")

    conn = get_connection()
    try:
        with conn.cursor() as cur:
            cur.execute("SELECT 1 FROM information_schema.tables WHERE table_name = 'users' LIMIT 1")
            if cur.fetchone() is None:
                raise HTTPException(status_code=500, detail="Users table not initialized. Run migrations first.")

            super_admins = _super_admin_count(cur)
            public_first_super_admin = (
                payload.role == ROLE_SUPER_ADMIN
                and super_admins == 0
                and _bootstrap_enabled()
                and actor is None
            )

            if payload.role == ROLE_SUPER_ADMIN and not public_first_super_admin:
                if actor is None or not is_super_admin(actor):
                    _audit_auth_event(
                        "auth_blocked",
                        "Blocked public super_admin registration attempt",
                        status="failed",
                        email=payload.email,
                    )
                    raise HTTPException(status_code=403, detail="Public super_admin registration is disabled.")

            if payload.role != ROLE_SUPER_ADMIN:
                if actor is None or not is_super_admin(actor):
                    _audit_auth_event(
                        "auth_blocked",
                        "Blocked unauthenticated user registration attempt",
                        status="failed",
                        email=payload.email,
                    )
                    raise HTTPException(status_code=403, detail="Only platform admins can create users.")

            if actor is not None and not is_super_admin(actor):
                _audit_auth_event(
                    "auth_escalation",
                    "Blocked role escalation attempt",
                    status="failed",
                    email=payload.email,
                )
                raise HTTPException(status_code=403, detail="Only platform admins can create users.")

            organization_id = None if payload.role == ROLE_SUPER_ADMIN else payload.organization_id
            user_id = uuid4().hex
            pw_hash = hash_password(payload.password)

            cur.execute("SELECT 1 FROM users WHERE email = %s", (payload.email,))
            if cur.fetchone():
                raise HTTPException(status_code=409, detail="Email already registered")
            cur.execute("""
                INSERT INTO users (id, email, password_hash, organization_id, role, business_id)
                VALUES (%s, %s, %s, %s, %s, %s)
            """, (user_id, payload.email, pw_hash, organization_id, payload.role, payload.business_id))
        conn.commit()
    except HTTPException:
        raise
    except Exception as exc:
        conn.rollback()
        logger.error("Registration failed: %s", exc)
        raise HTTPException(status_code=500, detail="Registration failed") from exc
    finally:
        conn.close()

    if payload.role == ROLE_SUPER_ADMIN and actor is None:
        _audit_auth_event("bootstrap", "First super_admin created via ALLOW_BOOTSTRAP_ADMIN", email=payload.email)
    elif actor is not None:
        _audit_auth_event("auth_user_created", f"Platform admin {actor.email} created user", email=payload.email)

    user = AuthUser(
        id=user_id,
        email=payload.email,
        organization_id=organization_id,
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
