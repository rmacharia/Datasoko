# Architecture

## System Flow

```
                          ┌──────────────┐
                          │  Next.js 15  │
                          │  Admin UI    │
                          │  :3000       │
                          └──────┬───────┘
                                 │ HTTP (JWT or ADMIN_TOKEN)
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

1. User signs in through `/auth/login` or bootstraps the first platform admin via `/setup`.
2. Platform admins choose organization/business context; tenant admins and SME users are pinned to their JWT tenant.
3. User uploads Excel/M-Pesa files via the admin UI.
4. Backend normalizes data, computes quality scores, persists tenant-scoped JSONB payloads, and logs activity.
5. Metrics and analytics endpoints compute dashboard data from stored payloads.
6. Report generation produces deterministic metrics, optional guarded narration, and optional WhatsApp delivery.
7. The optional scheduler can trigger report jobs when `RUN_SCHEDULER=true`.

## Multi-Tenant Model

```
Organization (1)  ──>  Subscription (1)
      │
      ├──>  User (many)
      │       └── roles: super_admin | admin | sme_user
      │
      └──>  Business (many)
                │
                └──>  ingestion_weekly_payloads (many)
```

- **Organization**: tenant boundary. Has an ID, name, and creation timestamp.
- **Subscription**: one per organization. Tracks plan, status, and expiry date.
- **User**: authenticated account. `super_admin` is platform-wide and has no tenant; `admin` is organization-scoped; `sme_user` is pinned to one business.
- **Business**: a single SME. Belongs to one organization. Identified by `business_id`.
- **Payloads**: weekly data uploads, tenant-tagged by `organization_id` and keyed by `(business_id, dataset, week_start, week_end)`.

Default organization `default_org` is seeded automatically by migrations.

## Backend Structure

```
backend/
  main.py                  # FastAPI app, admin routes, startup hook
  routes/
    auth.py                # /auth/status, bootstrap, register, login, me
    onboarding.py          # POST /onboard
    businesses.py          # POST/GET /businesses
    billing.py             # GET /billing/current
    users.py               # User CRUD for platform/org admins
    admin_platform.py      # Platform org/business listing and org creation
    analytics.py           # Dashboard analytics, activity, costs
    schedules.py           # Report schedule CRUD
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
    migration_002_analytics.py     # Activity + WhatsApp logs
    migration_003_scheduling.py    # Report schedules + WhatsApp costs
    migration_004_auth.py          # Users table
    migration_005_users_constraints.py
    migration_006_roles_split.py   # super_admin/admin/sme_user split
    migration_007_hardening.py     # schedule run tracking + cost defaults
    migration_008_tenant_payload_normalization.py
    manual_001_multitenancy.sql    # Manual SQL fallback
  scripts/
    run_migrations.py      # CLI entry point for startup.sh
    run_sql_file.py        # Manual SQL execution helper
  ai/narrator.py           # LLM narration (OpenAI/Azure)
  messaging/whatsapp_formatter.py  # WhatsApp message formatting
  admin_settings_store.py  # Settings + encrypted secrets
  auth.py                  # JWT, roles, tenant context helpers
  scheduler.py             # Optional in-process scheduled report runner
```

## Frontend Structure

```
frontend/
  app/
    page.tsx               # Dashboard (system health + analytics)
    setup/page.tsx         # First admin bootstrap flow
    (auth)/login/page.tsx  # Login page
    admin/page.tsx         # Platform admin console
    admin/organizations/   # Organization provisioning
    admin/businesses/      # Platform business listing
    admin/users/           # Platform user administration
    onboarding/page.tsx    # New org onboarding flow
    upload/page.tsx        # File upload
    reports/page.tsx       # Weekly reports
    jobs/page.tsx          # Job status
    settings/page.tsx      # Settings + billing + SME management
    users/page.tsx         # Tenant user management
  components/
    auth-provider.tsx      # Auth context (token in memory)
    auth-guard.tsx         # Route protection
    route-guard.tsx        # Role/context-aware routing guard
    org-provider.tsx       # Organization + active business context
    settings-provider.tsx  # Settings context
    internal-header.tsx    # Navigation header
    status-card.tsx        # Dashboard status cards
    toast-provider.tsx     # Toast notifications
  lib/
    api.ts                 # API client functions
    auth.ts                # Login/bootstrap/me client helpers
    routing.ts             # Role-aware post-login routing
    org-session.ts         # Platform admin org/business session persistence
```

## Design Principles

1. **No ORM.** Raw SQL with psycopg2. Queries are explicit and auditable.
2. **Idempotent everything.** Migrations, seed data, and backfills use `IF NOT EXISTS` and `ON CONFLICT DO NOTHING`.
3. **Fail open on startup.** Migration failures log errors but don't crash the app.
4. **Auth fails closed.** `JWT_SECRET` is required at startup; `ADMIN_TOKEN` remains only a legacy/service credential.
5. **Secrets stay encrypted.** Stored secrets use XOR-stream + HMAC-SHA-256. API keys never appear in logs.
6. **Decimal arithmetic.** All financial computations use `Decimal` to avoid floating-point drift.
7. **Protocol-based testing.** `NormalizedPayloadStore` protocol allows unit tests without a real DB.
