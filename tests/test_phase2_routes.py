from __future__ import annotations

import sys
import types
import unittest
from datetime import datetime, timedelta, timezone
from typing import Any

# ── FastAPI stub (same pattern as existing test files) ───────────────────────
if "fastapi" not in sys.modules:
    class _HTTPException(Exception):
        def __init__(self, status_code: int, detail: Any = None) -> None:
            super().__init__(detail)
            self.status_code = status_code
            self.detail = detail

    class _Route:
        def __init__(self, path: str, methods=None) -> None:
            self.path = path
            self.methods = methods or []

    class _APIRouter:
        def __init__(self, *a, **kw): pass
        def post(self, path, *a, **kw):
            def _d(fn):
                fn._route = _Route(path, ["POST"])
                return fn
            return _d
        def get(self, path, *a, **kw):
            def _d(fn):
                fn._route = _Route(path, ["GET"])
                return fn
            return _d

    class _FastAPI:
        def __init__(self, *a, **kw):
            self.routes: list[_Route] = []
        def get(self, path, *a, **kw):
            def _d(fn):
                self.routes.append(_Route(path, ["GET"]))
                return fn
            return _d
        def post(self, path, *a, **kw):
            def _d(fn):
                self.routes.append(_Route(path, ["POST"]))
                return fn
            return _d
        def put(self, path, *a, **kw):
            def _d(fn):
                self.routes.append(_Route(path, ["PUT"]))
                return fn
            return _d
        def add_middleware(self, *a, **kw): pass
        def on_event(self, *a, **kw):
            def _d(fn): return fn
            return _d
        def include_router(self, router, *a, **kw):
            for attr in vars(router.__class__).values():
                pass
            # collect routes registered via the router's decorators
            if hasattr(router, "_routes"):
                self.routes.extend(router._routes)

    class _BaseModel:
        def __init__(self, **kwargs):
            for k, v in kwargs.items():
                setattr(self, k, v)

    def _Field(*a, **kw): return None
    def _identity(*a, **kw): return None

    sys.modules["fastapi"] = types.SimpleNamespace(
        APIRouter=_APIRouter,
        FastAPI=_FastAPI,
        HTTPException=_HTTPException,
        Depends=_identity,
        File=_identity,
        Form=_identity,
        Header=_identity,
        UploadFile=object,
    )
    sys.modules["fastapi.middleware"] = types.SimpleNamespace()
    sys.modules["fastapi.middleware.cors"] = types.SimpleNamespace(CORSMiddleware=object)
    sys.modules["pydantic"] = types.SimpleNamespace(
        BaseModel=_BaseModel,
        Field=_Field,
    )


# ── Shared stub connection / cursor ──────────────────────────────────────────

class RecordingCursor:
    def __init__(self, conn: "RecordingConnection") -> None:
        self._conn = conn
        self._row_index = 0

    def __enter__(self) -> "RecordingCursor":
        return self

    def __exit__(self, *_: Any) -> None:
        pass

    def execute(self, query: str, params: Any = None) -> None:
        self._conn.executed.append((query.strip(), params))
        self._row_index = 0

    def fetchone(self) -> Any:
        results = self._conn._fetchone_queue
        if results:
            return results.pop(0)
        return self._conn._fetchone

    def fetchall(self) -> Any:
        return self._conn._fetchall


class RecordingConnection:
    def __init__(self) -> None:
        self.executed: list[tuple[str, Any]] = []
        self.commit_count = 0
        self.rollback_count = 0
        self._fetchone: Any = None
        self._fetchone_queue: list[Any] = []
        self._fetchall: list[Any] = []

    def cursor(self) -> RecordingCursor:
        return RecordingCursor(self)

    def commit(self) -> None:
        self.commit_count += 1

    def rollback(self) -> None:
        self.rollback_count += 1


# ─────────────────────────────────────────────────────────────────────────────
# 1. POST /onboard  — backend/routes/onboarding.py
# ─────────────────────────────────────────────────────────────────────────────

class TestOnboarding(unittest.TestCase):

    def _call(self, conn: RecordingConnection, **kwargs) -> dict:
        from backend.routes.onboarding import _do_onboard
        return _do_onboard(connection=conn, **kwargs)

    def test_inserts_org_and_subscription_on_new_org(self) -> None:
        conn = RecordingConnection()
        conn._fetchone = None  # no existing subscription

        result = self._call(conn, organization_id="org1", name="Org One", plan="starter")

        org_inserts = [q for q, _ in conn.executed if "INSERT INTO organizations" in q]
        sub_inserts = [q for q, _ in conn.executed if "INSERT INTO subscriptions" in q]
        self.assertEqual(len(org_inserts), 1)
        self.assertEqual(len(sub_inserts), 1)

    def test_commits_exactly_once_for_new_org(self) -> None:
        conn = RecordingConnection()
        conn._fetchone = None

        self._call(conn, organization_id="org1", name="Org One", plan="starter")

        self.assertEqual(conn.commit_count, 1)

    def test_returns_organization_id_and_status_active(self) -> None:
        conn = RecordingConnection()
        conn._fetchone = None

        result = self._call(conn, organization_id="org1", name="Org One", plan="starter")

        self.assertEqual(result["organization_id"], "org1")
        self.assertEqual(result["status"], "active")
        self.assertEqual(result["plan"], "starter")

    def test_returns_expiry_date_30_days_from_now(self) -> None:
        conn = RecordingConnection()
        conn._fetchone = None

        result = self._call(conn, organization_id="org1", name="Org One", plan="starter")

        expiry = datetime.fromisoformat(result["expiry_date"].replace("Z", "+00:00"))
        delta = expiry - datetime.now(timezone.utc)
        self.assertGreater(delta.days, 28)
        self.assertLessEqual(delta.days, 30)

    def test_raises_409_when_subscription_already_exists(self) -> None:
        from fastapi import HTTPException
        conn = RecordingConnection()
        expiry = datetime.now(timezone.utc) + timedelta(days=15)
        conn._fetchone = ("org1", "starter", "active", expiry)

        with self.assertRaises(HTTPException) as ctx:
            self._call(conn, organization_id="org1", name="Org One", plan="starter")

        self.assertEqual(ctx.exception.status_code, 409)

    def test_rolls_back_on_db_error(self) -> None:
        conn = RecordingConnection()
        conn._fetchone = None

        # Make the cursor raise on the INSERT INTO subscriptions
        original_execute = RecordingCursor.execute
        call_count = [0]

        def patched_execute(self_cur, query, params=None):
            if "INSERT INTO subscriptions" in query:
                raise RuntimeError("db error")
            original_execute(self_cur, query, params)

        RecordingCursor.execute = patched_execute
        try:
            with self.assertRaises(RuntimeError):
                self._call(conn, organization_id="org1", name="Org One", plan="starter")
        finally:
            RecordingCursor.execute = original_execute

        self.assertGreaterEqual(conn.rollback_count, 1)

    def test_org_insert_uses_on_conflict_do_nothing(self) -> None:
        conn = RecordingConnection()
        conn._fetchone = None

        self._call(conn, organization_id="org1", name="Org One", plan="starter")

        org_inserts = [q for q, _ in conn.executed if "INSERT INTO organizations" in q]
        self.assertTrue(any("ON CONFLICT" in q for q in org_inserts))


# ─────────────────────────────────────────────────────────────────────────────
# 2. POST /businesses  — backend/routes/businesses.py
# ─────────────────────────────────────────────────────────────────────────────

class TestCreateBusiness(unittest.TestCase):

    def _call(self, conn: RecordingConnection, **kwargs) -> dict:
        from backend.routes.businesses import _do_create_business
        return _do_create_business(connection=conn, **kwargs)

    def _conn_org_exists(self) -> RecordingConnection:
        conn = RecordingConnection()
        # first fetchone → org exists; second → business not yet in DB
        conn._fetchone_queue = [(1,), None]
        return conn

    def test_inserts_business_when_org_exists(self) -> None:
        conn = self._conn_org_exists()
        # RETURNING row
        conn._fetchone = ("biz1", "default_org", "Test Biz", None, datetime(2026, 1, 1, tzinfo=timezone.utc))

        self._call(conn, business_id="biz1", organization_id="default_org", name="Test Biz", whatsapp_phone=None)

        biz_inserts = [q for q, _ in conn.executed if "INSERT INTO businesses" in q]
        self.assertEqual(len(biz_inserts), 1)

    def test_raises_400_when_org_not_found(self) -> None:
        from fastapi import HTTPException
        conn = RecordingConnection()
        conn._fetchone = None  # org not found

        with self.assertRaises(HTTPException) as ctx:
            self._call(conn, business_id="biz1", organization_id="unknown_org", name="X", whatsapp_phone=None)

        self.assertEqual(ctx.exception.status_code, 400)

    def test_raises_409_when_business_already_exists(self) -> None:
        from fastapi import HTTPException
        conn = RecordingConnection()
        conn._fetchone_queue = [(1,), (1,)]  # org exists, biz exists

        with self.assertRaises(HTTPException) as ctx:
            self._call(conn, business_id="biz1", organization_id="default_org", name="X", whatsapp_phone=None)

        self.assertEqual(ctx.exception.status_code, 409)

    def test_returns_business_fields(self) -> None:
        conn = self._conn_org_exists()
        created_at = datetime(2026, 1, 1, tzinfo=timezone.utc)
        conn._fetchone = ("biz1", "default_org", "Test Biz", "+254700000000", created_at)

        result = self._call(conn, business_id="biz1", organization_id="default_org",
                            name="Test Biz", whatsapp_phone="+254700000000")

        self.assertEqual(result["id"], "biz1")
        self.assertEqual(result["organization_id"], "default_org")
        self.assertEqual(result["name"], "Test Biz")
        self.assertIn("created_at", result)

    def test_commits_on_success(self) -> None:
        conn = self._conn_org_exists()
        conn._fetchone = ("biz1", "default_org", None, None, datetime(2026, 1, 1, tzinfo=timezone.utc))

        self._call(conn, business_id="biz1", organization_id="default_org", name=None, whatsapp_phone=None)

        self.assertGreaterEqual(conn.commit_count, 1)


# ─────────────────────────────────────────────────────────────────────────────
# 3. GET /businesses  — backend/routes/businesses.py
# ─────────────────────────────────────────────────────────────────────────────

class TestListBusinesses(unittest.TestCase):

    def _call(self, conn: RecordingConnection, organization_id: str = "default_org") -> dict:
        from backend.routes.businesses import _do_list_businesses
        return _do_list_businesses(connection=conn, organization_id=organization_id)

    def test_returns_business_list_for_existing_org(self) -> None:
        conn = RecordingConnection()
        conn._fetchone = (1,)  # org exists
        conn._fetchall = [
            ("biz1", "Alpha", None, datetime(2026, 1, 1, tzinfo=timezone.utc)),
            ("biz2", "Beta", "+254", datetime(2026, 1, 2, tzinfo=timezone.utc)),
        ]

        result = self._call(conn)

        self.assertEqual(result["organization_id"], "default_org")
        self.assertEqual(len(result["businesses"]), 2)
        self.assertEqual(result["businesses"][0]["id"], "biz1")

    def test_returns_empty_list_when_no_businesses(self) -> None:
        conn = RecordingConnection()
        conn._fetchone = (1,)
        conn._fetchall = []

        result = self._call(conn)

        self.assertEqual(result["businesses"], [])

    def test_raises_404_when_org_not_found(self) -> None:
        from fastapi import HTTPException
        conn = RecordingConnection()
        conn._fetchone = None  # org not found

        with self.assertRaises(HTTPException) as ctx:
            self._call(conn, organization_id="ghost_org")

        self.assertEqual(ctx.exception.status_code, 404)

    def test_defaults_to_default_org(self) -> None:
        conn = RecordingConnection()
        conn._fetchone = (1,)
        conn._fetchall = []

        result = self._call(conn, organization_id="default_org")

        self.assertEqual(result["organization_id"], "default_org")
        check_sqls = [q for q, p in conn.executed if "organizations" in q and p == ("default_org",)]
        self.assertTrue(len(check_sqls) >= 1)


# ─────────────────────────────────────────────────────────────────────────────
# 4. GET /billing/current  — backend/routes/billing.py
# ─────────────────────────────────────────────────────────────────────────────

class TestBillingCurrent(unittest.TestCase):

    def _call(self, conn: RecordingConnection, organization_id: str = "default_org") -> dict:
        from backend.routes.billing import _do_billing_current
        return _do_billing_current(connection=conn, organization_id=organization_id)

    def test_returns_active_true_when_subscription_valid(self) -> None:
        conn = RecordingConnection()
        expiry = datetime.now(timezone.utc) + timedelta(days=20)
        conn._fetchone_queue = [(1,), ("starter", "active", expiry)]

        result = self._call(conn)

        self.assertTrue(result["active"])
        self.assertGreater(result["days_remaining"], 0)

    def test_returns_active_false_when_expired(self) -> None:
        conn = RecordingConnection()
        expiry = datetime.now(timezone.utc) - timedelta(days=1)
        conn._fetchone_queue = [(1,), ("starter", "active", expiry)]

        result = self._call(conn)

        self.assertFalse(result["active"])
        self.assertEqual(result["days_remaining"], 0)

    def test_returns_active_false_when_status_not_active(self) -> None:
        conn = RecordingConnection()
        expiry = datetime.now(timezone.utc) + timedelta(days=10)
        conn._fetchone_queue = [(1,), ("starter", "cancelled", expiry)]

        result = self._call(conn)

        self.assertFalse(result["active"])

    def test_raises_404_when_org_not_found(self) -> None:
        from fastapi import HTTPException
        conn = RecordingConnection()
        conn._fetchone = None  # org not found

        with self.assertRaises(HTTPException) as ctx:
            self._call(conn, organization_id="ghost")

        self.assertEqual(ctx.exception.status_code, 404)
        self.assertIn("organization", str(ctx.exception.detail).lower())

    def test_raises_404_when_subscription_not_found(self) -> None:
        from fastapi import HTTPException
        conn = RecordingConnection()
        conn._fetchone_queue = [(1,), None]  # org exists, no subscription

        with self.assertRaises(HTTPException) as ctx:
            self._call(conn)

        self.assertEqual(ctx.exception.status_code, 404)
        self.assertIn("subscription", str(ctx.exception.detail).lower())

    def test_returns_full_billing_payload(self) -> None:
        conn = RecordingConnection()
        expiry = datetime.now(timezone.utc) + timedelta(days=15)
        conn._fetchone_queue = [(1,), ("pro", "active", expiry)]

        result = self._call(conn)

        for key in ("organization_id", "plan", "status", "expiry_date", "active", "days_remaining"):
            self.assertIn(key, result)
        self.assertEqual(result["plan"], "pro")
        self.assertEqual(result["organization_id"], "default_org")


# ─────────────────────────────────────────────────────────────────────────────
# 5. Router modules are importable and expose a `router` object
# ─────────────────────────────────────────────────────────────────────────────

class TestRouterModulesExist(unittest.TestCase):

    def test_onboarding_module_has_router(self) -> None:
        from backend.routes import onboarding
        self.assertTrue(hasattr(onboarding, "router"))

    def test_businesses_module_has_router(self) -> None:
        from backend.routes import businesses
        self.assertTrue(hasattr(businesses, "router"))

    def test_billing_module_has_router(self) -> None:
        from backend.routes import billing
        self.assertTrue(hasattr(billing, "router"))

    def test_main_imports_onboarding_router(self) -> None:
        import importlib, ast, pathlib
        src = pathlib.Path("backend/main.py").read_text()
        tree = ast.parse(src)
        includes = [
            ast.unparse(node)
            for node in ast.walk(tree)
            if isinstance(node, ast.Call)
            and isinstance(node.func, ast.Attribute)
            and node.func.attr == "include_router"
        ]
        self.assertTrue(any("onboarding" in s for s in includes),
                        f"include_router(onboarding_router) not found in main.py. Found: {includes}")

    def test_main_imports_businesses_router(self) -> None:
        import ast, pathlib
        src = pathlib.Path("backend/main.py").read_text()
        tree = ast.parse(src)
        includes = [
            ast.unparse(node)
            for node in ast.walk(tree)
            if isinstance(node, ast.Call)
            and isinstance(node.func, ast.Attribute)
            and node.func.attr == "include_router"
        ]
        self.assertTrue(any("businesses" in s for s in includes),
                        f"include_router(businesses_router) not found in main.py. Found: {includes}")

    def test_main_imports_billing_router(self) -> None:
        import ast, pathlib
        src = pathlib.Path("backend/main.py").read_text()
        tree = ast.parse(src)
        includes = [
            ast.unparse(node)
            for node in ast.walk(tree)
            if isinstance(node, ast.Call)
            and isinstance(node.func, ast.Attribute)
            and node.func.attr == "include_router"
        ]
        self.assertTrue(any("billing" in s for s in includes),
                        f"include_router(billing_router) not found in main.py. Found: {includes}")


if __name__ == "__main__":
    unittest.main()
