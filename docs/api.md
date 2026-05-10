# API Reference

Base URL: `http://localhost:8000` (dev) or `https://datasoko-api.azurewebsites.net` (prod)

## Authentication

Most application endpoints require `Authorization: Bearer <token>`.

- JWTs are issued by `/auth/login`, `/auth/bootstrap`, and `/auth/register`.
- `ADMIN_TOKEN` is still accepted by legacy/platform routes as a service-level `super_admin` identity.
- `super_admin` can access platform routes and can pass `X-Organization-Id` / `X-Business-Id` to choose tenant context.
- `admin` is scoped to one organization.
- `sme_user` is scoped to one organization and business.

## Auth Endpoints

### GET /auth/status

Returns whether first-admin setup is available.

### POST /auth/bootstrap

Creates the first platform `super_admin`. Requires `ALLOW_BOOTSTRAP_ADMIN=true` and zero existing users.

**Request:**
```json
{
  "email": "owner@example.com",
  "password": "change-me"
}
```

### POST /auth/login

**Request:**
```json
{
  "email": "owner@example.com",
  "password": "change-me"
}
```

**Response:**
```json
{
  "access_token": "jwt",
  "token_type": "bearer",
  "user": {
    "id": "user_id",
    "email": "owner@example.com",
    "role": "super_admin",
    "organization_id": null,
    "business_id": null
  }
}
```

### GET /auth/me

Returns the authenticated user from the bearer token.

### POST /auth/register

Creates users. Public registration is limited to the first `super_admin` path when bootstrap is enabled; otherwise a platform admin token is required.

---

## Tenant Setup Endpoints

### POST /onboard

Create a trial subscription for an organization. Requires `super_admin` or tenant `admin`.

**Request:**
```json
{
  "organization_id": "org_123",
  "name": "Mama Fua Laundry",
  "plan": "starter"
}
```

**Response (201):**
```json
{
  "organization_id": "org_123",
  "name": "Mama Fua Laundry",
  "plan": "starter",
  "status": "active",
  "expiry_date": "2026-06-03T12:00:00+00:00"
}
```

**Errors:**
- `409` — Organization already has an active subscription

---

### POST /businesses

Register a business under an organization.

**Request:**
```json
{
  "id": "biz_001",
  "organization_id": "org_123",
  "name": "Mama Fua Downtown",
  "whatsapp_phone": "+254712345678"
}
```

**Response (201):**
```json
{
  "id": "biz_001",
  "organization_id": "org_123",
  "name": "Mama Fua Downtown",
  "whatsapp_phone": "+254712345678",
  "created_at": "2026-05-04T10:00:00+00:00"
}
```

**Errors:**
- `400` — Organization does not exist
- `403` — Tenant user attempted cross-organization access
- `409` — Business ID already exists

---

### GET /businesses?organization_id=org_123

List businesses for an organization.

**Response (200):**
```json
{
  "organization_id": "org_123",
  "businesses": [
    {
      "id": "biz_001",
      "name": "Mama Fua Downtown",
      "whatsapp_phone": "+254712345678",
      "created_at": "2026-05-04T10:00:00+00:00"
    }
  ]
}
```

**Errors:**
- `404` — Organization not found

---

### GET /billing/current?organization_id=org_123

Get current billing status for an organization.

**Response (200):**
```json
{
  "organization_id": "org_123",
  "plan": "starter",
  "status": "active",
  "expiry_date": "2026-06-03T12:00:00+00:00",
  "active": true,
  "days_remaining": 30
}
```

**Errors:**
- `404` — Organization or subscription not found

---

## Platform Admin Endpoints

These require a `super_admin` JWT or legacy `ADMIN_TOKEN`.

### POST /admin/organizations

Create an organization and its first org admin.

**Request:**
```json
{
  "name": "Mama Fua Group",
  "organization_id": "mama_fua",
  "admin_email": "admin@mama-fua.example",
  "admin_password": "change-me"
}
```

### GET /admin/organizations

List organizations with user/business counts and subscription summary.

### GET /admin/businesses

List all businesses across organizations.

---

## User Management

### POST /users

Create a tenant user. `super_admin` may create `admin` or `sme_user`; org `admin` may create only `sme_user` inside its organization.

### GET /users

List users visible to the authenticated platform/org admin.

### PATCH /users/{user_id}

Update role, tenant assignment, business assignment, or active state.

### DELETE /users/{user_id}

Soft-disables a user by setting `is_active=false`.

---

## Operational Admin Endpoints

Operational endpoints use different guards:

- Platform diagnostics/settings endpoints require a `super_admin` JWT or legacy `ADMIN_TOKEN`.
- Tenant operations such as upload/report generation require `super_admin` or tenant `admin`.
- Platform users should pass `X-Organization-Id` for tenant-scoped operations.

### GET /admin/status

System health check with database diagnostics.

Requires `super_admin` or `ADMIN_TOKEN`.

**Response:**
```json
{
  "backend_health": "ok",
  "version": {
    "app_version": "0.1.0",
    "schema_version": "1.0",
    "normalizer_version": "1.0",
    "contract_version": "1.0"
  },
  "db": {
    "connected": true,
    "tables_exist": true,
    "columns_complete": true,
    "missing_columns": [],
    "error": null
  },
  "last_run": null
}
```

---

### POST /admin/upload/weekly

Upload Excel and/or M-Pesa files for a business week. Multipart form data.

Requires `super_admin` or tenant `admin`.

**Form Fields:**
- `business_id` (required)
- `week_start` (required, date)
- `week_end` (required, date)
- `business_currency` (optional, default: `KES`)
- `excel_file` (optional, file)
- `mpesa_file` (optional, file)

---

### GET /admin/reports

Generate a weekly report for a business.

Requires `super_admin` or tenant `admin`.

**Query Parameters:**
- `business_id` (required)
- `week_start`, `week_end` (required, dates)
- `business_name` (optional, default: `Your Business`)
- `sme_type` (optional, default: `retail`)
- `currency` (optional, default: `KES`)

---

### POST /admin/reports/generate

Queue a report generation job.

Requires `super_admin` or tenant `admin`.

**Request:**
```json
{
  "business_id": "biz_001",
  "week_start": "2026-04-28",
  "week_end": "2026-05-04"
}
```

**Response:**
```json
{
  "job_id": "abc123",
  "status": "completed"
}
```

---

### GET /admin/jobs/{job_id}

Check job status.

---

### GET /admin/settings

Get current admin settings (non-secret).

Requires `super_admin` or `ADMIN_TOKEN`.

---

### PUT /admin/settings

Update admin settings. Supports `operational`, `ai`, and `whatsapp` sections.

Requires `super_admin` or `ADMIN_TOKEN`.

---

### POST /admin/whatsapp/test-send

Send a test WhatsApp message.

Requires `super_admin` or `ADMIN_TOKEN`.

**Request:**
```json
{
  "to_phone": "+254712345678"
}
```

---

### POST /reports/send-test

Legacy Twilio WhatsApp test send. Requires `ADMIN_TOKEN` or `super_admin`.

**Request:**
```json
{
  "phone": "+254712345678"
}
```

---

## Analytics Endpoints

These require tenant context through JWT or platform headers.

| Endpoint | Purpose |
|---|---|
| `GET /analytics/metrics?business_id=biz_001` | Revenue, expense, profit trends and totals |
| `GET /analytics/uploads?business_id=biz_001` | Recent processed uploads |
| `GET /analytics/whatsapp?business_id=biz_001` | WhatsApp delivery count, last send, success rate |
| `GET /analytics/activity?business_id=biz_001` | Recent activity timeline |
| `GET /analytics/costs` | Organization-level WhatsApp cost summary |

---

## Schedule Endpoints

Schedules require `super_admin` or org `admin` for writes. `sme_user` can read only where tenant access is allowed.

| Endpoint | Purpose |
|---|---|
| `POST /schedules` | Create daily, weekly, or monthly report schedule |
| `GET /schedules` | List schedules for current organization |
| `PATCH /schedules/{schedule_id}` | Update schedule fields or active state |
| `DELETE /schedules/{schedule_id}` | Delete a schedule |

**Create request:**
```json
{
  "business_id": "biz_001",
  "frequency": "weekly",
  "time_of_day": "18:00",
  "day_of_week": 4,
  "start_date": "2026-05-01",
  "send_whatsapp": true
}
```

---

### GET /health

Simple health check. No auth required.

**Response:** `{"status": "ok"}`

---

### GET /version

Version info. No auth required.

**Response:**
```json
{
  "app_version": "0.1.0",
  "schema_version": "1.0",
  "normalizer_version": "1.0",
  "contract_version": "1.0"
}
```
