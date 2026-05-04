-- DataSoko multitenancy schema (manual fallback)
-- Run this via Azure Portal → Query editor, or via backend/scripts/run_sql_file.py
--
-- Safe to re-run: all statements use IF NOT EXISTS / ON CONFLICT DO NOTHING.

-- Migration tracking
CREATE TABLE IF NOT EXISTS schema_migrations (
    migration_id  TEXT PRIMARY KEY,
    applied_at    TIMESTAMPTZ DEFAULT NOW()
);

-- Organizations
CREATE TABLE IF NOT EXISTS organizations (
    id          TEXT PRIMARY KEY,
    name        TEXT,
    created_at  TIMESTAMPTZ DEFAULT NOW()
);

-- Subscriptions
CREATE TABLE IF NOT EXISTS subscriptions (
    organization_id  TEXT PRIMARY KEY NOT NULL,
    plan             TEXT,
    status           TEXT,
    expiry_date      TIMESTAMPTZ,
    created_at       TIMESTAMPTZ DEFAULT NOW()
);

-- Businesses
CREATE TABLE IF NOT EXISTS businesses (
    id               TEXT PRIMARY KEY,
    organization_id  TEXT NOT NULL DEFAULT 'default_org',
    name             TEXT,
    whatsapp_phone   TEXT,
    created_at       TIMESTAMPTZ DEFAULT NOW()
);

-- Index
CREATE INDEX IF NOT EXISTS idx_businesses_org
ON businesses (organization_id);

-- Default org
INSERT INTO organizations (id, name)
VALUES ('default_org', 'Default Organization')
ON CONFLICT DO NOTHING;

-- Backfill existing businesses from ingestion data (skip if table doesn't exist)
DO $$
BEGIN
    IF EXISTS (
        SELECT 1 FROM information_schema.tables
        WHERE table_schema = 'public' AND table_name = 'ingestion_weekly_payloads'
    ) THEN
        INSERT INTO businesses (id, organization_id)
        SELECT DISTINCT business_id, 'default_org'
        FROM ingestion_weekly_payloads
        WHERE business_id IS NOT NULL
        ON CONFLICT (id) DO NOTHING;
    END IF;
END $$;

-- Record migration as applied so the app startup runner skips it
INSERT INTO schema_migrations (migration_id)
VALUES ('migration_001_multitenancy')
ON CONFLICT DO NOTHING;
