from __future__ import annotations

import os
import unittest
from unittest.mock import patch

from backend.auth import ROLE_ORG_ADMIN, ROLE_SUPER_ADMIN, AuthUser, create_jwt, get_jwt_secret
from backend.routes.auth import BootstrapRequest, RegisterRequest, auth_status, bootstrap, register


class _Cursor:
    def __init__(self, conn: "_Conn") -> None:
        self.conn = conn
        self.last_query = ""

    def __enter__(self) -> "_Cursor":
        return self

    def __exit__(self, exc_type, exc, tb) -> None:  # noqa: ANN001
        return None

    def execute(self, query: str, params=None) -> None:  # noqa: ANN001
        self.last_query = query
        self.conn.executed.append((query.strip(), params))
        if "INSERT INTO users" in query:
            self.conn.inserted = params

    def fetchone(self):
        if "information_schema.tables" in self.last_query:
            return (1,)
        if "COUNT(*) FROM users WHERE role" in self.last_query:
            return (self.conn.super_admin_count,)
        if "COUNT(*) FROM users" in self.last_query:
            return (self.conn.user_count,)
        if "SELECT 1 FROM users WHERE email" in self.last_query:
            return None
        return None


class _Conn:
    def __init__(self, super_admin_count: int, user_count: int | None = None) -> None:
        self.super_admin_count = super_admin_count
        self.user_count = super_admin_count if user_count is None else user_count
        self.executed = []
        self.inserted = None
        self.commit_count = 0
        self.rollback_count = 0

    def cursor(self) -> _Cursor:
        return _Cursor(self)

    def commit(self) -> None:
        self.commit_count += 1

    def rollback(self) -> None:
        self.rollback_count += 1

    def close(self) -> None:
        return None


class AuthHardeningTests(unittest.TestCase):
    def setUp(self) -> None:
        os.environ["JWT_SECRET"] = "unit-test-jwt-secret"
        os.environ["ADMIN_TOKEN"] = "unit-test-admin-token"
        os.environ.pop("ALLOW_BOOTSTRAP_ADMIN", None)

    def test_jwt_secret_fails_closed_when_missing(self) -> None:
        os.environ.pop("JWT_SECRET", None)
        with self.assertRaises(RuntimeError):
            get_jwt_secret()
        with self.assertRaises(RuntimeError):
            create_jwt({"user_id": "u1"})

    def test_first_super_admin_registration_requires_bootstrap_flag(self) -> None:
        conn = _Conn(super_admin_count=0)
        payload = RegisterRequest(email="root@example.com", password="secret1", role=ROLE_SUPER_ADMIN)

        with patch("backend.routes.auth.get_connection", return_value=conn):
            with self.assertRaises(Exception) as ctx:
                register(payload, actor=None)

        self.assertEqual(getattr(ctx.exception, "status_code", None), 403)
        self.assertEqual(conn.commit_count, 0)

    def test_first_super_admin_registration_allowed_when_bootstrap_enabled(self) -> None:
        os.environ["ALLOW_BOOTSTRAP_ADMIN"] = "true"
        conn = _Conn(super_admin_count=0)
        payload = RegisterRequest(email="root@example.com", password="secret1", role=ROLE_SUPER_ADMIN)

        with patch("backend.routes.auth.get_connection", return_value=conn):
            response = register(payload, actor=None)

        self.assertEqual(conn.commit_count, 1)
        self.assertEqual(response["user"]["role"], ROLE_SUPER_ADMIN)
        self.assertTrue(response["access_token"])

    def test_bootstrap_endpoint_requires_bootstrap_flag(self) -> None:
        payload = BootstrapRequest(email="root@example.com", password="secret1")

        with self.assertRaises(Exception) as ctx:
            bootstrap(payload)

        self.assertEqual(getattr(ctx.exception, "status_code", None), 403)

    def test_auth_status_reports_bootstrap_allowed_only_when_enabled_and_empty(self) -> None:
        conn = _Conn(super_admin_count=0, user_count=0)

        with patch("backend.routes.auth.get_connection", return_value=conn):
            status = auth_status()
        self.assertFalse(status["initialized"])
        self.assertFalse(status["bootstrap_allowed"])

        os.environ["ALLOW_BOOTSTRAP_ADMIN"] = "true"
        with patch("backend.routes.auth.get_connection", return_value=conn):
            status = auth_status()
        self.assertFalse(status["initialized"])
        self.assertTrue(status["bootstrap_allowed"])

    def test_org_admin_registration_requires_platform_admin(self) -> None:
        conn = _Conn(super_admin_count=1)
        payload = RegisterRequest(
            email="admin@example.com",
            password="secret1",
            role=ROLE_ORG_ADMIN,
            organization_id="org1",
        )

        with patch("backend.routes.auth.get_connection", return_value=conn):
            with self.assertRaises(Exception) as ctx:
                register(payload, actor=None)

        self.assertEqual(getattr(ctx.exception, "status_code", None), 403)
        self.assertEqual(conn.commit_count, 0)

    def test_platform_admin_can_register_org_admin(self) -> None:
        conn = _Conn(super_admin_count=1)
        actor = AuthUser(
            id="platform",
            email="platform@example.com",
            organization_id=None,
            role=ROLE_SUPER_ADMIN,
            business_id=None,
        )
        payload = RegisterRequest(
            email="admin@example.com",
            password="secret1",
            role=ROLE_ORG_ADMIN,
            organization_id="org1",
        )

        with patch("backend.routes.auth.get_connection", return_value=conn):
            response = register(payload, actor=actor)

        self.assertEqual(conn.commit_count, 1)
        self.assertEqual(response["user"]["role"], ROLE_ORG_ADMIN)


if __name__ == "__main__":
    unittest.main()
