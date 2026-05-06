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

JWT_EXPIRY_SECONDS = 3600
DEFAULT_ORG_ID = os.getenv("DEFAULT_ORG_ID", "default_org").strip() or "default_org"

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


def get_jwt_secret() -> str:
    """Return the configured JWT signing secret or fail closed.

    Phase 2 auth must never silently fall back to a public or static secret.
    Azure/local deployments should set JWT_SECRET explicitly; ADMIN_TOKEN may
    remain as a legacy service credential but is not a JWT signing key.
    """
    secret = os.getenv("JWT_SECRET", "").strip()
    if not secret:
        raise RuntimeError("JWT_SECRET is required for JWT auth. Configure it before starting DataSoko.")
    return secret


def create_jwt(payload: dict[str, Any]) -> str:
    secret = get_jwt_secret()
    header = {"alg": "HS256", "typ": "JWT"}
    header_b64 = _b64url_encode(json.dumps(header, separators=(",", ":")).encode())
    payload_b64 = _b64url_encode(json.dumps(payload, separators=(",", ":")).encode())
    signing_input = f"{header_b64}.{payload_b64}"
    sig = hmac.HMAC(secret.encode(), signing_input.encode(), hashlib.sha256).digest()
    sig_b64 = _b64url_encode(sig)
    return f"{header_b64}.{payload_b64}.{sig_b64}"


def decode_jwt(token: str) -> dict[str, Any] | None:
    try:
        secret = get_jwt_secret()
    except RuntimeError:
        logger.error("JWT_SECRET is not configured; JWT decode refused")
        return None
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


def optional_current_user(authorization: str | None = Header(default=None, alias="Authorization")) -> AuthUser | None:
    if not authorization:
        return None
    try:
        return get_current_user(authorization)
    except HTTPException:
        return None


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


@dataclass
class RequestContext:
    user: AuthUser
    organization_id: str | None   # effective org (from JWT or X-Organization-Id header for super_admin)
    business_id: str | None       # effective business (from JWT or X-Business-Id header for super_admin)


def get_request_context(
    user: AuthUser = Depends(get_current_user),
    x_organization_id: str | None = Header(default=None, alias="X-Organization-Id"),
    x_business_id: str | None = Header(default=None, alias="X-Business-Id"),
) -> RequestContext:
    if user.role == ROLE_SUPER_ADMIN:
        return RequestContext(
            user=user,
            organization_id=x_organization_id,
            business_id=x_business_id,
        )
    return RequestContext(
        user=user,
        organization_id=user.organization_id,
        business_id=user.business_id,
    )


def require_tenant_or_platform(
    ctx: RequestContext = Depends(get_request_context),
) -> RequestContext:
    if ctx.user.role == ROLE_SUPER_ADMIN and not ctx.organization_id:
        raise HTTPException(
            status_code=403,
            detail="No organization context selected. Select an org before accessing tenant routes.",
        )
    allowed = {ROLE_SUPER_ADMIN, ROLE_ORG_ADMIN, ROLE_SME_USER}
    if ctx.user.role not in allowed:
        raise HTTPException(status_code=403, detail="Forbidden")
    return ctx


def resolve_org_context(ctx: RequestContext, requested_org_id: str | None = None) -> str:
    """Resolve the effective organization without trusting client input.

    Tenant users are pinned to their JWT organization. Super admins may provide
    org context through the trusted platform-mode header, with default_org kept
    as an explicit compatibility fallback only when no org has been selected.
    """
    if ctx.user.role == ROLE_SUPER_ADMIN:
        return ctx.organization_id or requested_org_id or DEFAULT_ORG_ID
    if not ctx.user.organization_id:
        raise HTTPException(status_code=403, detail="No organization assigned to this user.")
    if requested_org_id and requested_org_id != ctx.user.organization_id:
        raise HTTPException(status_code=403, detail="Cross-organization access denied.")
    return ctx.user.organization_id


def assert_business_belongs_to_org(connection: Any, business_id: str, organization_id: str) -> None:
    with connection.cursor() as cur:
        cur.execute(
            "SELECT 1 FROM businesses WHERE id = %s AND organization_id = %s LIMIT 1",
            (business_id, organization_id),
        )
        if cur.fetchone() is None:
            raise HTTPException(status_code=403, detail="Business does not belong to the selected organization.")


def assert_user_can_access_business(user: AuthUser, business_id: str, organization_id: str, connection: Any) -> None:
    if is_super_admin(user):
        assert_business_belongs_to_org(connection, business_id, organization_id)
        return
    if is_org_admin(user):
        if user.organization_id != organization_id:
            raise HTTPException(status_code=403, detail="Cross-organization access denied.")
        assert_business_belongs_to_org(connection, business_id, organization_id)
        return
    if is_sme_user(user):
        if user.organization_id != organization_id or user.business_id != business_id:
            raise HTTPException(status_code=403, detail="Access denied for this business.")
        assert_business_belongs_to_org(connection, business_id, organization_id)
        return
    raise HTTPException(status_code=403, detail="Forbidden")
