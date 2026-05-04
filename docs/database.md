# Database

PostgreSQL on Azure (VNet-private). Connection via `DATABASE_URL` env var using `psycopg2-binary`.

## Tables

### schema_migrations

Tracks which migrations have been applied. The runner checks this before executing each migration.

```sql
CREATE TABLE schema_migrations (
    migration_id  TEXT PRIMARY KEY,
    applied_at    TIMESTAMPTZ DEFAULT NOW()
);
```

### organizations

Tenant boundary. Every business belongs to one organization.

```sql
CREATE TABLE organizations (
    id          TEXT PRIMARY KEY,
    name        TEXT,
    created_at  TIMESTAMPTZ DEFAULT NOW()
);
```

Seeded with `default_org` on first migration.

### subscriptions

One per organization. Tracks billing plan and status.

```sql
CREATE TABLE subscriptions (
    organization_id  TEXT PRIMARY KEY NOT NULL,
    plan             TEXT,
    status           TEXT,
    expiry_date      TIMESTAMPTZ,
    created_at       TIMESTAMPTZ DEFAULT NOW()
);
```

### businesses

Individual SMEs. Belongs to one organization.

```sql
CREATE TABLE businesses (
    id               TEXT PRIMARY KEY,
    organization_id  TEXT NOT NULL DEFAULT 'default_org',
    name             TEXT,
    whatsapp_phone   TEXT,
    created_at       TIMESTAMPTZ DEFAULT NOW()
);

CREATE INDEX idx_businesses_org ON businesses (organization_id);
```

### ingestion_weekly_payloads

JSONB storage for normalized upload data. Created by `PostgresIngestionStore.ensure_table()`.

```sql
-- Unique on (business_id, dataset, week_start, week_end)
```

### admin_settings / admin_secret_settings

Settings storage. Created by `SETTINGS_STORE` on first access.

## Migration Strategy

### Execution Flow

```
Container starts
  -> startup.sh runs
    -> python backend/scripts/run_migrations.py
      -> run_migrations(connection)
        -> CREATE TABLE IF NOT EXISTS schema_migrations
        -> For each migration_00*.py file:
            -> Check schema_migrations for migration_id
            -> If not applied: load module, call run(connection), record in schema_migrations
            -> If applied: skip
  -> gunicorn starts
    -> FastAPI startup hook verifies tables exist (safety net)
```

### Migration File Structure

Each migration is a Python file in `backend/migrations/` matching `migration_00*.py`:

```python
def run(connection):
    """Called by runner. Must NOT commit — runner owns the transaction."""
    with connection.cursor() as cur:
        cur.execute("...")
```

### Three-Phase DDL (migration_001)

To handle schema drift (tables exist but columns are missing):

1. **Phase 1: CREATE TABLES** — `CREATE TABLE IF NOT EXISTS` with full column definitions. No-op if table already exists.
2. **Phase 2: ALTER COLUMNS** — `ALTER TABLE ADD COLUMN IF NOT EXISTS` for every expected column. Repairs drift.
3. **Phase 3: INDEXES + SEED** — `CREATE INDEX IF NOT EXISTS` and `INSERT ... ON CONFLICT DO NOTHING`. Only runs after all columns exist.

This ordering prevents "column does not exist" errors when tables were partially created.

### Schema Drift Handling

The system handles three DB states:

| State | What Happens |
|---|---|
| Empty DB | Phase 1 creates tables with all columns. Phases 2-3 are no-ops. |
| Partial tables (drift) | Phase 1 is no-op (tables exist). Phase 2 adds missing columns. Phase 3 creates indexes. |
| Complete schema | All phases are no-ops (IF NOT EXISTS / ON CONFLICT). |

### Manual SQL Fallback

If automatic migrations fail, `backend/migrations/manual_001_multitenancy.sql` can be executed via:

```bash
# Via Azure Portal Query Editor, or:
DATABASE_URL=... python backend/scripts/run_sql_file.py backend/migrations/manual_001_multitenancy.sql
```

This should never be needed — it exists as a last resort.

## Health Check

`GET /admin/status` returns structured schema diagnostics:

```json
{
  "db": {
    "connected": true,
    "tables_exist": true,
    "columns_complete": true,
    "missing_columns": [],
    "error": null
  }
}
```

| Field | Meaning |
|---|---|
| `tables_exist` | All three tables (organizations, businesses, subscriptions) exist |
| `columns_complete` | businesses table has all required columns |
| `missing_columns` | List of missing column names (empty when healthy) |
