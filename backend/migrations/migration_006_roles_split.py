from __future__ import annotations

import logging
from typing import Any

logger = logging.getLogger(__name__)

# Role taxonomy split:
#   old: 'admin' | 'sme'
#   new: 'super_admin' | 'admin' | 'sme_user'
#
# The de-facto semantics of the pre-split 'admin' role was platform-wide
# (it guards /admin/* endpoints and bootstraps with no real tenant scope),
# so those rows become 'super_admin'. The new 'admin' role is reserved for
# future org-level tenant admins and is intentionally unused by this
# migration — it is created by API flows, not by backfill.

_DROP_CHECK = "ALTER TABLE users DROP CONSTRAINT IF EXISTS users_role_check"

# Widen the CHECK first so the subsequent UPDATEs can write the new values
# without tripping the old constraint. We install the final (narrow)
# constraint at the end.
_WIDEN_CHECK = """
ALTER TABLE users
ADD CONSTRAINT users_role_check
CHECK (role IN ('admin', 'sme', 'super_admin', 'sme_user'))
""".strip()

_RENAME_ADMIN = "UPDATE users SET role = 'super_admin' WHERE role = 'admin'"
_RENAME_SME = "UPDATE users SET role = 'sme_user' WHERE role = 'sme'"

# Platform users own no tenant, so clear their organization_id. The column
# is NULLABLE on fresh schemas; on older deployments the NOT NULL default
# set in migration_004 still holds — we relax it here.
_RELAX_ORG_NOT_NULL = "ALTER TABLE users ALTER COLUMN organization_id DROP NOT NULL"
_CLEAR_PLATFORM_ORG = "UPDATE users SET organization_id = NULL WHERE role = 'super_admin'"

_FINAL_CHECK_DROP = "ALTER TABLE users DROP CONSTRAINT IF EXISTS users_role_check"
_FINAL_CHECK_ADD = """
ALTER TABLE users
ADD CONSTRAINT users_role_check
CHECK (role IN ('super_admin', 'admin', 'sme_user'))
""".strip()


def run(connection: Any) -> None:
    with connection.cursor() as cur:
        cur.execute(_DROP_CHECK)
        cur.execute(_WIDEN_CHECK)
        logger.info("[migration_006] widened role check to accept old + new roles")

        cur.execute(_RENAME_ADMIN)
        cur.execute(_RENAME_SME)
        logger.info("[migration_006] renamed legacy admin→super_admin, sme→sme_user")

        cur.execute(_RELAX_ORG_NOT_NULL)
        cur.execute(_CLEAR_PLATFORM_ORG)
        logger.info("[migration_006] cleared organization_id for super_admin users")

        cur.execute(_FINAL_CHECK_DROP)
        cur.execute(_FINAL_CHECK_ADD)
        logger.info("[migration_006] installed final role check (super_admin|admin|sme_user)")
