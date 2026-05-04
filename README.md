# DataSoko

WhatsApp-first business analytics for Kenyan SMEs. Ingests Excel sales data and M-Pesa CSV statements, validates and normalizes them deterministically, computes weekly KPIs, generates LLM narrations, and delivers reports via WhatsApp.

## Architecture

```
Next.js 15 (App Router)  ──>  FastAPI backend  ──>  PostgreSQL (Azure)
     :3000                        :8000              VNet-private
```

- **Backend:** FastAPI (Python 3.11) — ingestion, metrics, AI narration, WhatsApp delivery
- **Frontend:** Next.js 15 — admin dashboard, onboarding, settings, reports
- **Database:** PostgreSQL on Azure — multi-tenant (organizations -> businesses)
- **Deployment:** GitHub Actions -> Azure App Service (Linux)
- **Migrations:** Automatic via `startup.sh` before app starts

See [docs/architecture.md](docs/architecture.md) for the full system design.

## Quick Start (Local)

### Backend

```bash
pip install -r requirements.txt
export ADMIN_TOKEN=your-secret-token
export DATABASE_URL=postgresql://postgres:postgres@localhost:5432/datasoko
uvicorn backend.main:app --reload --host 0.0.0.0 --port 8000
```

### Frontend

```bash
cd frontend
npm install
npm run dev
```

Open `http://localhost:3000/login` and enter your `ADMIN_TOKEN`.

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
| `ADMIN_TOKEN` | Yes | Bearer token for admin API routes |
| `BACKEND_CORS_ORIGINS` | No | Comma-separated CORS allowlist (default: `http://localhost:3000`) |
| `SETTINGS_ENCRYPTION_KEY` | No | Key for encrypting stored secrets (falls back to `ADMIN_TOKEN`) |
| `NEXT_PUBLIC_API_BASE_URL` | No | Frontend -> backend URL (default: `http://localhost:8000`) |

See [docs/deployment.md](docs/deployment.md) for Azure-specific variables.

## Documentation

- [Architecture](docs/architecture.md) — system design, multi-tenancy model, design principles
- [Database](docs/database.md) — table definitions, migration strategy, schema drift handling
- [API Reference](docs/api.md) — endpoints, request/response examples
- [Deployment](docs/deployment.md) — CI/CD flow, Azure setup, troubleshooting
- [Development](docs/development.md) — local setup, testing, migration rules, guardrails

## CI/CD

GitHub Actions workflows in `.github/workflows/`:
- `tests.yml` — runs unit + integration tests on push
- `main_datasoko-api.yml` — deploys backend to Azure on push to `main`
- `main_datasoko-web.yml` — deploys frontend to Azure on push to `main`

Migrations run automatically on Azure container startup via `startup.sh`. No manual SSH or SQL execution is required.
