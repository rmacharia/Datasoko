# Multi-Tenancy + Onboarding + Billing Foundation Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Add organizations, businesses, and subscriptions tables plus `/onboard`, `/businesses`, and `/billing/current` endpoints with an automated versioned migration system.

**Architecture:** All new logic lives in dedicated route modules under `backend/routes/`; `main.py` is updated only to wire routers and add a resilient startup migration hook. A `backend/migrations/` package handles ordered, tracked, transactional schema changes; a `backend/scripts/run_migrations.py` CLI entry point is used by CI/CD before each deploy.

**Tech Stack:** Python 3.11+, FastAPI (APIRouter), psycopg2-binary / psycopg, PostgreSQL 16, GitHub Actions

---

## File Map

| Action | Path | Responsibility |
|--------|------|----------------|
| Create | `backend/db/__init__.py` | Re-export `create_postgres_connection` |
| Create | `backend/db/connection.py` | Thin wrapper around `backend.storage.postgres_connection` |
| Create | `backend/migrations/__init__.py` | Empty package marker |
| Create | `backend/migrations/runner.py` | Discover, sort, apply migrations; track via `schema_migrations` |
| Create | `backend/migrations/001_multitenancy.py` | `run(connection)` — all DDL + backfill |
| Create | `backend/routes/__init__.py` | Empty package marker |
| Create | `backend/routes/utils.py` | `get_org_id()` helper |
| Create | `backend/routes/onboarding.py` | `POST /onboard` router |
| Create | `backend/routes/businesses.py` | `POST /businesses`, `GET /businesses` router |
| Create | `backend/routes/billing.py` | `GET /billing/current` router |
| Create | `backend/scripts/run_migrations.py` | CLI/CI migration entry point |
| Modify | `backend/main.py` | Add `include_router` calls + startup hook |
| Modify | `.github/workflows/main_datasoko-api.yml` | Add migration step before Azure deploy |
| Create | `tests/test_multitenancy.py` | 4 unit tests, stub-connection pattern |

---

## Task 1: `backend/db/` — shared connection helper

**Files:**
- Create: `backend/db/__init__.py`
- Create: `backend/db/connection.py`

- [ ] **Step 1: Create `backend/db/connection.py`**

```python
# backend/db/connection.py
from __future__ import annotations

from backend.storage.postgres_connection import create_postgres_connection

__all__ = ["create_postgres_connection"]
```

- [ ] **Step 2: Create `backend/db/__init__.py`**

```python
from .connection import create_postgres_connection

__all__ = ["create_postgres_connection"]
```

- [ ] **Step 3: Verify import works**

```bash
cd "C:/Users/Roy Macharia/desktop/Datasoko-main"
python -c "from backend.db import create_postgres_connection; print('ok')"
```

Expected output: `ok`

- [ ] **Step 4: Commit**

```bash
git add backend/db/
git commit -m "feat: add backend/db shared connection helper"
```

---

## Task 2: Migration runner

**Files:**
- Create: `backend/migrations/__init__.py`
- Create: `backend/migrations/runner.py`

- [ ] **Step 1: Create `backend/migrations/__init__.py`**

```python
```
(empty file)

- [ ] **Step 2: Create `backend/migrations/runner.py`**

```python
# backend/migrations/runner.py
from __future__ import annotations

import importlib.util
import logging
import os
from pathlib import Path
from typing import Any

logger = logging.getLogger(__name__)

CREATE_SCHEMA_MIGRATIONS_SQL = """
CREATE TABLE IF NOT EXISTS schema_migrations (
    migration_id  TEXT PRIMARY KEY,
    applied_at    TIMESTAMPTZ DEFAULT NOW()
)
""".strip()

CHECK_APPLIED_SQL = "SELECT 1 FROM schema_migrations WHERE migration_id = %s"
RECORD_APPLIED_SQL = "INSERT INTO schema_migrations (migration_id) VALUES (%s)"


def _discover_migrations() -> list[Path]:
    migrations_dir = Path(__file__).parent
    files = sorted(migrations_dir.glob("0*.py"))
    return files


def _ensure_tracking_table(connection: Any) -> None:
    with connection.cursor() as cur:
        cur.execute(CREATE_SCHEMA_MIGRATIONS_SQL)
    connection.commit()


def _is_applied(connection: Any, migration_id: str) -> bool:
    with connection.cursor() as cur:
        cur.execute(CHECK_APPLIED_SQL, (migration_id,))
        row = cur.fetchone()
    return row is not None


def _load_module(path: Path):
    spec = importlib.util.spec_from_file_location(path.stem, path)
    module = importlib.util.module_from_spec(spec)  # type: ignore[arg-type]
    spec.loader.exec_module(module)  # type: ignore[union-attr]
    return module


def run_migrations(connection: Any) -> None:
    _ensure_tracking_table(connection)
    files = _discover_migrations()

    for path in files:
        migration_id = path.stem
        if _is_applied(connection, migration_id):
            logger.info("[migration] skipped %s (already applied)", migration_id)
            continue

        logger.info("[migration] applying %s", migration_id)
        module = _load_module(path)
        try:
            module.run(connection)
            with connection.cursor() as cur:
                cur.execute(RECORD_APPLIED_SQL, (migration_id,))
            connection.commit()
            logger.info("[migration] applied %s", migration_id)
        except Exception:
            connection.rollback()
            logger.exception("[migration] FAILED %s — rolled back", migration_id)
            raise
```

- [ ] **Step 3: Verify import works**

```bash
python -c "from backend.migrations.runner import run_migrations; print('ok')"
```

Expected output: `ok`

- [ ] **Step 4: Commit**

```bash
git add backend/migrations/
git commit -m "feat: add versioned migration runner with schema_migrations tracking"
```

---

## Task 3: Migration `001_multitenancy`

**Files:**
- Create: `backend/migrations/001_multitenancy.py`

- [ ] **Step 1: Create `backend/migrations/001_multitenancy.py`**

```python
# backend/migrations/001_multitenancy.py
from __future__ import annotations

from typing import Any

SQL_STATEMENTS = [
    # Migration tracking (idempotent — runner already created it, but safe to repeat)
    """
    CREATE TABLE IF NOT EXISTS schema_migrations (
        migration_id  TEXT PRIMARY KEY,
        applied_at    TIMESTAMPTZ DEFAULT NOW()
    )
    """,
    # Organizations
    """
    CREATE TABLE IF NOT EXISTS organizations (
        id          TEXT PRIMARY KEY,
        name        TEXT,
        created_at  TIMESTAMPTZ DEFAULT NOW()
    )
    """,
    # Subscriptions
    """
    CREATE TABLE IF NOT EXISTS subscriptions (
        organization_id  TEXT PRIMARY KEY NOT NULL,
        plan             TEXT,
        status           TEXT,
        expiry_date      TIMESTAMPTZ,
        created_at       TIMESTAMPTZ DEFAULT NOW()
    )
    """,
    # Businesses registry
    """
    CREATE TABLE IF NOT EXISTS businesses (
        id               TEXT PRIMARY KEY,
        organization_id  TEXT NOT NULL DEFAULT 'default_org',
        name             TEXT,
        whatsapp_phone   TEXT,
        created_at       TIMESTAMPTZ DEFAULT NOW()
    )
    """,
    # Index for org-level queries
    """
    CREATE INDEX IF NOT EXISTS idx_businesses_org ON businesses (organization_id)
    """,
    # Seed default org
    """
    INSERT INTO organizations (id, name)
    VALUES ('default_org', 'Default Organization')
    ON CONFLICT DO NOTHING
    """,
    # Backfill businesses from existing payloads (null-safe)
    """
    INSERT INTO businesses (id, organization_id)
    SELECT DISTINCT business_id, 'default_org'
    FROM ingestion_weekly_payloads
    WHERE business_id IS NOT NULL
    ON CONFLICT (id) DO NOTHING
    """,
]


def run(connection: Any) -> None:
    with connection.cursor() as cur:
        for sql in SQL_STATEMENTS:
            cur.execute(sql.strip())
    # caller (runner.py) commits — do NOT commit here
```

- [ ] **Step 2: Verify import works**

```bash
python -c "from backend.migrations import runner; print('ok')"
```

Expected output: `ok`

- [ ] **Step 3: Commit**

```bash
git add backend/migrations/001_multitenancy.py
git commit -m "feat: add 001_multitenancy migration — organizations, businesses, subscriptions"
```

---

## Task 4: Unit tests for migration

**Files:**
- Create: `tests/test_multitenancy.py`

- [ ] **Step 1: Write the four failing tests**

```python
# tests/test_multitenancy.py
from __future__ import annotations

import unittest
from datetime import datetime, timedelta, timezone
from typing import Any


class RecordingCursor:
    def __init__(self, connection: "RecordingConnection") -> None:
        self.connection = connection

    def __enter__(self) -> "RecordingCursor":
        return self

    def __exit__(self, exc_type: Any, exc: Any, tb: Any) -> None:
        pass

    def execute(self, query: str, params: Any = None) -> None:
        self.connection.executed.append((query.strip(), params))

    def fetchone(self) -> Any:
        return self.connection._fetchone_result

    def fetchall(self) -> Any:
        return self.connection._fetchall_result


class RecordingConnection:
    def __init__(self) -> None:
        self.executed: list[tuple[str, Any]] = []
        self.commit_count = 0
        self.rollback_count = 0
        self._fetchone_result: Any = None
        self._fetchall_result: list[Any] = []

    def cursor(self) -> RecordingCursor:
        return RecordingCursor(self)

    def commit(self) -> None:
        self.commit_count += 1

    def rollback(self) -> None:
        self.rollback_count += 1


class TestMigration001(unittest.TestCase):
    def _run_migration(self) -> RecordingConnection:
        from backend.migrations.runner import run_migrations
        conn = RecordingConnection()
        # runner calls _ensure_tracking_table first, which commits;
        # then checks _is_applied → fetchone returns None → not applied;
        # then calls module.run(conn) + records + commits
        conn._fetchone_result = None  # migration not yet applied
        run_migrations(conn)
        return conn

    def test_migration_creates_organizations_table(self) -> None:
        conn = self._run_migration()
        all_sql = " ".join(q for q, _ in conn.executed)
        self.assertIn("CREATE TABLE IF NOT EXISTS organizations", all_sql)

    def test_migration_backfill_excludes_null_business_ids(self) -> None:
        conn = self._run_migration()
        all_sql = " ".join(q for q, _ in conn.executed)
        self.assertIn("WHERE business_id IS NOT NULL", all_sql)

    def test_migration_creates_businesses_table(self) -> None:
        conn = self._run_migration()
        all_sql = " ".join(q for q, _ in conn.executed)
        self.assertIn("CREATE TABLE IF NOT EXISTS businesses", all_sql)

    def test_migration_skipped_when_already_applied(self) -> None:
        from backend.migrations.runner import run_migrations
        conn = RecordingConnection()
        conn._fetchone_result = (1,)  # simulate already applied
        run_migrations(conn)
        # Only the schema_migrations table creation + check should have run
        ddl_statements = [q for q, _ in conn.executed if "CREATE TABLE" in q and "organizations" in q]
        self.assertEqual(ddl_statements, [])


class TestOnboardLogic(unittest.TestCase):
    def test_onboard_creates_org_and_subscription_atomically(self) -> None:
        from backend.routes.onboarding import _do_onboard
        conn = RecordingConnection()
        conn._fetchone_result = None  # no existing subscription
        result = _do_onboard(
            connection=conn,
            organization_id="org_test",
            name="Test Org",
            plan="starter",
        )
        org_inserts = [q for q, _ in conn.executed if "INSERT INTO organizations" in q]
        sub_inserts = [q for q, _ in conn.executed if "INSERT INTO subscriptions" in q]
        self.assertEqual(len(org_inserts), 1)
        self.assertEqual(len(sub_inserts), 1)
        self.assertEqual(conn.commit_count, 1)
        self.assertEqual(result["organization_id"], "org_test")
        self.assertEqual(result["status"], "active")


class TestBillingLogic(unittest.TestCase):
    def test_billing_current_active_and_days_remaining(self) -> None:
        from backend.routes.billing import _compute_billing

        expiry = datetime.now(timezone.utc) + timedelta(days=30)
        result = _compute_billing(
            organization_id="org_test",
            plan="starter",
            status="active",
            expiry_date=expiry,
        )
        self.assertTrue(result["active"])
        self.assertGreater(result["days_remaining"], 0)
        self.assertEqual(result["organization_id"], "org_test")

    def test_billing_expired_subscription_is_inactive(self) -> None:
        from backend.routes.billing import _compute_billing

        expiry = datetime.now(timezone.utc) - timedelta(days=1)
        result = _compute_billing(
            organization_id="org_test",
            plan="starter",
            status="active",
            expiry_date=expiry,
        )
        self.assertFalse(result["active"])
        self.assertEqual(result["days_remaining"], 0)


if __name__ == "__main__":
    unittest.main()
```

- [ ] **Step 2: Run tests — expect failures (modules not yet implemented)**

```bash
cd "C:/Users/Roy Macharia/desktop/Datasoko-main"
python -m unittest tests/test_multitenancy.py 2>&1 | head -40
```

Expected: `ImportError` or `ModuleNotFoundError` for `backend.routes.onboarding`, `backend.routes.billing`.

- [ ] **Step 3: Commit the tests**

```bash
git add tests/test_multitenancy.py
git commit -m "test: add multitenancy unit tests (red)"
```

---

## Task 5: `backend/routes/utils.py`

**Files:**
- Create: `backend/routes/__init__.py`
- Create: `backend/routes/utils.py`

- [ ] **Step 1: Create `backend/routes/__init__.py`**

```python
```
(empty file)

- [ ] **Step 2: Create `backend/routes/utils.py`**

```python
# backend/routes/utils.py
from __future__ import annotations


def get_org_id(organization_id: str | None) -> str:
    return organization_id or "default_org"
```

- [ ] **Step 3: Verify import works**

```bash
python -c "from backend.routes.utils import get_org_id; assert get_org_id(None) == 'default_org'; print('ok')"
```

Expected: `ok`

- [ ] **Step 4: Commit**

```bash
git add backend/routes/
git commit -m "feat: add routes package and get_org_id helper"
```

---

## Task 6: `backend/routes/onboarding.py`

**Files:**
- Create: `backend/routes/onboarding.py`

- [ ] **Step 1: Create `backend/routes/onboarding.py`**

```python
# backend/routes/onboarding.py
from __future__ import annotations

from datetime import datetime, timedelta, timezone
from typing import Any

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel, Field

from backend.db import create_postgres_connection
from backend.routes.utils import get_org_id

router = APIRouter()

INSERT_ORG_SQL = """
INSERT INTO organizations (id, name)
VALUES (%s, %s)
ON CONFLICT DO NOTHING
""".strip()

CHECK_SUB_SQL = """
SELECT organization_id, plan, status, expiry_date
FROM subscriptions
WHERE organization_id = %s
LIMIT 1
""".strip()

INSERT_SUB_SQL = """
INSERT INTO subscriptions (organization_id, plan, status, expiry_date)
VALUES (%s, %s, %s, %s)
""".strip()


class OnboardRequest(BaseModel):
    organization_id: str = Field(min_length=1)
    name: str = Field(min_length=1)
    plan: str = Field(min_length=1)


def _do_onboard(
    *,
    connection: Any,
    organization_id: str,
    name: str,
    plan: str,
) -> dict[str, Any]:
    # Pre-check: return existing subscription without touching a transaction
    with connection.cursor() as cur:
        cur.execute(CHECK_SUB_SQL, (organization_id,))
        row = cur.fetchone()

    if row is not None:
        existing_expiry = row[3]
        return {
            "organization_id": row[0],
            "name": name,
            "plan": row[1],
            "status": row[2],
            "expiry_date": existing_expiry.isoformat() if hasattr(existing_expiry, "isoformat") else str(existing_expiry),
            "already_existed": True,
        }

    expiry = datetime.now(timezone.utc) + timedelta(days=30)
    try:
        with connection.cursor() as cur:
            cur.execute(INSERT_ORG_SQL, (organization_id, name))
            cur.execute(INSERT_SUB_SQL, (organization_id, plan, "active", expiry))
        connection.commit()
    except Exception:
        connection.rollback()
        raise

    return {
        "organization_id": organization_id,
        "name": name,
        "plan": plan,
        "status": "active",
        "expiry_date": expiry.isoformat(),
        "already_existed": False,
    }


@router.post("/onboard", status_code=201)
def onboard(payload: OnboardRequest) -> dict[str, Any]:
    connection = create_postgres_connection()
    try:
        result = _do_onboard(
            connection=connection,
            organization_id=payload.organization_id,
            name=payload.name,
            plan=payload.plan,
        )
    except Exception as exc:
        raise HTTPException(status_code=500, detail=f"Onboarding failed: {exc}") from exc
    finally:
        connection.close()

    if result.pop("already_existed"):
        raise HTTPException(status_code=409, detail=result)

    return result
```

- [ ] **Step 2: Run the onboarding unit test**

```bash
python -m unittest tests/test_multitenancy.py::TestOnboardLogic -v
```

Expected: `TestOnboardLogic.test_onboard_creates_org_and_subscription_atomically ... ok`

- [ ] **Step 3: Commit**

```bash
git add backend/routes/onboarding.py
git commit -m "feat: add POST /onboard route with atomic org+subscription creation"
```

---

## Task 7: `backend/routes/businesses.py`

**Files:**
- Create: `backend/routes/businesses.py`

- [ ] **Step 1: Create `backend/routes/businesses.py`**

```python
# backend/routes/businesses.py
from __future__ import annotations

from typing import Any

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel, Field

from backend.db import create_postgres_connection
from backend.routes.utils import get_org_id

router = APIRouter()

CHECK_ORG_SQL = "SELECT 1 FROM organizations WHERE id = %s LIMIT 1"
CHECK_BIZ_SQL = "SELECT 1 FROM businesses WHERE id = %s LIMIT 1"

INSERT_BIZ_SQL = """
INSERT INTO businesses (id, organization_id, name, whatsapp_phone)
VALUES (%s, %s, %s, %s)
RETURNING id, organization_id, name, whatsapp_phone, created_at
""".strip()

LIST_BIZ_SQL = """
SELECT id, name, whatsapp_phone, created_at
FROM businesses
WHERE organization_id = %s
ORDER BY created_at ASC
""".strip()

CHECK_ORG_EXISTS_SQL = "SELECT 1 FROM organizations WHERE id = %s LIMIT 1"


class CreateBusinessRequest(BaseModel):
    id: str = Field(min_length=1)
    organization_id: str | None = None
    name: str | None = None
    whatsapp_phone: str | None = None


@router.post("/businesses", status_code=201)
def create_business(payload: CreateBusinessRequest) -> dict[str, Any]:
    org_id = get_org_id(payload.organization_id)
    connection = create_postgres_connection()
    try:
        with connection.cursor() as cur:
            cur.execute(CHECK_ORG_EXISTS_SQL, (org_id,))
            if cur.fetchone() is None:
                raise HTTPException(status_code=400, detail=f"organization_id '{org_id}' not found")

            cur.execute(CHECK_BIZ_SQL, (payload.id,))
            if cur.fetchone() is not None:
                raise HTTPException(status_code=409, detail=f"business '{payload.id}' already exists")

            cur.execute(INSERT_BIZ_SQL, (payload.id, org_id, payload.name, payload.whatsapp_phone))
            row = cur.fetchone()
        connection.commit()
    except HTTPException:
        raise
    except Exception as exc:
        connection.rollback()
        raise HTTPException(status_code=500, detail=f"Failed to create business: {exc}") from exc
    finally:
        connection.close()

    created_at = row[4]
    return {
        "id": row[0],
        "organization_id": row[1],
        "name": row[2],
        "whatsapp_phone": row[3],
        "created_at": created_at.isoformat() if hasattr(created_at, "isoformat") else str(created_at),
    }


@router.get("/businesses")
def list_businesses(organization_id: str | None = None) -> dict[str, Any]:
    org_id = get_org_id(organization_id)
    connection = create_postgres_connection()
    try:
        with connection.cursor() as cur:
            cur.execute(CHECK_ORG_EXISTS_SQL, (org_id,))
            if cur.fetchone() is None:
                raise HTTPException(status_code=404, detail=f"organization '{org_id}' not found")

            cur.execute(LIST_BIZ_SQL, (org_id,))
            rows = cur.fetchall()
    except HTTPException:
        raise
    except Exception as exc:
        raise HTTPException(status_code=500, detail=f"Failed to list businesses: {exc}") from exc
    finally:
        connection.close()

    businesses = [
        {
            "id": r[0],
            "name": r[1],
            "whatsapp_phone": r[2],
            "created_at": r[3].isoformat() if hasattr(r[3], "isoformat") else str(r[3]),
        }
        for r in rows
    ]
    return {"organization_id": org_id, "businesses": businesses}
```

- [ ] **Step 2: Verify import works**

```bash
python -c "from backend.routes.businesses import router; print('ok')"
```

Expected: `ok`

- [ ] **Step 3: Commit**

```bash
git add backend/routes/businesses.py
git commit -m "feat: add POST /businesses and GET /businesses routes"
```

---

## Task 8: `backend/routes/billing.py`

**Files:**
- Create: `backend/routes/billing.py`

- [ ] **Step 1: Create `backend/routes/billing.py`**

```python
# backend/routes/billing.py
from __future__ import annotations

from datetime import datetime, timezone
from typing import Any

from fastapi import APIRouter, HTTPException

from backend.db import create_postgres_connection
from backend.routes.utils import get_org_id

router = APIRouter()

CHECK_ORG_SQL = "SELECT 1 FROM organizations WHERE id = %s LIMIT 1"

GET_SUB_SQL = """
SELECT plan, status, expiry_date
FROM subscriptions
WHERE organization_id = %s
LIMIT 1
""".strip()


def _compute_billing(
    *,
    organization_id: str,
    plan: str | None,
    status: str | None,
    expiry_date: datetime | None,
) -> dict[str, Any]:
    now = datetime.now(timezone.utc)
    if expiry_date is not None and expiry_date.tzinfo is None:
        expiry_date = expiry_date.replace(tzinfo=timezone.utc)

    active = (status == "active") and (expiry_date is not None) and (expiry_date > now)
    if expiry_date is not None and expiry_date > now:
        days_remaining = max(0, (expiry_date - now).days)
    else:
        days_remaining = 0

    return {
        "organization_id": organization_id,
        "plan": plan,
        "status": status,
        "expiry_date": expiry_date.isoformat() if expiry_date is not None else None,
        "active": active,
        "days_remaining": days_remaining,
    }


@router.get("/billing/current")
def billing_current(organization_id: str | None = None) -> dict[str, Any]:
    org_id = get_org_id(organization_id)
    connection = create_postgres_connection()
    try:
        with connection.cursor() as cur:
            cur.execute(CHECK_ORG_SQL, (org_id,))
            if cur.fetchone() is None:
                raise HTTPException(status_code=404, detail="organization not found")

            cur.execute(GET_SUB_SQL, (org_id,))
            row = cur.fetchone()
    except HTTPException:
        raise
    except Exception as exc:
        raise HTTPException(status_code=500, detail=f"Failed to fetch billing: {exc}") from exc
    finally:
        connection.close()

    if row is None:
        raise HTTPException(status_code=404, detail="no subscription found")

    return _compute_billing(
        organization_id=org_id,
        plan=row[0],
        status=row[1],
        expiry_date=row[2],
    )
```

- [ ] **Step 2: Run billing unit tests**

```bash
python -m unittest tests/test_multitenancy.py::TestBillingLogic -v
```

Expected:
```
TestBillingLogic.test_billing_current_active_and_days_remaining ... ok
TestBillingLogic.test_billing_expired_subscription_is_inactive ... ok
```

- [ ] **Step 3: Commit**

```bash
git add backend/routes/billing.py
git commit -m "feat: add GET /billing/current route with active/days_remaining computation"
```

---

## Task 9: `backend/scripts/run_migrations.py`

**Files:**
- Create: `backend/scripts/run_migrations.py`

- [ ] **Step 1: Create `backend/scripts/run_migrations.py`**

```python
# backend/scripts/run_migrations.py
"""CLI/CI entry point: run all pending migrations and exit 0 on success, 1 on failure."""
from __future__ import annotations

import logging
import sys

logging.basicConfig(level=logging.INFO, format="%(levelname)s %(message)s")

# Ensure backend package is importable when run as a script from repo root
import os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", ".."))

from backend.db import create_postgres_connection
from backend.migrations.runner import run_migrations


def main() -> None:
    connection = None
    try:
        connection = create_postgres_connection()
        run_migrations(connection)
        print("[migrations] all migrations applied successfully")
        sys.exit(0)
    except Exception as exc:
        print(f"[migrations] FAILED: {exc}", file=sys.stderr)
        sys.exit(1)
    finally:
        if connection is not None:
            try:
                connection.close()
            except Exception:
                pass


if __name__ == "__main__":
    main()
```

- [ ] **Step 2: Verify script is importable**

```bash
python -c "import backend.scripts.run_migrations; print('ok')"
```

Expected: `ok`

- [ ] **Step 3: Commit**

```bash
git add backend/scripts/run_migrations.py
git commit -m "feat: add backend/scripts/run_migrations.py CLI entry point for CI/CD"
```

---

## Task 10: Wire routers and startup hook into `main.py`

**Files:**
- Modify: `backend/main.py`

- [ ] **Step 1: Add imports at the top of `main.py` (after existing imports)**

Find the line `app = FastAPI(title="DataSoko API", version="0.1.0")` and add the following **before** it:

```python
import logging

logger = logging.getLogger(__name__)
```

- [ ] **Step 2: Add router imports just after the `app = FastAPI(...)` line**

```python
from backend.routes.onboarding import router as onboarding_router
from backend.routes.businesses import router as businesses_router
from backend.routes.billing import router as billing_router

app.include_router(onboarding_router)
app.include_router(businesses_router)
app.include_router(billing_router)
```

- [ ] **Step 3: Add the resilient startup hook — place it just after the `app.add_middleware(...)` block**

```python
@app.on_event("startup")
async def run_migrations_on_startup() -> None:
    enabled = os.getenv("RUN_MIGRATIONS_ON_STARTUP", "true").lower() in {"1", "true", "yes"}
    if not enabled:
        return
    try:
        from backend.db import create_postgres_connection
        from backend.migrations.runner import run_migrations
        connection = create_postgres_connection()
        try:
            run_migrations(connection)
        finally:
            connection.close()
    except Exception as exc:
        logger.error("startup migration failed: %s", exc)
        # does NOT raise — app continues to start
```

- [ ] **Step 4: Verify `main.py` imports cleanly**

```bash
python -c "import backend.main; print('ok')"
```

Expected: `ok`

- [ ] **Step 5: Run full unit test suite to confirm nothing is broken**

```bash
./scripts/run_tests.sh unit
```

Expected: all existing tests still pass.

- [ ] **Step 6: Run the new multitenancy tests**

```bash
python -m unittest tests/test_multitenancy.py -v
```

Expected: all 6 tests pass.

- [ ] **Step 7: Commit**

```bash
git add backend/main.py
git commit -m "feat: wire onboarding/businesses/billing routers and resilient startup migration hook"
```

---

## Task 11: CI/CD — add migration step to deploy workflow

**Files:**
- Modify: `.github/workflows/main_datasoko-api.yml`

- [ ] **Step 1: Open `.github/workflows/main_datasoko-api.yml` and locate the `deploy` job's steps**

The `deploy` job currently has two steps:
1. `Download artifact from build job`
2. `Deploy to Azure Web App`

- [ ] **Step 2: Insert the migration step between them**

Replace the `deploy` job steps section so it reads:

```yaml
    steps:
      - name: Download artifact from build job
        uses: actions/download-artifact@v4
        with:
          name: python-app

      - name: Run database migrations
        env:
          DATABASE_URL: ${{ secrets.DATABASE_URL }}
        run: |
          pip install -r requirements.txt
          python backend/scripts/run_migrations.py

      - name: Deploy to Azure Web App
        id: deploy-to-webapp
        uses: azure/webapps-deploy@v3
        with:
          app-name: 'datasoko-api'
          slot-name: 'Production'
          publish-profile: ${{ secrets.AZURE_BACKEND_WEBAPP_PUBLISH_PROFILE }}
          package: .
```

- [ ] **Step 3: Verify the workflow file is valid YAML**

```bash
python -c "import yaml; yaml.safe_load(open('.github/workflows/main_datasoko-api.yml')); print('valid yaml')"
```

Expected: `valid yaml`

- [ ] **Step 4: Commit**

```bash
git add .github/workflows/main_datasoko-api.yml
git commit -m "ci: run database migrations before Azure deploy"
```

---

## Task 12: Final verification

- [ ] **Step 1: Run the complete unit test suite**

```bash
./scripts/run_tests.sh unit
```

Expected: all tests pass with output like:
```
[tests] running unit tests
......
----------------------------------------------------------------------
Ran N tests in 0.XXXs
OK
```

- [ ] **Step 2: Verify all new modules are importable**

```bash
python -c "
from backend.db import create_postgres_connection
from backend.migrations.runner import run_migrations
from backend.migrations import runner
from backend.routes.utils import get_org_id
from backend.routes.onboarding import router as r1
from backend.routes.businesses import router as r2
from backend.routes.billing import router as r3
from backend.scripts.run_migrations import main
print('all imports ok')
"
```

Expected: `all imports ok`

- [ ] **Step 3: Check that existing endpoints are still defined in main**

```bash
python -c "
import backend.main as m
routes = [r.path for r in m.app.routes]
assert '/health' in routes
assert '/ingest/weekly' in routes
assert '/metrics/weekly' in routes
assert '/admin/status' in routes
assert '/onboard' in routes
assert '/businesses' in routes
assert '/billing/current' in routes
print('all routes present:', routes)
"
```

Expected: all routes listed including the three new ones.

- [ ] **Step 4: Final commit tag**

```bash
git add -A
git status  # confirm nothing untracked or unexpected
git commit -m "feat: complete multi-tenancy foundation — orgs, businesses, subscriptions, migrations" --allow-empty
```

---

## Self-Review Checklist

- [x] **Spec coverage:** All spec requirements covered — `organizations`, `businesses`, `subscriptions` tables (Task 3), migration runner with `schema_migrations` tracking (Task 2), `001_multitenancy` with null-safe backfill (Task 3), `/onboard` atomic transaction with 409 pre-check (Task 6), `POST /businesses` with org validation (Task 7), `GET /businesses` (Task 7), `/billing/current` with `active` + `days_remaining` (Task 8), `get_org_id` helper (Task 5), `run_migrations.py` CLI (Task 9), startup hook gated by `RUN_MIGRATIONS_ON_STARTUP` (Task 10), CI migration step (Task 11), 4+ unit tests (Task 4).
- [x] **No placeholders:** All steps contain actual code.
- [x] **Type consistency:** `_do_onboard` signature in Task 6 matches test stub calls in Task 4; `_compute_billing` signature in Task 8 matches test calls in Task 4; `run_migrations(connection)` in Task 2 matches usage in Tasks 9 and 10.
