from __future__ import annotations

import importlib.util
import logging
from pathlib import Path
from typing import Any

logger = logging.getLogger(__name__)

_ENSURE_TRACKING_SQL = """
CREATE TABLE IF NOT EXISTS schema_migrations (
    migration_id  TEXT PRIMARY KEY,
    applied_at    TIMESTAMPTZ DEFAULT NOW()
)
""".strip()

_CHECK_APPLIED_SQL = "SELECT 1 FROM schema_migrations WHERE migration_id = %s"
_RECORD_APPLIED_SQL = "INSERT INTO schema_migrations (migration_id) VALUES (%s)"


def _discover_migrations() -> list[Path]:
    return sorted(Path(__file__).parent.glob("migration_00*.py"))


def _load_module(path: Path) -> Any:
    spec = importlib.util.spec_from_file_location(path.stem, path)
    mod = importlib.util.module_from_spec(spec)  # type: ignore[arg-type]
    spec.loader.exec_module(mod)  # type: ignore[union-attr]
    return mod


def _log(msg: str, *args: Any) -> None:
    formatted = msg % args if args else msg
    logger.info(formatted)
    print(formatted, flush=True)


def run_migrations(connection: Any) -> None:
    _log("[migration] ensuring schema_migrations tracking table exists")
    with connection.cursor() as cur:
        cur.execute(_ENSURE_TRACKING_SQL)
    connection.commit()

    paths = _discover_migrations()
    filenames = [p.name for p in paths]
    _log("[migration] found: %s", ", ".join(filenames) if filenames else "(none)")

    if not paths:
        _log("[migration] WARNING: no migration files found — nothing to apply")
        return

    applied = 0
    skipped = 0

    for path in paths:
        migration_id = path.stem
        with connection.cursor() as cur:
            cur.execute(_CHECK_APPLIED_SQL, (migration_id,))
            already = cur.fetchone()

        if already is not None:
            _log("[migration] skipping %s (already applied)", migration_id)
            skipped += 1
            continue

        _log("[migration] applying %s", migration_id)
        mod = _load_module(path)
        try:
            mod.run(connection)
            with connection.cursor() as cur:
                cur.execute(_RECORD_APPLIED_SQL, (migration_id,))
            connection.commit()
            _log("[migration] applied %s successfully", migration_id)
            applied += 1
        except Exception as exc:
            connection.rollback()
            msg = "[migration] FAILED %s — rolled back: %s" % (migration_id, exc)
            logger.error(msg)
            print(msg, flush=True)
            raise

    _log("[migration] done — applied=%d skipped=%d total=%d", applied, skipped, len(paths))
