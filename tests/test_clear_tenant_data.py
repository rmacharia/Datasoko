from __future__ import annotations

import unittest

from backend.scripts.clear_tenant_data import cleanup_database


class FakeCursor:
    def __init__(self) -> None:
        self.queries: list[tuple[str, tuple[object, ...] | None]] = []

    def __enter__(self) -> "FakeCursor":
        return self

    def __exit__(self, exc_type, exc, tb) -> None:
        return None

    def execute(self, query: str, params: tuple[object, ...] | None = None) -> None:
        self.queries.append((query, params))

    def fetchall(self) -> list[tuple[str]]:
        return [
            ("users",),
            ("organizations",),
            ("businesses",),
            ("subscriptions",),
            ("ingestion_weekly_payloads",),
            ("report_schedules",),
            ("activity_log",),
            ("whatsapp_message_log",),
        ]

    def fetchone(self) -> tuple[int]:
        return (3,)


class FakeConnection:
    def __init__(self) -> None:
        self.cursor_obj = FakeCursor()
        self.commits = 0
        self.rollbacks = 0

    def cursor(self) -> FakeCursor:
        return self.cursor_obj

    def commit(self) -> None:
        self.commits += 1

    def rollback(self) -> None:
        self.rollbacks += 1


class ClearTenantDataTests(unittest.TestCase):
    def test_deletes_tenant_data_and_preserves_super_admin_users(self) -> None:
        connection = FakeConnection()

        result = cleanup_database(connection, dry_run=False)

        executed_sql = "\n".join(query for query, _ in connection.cursor_obj.queries)
        self.assertIn("DELETE FROM users WHERE role <> %s", executed_sql)
        self.assertNotIn("DELETE FROM users", executed_sql.replace("DELETE FROM users WHERE role <> %s", ""))
        self.assertIn("DELETE FROM organizations", executed_sql)
        self.assertIn("DELETE FROM businesses", executed_sql)
        self.assertEqual(connection.commits, 1)
        self.assertEqual(connection.rollbacks, 0)
        self.assertFalse(result.dry_run)


if __name__ == "__main__":
    unittest.main()
