                                                                                                                                                                                                 backend/storage/postgres_connection.py                                                                                                                                                                                                                         
from __future__ import annotations

import os
from dataclasses import dataclass
from typing import Any


@dataclass(frozen=True)
class PostgresConnectionConfig:
    dsn: str | None
    host: str
    port: int
    database: str
    user: str
    password: str
    sslmode: str


def load_postgres_config_from_env() -> PostgresConnectionConfig:
    return PostgresConnectionConfig(
        dsn=os.getenv("DATABASE_URL"),
        host=os.getenv("PGHOST", "localhost"),
        port=int(os.getenv("PGPORT", "5432")),
        database=os.getenv("PGDATABASE", "datasoko"),
        user=os.getenv("PGUSER", "postgres"),
        password=os.getenv("PGPASSWORD", "postgres"),
        sslmode=os.getenv("PGSSLMODE", "prefer"),
    )


def create_postgres_connection(config: PostgresConnectionConfig | None = None) -> Any:
    cfg = config or load_postgres_config_from_env()

    dsn = os.getenv("DATABASE_URL")

    # ✅ PRIORITIZE DATABASE_URL
    if dsn:
        try:
            import psycopg
            return psycopg.connect(dsn)
        except ImportError:
            import psycopg2
            return psycopg2.connect(dsn)

    # 🔁 FALLBACK (old logic)
    cfg = config or load_postgres_config_from_env()

    try:
        import psycopg
        if cfg.dsn:
            return psycopg.connect(cfg.dsn)
        return psycopg.connect(
            host=cfg.host,
            port=cfg.port,
            dbname=cfg.database,
            user=cfg.user,
            password=cfg.password,
            sslmode=cfg.sslmode,
        )
    except ImportError:
        import psycopg2
        if cfg.dsn:
            return psycopg2.connect(cfg.dsn)
        return psycopg2.connect(
            host=cfg.host,
            port=cfg.port,
            dbname=cfg.database,
            user=cfg.user,
            password=cfg.password,
            sslmode=cfg.sslmode,
        )
