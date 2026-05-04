# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## What This Is

DataSoko is a WhatsApp-first business analytics tool for Kenyan SMEs. It ingests Excel sales data and M-Pesa CSV statements, validates/normalizes them deterministically, computes weekly KPIs, generates LLM narrations, and delivers reports via WhatsApp. The stack is a FastAPI backend + Next.js 15 admin UI.

## Commands

### Backend

```bash
# Install dependencies
pip install -r requirements.txt

# Start backend (dev)
uvicorn backend.main:app --reload --host 0.0.0.0 --port 8000

# Run unit tests (no DB required)
./scripts/run_tests.sh unit

# Run integration tests (requires PostgreSQL)
DATABASE_URL=postgresql://postgres:postgres@localhost:5432/datasoko_test \
./scripts/run_tests.sh integration

# Run all tests
./scripts/run_tests.sh all

# Run a single test file
python3 -m unittest -q tests/test_metrics_contracts.py
```

### Frontend

```bash
cd frontend
npm install
npm run dev          # start at http://localhost:3000
npm run typecheck    # TypeScript check (separate tsconfig.typecheck.json)
npm run lint
npm run test         # vitest
npm run build
```

### Local Login

Navigate to `http://localhost:3000/login` and enter the `ADMIN_TOKEN` env var value.

## Architecture

### Backend (`backend/`)

**`main.py`** — Single FastAPI app file. All routes live here. Admin routes are guarded by `_require_admin_token` (Bearer token via `ADMIN_TOKEN` env var). Module-level `LAST_RUN_SUMMARY` and `JOBS` dicts serve as in-memory state for the MVP (no task queue).

**`ingestion/`** — File loading and normalization pipeline:
- `loaders.py` — `load_excel_sales()` and `load_mpesa_csv()` return `NormalizationResult` (Pydantic model)
- `service.py` — `IngestionService` orchestrates loading + persistence; accepts a `NormalizedPayloadStore` protocol so tests can inject stubs without a real DB
- `factory.py` — wires up `IngestionService` with a real `PostgresIngestionStore`

**`validation/`** — `schemas.py` defines all Pydantic models: `ExcelSalesRecord`, `MpesaRecord`, `QualityReport`, `NormalizationResult`, `ValidationIssue`. `normalizers.py` contains the deterministic row-level transformations and scoring logic.

**`metrics/`** — `weekly_metrics.py` is a pure-Python, DB-free KPI engine. Takes a list of canonical sales records plus a date window; returns revenue, WoW delta, top products, slow movers, repeat customers, avg transaction value. All computations use `Decimal` for determinism. `contracts.py` provides `validate_metrics_json()` and `build_llm_narration_input()`.

**`storage/`** — `postgres_connection.py` creates connections using `DATABASE_URL` or individual `PG*` env vars. `postgres_ingestion_store.py` stores normalized payloads as JSONB in `ingestion_weekly_payloads` (unique on `business_id + dataset + week_start + week_end`).

**`admin_settings_store.py`** — Singleton `SETTINGS_STORE`. Non-secret settings (AI provider, WhatsApp config, operational defaults) live in the `admin_settings` Postgres table with in-memory fallback. Secrets (`ai_api_key`, `whatsapp_access_token`, `whatsapp_verify_token`) are stored encrypted in `admin_secret_settings` or read from env vars. Encryption is XOR-stream with SHA-256 keystream + HMAC-SHA-256 MAC (custom `v1` scheme, key derived from `SETTINGS_ENCRYPTION_KEY` or `ADMIN_TOKEN`).

**`ai/narrator.py`** — Calls OpenAI or Azure OpenAI (`/v1/chat/completions`) via stdlib `urllib`. Falls back to a metrics-only deterministic narration when no API key is configured or the LLM call fails.

**`messaging/whatsapp_formatter.py`** — Formats computed metrics into a WhatsApp-ready text message.

### Frontend (`frontend/`)

Next.js 15 App Router. Pages: `login`, `upload`, `reports`, `jobs`, `settings`. Auth state is managed in `components/auth-provider.tsx` (stores the admin token in memory). `components/settings-provider.tsx` loads settings from `/admin/settings` on mount.

API calls use `NEXT_PUBLIC_API_BASE_URL` (default `http://localhost:8000`).

## Key Environment Variables

| Variable | Purpose |
|---|---|
| `DATABASE_URL` | PostgreSQL connection string |
| `ADMIN_TOKEN` | Internal admin bearer token (required) |
| `BACKEND_CORS_ORIGINS` | Comma-separated CORS allowlist (default: `http://localhost:3000`) |
| `SETTINGS_ENCRYPTION_KEY` | Key for encrypting stored secrets (falls back to `ADMIN_TOKEN`) |
| `AZURE_OPENAI_ENDPOINT` / `AZURE_OPENAI_API_KEY` / `AZURE_OPENAI_DEPLOYMENT` | Azure OpenAI credentials |
| `OPENAI_API_KEY` | OpenAI credentials |
| `WHATSAPP_PHONE_NUMBER_ID` / `WHATSAPP_ACCESS_TOKEN` | Meta Cloud API credentials |
| `NEXT_PUBLIC_API_BASE_URL` | Frontend → backend URL |

## Testing Notes

- **Unit tests** (`test_admin_settings_api.py`, `test_storage_and_runtime.py`, `test_metrics_contracts.py`) are fully deterministic — no DB, no network.
- **Integration tests** (`test_postgres_integration.py`) require a live PostgreSQL instance via `DATABASE_URL`. They are skipped cleanly if `DATABASE_URL` is unset.
- The `NormalizedPayloadStore` protocol in `ingestion/service.py` is the main seam for unit-testing ingestion without a real DB.

## Database Schema

Two tables are created automatically on first use (via `ensure_table()`):
- `ingestion_weekly_payloads` — JSONB payloads, unique on `(business_id, dataset, week_start, week_end)`
- `admin_settings` — single-row (`global`) non-secret settings as JSONB
- `admin_secret_settings` — encrypted secrets per key
