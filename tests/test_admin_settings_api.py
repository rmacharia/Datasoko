from __future__ import annotations

import os
import sys
import types
import unittest
from unittest.mock import patch

if "pydantic" not in sys.modules:
    class _BaseModel:
        def __init__(self, **kwargs):
            for key, value in kwargs.items():
                setattr(self, key, value)

        def model_dump(self, mode=None, exclude_none=False):  # noqa: ARG002
            payload = dict(self.__dict__)
            if exclude_none:
                payload = {k: v for k, v in payload.items() if v is not None}
            return payload

    def _field(*args, **kwargs):  # noqa: ARG001, ANN001
        return None

    sys.modules["pydantic"] = types.SimpleNamespace(BaseModel=_BaseModel, Field=_field)

if "fastapi" not in sys.modules:
    class _HTTPException(Exception):
        def __init__(self, status_code: int, detail: str) -> None:
            super().__init__(detail)
            self.status_code = status_code
            self.detail = detail

    class _FastAPI:
        def __init__(self, *args, **kwargs) -> None:  # noqa: ARG002, ANN001
            return None

        def get(self, *args, **kwargs):  # noqa: ARG002, ANN001
            def _decorator(fn):
                return fn

            return _decorator

        def post(self, *args, **kwargs):  # noqa: ARG002, ANN001
            def _decorator(fn):
                return fn

            return _decorator

        def put(self, *args, **kwargs):  # noqa: ARG002, ANN001
            def _decorator(fn):
                return fn

            return _decorator

        def add_middleware(self, *args, **kwargs) -> None:  # noqa: ARG002, ANN001
            return None

    def _identity(*args, **kwargs):  # noqa: ARG001, ANN001
        return None

    sys.modules["fastapi"] = types.SimpleNamespace(
        Depends=_identity,
        FastAPI=_FastAPI,
        File=_identity,
        Form=_identity,
        Header=_identity,
        HTTPException=_HTTPException,
        UploadFile=object,
    )
    sys.modules["fastapi.middleware"] = types.SimpleNamespace()
    sys.modules["fastapi.middleware.cors"] = types.SimpleNamespace(CORSMiddleware=object)

from backend.admin_settings_store import SETTINGS_STORE, AdminSettingsStore, decrypt_secret, default_non_secret_settings, encrypt_secret
from backend.main import (
    AdminSettingsUpdateRequest,
    AiNarratorSettingsUpdate,
    OperationalSettingsUpdate,
    WhatsAppSettingsUpdate,
    _require_admin_token,
    _settings_response,
    admin_update_settings,
)


def _collect_keys(value: object, sink: set[str]) -> None:
    if isinstance(value, dict):
        for key, nested in value.items():
            sink.add(str(key))
            _collect_keys(nested, sink)
    elif isinstance(value, list):
        for nested in value:
            _collect_keys(nested, sink)


class AdminSettingsApiTests(unittest.TestCase):
    def setUp(self) -> None:
        os.environ["ADMIN_TOKEN"] = "test-admin-token"
        SETTINGS_STORE._memory_non_secret = default_non_secret_settings()
        SETTINGS_STORE._secret_overrides = {}

    def test_require_admin_token_rejects_missing_and_invalid(self) -> None:
        with self.assertRaises(Exception) as ctx_missing:
            _require_admin_token(None)
        self.assertEqual(getattr(ctx_missing.exception, "status_code", None), 401)

        with self.assertRaises(Exception) as ctx_invalid:
            _require_admin_token("Bearer wrong-token")
        self.assertEqual(getattr(ctx_invalid.exception, "status_code", None), 401)

    def test_update_settings_persists_non_secret_values_and_never_leaks_secret_fields(self) -> None:
        payload = AdminSettingsUpdateRequest(
            operational=OperationalSettingsUpdate(default_business_id="biz_qa"),
            ai=AiNarratorSettingsUpdate(provider="openai", api_key="sk-test-secret"),
            whatsapp=WhatsAppSettingsUpdate(
                provider="meta_cloud_api",
                phone_number_id="123456789",
                access_token="wa-secret-token",
                webhook_verify_token="verify-secret",
            ),
        )
        response = admin_update_settings(payload, None)

        self.assertEqual(response["operational"]["default_business_id"], "biz_qa")
        self.assertTrue(response["ai"]["has_api_key"])
        self.assertTrue(response["whatsapp"]["has_access_token"])
        self.assertTrue(response["whatsapp"]["has_webhook_verify_token"])

        keys: set[str] = set()
        _collect_keys(response, keys)
        self.assertNotIn("api_key", keys)
        self.assertNotIn("access_token", keys)
        self.assertNotIn("webhook_verify_token", keys)

        fetched = _settings_response()
        self.assertEqual(fetched["operational"]["default_business_id"], "biz_qa")
        self.assertTrue(fetched["ai"]["has_api_key"])

    def test_secret_crypto_roundtrip(self) -> None:
        secret = "super-secret-value"
        encrypted = encrypt_secret(secret)
        self.assertNotEqual(encrypted, secret)
        self.assertEqual(decrypt_secret(encrypted), secret)

    def test_secret_is_encrypted_when_persisted(self) -> None:
        class _Cursor:
            def __init__(self, conn):
                self._conn = conn
                self._last_key = None

            def __enter__(self):
                return self

            def __exit__(self, exc_type, exc, tb):  # noqa: ANN001
                return None

            def execute(self, query, params=None):  # noqa: ANN001
                q = str(query).strip().upper()
                if "UPSERT_SECRET" in q or ("INSERT INTO ADMIN_SECRET_SETTINGS" in q and params):
                    self._conn.secrets[str(params[0])] = str(params[1])
                elif "SELECT ENCRYPTED_VALUE" in q and params:
                    self._last_key = str(params[0])
                elif "DELETE FROM ADMIN_SECRET_SETTINGS" in q and params:
                    self._conn.secrets.pop(str(params[0]), None)

            def fetchone(self):
                if self._last_key is None:
                    return None
                value = self._conn.secrets.get(self._last_key)
                return (value,) if value else None

        class _Conn:
            def __init__(self):
                self.secrets = {}

            def cursor(self):
                return _Cursor(self)

            def commit(self):
                return None

            def rollback(self):
                return None

            def close(self):
                return None

        conn = _Conn()
        store = AdminSettingsStore()
        with patch("backend.admin_settings_store.create_postgres_connection", return_value=conn):
            store.set_secret("whatsapp_access_token", "wa-token-123")
            persisted = conn.secrets.get("whatsapp_access_token")
            self.assertIsNotNone(persisted)
            self.assertNotEqual(persisted, "wa-token-123")
            self.assertEqual(store.get_secret("whatsapp_access_token"), "wa-token-123")


if __name__ == "__main__":
    unittest.main()
