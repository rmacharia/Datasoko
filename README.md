# DataSoko

DataSoko is a WhatsApp-first business analyst for Kenyan SMEs.

It ingests Excel sales data and M-Pesa CSV statements, validates and normalizes them deterministically, and prepares structured outputs for weekly insight generation.

## Testing

Use the unified test runner:

```bash
./scripts/run_tests.sh [unit|integration|all]
```

### Unit tests (always runnable)

```bash
./scripts/run_tests.sh unit
```

Runs local deterministic tests that do not require a live database.

### Integration tests (requires PostgreSQL)

```bash
DATABASE_URL=postgresql://postgres:postgres@localhost:5432/datasoko_test \
./scripts/run_tests.sh integration
```

Behavior:
- If `DATABASE_URL` is set: executes live PostgreSQL integration tests.
- If `DATABASE_URL` is not set: integration tests are skipped cleanly.

### Run all

```bash
./scripts/run_tests.sh all
```

Runs unit tests first, then integration tests (or skip if `DATABASE_URL` is unset).

## CI

GitHub Actions workflow: `.github/workflows/tests.yml`
- `unit-tests` job always runs.
- `integration-tests` job runs with a Postgres service and `DATABASE_URL` configured.

## Run Backend + Internal Admin UI (Local)

1. Start backend:

```bash
uvicorn backend.main:app --reload --host 0.0.0.0 --port 8000
```

2. In another terminal, start frontend:

```bash
cd frontend
npm install
npm run dev
```

3. Open `http://localhost:3000/login`, enter internal admin token, then use Overview.

Environment variables used:
- Backend: `ADMIN_TOKEN` (for internal auth rollout), PostgreSQL `DATABASE_URL`/`PG*`
- Backend: `BACKEND_CORS_ORIGINS` (comma-separated, restrictive CORS allowlist)
- Frontend: `NEXT_PUBLIC_API_BASE_URL` (default `http://localhost:8000`)
