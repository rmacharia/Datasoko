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

    try:
        import psycopg  # type: ignore

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
        pass

    try:
        import psycopg2  # type: ignore

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
    except ImportError as exc:
        raise RuntimeError(
            "PostgreSQL driver not installed. Install `psycopg` or `psycopg2-binary`."
        ) from exc
