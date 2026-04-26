from __future__ import annotations

import base64
import hashlib
import hmac
import json
import os
import secrets
from copy import deepcopy
from typing import Any

from backend.storage import create_postgres_connection

SETTINGS_ROW_KEY = "global"

CREATE_SETTINGS_TABLE_SQL = """
CREATE TABLE IF NOT EXISTS admin_settings (
    setting_key TEXT PRIMARY KEY,
    value_json JSONB NOT NULL,
    updated_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
)
"""

SELECT_SETTINGS_SQL = """
SELECT value_json
FROM admin_settings
WHERE setting_key = %s
"""

UPSERT_SETTINGS_SQL = """
INSERT INTO admin_settings (setting_key, value_json, updated_at)
VALUES (%s, %s::jsonb, NOW())
ON CONFLICT (setting_key)
DO UPDATE SET value_json = EXCLUDED.value_json, updated_at = NOW()
"""

CREATE_SECRET_TABLE_SQL = """
CREATE TABLE IF NOT EXISTS admin_secret_settings (
    secret_key TEXT PRIMARY KEY,
    encrypted_value TEXT NOT NULL,
    updated_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
)
"""

SELECT_SECRET_SQL = """
SELECT encrypted_value
FROM admin_secret_settings
WHERE secret_key = %s
"""

UPSERT_SECRET_SQL = """
INSERT INTO admin_secret_settings (secret_key, encrypted_value, updated_at)
VALUES (%s, %s, NOW())
ON CONFLICT (secret_key)
DO UPDATE SET encrypted_value = EXCLUDED.encrypted_value, updated_at = NOW()
"""

DELETE_SECRET_SQL = """
DELETE FROM admin_secret_settings
WHERE secret_key = %s
"""

SECRET_ENV_KEYS: dict[str, list[str]] = {
    "ai_api_key": ["AZURE_OPENAI_API_KEY", "OPENAI_API_KEY"],
    "whatsapp_access_token": ["WHATSAPP_ACCESS_TOKEN"],
    "whatsapp_verify_token": ["WHATSAPP_VERIFY_TOKEN"],
}


def _to_bool(value: str | None, fallback: bool) -> bool:
    if value is None:
        return fallback
    return value.strip().lower() in {"1", "true", "yes", "on"}


def _to_int(value: str | None, fallback: int, *, minimum: int, maximum: int) -> int:
    if value is None:
        return fallback
    try:
        parsed = int(value)
    except ValueError:
        return fallback
    return min(max(parsed, minimum), maximum)


def _to_float(value: str | None, fallback: float, *, minimum: float, maximum: float) -> float:
    if value is None:
        return fallback
    try:
        parsed = float(value)
    except ValueError:
        return fallback
    return min(max(parsed, minimum), maximum)


def _ai_provider_default() -> str:
    if any(
        os.getenv(key)
        for key in (
            "AZURE_OPENAI_ENDPOINT",
            "AZURE_OPENAI_API_KEY",
            "AZURE_OPENAI_DEPLOYMENT",
        )
    ):
        return "azure_openai"
    return "openai"


def default_non_secret_settings() -> dict[str, Any]:
    return {
        "operational": {
            "default_business_id": os.getenv("DEFAULT_BUSINESS_ID", "biz_001"),
            "default_currency": os.getenv("DEFAULT_CURRENCY", "KES"),
            "timezone": os.getenv("BUSINESS_TIMEZONE", "Africa/Nairobi"),
            "report_schedule_day": os.getenv("REPORT_SCHEDULE_DAY", "Friday"),
            "report_schedule_time": os.getenv("REPORT_SCHEDULE_TIME", "18:00"),
        },
        "ai": {
            "provider": os.getenv("AI_PROVIDER", _ai_provider_default()),
            "model": os.getenv("AI_MODEL") or os.getenv("AZURE_OPENAI_DEPLOYMENT") or os.getenv("OPENAI_MODEL") or "gpt-4.1-mini",
            "temperature": _to_float(os.getenv("AI_TEMPERATURE"), 0.2, minimum=0.0, maximum=1.0),
            "max_output_tokens": _to_int(os.getenv("AI_MAX_OUTPUT_TOKENS"), 700, minimum=64, maximum=4096),
            "strict_json_only": _to_bool(os.getenv("AI_STRICT_JSON_ONLY"), True),
            "metrics_only_fallback": _to_bool(os.getenv("AI_METRICS_ONLY_FALLBACK"), True),
            "azure_endpoint": os.getenv("AZURE_OPENAI_ENDPOINT"),
            "azure_deployment": os.getenv("AZURE_OPENAI_DEPLOYMENT"),
        },
        "whatsapp": {
            "provider": os.getenv("WHATSAPP_PROVIDER", "meta_cloud_api"),
            "phone_number_id": os.getenv("WHATSAPP_PHONE_NUMBER_ID"),
            "business_account_id": os.getenv("WHATSAPP_BUSINESS_ACCOUNT_ID"),
            "sender_display_name": os.getenv("WHATSAPP_SENDER_DISPLAY_NAME"),
            "webhook_callback_url": os.getenv("WHATSAPP_WEBHOOK_URL"),
        },
    }


def deep_merge(base: dict[str, Any], update: dict[str, Any]) -> dict[str, Any]:
    merged = deepcopy(base)
    for key, value in update.items():
        if isinstance(value, dict) and isinstance(merged.get(key), dict):
            merged[key] = deep_merge(merged[key], value)
        else:
            merged[key] = value
    return merged


def _keystream(key: bytes, nonce: bytes, length: int) -> bytes:
    output = bytearray()
    counter = 0
    while len(output) < length:
        block = hashlib.sha256(key + nonce + counter.to_bytes(4, "big")).digest()
        output.extend(block)
        counter += 1
    return bytes(output[:length])


def _encryption_key_bytes() -> bytes:
    raw = os.getenv("SETTINGS_ENCRYPTION_KEY") or os.getenv("ADMIN_TOKEN") or "datasoko-internal-dev-key"
    return hashlib.sha256(raw.encode("utf-8")).digest()


def encrypt_secret(plaintext: str) -> str:
    key = _encryption_key_bytes()
    nonce = secrets.token_bytes(16)
    plain_bytes = plaintext.encode("utf-8")
    stream = _keystream(key, nonce, len(plain_bytes))
    cipher = bytes(a ^ b for a, b in zip(plain_bytes, stream))
    mac = hmac.new(key, nonce + cipher, hashlib.sha256).digest()
    packed = b"v1" + nonce + mac + cipher
    return base64.urlsafe_b64encode(packed).decode("utf-8")


def decrypt_secret(token: str) -> str | None:
    try:
        packed = base64.urlsafe_b64decode(token.encode("utf-8"))
        if len(packed) < 2 + 16 + 32 or packed[:2] != b"v1":
            return None
        nonce = packed[2:18]
        mac = packed[18:50]
        cipher = packed[50:]
        key = _encryption_key_bytes()
        expected = hmac.new(key, nonce + cipher, hashlib.sha256).digest()
        if not hmac.compare_digest(mac, expected):
            return None
        stream = _keystream(key, nonce, len(cipher))
        plain_bytes = bytes(a ^ b for a, b in zip(cipher, stream))
        return plain_bytes.decode("utf-8")
    except Exception:
        return None


class AdminSettingsStore:
    def __init__(self) -> None:
        self._memory_non_secret: dict[str, Any] = default_non_secret_settings()
        self._secret_overrides: dict[str, str] = {}

    def _load_from_postgres(self) -> dict[str, Any] | None:
        connection = None
        try:
            connection = create_postgres_connection()
            with connection.cursor() as cursor:
                cursor.execute(CREATE_SETTINGS_TABLE_SQL)
                cursor.execute(SELECT_SETTINGS_SQL, (SETTINGS_ROW_KEY,))
                row = cursor.fetchone()
            connection.commit()
            if not row:
                return None
            value = row[0]
            if isinstance(value, str):
                payload = json.loads(value)
            else:
                payload = value
            if isinstance(payload, dict):
                return payload
            return None
        except Exception:
            if connection is not None:
                try:
                    connection.rollback()
                except Exception:
                    pass
            return None
        finally:
            if connection is not None:
                try:
                    connection.close()
                except Exception:
                    pass

    def _save_to_postgres(self, payload: dict[str, Any]) -> bool:
        connection = None
        try:
            connection = create_postgres_connection()
            with connection.cursor() as cursor:
                cursor.execute(CREATE_SETTINGS_TABLE_SQL)
                cursor.execute(UPSERT_SETTINGS_SQL, (SETTINGS_ROW_KEY, json.dumps(payload)))
            connection.commit()
            return True
        except Exception:
            if connection is not None:
                try:
                    connection.rollback()
                except Exception:
                    pass
            return False
        finally:
            if connection is not None:
                try:
                    connection.close()
                except Exception:
                    pass

    def _load_secret_from_postgres(self, key: str) -> str | None:
        connection = None
        try:
            connection = create_postgres_connection()
            with connection.cursor() as cursor:
                cursor.execute(CREATE_SECRET_TABLE_SQL)
                cursor.execute(SELECT_SECRET_SQL, (key,))
                row = cursor.fetchone()
            connection.commit()
            if not row:
                return None
            encrypted_value = row[0]
            if not isinstance(encrypted_value, str):
                return None
            return decrypt_secret(encrypted_value)
        except Exception:
            if connection is not None:
                try:
                    connection.rollback()
                except Exception:
                    pass
            return None
        finally:
            if connection is not None:
                try:
                    connection.close()
                except Exception:
                    pass

    def _save_secret_to_postgres(self, key: str, value: str) -> bool:
        connection = None
        try:
            encrypted = encrypt_secret(value)
            connection = create_postgres_connection()
            with connection.cursor() as cursor:
                cursor.execute(CREATE_SECRET_TABLE_SQL)
                cursor.execute(UPSERT_SECRET_SQL, (key, encrypted))
            connection.commit()
            return True
        except Exception:
            if connection is not None:
                try:
                    connection.rollback()
                except Exception:
                    pass
            return False
        finally:
            if connection is not None:
                try:
                    connection.close()
                except Exception:
                    pass

    def _delete_secret_in_postgres(self, key: str) -> bool:
        connection = None
        try:
            connection = create_postgres_connection()
            with connection.cursor() as cursor:
                cursor.execute(CREATE_SECRET_TABLE_SQL)
                cursor.execute(DELETE_SECRET_SQL, (key,))
            connection.commit()
            return True
        except Exception:
            if connection is not None:
                try:
                    connection.rollback()
                except Exception:
                    pass
            return False
        finally:
            if connection is not None:
                try:
                    connection.close()
                except Exception:
                    pass

    def get_non_secret_settings(self) -> dict[str, Any]:
        defaults = default_non_secret_settings()
        postgres_payload = self._load_from_postgres()
        if isinstance(postgres_payload, dict):
            merged = deep_merge(defaults, postgres_payload)
            self._memory_non_secret = merged
            return merged
        self._memory_non_secret = deep_merge(defaults, self._memory_non_secret)
        return deepcopy(self._memory_non_secret)

    def update_non_secret_settings(self, update: dict[str, Any]) -> dict[str, Any]:
        current = self.get_non_secret_settings()
        merged = deep_merge(current, update)
        if self._save_to_postgres(merged):
            self._memory_non_secret = merged
            return deepcopy(merged)
        self._memory_non_secret = merged
        return deepcopy(merged)

    def set_secret(self, key: str, value: str | None) -> None:
        if value is None:
            return
        trimmed = value.strip()
        if not trimmed:
            self._secret_overrides.pop(key, None)
            self._delete_secret_in_postgres(key)
            return
        if not self._save_secret_to_postgres(key, trimmed):
            self._secret_overrides[key] = trimmed
            return
        self._secret_overrides[key] = trimmed

    def get_secret(self, key: str) -> str | None:
        override = self._secret_overrides.get(key)
        if override:
            return override

        persisted = self._load_secret_from_postgres(key)
        if persisted:
            self._secret_overrides[key] = persisted
            return persisted

        for env_key in SECRET_ENV_KEYS.get(key, []):
            value = os.getenv(env_key)
            if value:
                return value
        return None

    def has_secret(self, key: str) -> bool:
        return bool(self.get_secret(key))


SETTINGS_STORE = AdminSettingsStore()
