from __future__ import annotations

import hashlib
import hmac
import os
import time
import json
import base64
import logging
from dataclasses import dataclass
from typing import Any

from fastapi import Depends, Header, HTTPException

logger = logging.getLogger(__name__)

JWT_SECRET = os.getenv("JWT_SECRET", "").strip()
JWT_EXPIRY_SECONDS = 3600

# Role taxonomy
ROLE_SUPER_ADMIN = "super_admin"
ROLE_ORG_ADMIN = "admin"
ROLE_SME_USER = "sme_user"

ALL_ROLES = (ROLE_SUPER_ADMIN, ROLE_ORG_ADMIN, ROLE_SME_USER)


@dataclass
class AuthUser:
    id: str
    email: str
    organization_id: str | None
    role: str
    business_id: str | None


def is_super_admin(user: AuthUser) -> bool:
    return user.role == ROLE_SUPER_ADMIN


def is_org_admin(user: AuthUser) -> bool:
    return user.role == ROLE_ORG_ADMIN


def is_sme_user(user: AuthUser) -> bool:
    return user.role == ROLE_SME_USER


def hash_password(password: str) -> str:
    salt = os.urandom(16).hex()
    h = hashlib.pbkdf2_hmac("sha256", password.encode(), salt.encode(), 100_000)
    return f"{salt}:{h.hex()}"


def verify_password(password: str, stored_hash: str) -> bool:
    parts = stored_hash.split(":", 1)
    if len(parts) != 2:
        return False
    salt, expected_hex = parts
    h = hashlib.pbkdf2_hmac("sha256", password.encode(), salt.encode(), 100_000)
    return hmac.compare_digest(h.hex(), expected_hex)


def _b64url_encode(data: bytes) -> str:
    return base64.urlsafe_b64encode(data).rstrip(b"=").decode()


def _b64url_decode(s: str) -> bytes:
    padding = 4 - len(s) % 4
    if padding != 4:
        s += "=" * padding
    return base64.urlsafe_b64decode(s)


def create_jwt(payload: dict[str, Any]) -> str:
    secret = JWT_SECRET or os.getenv("ADMIN_TOKEN", "fallback-secret")
    header = {"alg": "HS256", "typ": "JWT"}
    header_b64 = _b64url_encode(json.dumps(header, separators=(",", ":")).encode())
    payload_b64 = _b64url_encode(json.dumps(payload, separators=(",", ":")).encode())
    signing_input = f"{header_b64}.{payload_b64}"
    sig = hmac.HMAC(secret.encode(), signing_input.encode(), hashlib.sha256).digest()
    sig_b64 = _b64url_encode(sig)
    return f"{header_b64}.{payload_b64}.{sig_b64}"


def decode_jwt(token: str) -> dict[str, Any] | None:
    secret = JWT_SECRET or os.getenv("ADMIN_TOKEN", "fallback-secret")
    parts = token.split(".")
    if len(parts) != 3:
        return None
    header_b64, payload_b64, sig_b64 = parts
    signing_input = f"{header_b64}.{payload_b64}"
    expected_sig = hmac.HMAC(secret.encode(), signing_input.encode(), hashlib.sha256).digest()
    actual_sig = _b64url_decode(sig_b64)
    if not hmac.compare_digest(expected_sig, actual_sig):
        return None
    try:
        payload = json.loads(_b64url_decode(payload_b64))
    except Exception:
        return None
    if payload.get("exp") and payload["exp"] < time.time():
        return None
    return payload


def _normalize_role(role: str | None) -> str:
    # Accept legacy JWTs minted before the role split so tokens already in
    # the wild keep working for their remaining lifetime.
    if role == "admin":
        return ROLE_ORG_ADMIN
    if role == "sme":
        return ROLE_SME_USER
    return role or ""


def issue_token(user: AuthUser) -> str:
    payload = {
        "user_id": user.id,
        "email": user.email,
        "organization_id": user.organization_id,
        "role": user.role,
        "business_id": user.business_id,
        "exp": int(time.time()) + JWT_EXPIRY_SECONDS,
    }
    return create_jwt(payload)


def get_current_user(authorization: str | None = Header(default=None, alias="Authorization")) -> AuthUser:
    if not authorization:
        raise HTTPException(status_code=401, detail="Authorization header required.")

    parts = authorization.split(" ", 1)
    if len(parts) != 2 or parts[0].lower() != "bearer":
        raise HTTPException(status_code=401, detail="Invalid authorization format.")

    token_str = parts[1].strip()

    # Try JWT first
    payload = decode_jwt(token_str)
    if payload and "user_id" in payload:
        return AuthUser(
            id=payload["user_id"],
            email=payload.get("email", ""),
            organization_id=payload.get("organization_id"),
            role=_normalize_role(payload.get("role")),
            business_id=payload.get("business_id"),
        )

    # Fallback: accept ADMIN_TOKEN as a platform-level identity.
    admin_token = os.getenv("ADMIN_TOKEN", "").strip()
    if admin_token and hmac.compare_digest(token_str, admin_token):
        return AuthUser(
            id="system_admin",
            email="admin@system",
            organization_id=None,
            role=ROLE_SUPER_ADMIN,
            business_id=None,
        )

    raise HTTPException(status_code=401, detail="Invalid or expired token.")


def require_role(*allowed_roles: str):
    """FastAPI dependency factory that enforces role membership."""
    allowed = set(allowed_roles)

    def _checker(user: AuthUser = Depends(get_current_user)) -> AuthUser:
        if user.role not in allowed:
            raise HTTPException(status_code=403, detail="Forbidden")
        return user

    return _checker


# Named guards — prefer these over inline require_role(...) at call sites
# so the intent of each route is unmistakable.
require_platform_admin = require_role(ROLE_SUPER_ADMIN)
require_org_admin_only = require_role(ROLE_ORG_ADMIN)
require_org_admin_or_platform = require_role(ROLE_SUPER_ADMIN, ROLE_ORG_ADMIN)
require_tenant_user = require_role(ROLE_ORG_ADMIN, ROLE_SME_USER)
require_any_authenticated = require_role(ROLE_SUPER_ADMIN, ROLE_ORG_ADMIN, ROLE_SME_USER)


def enforce_business_access(user: AuthUser, business_id: str | None) -> None:
    # Platform admins have cross-tenant visibility.
    if is_super_admin(user):
        return
    # Org admins can reach any business within their own org — callers must
    # pair this with an organization_id check when needed.
    if is_org_admin(user):
        return
    if is_sme_user(user) and user.business_id and business_id != user.business_id:
        raise HTTPException(status_code=403, detail="Access denied: you can only access your assigned business.")


def resolve_business_id(user: AuthUser, requested: str | None) -> str:
    if is_sme_user(user):
        if user.business_id:
            return user.business_id
        raise HTTPException(status_code=403, detail="No business assigned to this user.")
    return requested or "biz_001"
