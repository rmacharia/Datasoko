# API Reference

Base URL: `http://localhost:8000` (dev) or `https://datasoko-api.azurewebsites.net` (prod)

## Public Endpoints

### POST /onboard

Create a new organization with a trial subscription.

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

## Admin Endpoints

All admin endpoints require `Authorization: Bearer <ADMIN_TOKEN>`.

### GET /admin/status

System health check with database diagnostics.

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

**Query Parameters:**
- `business_id` (required)
- `week_start`, `week_end` (required, dates)
- `business_name` (optional, default: `Your Business`)
- `sme_type` (optional, default: `retail`)
- `currency` (optional, default: `KES`)

---

### POST /admin/reports/generate

Queue a report generation job.

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

---

### PUT /admin/settings

Update admin settings. Supports `operational`, `ai`, and `whatsapp` sections.

---

### POST /admin/whatsapp/test-send

Send a test WhatsApp message.

**Request:**
```json
{
  "to_phone": "+254712345678"
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
