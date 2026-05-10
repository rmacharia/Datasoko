# Development

## Prerequisites

- Python 3.11+
- Node.js 20+ (22 recommended)
- PostgreSQL (local or Docker, for integration tests)

## Local Setup

### Backend

```bash
pip install -r requirements.txt
export ADMIN_TOKEN=dev-token
export JWT_SECRET=dev-jwt-secret
export ALLOW_BOOTSTRAP_ADMIN=true
export DATABASE_URL=postgresql://postgres:postgres@localhost:5432/datasoko

# Run migrations
python backend/scripts/run_migrations.py

# Start server
uvicorn backend.main:app --reload --host 0.0.0.0 --port 8000
```

The FastAPI startup hook will also check for missing tables and run migrations if needed. This is the safety-net path for dev — in production, `startup.sh` handles it.

### Frontend

```bash
cd frontend
npm install
npm run dev
```

Open `http://localhost:3000/setup` for first-time setup, then sign in at `http://localhost:3000/login`.

The setup page calls `/auth/status` and `/auth/bootstrap`. Bootstrap only works when `ALLOW_BOOTSTRAP_ADMIN=true` and no users exist. After the first `super_admin` exists, use `/auth/login` and create tenant admins/users from the UI or API.

### Quick PostgreSQL with Docker

```bash
docker run -d --name datasoko-pg \
  -e POSTGRES_PASSWORD=postgres \
  -e POSTGRES_DB=datasoko \
  -p 5432:5432 \
  postgres:16
```

## Testing

### Run Tests

```bash
./scripts/run_tests.sh unit          # No DB required
./scripts/run_tests.sh integration   # Requires DATABASE_URL
./scripts/run_tests.sh all           # Both

# Single file
python -m unittest -q tests/test_multitenancy.py

# Frontend
cd frontend && npm run test
cd frontend && npm run typecheck
cd frontend && npm run lint
```

### Test Architecture

- **Unit tests** are fully deterministic. No database, no network.
- **Integration tests** require a live PostgreSQL via `DATABASE_URL`. Skipped cleanly if unset.
- Backend tests use `RecordingConnection` stubs that capture executed SQL.
- The `NormalizedPayloadStore` protocol in `ingestion/service.py` is the main seam for testing ingestion without a real DB.
- Frontend tests cover auth/session routing, API normalization, settings secrets, dashboards, JSON panels, and WhatsApp previews with Vitest.

## Writing Migrations

### Rules

1. Every migration is a Python file matching `backend/migrations/migration_00*.py`
2. Must export a `run(connection)` function
3. New migrations must **not** call `connection.commit()` — the runner owns the transaction. `migration_005_users_constraints.py` is a legacy exception and should not be copied.
4. Must be idempotent: `CREATE TABLE IF NOT EXISTS`, `ALTER TABLE ADD COLUMN IF NOT EXISTS`, `ON CONFLICT DO NOTHING`
5. Must handle schema drift: tables may exist with missing columns

### Three-Phase Pattern

```python
def run(connection):
    with connection.cursor() as cur:
        # Phase 1: Create tables (no-op if they exist)
        cur.execute("CREATE TABLE IF NOT EXISTS foo (...)")

        # Phase 2: Add any missing columns (handles drift)
        cur.execute("ALTER TABLE foo ADD COLUMN IF NOT EXISTS bar TEXT")

        # Phase 3: Indexes and seed data (safe now — all columns exist)
        cur.execute("CREATE INDEX IF NOT EXISTS idx_foo_bar ON foo (bar)")
        cur.execute("INSERT INTO foo (...) ON CONFLICT DO NOTHING")
```

Phase 2 must run **before** phase 3. If you create an index on a column that doesn't exist yet (because of drift), the migration fails.

### Testing Migrations

Add tests in `tests/test_multitenancy.py` using the `RecordingConnection` stub:

```python
def test_my_migration(self):
    from backend.migrations.migration_XXX import run
    conn = RecordingConnection()
    run(conn)
    all_sql = " ".join(q for q, _ in conn.executed)
    self.assertIn("CREATE TABLE IF NOT EXISTS my_table", all_sql)
    self.assertEqual(conn.commit_count, 0)  # migration must NOT commit
```

## Guardrails

- **No ORM.** Raw SQL with psycopg2. If you need a query, write it.
- **No psycopg (v3).** We use `psycopg2-binary` only. The connection module has a try/fallback but `psycopg2-binary` is the installed package.
- **No manual SQL in production.** Everything goes through the migration runner. The manual SQL fallback exists but should never be needed.
- **Decimal for money.** All financial computations use `Decimal`. No floats.
- **JWT secret is mandatory.** Set `JWT_SECRET` locally; the backend startup hook refuses silent fallback secrets.
- **Admin routes require auth.** Platform-only `/admin/*` endpoints require a `super_admin` JWT or legacy `ADMIN_TOKEN`. Tenant operational routes accept `super_admin`, `admin`, or `sme_user` only where explicitly allowed.
- **Tenant context matters.** Platform admins pass `X-Organization-Id` and optionally `X-Business-Id` for tenant-scoped routes. Tenant admins and SME users are pinned to the organization/business in their JWT.
- **Secrets stay encrypted.** Never log API keys or tokens. The `_mask_dsn()` function in `run_migrations.py` shows how to handle connection strings.
- **Migrations don't crash the app.** `startup.sh` continues even if migrations fail. The safety-net hook in `main.py` logs but doesn't raise.
- **Scheduler is opt-in.** Set `RUN_SCHEDULER=true` only on one backend instance to avoid duplicate schedule processing.
