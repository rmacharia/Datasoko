# SECURITY.md

## Internal Admin Security Notes

### Auth
- JWT auth is required for normal UI use. `JWT_SECRET` must be configured; startup fails closed when it is missing.
- `ADMIN_TOKEN` remains a legacy/service credential and is treated as a platform `super_admin` identity where accepted.
- Role taxonomy:
  - `super_admin`: platform-wide, no tenant assignment.
  - `admin`: organization-scoped tenant admin.
  - `sme_user`: organization and business scoped.
- Platform users pass `X-Organization-Id` and optionally `X-Business-Id` for tenant-scoped operations.
- Missing or invalid credentials return `401`; valid credentials without permission return `403`.
- `ALLOW_BOOTSTRAP_ADMIN=true` should only be enabled during controlled first-admin setup.

### Secrets Handling
- Secrets should be provided via environment variables in production.
- Settings UI accepts secret updates as write-only fields.
- API never returns raw secret values after save; it only returns `has_*` flags.
- Backend avoids logging tokens and phone numbers; WhatsApp test responses are summarized/redacted.
- Secret values persisted in database are encrypted-at-rest using keyed symmetric encryption.

### Data Exposure Rules
- Admin UI never renders raw transaction rows.
- Metrics/report rendering is deterministic and backend-derived only.
- PII must not be displayed in UI or API debug payloads.
- LLM narrator receives only structured metrics and business profile context, never raw transactional rows.
- Analytics and report endpoints enforce organization/business access before reading tenant data.

### Operational Guidance
- Keep `BACKEND_CORS_ORIGINS` restrictive by default.
- Rotate `ADMIN_TOKEN` regularly and avoid sharing in chat/log channels.
- Rotate `JWT_SECRET` with awareness that existing sessions will be invalidated.
- Enable `RUN_SCHEDULER=true` on only one backend instance unless scheduling is moved to a dedicated worker.
