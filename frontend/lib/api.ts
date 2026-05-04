import { getApiBaseUrlCandidates } from "@/lib/config";

export type ApiError = {
  status: number;
  message: string;
  code?: string;
};

export type HealthResponse = {
  status: string;
};

export type VersionResponse = {
  app_version: string;
  schema_version: string;
  normalizer_version: string;
  contract_version: string;
};

export type AdminStatusResponse = {
  backend_health: string;
  version: VersionResponse;
  db: {
    connected: boolean;
    error: string | null;
  };
  last_run: {
    source?: string;
    business_id?: string;
    week_start?: string;
    week_end?: string;
    timestamp?: string;
  } | null;
};

export type UploadIssue = {
  error_code: string;
  severity: "error" | "warning";
  message: string;
  row_number: number | null;
  field: string | null;
  rule_id: string;
  suggestion: string | null;
};

export type UploadDatasetResult = {
  summary: {
    business_id: string;
    dataset: string;
    week_start: string;
    week_end: string;
    row_count: number;
    valid_row_count: number;
    error_count: number;
    warning_count: number;
    quality_score: number;
    quality_band: string;
    persisted: boolean;
  };
  quality: {
    dataset: string;
    quality_score: number;
    quality_band: string;
    row_count: number;
    valid_row_count: number;
    error_count: number;
    warning_count: number;
    top_issues: Array<{ rule_id: string; count: number }>;
  };
  schema_fields: string[];
  issues: UploadIssue[];
};

export type AdminUploadWeeklyResponse = {
  business_id: string;
  week_start: string;
  week_end: string;
  excel: UploadDatasetResult | null;
  mpesa: UploadDatasetResult | null;
};

export type AdminUploadWeeklyRequest = {
  token: string;
  businessId: string;
  weekStart: string;
  weekEnd: string;
  businessCurrency?: string;
  excelFile?: File;
  mpesaFile?: File;
  onProgress?: (progressPct: number) => void;
};

export type AdminReportsResponse = {
  business_id: string;
  week_start: string;
  week_end: string;
  metrics_json: Record<string, unknown>;
  llm_narration_json: Record<string, unknown> | null;
  whatsapp_preview: {
    message: string;
  };
};

export type AdminGenerateReportRequest = {
  business_id?: string;
  week_start: string;
  week_end: string;
  slow_mover_days?: number;
  top_n_products?: number;
  business_name?: string;
  sme_type?: string;
  currency?: string;
  all_businesses?: boolean;
};

export type AdminGenerateReportResponse = {
  job_id: string;
  status: string;
};

export type AdminJobStatusResponse = {
  job_id: string;
  status: "queued" | "running" | "completed" | "failed";
  requested_at: string;
  started_at: string | null;
  finished_at: string | null;
  error: string | null;
  business_id: string;
  week_start: string;
  week_end: string;
  result_summary: {
    weekly_revenue?: number | string;
    repeat_customers?: number;
    records_processed?: number;
  } | null;
};

export type AdminSettingsResponse = {
  operational: {
    default_business_id: string;
    default_currency: string;
    timezone: string;
    report_schedule_day: string;
    report_schedule_time: string;
  };
  ai: {
    provider: string;
    model: string;
    temperature: number;
    max_output_tokens: number;
    strict_json_only: boolean;
    metrics_only_fallback: boolean;
    azure_endpoint?: string | null;
    azure_deployment?: string | null;
    has_api_key: boolean;
  };
  whatsapp: {
    provider: string;
    phone_number_id: string | null;
    business_account_id: string | null;
    sender_display_name: string | null;
    webhook_callback_url: string | null;
    has_access_token: boolean;
    has_webhook_verify_token: boolean;
    twilio_account_sid: string | null;
    twilio_whatsapp_number: string | null;
    has_twilio_auth_token: boolean;
  };
};

export type AdminSettingsUpdateRequest = {
  operational?: {
    default_business_id?: string;
    default_currency?: string;
    timezone?: string;
    report_schedule_day?: string;
    report_schedule_time?: string;
  };
  ai?: {
    provider?: string;
    model?: string;
    temperature?: number;
    max_output_tokens?: number;
    strict_json_only?: boolean;
    metrics_only_fallback?: boolean;
    azure_endpoint?: string;
    azure_deployment?: string;
    api_key?: string;
  };
  whatsapp?: {
    provider?: string;
    phone_number_id?: string;
    business_account_id?: string;
    sender_display_name?: string;
    webhook_callback_url?: string;
    access_token?: string;
    webhook_verify_token?: string;
  };
};

export type AdminWhatsAppTestSendResponse = {
  status: string;
  provider_response_summary: Record<string, unknown>;
};

// ── Dashboard enhanced-mode types ───────────────────────────────────────────

export type RecentUpload = {
  business_id: string;
  timestamp: string;
  status: "success" | "partial" | "failed";
  record_count: number;
  dataset: string;
  week_start: string;
  week_end: string;
  quality_score?: number;
  parsed_data?: Record<string, unknown>[];
};

export type RecentUploadsResponse = {
  uploads: RecentUpload[];
};

export type WeeklyMetricsResponse = {
  business_id: string;
  week_start: string;
  week_end: string;
  revenue: number;
  order_count: number;
  avg_order_value: number;
  top_product: string | null;
  repeat_customers: number;
  wow_revenue_delta: number | null;
  wow_order_delta: number | null;
};

export type WhatsAppStatusResponse = {
  last_sent: {
    phone: string;
    timestamp: string;
    preview_text: string;
    status: "delivered" | "sent" | "failed";
    business_id: string;
  } | null;
};

// ── Analytics types ─────────────────────────────────────────────────────────

export type AnalyticsTrendPoint = {
  date: string;
  value: number;
};

export type AnalyticsMetricsResponse = {
  revenue_trend: AnalyticsTrendPoint[];
  expenses_trend: AnalyticsTrendPoint[];
  profit_trend: AnalyticsTrendPoint[];
  totals: {
    revenue: number;
    expenses: number;
    profit: number;
  };
};

export type AnalyticsUpload = {
  file_name: string;
  dataset: string;
  rows: number;
  quality_score: number | null;
  uploaded_at: string;
  status: string;
  week_start: string;
  week_end: string;
};

export type AnalyticsWhatsAppStats = {
  total_sent: number;
  last_sent: string | null;
  success_rate: number;
};

export type AnalyticsActivity = {
  type: "upload" | "report" | "whatsapp" | "error";
  message: string;
  status: "success" | "failed";
  timestamp: string;
};

const DEFAULT_TIMEOUT_MS = 12_000;

function isObject(value: unknown): value is Record<string, unknown> {
  return typeof value === "object" && value !== null;
}

function normalizeError(status: number, payload: unknown): ApiError {
  if (isObject(payload)) {
    const detail = typeof payload.detail === "string" ? payload.detail : undefined;
    const message = typeof payload.message === "string" ? payload.message : detail;
    const code = typeof payload.code === "string" ? payload.code : undefined;
    return {
      status,
      message: message ?? "Request failed",
      code,
    };
  }

  return {
    status,
    message: "Request failed",
  };
}

export async function apiRequest<T>(
  path: string,
  options: RequestInit & { token?: string; timeoutMs?: number } = {},
): Promise<T> {
  const headers = new Headers(options.headers ?? undefined);
  if (!headers.has("Content-Type")) {
    headers.set("Content-Type", "application/json");
  }

  if (options.token) {
    headers.set("Authorization", `Bearer ${options.token}`);
  }

  const timeoutMs = options.timeoutMs ?? DEFAULT_TIMEOUT_MS;
  const baseUrls = getApiBaseUrlCandidates();
  let lastNetworkError: unknown = null;

  for (const baseUrl of baseUrls) {
    const controller = new AbortController();
    const timeout = setTimeout(() => controller.abort(), timeoutMs);
    try {
      const response = await fetch(`${baseUrl}${path}`, {
        ...options,
        headers,
        signal: controller.signal,
      });

      const contentType = response.headers.get("content-type") ?? "";
      const payload = contentType.includes("application/json") ? await response.json() : await response.text();

      if (!response.ok) {
        throw normalizeError(response.status, payload);
      }

      return payload as T;
    } catch (error: unknown) {
      if (isApiError(error)) {
        throw error;
      }
      if (error instanceof DOMException && error.name === "AbortError") {
        throw {
          status: 408,
          message: "Request timed out. Try again.",
          code: "TIMEOUT",
        } satisfies ApiError;
      }
      lastNetworkError = error;
    } finally {
      clearTimeout(timeout);
    }
  }

  throw {
    status: 0,
    message: `Network error. Confirm backend is reachable. Tried: ${baseUrls.join(", ")}`,
    code: "NETWORK_ERROR",
    cause: lastNetworkError,
  } satisfies ApiError & { cause?: unknown };
}

export function isApiError(value: unknown): value is ApiError {
  return isObject(value) && typeof value.status === "number" && typeof value.message === "string";
}

export function getHealth(token?: string): Promise<HealthResponse> {
  return apiRequest<HealthResponse>("/health", { method: "GET", token });
}

export function getVersion(token?: string): Promise<VersionResponse> {
  return apiRequest<VersionResponse>("/version", { method: "GET", token });
}

export function getAdminStatus(token: string): Promise<AdminStatusResponse> {
  return apiRequest<AdminStatusResponse>("/admin/status", { method: "GET", token });
}

export function getAdminReports(
  token: string,
  params: {
    businessId: string;
    weekStart: string;
    weekEnd: string;
  },
): Promise<AdminReportsResponse> {
  const query = new URLSearchParams({
    business_id: params.businessId,
    week_start: params.weekStart,
    week_end: params.weekEnd,
  });
  return apiRequest<AdminReportsResponse>(`/admin/reports?${query.toString()}`, { method: "GET", token });
}

export function generateAdminReport(
  token: string,
  payload: AdminGenerateReportRequest,
): Promise<AdminGenerateReportResponse> {
  return apiRequest<AdminGenerateReportResponse>("/admin/reports/generate", {
    method: "POST",
    token,
    body: JSON.stringify(payload),
  });
}

export function getAdminJobStatus(token: string, jobId: string): Promise<AdminJobStatusResponse> {
  return apiRequest<AdminJobStatusResponse>(`/admin/jobs/${jobId}`, { method: "GET", token });
}

export function getAdminSettings(token: string): Promise<AdminSettingsResponse> {
  return apiRequest<AdminSettingsResponse>("/admin/settings", { method: "GET", token });
}

export function updateAdminSettings(token: string, payload: AdminSettingsUpdateRequest): Promise<AdminSettingsResponse> {
  return apiRequest<AdminSettingsResponse>("/admin/settings", {
    method: "PUT",
    token,
    body: JSON.stringify(payload),
  });
}

// ── Multi-tenancy types ──────────────────────────────────────────────────────

export type OnboardRequest = {
  organization_id: string;
  name: string;
  plan: string;
};

export type OnboardResponse = {
  organization_id: string;
  name: string;
  plan: string;
  status: string;
  expiry_date: string;
};

export type Business = {
  id: string;
  name: string | null;
  whatsapp_phone: string | null;
  created_at: string;
};

export type BusinessesResponse = {
  organization_id: string;
  businesses: Business[];
};

export type CreateBusinessRequest = {
  id: string;
  organization_id?: string;
  name?: string;
  whatsapp_phone?: string;
};

export type CreateBusinessResponse = {
  id: string;
  organization_id: string;
  name: string | null;
  whatsapp_phone: string | null;
  created_at: string;
};

export type BillingResponse = {
  organization_id: string;
  plan: string | null;
  status: string | null;
  expiry_date: string | null;
  active: boolean;
  days_remaining: number;
};

export function onboard(payload: OnboardRequest): Promise<OnboardResponse> {
  return apiRequest<OnboardResponse>("/onboard", {
    method: "POST",
    body: JSON.stringify(payload),
  });
}

export function getBusinesses(organizationId = "default_org"): Promise<BusinessesResponse> {
  return apiRequest<BusinessesResponse>(`/businesses?organization_id=${encodeURIComponent(organizationId)}`, {
    method: "GET",
  });
}

export function createBusiness(payload: CreateBusinessRequest): Promise<CreateBusinessResponse> {
  return apiRequest<CreateBusinessResponse>("/businesses", {
    method: "POST",
    body: JSON.stringify(payload),
  });
}

export function getBilling(organizationId = "default_org"): Promise<BillingResponse> {
  return apiRequest<BillingResponse>(`/billing/current?organization_id=${encodeURIComponent(organizationId)}`, {
    method: "GET",
  });
}

export function sendAdminWhatsAppTest(
  token: string,
  payload: { to_phone: string; message: string },
): Promise<AdminWhatsAppTestSendResponse> {
  return apiRequest<AdminWhatsAppTestSendResponse>("/admin/whatsapp/test-send", {
    method: "POST",
    token,
    body: JSON.stringify(payload),
  });
}

export type TwilioTestSendResponse = {
  status: string;
  sid?: string;
  to_phone_masked?: string;
};

export function sendTwilioTest(
  token: string,
  phone: string,
): Promise<TwilioTestSendResponse> {
  return apiRequest<TwilioTestSendResponse>("/reports/send-test", {
    method: "POST",
    token,
    body: JSON.stringify({ phone }),
  });
}

export function uploadAdminWeekly(request: AdminUploadWeeklyRequest): Promise<AdminUploadWeeklyResponse> {
  const formData = new FormData();
  formData.append("business_id", request.businessId);
  formData.append("week_start", request.weekStart);
  formData.append("week_end", request.weekEnd);
  formData.append("business_currency", request.businessCurrency ?? "KES");
  if (request.excelFile) {
    formData.append("excel_file", request.excelFile);
  }
  if (request.mpesaFile) {
    formData.append("mpesa_file", request.mpesaFile);
  }

  const baseUrls = getApiBaseUrlCandidates();
  let index = 0;

  return new Promise((resolve, reject) => {
    const attempt = () => {
      if (index >= baseUrls.length) {
        reject({
          status: 0,
          message: `Network error. Confirm backend is reachable. Tried: ${baseUrls.join(", ")}`,
          code: "NETWORK_ERROR",
        } satisfies ApiError);
        return;
      }

      const baseUrl = baseUrls[index++];
      const xhr = new XMLHttpRequest();
      xhr.open("POST", `${baseUrl}/admin/upload/weekly`);
      xhr.setRequestHeader("Authorization", `Bearer ${request.token}`);

      xhr.upload.onprogress = (event) => {
        if (!request.onProgress) {
          return;
        }
        if (event.lengthComputable) {
          request.onProgress(Math.round((event.loaded / event.total) * 100));
        }
      };

      xhr.onerror = () => {
        attempt();
      };

      xhr.onload = () => {
        const text = xhr.responseText;
        const parsed = text ? safeJsonParse(text) : null;

        if (xhr.status >= 200 && xhr.status < 300 && parsed) {
          resolve(parsed as AdminUploadWeeklyResponse);
          return;
        }

        reject(normalizeError(xhr.status, parsed));
      };

      xhr.send(formData);
    };

    attempt();
  });
}

function safeJsonParse(text: string): unknown {
  try {
    return JSON.parse(text);
  } catch {
    return { detail: text };
  }
}

// ── Dashboard enhanced-mode endpoints ───────────────────────────────────────

export function getRecentUploads(token: string, limit = 5): Promise<RecentUploadsResponse> {
  return apiRequest<RecentUploadsResponse>(`/admin/uploads/recent?limit=${limit}`, { method: "GET", token });
}

export function getWeeklyMetrics(
  token: string,
  businessId: string,
): Promise<WeeklyMetricsResponse> {
  return apiRequest<WeeklyMetricsResponse>(
    `/metrics/weekly?business_id=${encodeURIComponent(businessId)}`,
    { method: "GET", token },
  );
}

export function getWhatsAppStatus(token: string): Promise<WhatsAppStatusResponse> {
  return apiRequest<WhatsAppStatusResponse>("/admin/whatsapp/status", { method: "GET", token });
}

// ── Analytics endpoints ─────────────────────────────────────────────────────

export function getAnalyticsMetrics(
  token: string,
  params: { organizationId: string; businessId: string },
): Promise<AnalyticsMetricsResponse> {
  const query = new URLSearchParams({
    organization_id: params.organizationId,
    business_id: params.businessId,
  });
  return apiRequest<AnalyticsMetricsResponse>(`/analytics/metrics?${query}`, { method: "GET", token });
}

export function getAnalyticsUploads(
  token: string,
  params: { organizationId: string; businessId: string },
): Promise<AnalyticsUpload[]> {
  const query = new URLSearchParams({
    organization_id: params.organizationId,
    business_id: params.businessId,
  });
  return apiRequest<AnalyticsUpload[]>(`/analytics/uploads?${query}`, { method: "GET", token });
}

export function getAnalyticsWhatsApp(
  token: string,
  params: { organizationId: string; businessId: string },
): Promise<AnalyticsWhatsAppStats> {
  const query = new URLSearchParams({
    organization_id: params.organizationId,
    business_id: params.businessId,
  });
  return apiRequest<AnalyticsWhatsAppStats>(`/analytics/whatsapp?${query}`, { method: "GET", token });
}

export function getAnalyticsActivity(
  token: string,
  params: { organizationId: string; businessId: string },
): Promise<AnalyticsActivity[]> {
  const query = new URLSearchParams({
    organization_id: params.organizationId,
    business_id: params.businessId,
  });
  return apiRequest<AnalyticsActivity[]>(`/analytics/activity?${query}`, { method: "GET", token });
}
