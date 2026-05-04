# Architecture

## System Flow

```
                          ┌──────────────┐
                          │  Next.js 15  │
                          │  Admin UI    │
                          │  :3000       │
                          └──────┬───────┘
                                 │ HTTP (Bearer token)
                                 v
                          ┌──────────────┐
                          │  FastAPI     │
                          │  Backend     │
                          │  :8000       │
                          └──┬───┬───┬───┘
                             │   │   │
              ┌──────────────┘   │   └──────────────┐
              v                  v                  v
     ┌────────────┐    ┌──────────────┐    ┌──────────────┐
     │ PostgreSQL │    │ OpenAI/Azure │    │ WhatsApp     │
     │ (Azure)    │    │ LLM API      │    │ Cloud API    │
     └────────────┘    └──────────────┘    └──────────────┘
```

## Request Flow

1. User uploads Excel/M-Pesa file via admin UI
2. Backend normalizes data, computes quality scores, persists as JSONB
3. Metrics engine computes weekly KPIs from stored payloads
4. LLM narration generates human-readable insights (optional)
5. WhatsApp formatter prepares delivery message

## Multi-Tenant Model

```
Organization (1)  ──>  Subscription (1)
      │
      └──>  Business (many)
                │
                └──>  ingestion_weekly_payloads (many)
```

- **Organization**: tenant boundary. Has an ID, name, and creation timestamp.
- **Subscription**: one per organization. Tracks plan, status, and expiry date.
- **Business**: a single SME. Belongs to one organization. Identified by `business_id`.
- **Payloads**: weekly data uploads, keyed by `(business_id, dataset, week_start, week_end)`.

Default organization `default_org` is seeded automatically by migrations.

## Backend Structure

```
backend/
  main.py                  # FastAPI app, admin routes, startup hook
  routes/
    onboarding.py          # POST /onboard
    businesses.py          # POST/GET /businesses
    billing.py             # GET /billing/current
  ingestion/
    loaders.py             # Excel + M-Pesa file parsers
    service.py             # Orchestrates loading + persistence
    factory.py             # Wires IngestionService with real store
  validation/
    schemas.py             # Pydantic models for all data types
    normalizers.py         # Deterministic row-level transforms
  metrics/
    weekly_metrics.py      # Pure-Python KPI engine (Decimal arithmetic)
    contracts.py           # JSON validation + LLM narration input builder
  storage/
    postgres_connection.py # Connection factory (psycopg2-binary)
    postgres_ingestion_store.py  # JSONB payload persistence
  db/
    connection.py          # get_connection() wrapper (autocommit=False)
  migrations/
    run.py                 # Migration runner with schema_migrations tracking
    migration_001_multitenancy.py  # Multi-tenancy DDL + drift repair
    manual_001_multitenancy.sql    # Manual SQL fallback
  scripts/
    run_migrations.py      # CLI entry point for startup.sh
    run_sql_file.py        # Manual SQL execution helper
  ai/narrator.py           # LLM narration (OpenAI/Azure)
  messaging/whatsapp_formatter.py  # WhatsApp message formatting
  admin_settings_store.py  # Settings + encrypted secrets
```

## Frontend Structure

```
frontend/
  app/
    page.tsx               # Dashboard (system health + analytics)
    (auth)/login/page.tsx  # Login page
    onboarding/page.tsx    # New org onboarding flow
    upload/page.tsx        # File upload
    reports/page.tsx       # Weekly reports
    jobs/page.tsx          # Job status
    settings/page.tsx      # Settings + billing + SME management
  components/
    auth-provider.tsx      # Auth context (token in memory)
    auth-guard.tsx         # Route protection
    org-provider.tsx       # Organization + active business context
    settings-provider.tsx  # Settings context
    internal-header.tsx    # Navigation header
    status-card.tsx        # Dashboard status cards
    toast-provider.tsx     # Toast notifications
  lib/
    api.ts                 # API client functions
```

## Design Principles

1. **No ORM.** Raw SQL with psycopg2. Queries are explicit and auditable.
2. **Idempotent everything.** Migrations, seed data, and backfills use `IF NOT EXISTS` and `ON CONFLICT DO NOTHING`.
3. **Fail open on startup.** Migration failures log errors but don't crash the app.
4. **Secrets stay encrypted.** Stored secrets use XOR-stream + HMAC-SHA-256. API keys never appear in logs.
5. **Decimal arithmetic.** All financial computations use `Decimal` to avoid floating-point drift.
6. **Protocol-based testing.** `NormalizedPayloadStore` protocol allows unit tests without a real DB.
