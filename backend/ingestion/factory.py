from __future__ import annotations

from dataclasses import dataclass
from typing import Any

from backend.storage.postgres_connection import create_postgres_connection
from backend.storage.postgres_ingestion_store import PostgresIngestionStore

from .service import IngestionService


@dataclass
class IngestionRuntime:
    service: IngestionService
    connection: Any

    def close(self) -> None:
        self.connection.close()


def create_ingestion_runtime(*, ensure_table: bool = True) -> IngestionRuntime:
    connection = create_postgres_connection()
    store = PostgresIngestionStore(connection)
    if ensure_table:
        store.ensure_table()

    service = IngestionService(store=store)
    return IngestionRuntime(service=service, connection=connection)
