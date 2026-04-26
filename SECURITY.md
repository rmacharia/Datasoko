# SECURITY.md

## Internal Admin Security Notes

### Auth
- `/admin/*` endpoints require `Authorization: Bearer <ADMIN_TOKEN>`.
- Missing or invalid admin token returns `401`.

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

### Operational Guidance
- Keep `BACKEND_CORS_ORIGINS` restrictive by default.
- Rotate `ADMIN_TOKEN` regularly and avoid sharing in chat/log channels.
