# DataSoko

WhatsApp-first business analytics for Kenyan SMEs. DataSoko ingests Excel sales data and M-Pesa CSV statements, validates and normalizes them deterministically, computes weekly KPIs, generates guarded narration, and delivers internal dashboards plus WhatsApp-ready reports.

## Architecture

```
Next.js 15 (App Router)  ──>  FastAPI backend  ──>  PostgreSQL (Azure)
     :3000                        :8000              VNet-private
```

- **Backend:** FastAPI (Python 3.11) — auth, tenant routing, ingestion, metrics, AI narration, WhatsApp delivery, scheduling
- **Frontend:** Next.js 15 / React 19 — setup, login, tenant-aware dashboard, upload, reports, analytics, schedules, settings, user/org admin
- **Database:** PostgreSQL on Azure — multi-tenant organizations, businesses, users, payloads, activity, WhatsApp logs, schedules
- **Deployment:** GitHub Actions -> Azure App Service (Linux)
- **Migrations:** Automatic via `startup.sh` before app starts

See [docs/architecture.md](docs/architecture.md) for the full system design.

## Quick Start (Local)

### Backend

```bash
pip install -r requirements.txt
export ADMIN_TOKEN=your-secret-token
export JWT_SECRET=your-jwt-signing-secret
export ALLOW_BOOTSTRAP_ADMIN=true
export DATABASE_URL=postgresql://postgres:postgres@localhost:5432/datasoko
python backend/scripts/run_migrations.py
uvicorn backend.main:app --reload --host 0.0.0.0 --port 8000
```

### Frontend

```bash
cd frontend
npm install
npm run dev
```

Open `http://localhost:3000/setup` for first-time setup, then sign in at `http://localhost:3000/login`.

First-time setup creates a platform `super_admin` only when `ALLOW_BOOTSTRAP_ADMIN=true` and no users exist. Turn it off after bootstrapping.

## Testing

```bash
# Unit tests (no DB required)
./scripts/run_tests.sh unit

# Integration tests (requires PostgreSQL)
DATABASE_URL=postgresql://postgres:postgres@localhost:5432/datasoko_test \
./scripts/run_tests.sh integration

# All tests
./scripts/run_tests.sh all

# Single test file
python -m unittest -q tests/test_multitenancy.py
```

## Environment Variables

| Variable | Required | Purpose |
|---|---|---|
| `DATABASE_URL` | Yes | PostgreSQL connection string |
| `ADMIN_TOKEN` | Yes | Legacy/service bearer token for admin API routes |
| `JWT_SECRET` | Yes | JWT signing secret; app fails closed if missing |
| `ALLOW_BOOTSTRAP_ADMIN` | No | Allows first public `super_admin` registration only when `true` |
| `BACKEND_CORS_ORIGINS` | No | Comma-separated CORS allowlist (default: `http://localhost:3000`) |
| `SETTINGS_ENCRYPTION_KEY` | No | Key for encrypting stored secrets (falls back to `ADMIN_TOKEN`) |
| `RUN_SCHEDULER` | No | Starts the in-process report scheduler when set to `true` |
| `NEXT_PUBLIC_API_BASE_URL` | No | Frontend -> backend URL (default: `http://localhost:8000`) |
| `TWILIO_ACCOUNT_SID` / `TWILIO_AUTH_TOKEN` / `TWILIO_WHATSAPP_NUMBER` | No | Twilio WhatsApp sending for generated reports and test sends |
| `AZURE_OPENAI_*` / `OPENAI_*` | No | Optional narration provider credentials |
| `WHATSAPP_*` | No | Optional Meta Cloud API settings for settings-console test sends |

See [docs/deployment.md](docs/deployment.md) for Azure-specific variables.

## Documentation

- [Architecture](docs/architecture.md) — system design, multi-tenancy model, design principles
- [Database](docs/database.md) — table definitions, migration strategy, schema drift handling
- [API Reference](docs/api.md) — auth, tenant context, endpoint map, request/response examples
- [Deployment](docs/deployment.md) — CI/CD flow, Azure setup, troubleshooting
- [Development](docs/development.md) — local setup, testing, migration rules, guardrails

## CI/CD

GitHub Actions workflows in `.github/workflows/`:
- `tests.yml` — runs unit + integration tests on push
- `main_datasoko-api.yml` — deploys backend to Azure on push to `main`
- `main_datasoko-web.yml` — deploys frontend to Azure on push to `main`

Migrations run automatically on Azure container startup via `startup.sh`. No manual SSH or SQL execution is required for normal deployments.
