# Deployment

## CI/CD Flow

```
Push to main
  -> GitHub Actions
    -> main_datasoko-api.yml (backend paths changed)
        -> pip install -r requirements.txt
        -> Deploy to Azure Web App (datasoko-api)
    -> main_datasoko-web.yml (frontend paths changed)
        -> npm install && npm run build
        -> Deploy to Azure Web App (datasoko-web)
  -> Azure App Service
    -> bash startup.sh
      -> python backend/scripts/run_migrations.py
      -> gunicorn starts
```

No migrations run in CI. The database is VNet-private and unreachable from GitHub Actions runners. Migrations execute on the Azure container itself via `startup.sh`.

## Azure App Service Configuration

### Backend (datasoko-api)

**Runtime:** Python 3.11 (Linux)
**Startup command:** `bash startup.sh`

Required App Settings:

| Setting | Value |
|---|---|
| `DATABASE_URL` | PostgreSQL connection string |
| `ADMIN_TOKEN` | Legacy/service bearer token for admin routes |
| `JWT_SECRET` | JWT signing secret; backend startup fails if missing |
| `BACKEND_CORS_ORIGINS` | `https://datasoko-web.azurewebsites.net` |
| `SCM_DO_BUILD_DURING_DEPLOYMENT` | `true` |

Optional App Settings:

| Setting | Purpose |
|---|---|
| `SETTINGS_ENCRYPTION_KEY` | Encryption key for stored secrets |
| `ALLOW_BOOTSTRAP_ADMIN` | Set `true` only during controlled first-admin setup; keep `false` otherwise |
| `AZURE_OPENAI_ENDPOINT` | Azure OpenAI endpoint URL |
| `AZURE_OPENAI_API_KEY` | Azure OpenAI API key |
| `AZURE_OPENAI_DEPLOYMENT` | Azure OpenAI deployment name |
| `WHATSAPP_PHONE_NUMBER_ID` | Meta Cloud API phone number ID |
| `WHATSAPP_ACCESS_TOKEN` | Meta Cloud API access token |

### Frontend (datasoko-web)

**Runtime:** Node 22 (Linux)

Required App Settings:

| Setting | Value |
|---|---|
| `NEXT_PUBLIC_API_BASE_URL` | `https://datasoko-api.azurewebsites.net` |

## startup.sh Behavior

```bash
#!/bin/bash
set -e

echo "=== RUNNING DB MIGRATIONS ==="
python backend/scripts/run_migrations.py || echo "[migrations] WARNING: failed but continuing..."

echo "=== STARTING APP ==="
exec gunicorn -k uvicorn.workers.UvicornWorker backend.main:app --bind=0.0.0.0:$PORT --timeout 120
```

- Runs migrations **before** the app starts
- Migration failure does **not** crash the app (logs warning, continues)
- Uses `exec` so gunicorn replaces the shell process (proper signal handling)
- `$PORT` is set by Azure App Service

### Expected Log Output (Healthy)

```
=== RUNNING DB MIGRATIONS ===
[migrations] starting
[migrations] DATABASE_URL: postgresql://***@server.postgres.database.azure.com/datasoko
[migrations] database connection established
[migration] ensuring schema_migrations tracking table exists
[migration] found: migration_001_multitenancy.py
[migration] skipping migration_001_multitenancy (already applied)
[migration] done — applied=0 skipped=1 total=1
[migrations] completed successfully
=== STARTING APP ===
```

### Expected Log Output (First Deploy)

```
=== RUNNING DB MIGRATIONS ===
[migrations] starting
[migrations] DATABASE_URL: postgresql://***@server.postgres.database.azure.com/datasoko
[migrations] database connection established
[migration] ensuring schema_migrations tracking table exists
[migration] found: migration_001_multitenancy.py
[migration] applying migration_001_multitenancy
[migration] applied migration_001_multitenancy successfully
[migration] done — applied=1 skipped=0 total=1
[migrations] completed successfully
=== STARTING APP ===
```

## Safety Net

The FastAPI startup hook in `main.py` acts as a secondary check. If `startup.sh` was bypassed (e.g., running `uvicorn` directly in dev), the hook checks whether the `organizations` table exists. If missing, it runs migrations.

This is a fallback only. The primary path is always `startup.sh`.

## Troubleshooting

### "relation does not exist" errors

**Cause:** Migrations didn't run or ran incompletely.

**Check:** `GET /admin/status` — look at `tables_exist` and `columns_complete`.

**Fix:** Redeploy (triggers `startup.sh`). If that fails, check Azure Log Stream for migration errors.

### Migrations fail with connection error

**Cause:** `DATABASE_URL` is wrong or the database is unreachable.

**Check:** Azure Log Stream for `[migrations] FAILED:` message.

**Fix:** Verify `DATABASE_URL` in App Settings. Ensure the App Service is in the same VNet as the database.

### "column does not exist" after partial migration

**Cause:** Tables were created but columns are missing (schema drift).

**Fix:** The migration's three-phase approach (CREATE -> ALTER -> INDEX) handles this automatically. Redeploy to trigger. If stuck, run the manual SQL fallback:

```bash
# Via Azure Cloud Shell or SSH:
DATABASE_URL=... python backend/scripts/run_sql_file.py backend/migrations/manual_001_multitenancy.sql
```

### Migration runs but tables still missing

**Cause:** Migration was recorded in `schema_migrations` during a previous partial run, so the runner skips it.

**Fix:** Delete the migration record and redeploy:

```sql
DELETE FROM schema_migrations WHERE migration_id = 'migration_001_multitenancy';
```

### App starts but UI shows DB errors

**Cause:** App is running but can't reach the database.

**Check:** `GET /admin/status` returns `db.connected: false` with an error message.

**Fix:** Check Azure networking (VNet, private endpoint, firewall rules).
