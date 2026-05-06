from __future__ import annotations

import sys
import types
import unittest
from typing import Any

# ── Minimal FastAPI stub so backend.routes modules import without FastAPI installed ──
if "fastapi" not in sys.modules:
    class _HTTPException(Exception):
        def __init__(self, status_code: int, detail: Any = None) -> None:
            super().__init__(detail)
            self.status_code = status_code
            self.detail = detail

    class _APIRouter:
        def post(self, *a, **kw):
            def _d(fn): return fn
            return _d
        def get(self, *a, **kw):
            def _d(fn): return fn
            return _d
        def patch(self, *a, **kw):
            def _d(fn): return fn
            return _d
        def delete(self, *a, **kw):
            def _d(fn): return fn
            return _d

    class _BaseModel:
        def __init__(self, **kwargs):
            for k, v in kwargs.items():
                setattr(self, k, v)

    def _Field(*a, **kw): return None

    sys.modules["fastapi"] = types.SimpleNamespace(
        APIRouter=_APIRouter,
        HTTPException=_HTTPException,
    )
    sys.modules["pydantic"] = types.SimpleNamespace(BaseModel=_BaseModel, Field=_Field)


# ─────────────────────────────────────────────
# Shared stub connection / cursor
# ─────────────────────────────────────────────

class RecordingCursor:
    def __init__(self, conn: "RecordingConnection") -> None:
        self._conn = conn

    def __enter__(self) -> "RecordingCursor":
        return self

    def __exit__(self, *_: Any) -> None:
        pass

    def execute(self, query: str, params: Any = None) -> None:
        self._conn.executed.append((query.strip(), params))

    def fetchone(self) -> Any:
        return self._conn._fetchone

    def fetchall(self) -> Any:
        return self._conn._fetchall


class RecordingConnection:
    def __init__(self) -> None:
        self.executed: list[tuple[str, Any]] = []
        self.commit_count = 0
        self.rollback_count = 0
        self._fetchone: Any = None
        self._fetchall: list[Any] = []

    def cursor(self) -> RecordingCursor:
        return RecordingCursor(self)

    def commit(self) -> None:
        self.commit_count += 1

    def rollback(self) -> None:
        self.rollback_count += 1


# ─────────────────────────────────────────────
# 1. backend/db/connection.py — get_connection()
# ─────────────────────────────────────────────

class TestGetConnection(unittest.TestCase):
    def test_get_connection_returns_connection_with_autocommit_false(self) -> None:
        """get_connection() must expose autocommit=False so callers control transactions."""
        import os
        from unittest.mock import patch, MagicMock

        fake_conn = MagicMock()
        fake_conn.autocommit = False

        with patch.dict(os.environ, {"DATABASE_URL": "postgresql://test"}), \
             patch("backend.db.connection.create_postgres_connection", return_value=fake_conn):
            from backend.db.connection import get_connection
            conn = get_connection()

        self.assertFalse(conn.autocommit)

    def test_get_connection_delegates_to_create_postgres_connection(self) -> None:
        """get_connection() is a thin wrapper — it must call create_postgres_connection."""
        from unittest.mock import patch, MagicMock
        import backend.db.connection as mod

        sentinel = MagicMock()
        sentinel.autocommit = False
        with patch.object(mod, "create_postgres_connection", return_value=sentinel) as mock_factory:
            conn = mod.get_connection()

        mock_factory.assert_called_once()
        self.assertIs(conn, sentinel)


# ─────────────────────────────────────────────
# 2. Migration runner — backend/migrations/run.py
# ─────────────────────────────────────────────

class TestMigrationRunner(unittest.TestCase):
    def _fresh_conn(self) -> RecordingConnection:
        """Return a connection where _fetchone=None (migration not yet applied)."""
        conn = RecordingConnection()
        conn._fetchone = None
        return conn

    def test_runner_creates_schema_migrations_table(self) -> None:
        """Runner must ensure schema_migrations exists before doing anything else."""
        from backend.migrations.run import run_migrations
        conn = self._fresh_conn()
        run_migrations(conn)
        all_sql = " ".join(q for q, _ in conn.executed)
        self.assertIn("schema_migrations", all_sql)
        self.assertIn("CREATE TABLE IF NOT EXISTS", all_sql)

    def test_runner_commits_after_tracking_table(self) -> None:
        """Tracking-table creation must be committed so it survives a later rollback."""
        from backend.migrations.run import run_migrations
        conn = self._fresh_conn()
        run_migrations(conn)
        self.assertGreaterEqual(conn.commit_count, 1)

    def test_runner_skips_already_applied_migration(self) -> None:
        """If fetchone returns a row, the migration DDL must NOT be executed."""
        from backend.migrations.run import run_migrations
        conn = RecordingConnection()
        conn._fetchone = (1,)  # simulate already applied
        run_migrations(conn)
        all_sql = " ".join(q for q, _ in conn.executed)
        # organisations DDL must be absent — migration was skipped
        self.assertNotIn("CREATE TABLE IF NOT EXISTS organizations", all_sql)

    def test_runner_rolls_back_on_migration_failure(self) -> None:
        """A failing migration must trigger a rollback and re-raise."""
        import importlib.util, types
        from pathlib import Path

        # Patch the discovery to return a single bad migration
        bad_mod = types.ModuleType("bad_migration")
        bad_mod.run = lambda conn: (_ for _ in ()).throw(RuntimeError("boom"))  # type: ignore[assignment]

        from unittest.mock import patch
        from backend.migrations import run as runner_mod

        conn = RecordingConnection()
        conn._fetchone = None  # not applied yet

        with patch.object(runner_mod, "_discover_migrations", return_value=[Path("bad.py")]), \
             patch.object(runner_mod, "_load_module", return_value=bad_mod):
            with self.assertRaises(RuntimeError):
                runner_mod.run_migrations(conn)

        self.assertGreaterEqual(conn.rollback_count, 1)

    def test_runner_records_migration_id_after_success(self) -> None:
        """After a successful migration run, migration_id must be inserted into schema_migrations."""
        from backend.migrations.run import run_migrations
        conn = self._fresh_conn()
        run_migrations(conn)
        insert_sqls = [q for q, _ in conn.executed if "INSERT INTO schema_migrations" in q]
        self.assertTrue(len(insert_sqls) >= 1, "Expected at least one INSERT INTO schema_migrations")


# ─────────────────────────────────────────────
# 3. Migration 001 — DDL correctness
# ─────────────────────────────────────────────

class TestMigration001(unittest.TestCase):
    def _run_001(self) -> RecordingConnection:
        from backend.migrations.migration_001_multitenancy import run
        conn = RecordingConnection()
        run(conn)
        return conn

    def test_creates_organizations_table(self) -> None:
        conn = self._run_001()
        all_sql = " ".join(q for q, _ in conn.executed)
        self.assertIn("CREATE TABLE IF NOT EXISTS organizations", all_sql)

    def test_creates_businesses_table(self) -> None:
        conn = self._run_001()
        all_sql = " ".join(q for q, _ in conn.executed)
        self.assertIn("CREATE TABLE IF NOT EXISTS businesses", all_sql)

    def test_creates_subscriptions_table(self) -> None:
        conn = self._run_001()
        all_sql = " ".join(q for q, _ in conn.executed)
        self.assertIn("CREATE TABLE IF NOT EXISTS subscriptions", all_sql)

    def test_seeds_default_org(self) -> None:
        conn = self._run_001()
        all_sql = " ".join(q for q, _ in conn.executed)
        self.assertIn("default_org", all_sql)
        self.assertIn("INSERT INTO organizations", all_sql)

    def test_backfill_excludes_null_business_ids(self) -> None:
        from backend.migrations.migration_001_multitenancy import run
        conn = RecordingConnection()
        conn._fetchone = (1,)  # simulate ingestion_weekly_payloads exists
        run(conn)
        all_sql = " ".join(q for q, _ in conn.executed)
        self.assertIn("WHERE business_id IS NOT NULL", all_sql)
        self.assertIn("INSERT INTO businesses", all_sql)

    def test_backfill_skipped_when_ingestion_table_missing(self) -> None:
        conn = self._run_001()  # _fetchone defaults to None
        all_sql = " ".join(q for q, _ in conn.executed)
        self.assertNotIn("FROM ingestion_weekly_payloads", all_sql)

    def test_creates_index_on_organization_id(self) -> None:
        conn = self._run_001()
        all_sql = " ".join(q for q, _ in conn.executed)
        self.assertIn("CREATE INDEX IF NOT EXISTS", all_sql)
        self.assertIn("organization_id", all_sql)

    def test_all_ddl_is_idempotent(self) -> None:
        """Every CREATE statement must use IF NOT EXISTS."""
        from backend.migrations.migration_001_multitenancy import run
        conn = RecordingConnection()
        run(conn)
        create_stmts = [q for q, _ in conn.executed if q.startswith("CREATE")]
        self.assertTrue(len(create_stmts) > 0)
        for stmt in create_stmts:
            self.assertIn("IF NOT EXISTS", stmt,
                          f"Non-idempotent CREATE found: {stmt[:80]}")

    def test_migration_does_not_commit(self) -> None:
        """The migration run() must NOT commit — the runner owns the transaction."""
        conn = self._run_001()
        self.assertEqual(conn.commit_count, 0,
                         "Migration 001 must not commit; runner commits after recording.")


# ─────────────────────────────────────────────
# 4. CLI script — backend/scripts/run_migrations.py
# ─────────────────────────────────────────────

class TestRunMigrationsCLI(unittest.TestCase):
    def _import_cli(self):
        import backend.scripts.run_migrations as mod
        return mod

    def test_cli_exits_0_on_success(self) -> None:
        """main() must sys.exit(0) when migrations succeed."""
        import os
        from unittest.mock import patch, MagicMock
        fake_conn = MagicMock()
        cli_mod = self._import_cli()

        with patch.dict(os.environ, {"DATABASE_URL": "postgresql://test"}), \
             patch.object(cli_mod, "get_connection", return_value=fake_conn), \
             patch.object(cli_mod, "run_migrations", return_value=None):
            with self.assertRaises(SystemExit) as ctx:
                cli_mod.main()
        self.assertEqual(ctx.exception.code, 0)

    def test_cli_exits_1_on_missing_database_url(self) -> None:
        """main() must sys.exit(1) when DATABASE_URL is not set."""
        import os
        from unittest.mock import patch
        cli_mod = self._import_cli()

        env_without_db = {k: v for k, v in os.environ.items() if k != "DATABASE_URL"}
        with patch.dict(os.environ, env_without_db, clear=True):
            with self.assertRaises(SystemExit) as ctx:
                cli_mod.main()
        self.assertEqual(ctx.exception.code, 1)

    def test_cli_exits_1_on_failure(self) -> None:
        """main() must sys.exit(1) when run_migrations raises."""
        import os
        from unittest.mock import patch, MagicMock
        fake_conn = MagicMock()
        cli_mod = self._import_cli()

        with patch.dict(os.environ, {"DATABASE_URL": "postgresql://test"}), \
             patch.object(cli_mod, "get_connection", return_value=fake_conn), \
             patch.object(cli_mod, "run_migrations", side_effect=Exception("db down")):
            with self.assertRaises(SystemExit) as ctx:
                cli_mod.main()
        self.assertEqual(ctx.exception.code, 1)

    def test_cli_closes_connection_on_success(self) -> None:
        """Connection must be closed even on a successful run."""
        import os
        from unittest.mock import patch, MagicMock
        fake_conn = MagicMock()
        cli_mod = self._import_cli()

        with patch.dict(os.environ, {"DATABASE_URL": "postgresql://test"}), \
             patch.object(cli_mod, "get_connection", return_value=fake_conn), \
             patch.object(cli_mod, "run_migrations", return_value=None):
            try:
                cli_mod.main()
            except SystemExit:
                pass

        fake_conn.close.assert_called_once()

    def test_cli_closes_connection_on_failure(self) -> None:
        """Connection must be closed even when migrations fail."""
        import os
        from unittest.mock import patch, MagicMock
        fake_conn = MagicMock()
        cli_mod = self._import_cli()

        with patch.dict(os.environ, {"DATABASE_URL": "postgresql://test"}), \
             patch.object(cli_mod, "get_connection", return_value=fake_conn), \
             patch.object(cli_mod, "run_migrations", side_effect=Exception("boom")):
            try:
                cli_mod.main()
            except SystemExit:
                pass

        fake_conn.close.assert_called_once()


# ─────────────────────────────────────────────
# 5. Schema drift — ALTER TABLE coverage
# ─────────────────────────────────────────────

class TestMigration001SchemaDrift(unittest.TestCase):
    def test_alter_statements_run_after_ddl(self) -> None:
        """ALTER TABLE ADD COLUMN IF NOT EXISTS must execute for all expected columns."""
        from backend.migrations.migration_001_multitenancy import run
        conn = RecordingConnection()
        run(conn)
        all_sql = " ".join(q for q, _ in conn.executed)
        self.assertIn("ALTER TABLE businesses ADD COLUMN IF NOT EXISTS organization_id", all_sql)
        self.assertIn("ALTER TABLE businesses ADD COLUMN IF NOT EXISTS name", all_sql)
        self.assertIn("ALTER TABLE businesses ADD COLUMN IF NOT EXISTS whatsapp_phone", all_sql)
        self.assertIn("ALTER TABLE businesses ADD COLUMN IF NOT EXISTS created_at", all_sql)

    def test_alter_covers_organizations_table(self) -> None:
        from backend.migrations.migration_001_multitenancy import run
        conn = RecordingConnection()
        run(conn)
        all_sql = " ".join(q for q, _ in conn.executed)
        self.assertIn("ALTER TABLE organizations ADD COLUMN IF NOT EXISTS name", all_sql)
        self.assertIn("ALTER TABLE organizations ADD COLUMN IF NOT EXISTS created_at", all_sql)

    def test_alter_covers_subscriptions_table(self) -> None:
        from backend.migrations.migration_001_multitenancy import run
        conn = RecordingConnection()
        run(conn)
        all_sql = " ".join(q for q, _ in conn.executed)
        self.assertIn("ALTER TABLE subscriptions ADD COLUMN IF NOT EXISTS plan", all_sql)
        self.assertIn("ALTER TABLE subscriptions ADD COLUMN IF NOT EXISTS status", all_sql)
        self.assertIn("ALTER TABLE subscriptions ADD COLUMN IF NOT EXISTS expiry_date", all_sql)

    def test_alter_is_idempotent(self) -> None:
        """Running migration twice must not fail — ALTER uses IF NOT EXISTS."""
        from backend.migrations.migration_001_multitenancy import run
        conn = RecordingConnection()
        run(conn)
        run(conn)
        alter_stmts = [q for q, _ in conn.executed if q.startswith("ALTER TABLE")]
        self.assertTrue(len(alter_stmts) >= 20, "Expected ALTER stmts from both runs")
        for stmt in alter_stmts:
            self.assertIn("IF NOT EXISTS", stmt)

    def test_migration_still_does_not_commit(self) -> None:
        """Even with ALTER statements, the migration must not commit."""
        from backend.migrations.migration_001_multitenancy import run
        conn = RecordingConnection()
        run(conn)
        self.assertEqual(conn.commit_count, 0)

    def test_alter_runs_before_index_and_seed(self) -> None:
        """ALTER columns must execute BEFORE CREATE INDEX and INSERT (prevents drift failure)."""
        from backend.migrations.migration_001_multitenancy import run
        conn = RecordingConnection()
        run(conn)
        sqls = [q for q, _ in conn.executed]

        last_alter = max(
            i for i, q in enumerate(sqls) if q.startswith("ALTER TABLE")
        )
        first_index = next(
            i for i, q in enumerate(sqls) if "CREATE INDEX" in q
        )
        first_insert = next(
            i for i, q in enumerate(sqls) if q.startswith("INSERT INTO organizations")
        )
        self.assertLess(last_alter, first_index,
                        "All ALTERs must finish before CREATE INDEX")
        self.assertLess(last_alter, first_insert,
                        "All ALTERs must finish before INSERT seed data")


if __name__ == "__main__":
    unittest.main()
