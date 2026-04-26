# Multi-Tenancy + Onboarding + Billing Foundation — Design Spec

**Date:** 2026-04-26  
**Status:** Approved

---

## Overview

Introduce thin multi-tenancy to DataSoko: organizations (intermediaries), businesses (SMEs), and subscriptions. All changes are additive. Existing endpoints, tables, and `business_id` usage are untouched. New tables are created via a versioned migration system that runs automatically on startup and in CI/CD.

---

## Goals

- Add `organizations`, `businesses`, and `subscriptions` tables
- Backfill existing `business_id` values from `ingestion_weekly_payloads` into `businesses` under `default_org`
- Expose `/onboard`, `POST /businesses`, `GET /businesses`, and `GET /billing/current`
- Apply schema changes automatically — no manual SQL ever required
- Keep `main.py` as a thin wiring layer; all new logic in dedicated route modules

## Non-Goals

- No JWT auth, RBAC, or API keys
- No foreign key constraints (not yet)
- No frontend changes
- No modification of existing endpoints or tables

---

## File Structure

```
backend/
  db/
    __init__.py
    connection.py              re-exports create_postgres_connection for new modules
  migrations/
    __init__.py
    runner.py                  sorts files, tracks applied via schema_migrations, wraps each in a transaction
    001_multitenancy.py        run(connection) — all new tables + backfill
  routes/
    __init__.py
    onboarding.py              POST /onboard
    businesses.py              POST /businesses, GET /businesses
    billing.py                 GET /billing/current
    utils.py                   get_org_id() helper
  scripts/
    run_migrations.py          CLI/CI entry point
  main.py                      updated: 3 include_router calls + resilient startup hook
tests/
  test_multitenancy.py         4 unit tests, stub-connection pattern
.github/workflows/
  main_datasoko-api.yml        updated: migration step before Azure deploy
```

---

## Database Schema

All DDL is idempotent (`CREATE TABLE IF NOT EXISTS`, `ON CONFLICT DO NOTHING`).

```sql
-- Migration tracking
CREATE TABLE IF NOT EXISTS schema_migrations (
    migration_id  TEXT PRIMARY KEY,
    applied_at    TIMESTAMPTZ DEFAULT NOW()
);

-- Organizations (intermediaries)
CREATE TABLE IF NOT EXISTS organizations (
    id          TEXT PRIMARY KEY,
    name        TEXT,
    created_at  TIMESTAMPTZ DEFAULT NOW()
);

-- Subscriptions (one per org)
CREATE TABLE IF NOT EXISTS subscriptions (
    organization_id  TEXT PRIMARY KEY NOT NULL,
    plan             TEXT,
    status           TEXT,
    expiry_date      TIMESTAMPTZ,
    created_at       TIMESTAMPTZ DEFAULT NOW()
);

-- Businesses registry
CREATE TABLE IF NOT EXISTS businesses (
    id               TEXT PRIMARY KEY,
    organization_id  TEXT NOT NULL DEFAULT 'default_org',
    name             TEXT,
    whatsapp_phone   TEXT,
    created_at       TIMESTAMPTZ DEFAULT NOW()
);

-- Index for org-level queries
CREATE INDEX IF NOT EXISTS idx_businesses_org ON businesses (organization_id);

-- Seed default org
INSERT INTO organizations (id, name)
VALUES ('default_org', 'Default Organization')
ON CONFLICT DO NOTHING;

-- Backfill businesses from existing payloads (null-safe)
INSERT INTO businesses (id, organization_id)
SELECT DISTINCT business_id, 'default_org'
FROM ingestion_weekly_payloads
WHERE business_id IS NOT NULL
ON CONFLICT (id) DO NOTHING;
```

No `ALTER TABLE` on existing tables. No foreign key constraints.

---

## Migration Runner

**`backend/migrations/runner.py`**

1. Ensure `schema_migrations` table exists
2. Discover migration files via glob `backend/migrations/0*.py`, sort lexicographically (deterministic order)
3. For each file, skip if `migration_id` already in `schema_migrations`
4. Wrap each migration in a transaction: call `module.run(connection)`, then insert into `schema_migrations`, then commit — rollback and raise on any error
5. Log `[migration] applied 001_multitenancy` or `[migration] skipped 001_multitenancy (already applied)`

**`backend/scripts/run_migrations.py`** — opens a connection, calls runner, exits 0 on success, exits 1 on failure. Used by CI and for local one-off runs.

**Startup hook in `main.py`**

```python
@app.on_event("startup")
async def run_migrations_on_startup() -> None:
    enabled = os.getenv("RUN_MIGRATIONS_ON_STARTUP", "true").lower() in {"1", "true", "yes"}
    if not enabled:
        return
    try:
        connection = create_postgres_connection()
        try:
            run_migrations(connection)
        finally:
            connection.close()
    except Exception as exc:
        logger.error("startup migration failed: %s", exc)
        # does NOT raise — app continues to start
```

The env var `RUN_MIGRATIONS_ON_STARTUP` (default `true`) gates this to prevent concurrent execution across multiple Azure App Service instances. Set it to `false` on replicas; let CI handle migrations via the script.

---

## API Endpoints

### `POST /onboard`

**Router:** `backend/routes/onboarding.py`

```
Input:
  organization_id  str   required
  name             str   required
  plan             str   required

Output (201 or 409):
  { organization_id, name, plan, status, expiry_date }
```

- Pre-check: query `subscriptions` for `organization_id` before opening the transaction; if a row exists return 409 immediately with the existing subscription payload (safe for retries, avoids partial transaction state)
- If no existing subscription: open a single transaction, insert org (`ON CONFLICT DO NOTHING`), insert subscription, commit
- `status = "active"`, `expiry_date = NOW() + 30 days`

---

### `POST /businesses`

**Router:** `backend/routes/businesses.py`

```
Input:
  id               str   required
  organization_id  str   optional, defaults to "default_org"
  name             str   optional
  whatsapp_phone   str   optional

Output (201):
  { id, organization_id, name, whatsapp_phone, created_at }
```

- Validates that `organization_id` exists in `organizations` → 400 if not found
- Returns 409 if `id` already exists in `businesses`

---

### `GET /businesses`

**Router:** `backend/routes/businesses.py`

```
Query param: organization_id (optional, defaults to "default_org")

Output:
  { organization_id, businesses: [ { id, name, whatsapp_phone, created_at }, ... ] }
```

- Returns 404 if `organization_id` not found in `organizations`

---

### `GET /billing/current`

**Router:** `backend/routes/billing.py`

```
Query param: organization_id (optional, defaults to "default_org")

Output:
  { organization_id, plan, status, expiry_date, active, days_remaining }
```

- `active`: `status == "active"` AND `expiry_date > NOW()`
- `days_remaining`: `max(0, (expiry_date - NOW()).days)` — 0 if expired
- 404 with `detail: "organization not found"` if org row missing
- 404 with `detail: "no subscription found"` if org exists but subscription missing

---

### `backend/routes/utils.py`

```python
def get_org_id(organization_id: str | None) -> str:
    return organization_id or "default_org"
```

---

## CI/CD — `.github/workflows/main_datasoko-api.yml`

New step added to the `deploy` job, after artifact download, before the Azure deploy action:

```yaml
- name: Run database migrations
  env:
    DATABASE_URL: ${{ secrets.DATABASE_URL }}
  run: |
    pip install -r requirements.txt
    python backend/scripts/run_migrations.py
```

- Uses full `requirements.txt` (not just psycopg2-binary) to match runtime
- Exits non-zero on failure → Azure deploy step is skipped automatically
- `schema_migrations` table ensures re-runs are no-ops
- Note: requires `DATABASE_URL` secret to point to a reachable DB; if the DB is behind a VNet, migrations should run from within the App Service via the startup hook instead, with `RUN_MIGRATIONS_ON_STARTUP=true` on a single designated instance

---

## Tests — `tests/test_multitenancy.py`

Uses the same stub-connection pattern as `test_storage_and_runtime.py`. No live DB required.

1. **`test_migration_creates_organizations_table`** — runs `001_multitenancy.py` against a stub cursor, asserts `CREATE TABLE IF NOT EXISTS organizations` was executed
2. **`test_migration_backfill_excludes_null_business_ids`** — asserts the backfill INSERT includes `WHERE business_id IS NOT NULL`
3. **`test_onboard_creates_org_and_subscription_atomically`** — stubs DB, calls onboard logic, asserts both inserts executed and `commit_count == 1` (single transaction)
4. **`test_billing_current_active_and_days_remaining`** — stub returns a subscription with `expiry_date = NOW() + 30 days`, asserts `active=True` and `days_remaining > 0`

---

## Backward Compatibility

- All existing endpoints unchanged
- `ingestion_weekly_payloads.business_id` remains a plain text column
- `businesses` table is a read/write registry; it is never queried by existing ingestion or metrics logic
- `default_org` is seeded so all existing data maps to a valid org from day one
