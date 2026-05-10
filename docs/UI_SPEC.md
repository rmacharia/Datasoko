# UI_SPEC.md

## Internal Admin UI (MVP) - New Section

### Scope
- This UI is internal-only for operations/admin workflows.
- SME-facing experience remains WhatsApp-first; this UI does not replace that channel.

### Vertical Slice Implemented
- First-admin setup at `/setup` using `/auth/status` and `/auth/bootstrap`.
- Login gate at `/login` storing bearer token in memory and optional `sessionStorage`.
- Role-aware routing after login:
  - `super_admin` lands in platform admin context.
  - `admin` lands in tenant operations.
  - `sme_user` is scoped to the assigned business.
- Overview page at `/` with text-first status cards from:
  - `GET /admin/status` (health, version, db connectivity, last run)
  - analytics widgets from `/analytics/*`
- Upload + Validate page at `/upload` with:
  - `POST /admin/upload/weekly` multipart upload
  - progress indicator, quality summary, schema fields, and copyable actionable errors
- Typed fetch client with timeout/error normalization.
- Platform admin pages under `/admin` for organizations, businesses, and users.
- Tenant user management at `/users`.
- Reports, jobs, schedules, settings, and WhatsApp preview surfaces.

### Guardrails
- UI never computes business metrics; it only renders backend responses.
- No raw transaction rows are shown in this slice.
- No PII rendering or PII logging in client components.

### Tenant Context
- Platform admins select an organization/business context; API requests include `X-Organization-Id` and optionally `X-Business-Id`.
- Tenant admins and SME users use JWT-scoped organization/business context.
- Cross-tenant access failures must be shown as actionable auth/context errors, not generic network failures.

## Settings Console - New Section

### Route
- `GET/PUT /admin/settings` for internal defaults + narrator + WhatsApp delivery configuration.
- `POST /admin/whatsapp/test-send` for safe test message delivery checks.

### UI Sections
- Appearance:
  - Theme preference `system|dark|light` (localStorage, client-side only)
  - Enhanced Mode toggle (localStorage, reduced-motion aware)
- Defaults:
  - `default_business_id`, `default_currency`, `timezone`, reporting schedule day/time
- AI Narrator:
  - provider/model/temperature/max tokens and deterministic guardrails flags
- WhatsApp Delivery:
  - provider, IDs, callback URL, and write-only secrets
  - Test Send panel

### Data Safety Contract
- Secrets are write-only from UI inputs and are never returned by API.
- API only returns booleans for secret presence (e.g., `has_access_token`).
- Settings and report screens never render raw transaction rows or PII.
- Secrets persisted server-side are encrypted-at-rest before database storage.

### Narrator Runtime
- `/admin/reports` now attempts LLM narration using server-side AI settings.
- Narration input is generated from deterministic `metrics_json` only with strict JSON guardrails.
- If provider call fails or keys are missing, system falls back to metrics-only narration output.

## Scheduling and Analytics - New Section

### Routes
- `/reports` previews deterministic metrics and WhatsApp-ready report text.
- `/jobs` shows generated report jobs and statuses.
- `/settings` manages operational defaults, AI, WhatsApp, schedules, and billing-related context.
- `/admin/*` pages are platform-only.

### Data Sources
- `/analytics/metrics`, `/analytics/uploads`, `/analytics/whatsapp`, `/analytics/activity`, and `/analytics/costs`.
- `/schedules` CRUD for scheduled report delivery.
