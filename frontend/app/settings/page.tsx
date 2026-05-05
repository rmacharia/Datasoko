"use client";

import { zodResolver } from "@hookform/resolvers/zod";
import { useRouter } from "next/navigation";
import { useEffect, useState } from "react";
import { useForm } from "react-hook-form";
import { z } from "zod";

import { AuthGuard } from "@/components/auth-guard";
import { useAuth } from "@/components/auth-provider";
import { useOrg } from "@/components/org-provider";
import { useSettings, type ThemePreference } from "@/components/settings-provider";
import { SystemContext } from "@/components/system-context";
import { useToast } from "@/components/toast-provider";
import { Alert } from "@/components/ui/alert";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { Select } from "@/components/ui/select";
import { ScheduleManager } from "@/components/schedule-manager";
import {
  createBusiness,
  getAdminSettings,
  getBilling,
  getBusinesses,
  isApiError,
  sendAdminWhatsAppTest,
  sendTwilioTest,
  updateAdminSettings,
  type AdminSettingsResponse,
  type BillingResponse,
  type Business,
} from "@/lib/api";
import { toSettingsFormDefaults } from "@/lib/settings";

const settingsSchema = z.object({
  default_business_id: z.string().min(1, "Business ID is required."),
  default_currency: z.string().min(1, "Currency is required.").max(8),
  timezone: z.string().min(1, "Timezone is required."),
  report_schedule_day: z.string().min(1, "Schedule day is required."),
  report_schedule_time: z.string().regex(/^\d{2}:\d{2}$/, "Use HH:MM format."),
  ai_provider: z.enum(["azure_openai", "openai"]),
  ai_model: z.string().min(1, "Model is required."),
  ai_temperature: z.coerce.number().min(0).max(1),
  ai_max_output_tokens: z.coerce.number().int().min(64).max(4096),
  ai_strict_json_only: z.boolean(),
  ai_metrics_only_fallback: z.boolean(),
  ai_api_key: z.string().optional(),
  whatsapp_provider: z.string().min(1),
  whatsapp_phone_number_id: z.string().optional(),
  whatsapp_business_account_id: z.string().optional(),
  whatsapp_sender_display_name: z.string().optional(),
  whatsapp_webhook_callback_url: z.string().url("Use a valid URL.").or(z.literal("")).optional(),
  whatsapp_access_token: z.string().optional(),
  whatsapp_webhook_verify_token: z.string().optional(),
  twilio_account_sid: z.string().optional(),
  twilio_whatsapp_number: z.string().optional(),
});

const testSendSchema = z.object({
  to_phone: z.string().min(6),
});

type SettingsForm = z.infer<typeof settingsSchema>;
type TestSendForm = z.infer<typeof testSendSchema>;

const addSmeSchema = z.object({
  id: z.string().min(1, "Business ID is required."),
  name: z.string().optional(),
  whatsapp_phone: z.string().optional(),
});
type AddSmeForm = z.infer<typeof addSmeSchema>;

export default function SettingsPage() {
  const router = useRouter();
  const { token } = useAuth();
  const { organizationId, activeBusinessId, setActiveBusinessId } = useOrg();
  const { theme, setTheme, enhancedMode, setEnhancedMode } = useSettings();
  const { pushToast } = useToast();

  const [error, setError] = useState<string | null>(null);
  const [loading, setLoading] = useState(false);
  const [settingsState, setSettingsState] = useState<AdminSettingsResponse | null>(null);
  const [testSummary, setTestSummary] = useState<string | null>(null);
  const [testStatus, setTestStatus] = useState<"idle" | "sending" | "success" | "error">("idle");
  const [testError, setTestError] = useState<string | null>(null);

  const [billing, setBilling] = useState<BillingResponse | null>(null);
  const [billingLoading, setBillingLoading] = useState(false);
  const [billingError, setBillingError] = useState<string | null>(null);

  const [businesses, setBusinesses] = useState<Business[]>([]);
  const [bizLoading, setBizLoading] = useState(false);
  const [bizError, setBizError] = useState<string | null>(null);
  const [addSmeError, setAddSmeError] = useState<string | null>(null);

  const addSmeForm = useForm<AddSmeForm>({
    resolver: zodResolver(addSmeSchema),
    defaultValues: { id: "", name: "", whatsapp_phone: "" },
  });

  const settingsForm = useForm<SettingsForm>({
    resolver: zodResolver(settingsSchema),
    defaultValues: {
      default_business_id: "biz_001",
      default_currency: "KES",
      timezone: "Africa/Nairobi",
      report_schedule_day: "Friday",
      report_schedule_time: "18:00",
      ai_provider: "azure_openai",
      ai_model: "gpt-4.1-mini",
      ai_temperature: 0.2,
      ai_max_output_tokens: 700,
      ai_strict_json_only: true,
      ai_metrics_only_fallback: true,
      ai_api_key: "",
      whatsapp_provider: "twilio_whatsapp",
      whatsapp_phone_number_id: "",
      whatsapp_business_account_id: "",
      whatsapp_sender_display_name: "",
      whatsapp_webhook_callback_url: "",
      whatsapp_access_token: "",
      whatsapp_webhook_verify_token: "",
      twilio_account_sid: "",
      twilio_whatsapp_number: "",
    },
  });

  const testSendForm = useForm<TestSendForm>({
    resolver: zodResolver(testSendSchema),
    defaultValues: {
      to_phone: "",
    },
  });

  useEffect(() => {
    if (!token) return;
    let mounted = true;
    setLoading(true);
    void getAdminSettings(token)
      .then((response) => {
        if (!mounted) return;
        setSettingsState(response);
        settingsForm.reset(toSettingsFormDefaults(response));
      })
      .catch((requestError) => {
        if (!mounted) return;
        if (isApiError(requestError) && requestError.status === 401) {
          setError("Session expired. Please log in again.");
          return;
        }
        const message = isApiError(requestError) ? requestError.message : "Failed to load settings.";
        setError(message);
      })
      .finally(() => {
        if (mounted) setLoading(false);
      });

    return () => {
      mounted = false;
    };
  }, [token, router, settingsForm]);

  useEffect(() => {
    if (!token) return;
    let mounted = true;
    setBillingLoading(true);
    void getBilling(token, organizationId)
      .then((res) => { if (mounted) setBilling(res); })
      .catch((err) => { if (mounted) setBillingError(isApiError(err) ? err.message : "Failed to load billing."); })
      .finally(() => { if (mounted) setBillingLoading(false); });
    return () => { mounted = false; };
  }, [token, organizationId]);

  useEffect(() => {
    if (!token) return;
    let mounted = true;
    setBizLoading(true);
    void getBusinesses(token, organizationId)
      .then((res) => { if (mounted) setBusinesses(res.businesses); })
      .catch((err) => { if (mounted) setBizError(isApiError(err) ? err.message : "Failed to load businesses."); })
      .finally(() => { if (mounted) setBizLoading(false); });
    return () => { mounted = false; };
  }, [token, organizationId]);

  const onAddSme = addSmeForm.handleSubmit(async (values) => {
    setAddSmeError(null);
    if (!token) return;
    try {
      const created = await createBusiness(token, {
        id: values.id.trim(),
        organization_id: organizationId ?? undefined,
        name: values.name?.trim() || undefined,
        whatsapp_phone: values.whatsapp_phone?.trim() || undefined,
      });
      setBusinesses((prev) => [...prev, created]);
      addSmeForm.reset();
      pushToast(`Business "${created.id}" added.`, "success");
    } catch (err) {
      const msg = isApiError(err) ? err.message : "Failed to create business.";
      setAddSmeError(msg);
      pushToast(msg, "danger");
    }
  });

  const onSave = settingsForm.handleSubmit(async (values) => {
    if (!token) {
      router.replace("/login");
      return;
    }
    setError(null);

    const payload = {
      operational: {
        default_business_id: values.default_business_id,
        default_currency: values.default_currency,
        timezone: values.timezone,
        report_schedule_day: values.report_schedule_day,
        report_schedule_time: values.report_schedule_time,
      },
      ai: {
        provider: values.ai_provider,
        model: values.ai_model,
        temperature: values.ai_temperature,
        max_output_tokens: values.ai_max_output_tokens,
        strict_json_only: values.ai_strict_json_only,
        metrics_only_fallback: values.ai_metrics_only_fallback,
        ...(values.ai_api_key?.trim() ? { api_key: values.ai_api_key.trim() } : {}),
      },
      whatsapp: {
        provider: values.whatsapp_provider,
        phone_number_id: values.whatsapp_phone_number_id?.trim() || "",
        business_account_id: values.whatsapp_business_account_id?.trim() || "",
        sender_display_name: values.whatsapp_sender_display_name?.trim() || "",
        webhook_callback_url: values.whatsapp_webhook_callback_url?.trim() || "",
        ...(values.whatsapp_access_token?.trim() ? { access_token: values.whatsapp_access_token.trim() } : {}),
        ...(values.whatsapp_webhook_verify_token?.trim()
          ? { webhook_verify_token: values.whatsapp_webhook_verify_token.trim() }
          : {}),
      },
    };

    try {
      const updated = await updateAdminSettings(token, payload);
      setSettingsState(updated);
      settingsForm.reset(toSettingsFormDefaults(updated));
      pushToast("Settings saved.", "success");
    } catch (requestError) {
      const message = isApiError(requestError) ? requestError.message : "Failed to save settings.";
      setError(message);
      pushToast(message, "danger");
    }
  });

  const onTestSend = testSendForm.handleSubmit(async (values) => {
    if (!token) {
      router.replace("/login");
      return;
    }
    setError(null);
    setTestStatus("sending");
    setTestError(null);
    setTestSummary(null);

    const provider = settingsForm.getValues("whatsapp_provider");

    try {
      if (provider === "twilio_whatsapp") {
        const result = await sendTwilioTest(token, values.to_phone);
        setTestSummary(JSON.stringify(result, null, 2));
        setTestStatus("success");
        pushToast("Message sent via Twilio", "success");
      } else {
        const result = await sendAdminWhatsAppTest(token, {
          to_phone: values.to_phone,
          message: "DataSoko internal integration test message. No business data included.",
        });
        setTestSummary(JSON.stringify(result.provider_response_summary, null, 2));
        setTestStatus(result.status === "sent" ? "success" : "error");
        pushToast(`Test send status: ${result.status}`, result.status === "sent" ? "success" : "warning");
      }
    } catch (requestError) {
      const message = isApiError(requestError) ? requestError.message : "Failed to send WhatsApp test.";
      setTestStatus("error");
      setTestError(message);
      pushToast(`Failed: ${message}`, "danger");
    }
  });

  return (
    <AuthGuard>
      <main className="mx-auto max-w-6xl p-4 md:p-6">
        <SystemContext
          title="Settings"
          subtitle="Internal operational config for defaults, narrator, and WhatsApp delivery."
          businessId={settingsForm.watch("default_business_id") || "biz_001"}
          timezone={settingsForm.watch("timezone") || "Africa/Nairobi"}
          currency={settingsForm.watch("default_currency") || "KES"}
        />

        {error ? <Alert tone="danger">{error}</Alert> : null}
        {loading ? <p className="mt-3 text-sm muted">Loading settings...</p> : null}

        {/* ── Organization ───────────────────────────────────── */}
        <section className="mt-4 card p-6">
          <h2 className="text-lg font-semibold">Organization</h2>
          <p className="mt-1 text-sm muted">Active organization context for all API calls.</p>
          <div className="mt-4 grid gap-2 text-sm">
            <div className="flex items-center gap-3 rounded-md border border-[var(--border)] bg-[rgba(10,19,33,0.6)] px-4 py-3">
              <span className="muted w-32 shrink-0">Current Organization</span>
              <span className="font-mono font-semibold text-[var(--accent)]">{organizationId}</span>
            </div>
          </div>
        </section>

        {/* ── Billing ────────────────────────────────────────── */}
        <section className="mt-4 card p-6">
          <h2 className="text-lg font-semibold">Billing</h2>
          <p className="mt-1 text-sm muted">Current subscription status for this organization.</p>
          {billingLoading ? <p className="mt-3 text-sm muted">Loading billing...</p> : null}
          {billingError ? <div className="mt-3"><Alert tone="danger">{billingError}</Alert></div> : null}
          {billing && !billingLoading ? (
            <div className="mt-4 grid gap-2 text-sm md:grid-cols-2">
              <div className="flex items-center gap-3 rounded-md border border-[var(--border)] bg-[rgba(10,19,33,0.6)] px-4 py-3">
                <span className="muted w-28 shrink-0">Plan</span>
                <span className="font-semibold capitalize">{billing.plan ?? "—"}</span>
              </div>
              <div className="flex items-center gap-3 rounded-md border border-[var(--border)] bg-[rgba(10,19,33,0.6)] px-4 py-3">
                <span className="muted w-28 shrink-0">Status</span>
                <span className={`font-semibold ${billing.active ? "text-[var(--ok)]" : "text-[var(--danger)]"}`}>
                  {billing.status ?? "—"}
                </span>
              </div>
              <div className="flex items-center gap-3 rounded-md border border-[var(--border)] bg-[rgba(10,19,33,0.6)] px-4 py-3">
                <span className="muted w-28 shrink-0">Expires</span>
                <span className="font-mono text-xs">
                  {billing.expiry_date ? new Date(billing.expiry_date).toLocaleDateString() : "—"}
                </span>
              </div>
              <div className="flex items-center gap-3 rounded-md border border-[var(--border)] bg-[rgba(10,19,33,0.6)] px-4 py-3">
                <span className="muted w-28 shrink-0">Days Left</span>
                <span className={`font-semibold tabular-nums ${billing.days_remaining < 7 ? "text-[var(--warn)]" : ""}`}>
                  {billing.days_remaining}
                </span>
                {billing.days_remaining < 7 ? (
                  <span className="inline-flex items-center rounded-md bg-[rgba(255,200,87,0.18)] px-2 py-0.5 text-xs font-semibold text-[var(--warn)]">
                    Expiring soon
                  </span>
                ) : null}
              </div>
            </div>
          ) : null}
        </section>

        {/* ── SME Management ─────────────────────────────────── */}
        <section className="mt-4 card p-6">
          <div className="flex flex-wrap items-end justify-between gap-2">
            <div>
              <h2 className="text-lg font-semibold">SME Businesses</h2>
              <p className="mt-1 text-sm muted">Businesses registered under this organization.</p>
            </div>
            {!bizLoading && businesses.length > 0 ? (
              <span className="rounded-md border border-[var(--border)] bg-[rgba(10,19,33,0.6)] px-3 py-1 text-xs font-semibold tabular-nums">
                {businesses.length} {businesses.length === 1 ? "SME" : "SMEs"}
              </span>
            ) : null}
          </div>

          {bizLoading ? <p className="mt-3 text-sm muted">Loading businesses...</p> : null}
          {bizError ? <div className="mt-3"><Alert tone="danger">{bizError}</Alert></div> : null}

          {!bizLoading && businesses.length > 0 ? (
            <div className="mt-4 overflow-x-auto rounded-md border border-[var(--border)]">
              <table className="w-full text-sm">
                <thead>
                  <tr className="border-b border-[var(--border)] bg-[rgba(10,19,33,0.7)] text-left">
                    <th className="px-4 py-2 font-semibold">ID</th>
                    <th className="px-4 py-2 font-semibold">Name</th>
                    <th className="px-4 py-2 font-semibold">WhatsApp</th>
                    <th className="px-4 py-2 font-semibold">Created</th>
                    <th className="px-4 py-2" />
                  </tr>
                </thead>
                <tbody>
                  {businesses.map((biz) => (
                    <tr
                      key={biz.id}
                      className={`border-b border-[var(--border)] last:border-0 ${
                        biz.id === activeBusinessId
                          ? "bg-[rgba(55,181,255,0.1)] border-l-2 border-l-[var(--accent)]"
                          : "hover:bg-[rgba(79,121,199,0.07)]"
                      }`}
                    >
                      <td className="px-4 py-2 font-mono text-[var(--accent)]">
                        {biz.id}
                        {biz.id === activeBusinessId ? (
                          <span className="ml-2 inline-flex items-center rounded bg-[rgba(55,181,255,0.18)] px-1.5 py-0.5 text-[10px] font-semibold uppercase text-[var(--accent)]">
                            Active
                          </span>
                        ) : null}
                      </td>
                      <td className="px-4 py-2">{biz.name ?? <span className="muted">—</span>}</td>
                      <td className="px-4 py-2 font-mono text-xs">{biz.whatsapp_phone ?? <span className="muted">—</span>}</td>
                      <td className="px-4 py-2 text-xs muted">{new Date(biz.created_at).toLocaleDateString()}</td>
                      <td className="px-4 py-2">
                        {biz.id === activeBusinessId ? (
                          <span className="text-xs muted">Current</span>
                        ) : (
                          <button
                            type="button"
                            className="text-xs text-[var(--accent)] underline"
                            onClick={() => setActiveBusinessId(biz.id)}
                          >
                            Set active
                          </button>
                        )}
                      </td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
          ) : !bizLoading ? (
            <p className="mt-4 text-sm muted">No businesses found.</p>
          ) : null}

          <div className="mt-6 border-t border-[var(--border)] pt-5">
            <h3 className="text-base font-semibold">Add SME</h3>
            {addSmeError ? <div className="mt-2"><Alert tone="danger">{addSmeError}</Alert></div> : null}
            <form className="mt-3 grid gap-3 md:grid-cols-3" onSubmit={(e) => void onAddSme(e)}>
              <label className="text-sm font-medium">
                Business ID <span className="text-[var(--danger)]">*</span>
                <Input {...addSmeForm.register("id")} placeholder="biz_acme" className="mt-1" />
                {addSmeForm.formState.errors.id ? (
                  <p className="mt-1 text-xs text-[var(--danger)]">{addSmeForm.formState.errors.id.message}</p>
                ) : null}
              </label>
              <label className="text-sm font-medium">
                Display Name
                <Input {...addSmeForm.register("name")} placeholder="Acme Shop" className="mt-1" />
              </label>
              <label className="text-sm font-medium">
                WhatsApp Phone
                <Input {...addSmeForm.register("whatsapp_phone")} placeholder="+254700000000" className="mt-1" />
              </label>
              <div className="md:col-span-3">
                <Button type="submit" variant="secondary" disabled={addSmeForm.formState.isSubmitting}>
                  {addSmeForm.formState.isSubmitting ? "Adding..." : "Add Business"}
                </Button>
              </div>
            </form>
          </div>
        </section>

        <section className="mt-4 card p-6">
          <h2 className="text-lg font-semibold">Appearance</h2>
          <p className="mt-1 text-sm muted">Theme and internal visual enhancements.</p>
          <div className="mt-4 grid gap-4 md:grid-cols-2">
            <label className="text-sm font-medium" htmlFor="theme">
              Theme
              <Select
                id="theme"
                value={theme}
                onChange={(event) => setTheme(event.target.value as ThemePreference)}
                className="mt-1"
              >
                <option value="system">System</option>
                <option value="dark">Dark</option>
                <option value="light">Light</option>
              </Select>
            </label>

            <label className="text-sm font-medium">
              Enhanced Mode
              <div className="mt-2 flex h-10 items-center gap-2 rounded-md border border-[var(--border)] px-3">
                <input
                  type="checkbox"
                  checked={enhancedMode}
                  onChange={(event) => setEnhancedMode(event.target.checked)}
                  aria-label="Enhanced Mode"
                />
                <span className="text-sm">{enhancedMode ? "Enabled" : "Disabled"}</span>
              </div>
            </label>
          </div>
        </section>

        <div className="mt-4 grid gap-4">
          <section className="card p-6">
            <h2 className="text-lg font-semibold">Defaults</h2>
            <div className="mt-4 grid gap-4 md:grid-cols-2">
              <label className="text-sm font-medium">
                Default Business ID
                <Input {...settingsForm.register("default_business_id")} />
              </label>
              <label className="text-sm font-medium">
                Default Currency
                <Input {...settingsForm.register("default_currency")} />
              </label>
              <label className="text-sm font-medium">
                Timezone
                <Input {...settingsForm.register("timezone")} />
              </label>
              <label className="text-sm font-medium">
                Report Schedule (Day)
                <Input {...settingsForm.register("report_schedule_day")} />
              </label>
              <label className="text-sm font-medium">
                Report Schedule Time (HH:MM)
                <Input {...settingsForm.register("report_schedule_time")} />
              </label>
            </div>
          </section>

          <section className="card p-6">
            <h2 className="text-lg font-semibold">AI Narrator</h2>
            <div className="mt-4 grid gap-4 md:grid-cols-2">
              <label className="text-sm font-medium">
                Provider
                <Select {...settingsForm.register("ai_provider")} className="mt-1">
                  <option value="azure_openai">Azure OpenAI</option>
                  <option value="openai">OpenAI</option>
                </Select>
              </label>
              <label className="text-sm font-medium">
                Model
                <Input {...settingsForm.register("ai_model")} />
              </label>
              <label className="text-sm font-medium">
                Temperature
                <Input type="number" step="0.1" {...settingsForm.register("ai_temperature")} />
              </label>
              <label className="text-sm font-medium">
                Max Output Tokens
                <Input type="number" step="1" {...settingsForm.register("ai_max_output_tokens")} />
              </label>
              <label className="text-sm font-medium">
                API Key {settingsState?.ai.has_api_key ? <span className="muted">(saved)</span> : null}
                <Input type="password" autoComplete="new-password" {...settingsForm.register("ai_api_key")} />
              </label>
              <label className="mt-6 inline-flex items-center gap-2 text-sm">
                <input type="checkbox" {...settingsForm.register("ai_strict_json_only")} />
                Strict JSON-only output
              </label>
              <label className="inline-flex items-center gap-2 text-sm">
                <input type="checkbox" {...settingsForm.register("ai_metrics_only_fallback")} />
                Metrics-only fallback on narrator failure
              </label>
            </div>
          </section>

          <section className="card p-6">
            <h2 className="text-lg font-semibold">WhatsApp Delivery</h2>
            <div className="mt-4 grid gap-4 md:grid-cols-2">
              <label className="text-sm font-medium">
                Provider
                <Select {...settingsForm.register("whatsapp_provider")} className="mt-1">
                  <option value="twilio_whatsapp">Twilio WhatsApp (Active)</option>
                  <option value="meta_cloud_api" disabled>Meta Cloud API (Coming Soon)</option>
                </Select>
              </label>
              <label className="text-sm font-medium">
                Sender Display Name
                <Input {...settingsForm.register("whatsapp_sender_display_name")} />
              </label>
            </div>

            {settingsForm.watch("whatsapp_provider") === "twilio_whatsapp" ? (
              <div className="mt-4">
                <div className="grid gap-4 md:grid-cols-2">
                  <label className="text-sm font-medium">
                    Account SID
                    <Input
                      value={settingsState?.whatsapp.twilio_account_sid ?? ""}
                      readOnly
                      className="mt-1 opacity-70"
                      placeholder="From Azure environment"
                    />
                    <p className="mt-1 text-[10px] muted">Read-only. Set via TWILIO_ACCOUNT_SID env var.</p>
                  </label>
                  <label className="text-sm font-medium">
                    Auth Token
                    <Input
                      value={settingsState?.whatsapp.has_twilio_auth_token ? "********" : ""}
                      readOnly
                      className="mt-1 opacity-70"
                      placeholder="From Azure environment"
                    />
                    <p className="mt-1 text-[10px] muted">Read-only. Set via TWILIO_AUTH_TOKEN env var.</p>
                  </label>
                  <label className="text-sm font-medium">
                    WhatsApp Number
                    <Input
                      value={settingsState?.whatsapp.twilio_whatsapp_number ?? ""}
                      readOnly
                      className="mt-1 opacity-70"
                      placeholder="From Azure environment"
                    />
                    <p className="mt-1 text-[10px] muted">Read-only. Set via TWILIO_WHATSAPP_NUMBER env var.</p>
                  </label>
                </div>
                <div className="mt-4 rounded-md border border-[var(--border)] bg-[rgba(55,181,255,0.06)] px-4 py-3">
                  <p className="text-xs text-[var(--accent)]">
                    Credentials are securely managed via Azure App Service environment variables.
                    To update, change the values in Azure Portal &rarr; App Service &rarr; Configuration.
                  </p>
                </div>
              </div>
            ) : (
              <div className="mt-4 grid gap-4 md:grid-cols-2">
                <label className="text-sm font-medium">
                  Phone Number ID
                  <Input {...settingsForm.register("whatsapp_phone_number_id")} />
                </label>
                <label className="text-sm font-medium">
                  Business Account ID
                  <Input {...settingsForm.register("whatsapp_business_account_id")} />
                </label>
                <label className="text-sm font-medium md:col-span-2">
                  Webhook Callback URL
                  <Input {...settingsForm.register("whatsapp_webhook_callback_url")} />
                </label>
                <label className="text-sm font-medium">
                  Access Token {settingsState?.whatsapp.has_access_token ? <span className="muted">(saved)</span> : null}
                  <Input type="password" autoComplete="new-password" {...settingsForm.register("whatsapp_access_token")} />
                </label>
                <label className="text-sm font-medium">
                  Webhook Verify Token{" "}
                  {settingsState?.whatsapp.has_webhook_verify_token ? <span className="muted">(saved)</span> : null}
                  <Input
                    type="password"
                    autoComplete="new-password"
                    {...settingsForm.register("whatsapp_webhook_verify_token")}
                  />
                </label>
              </div>
            )}

            <div className="mt-6 border-t border-[var(--border)] pt-5">
              <h3 className="text-base font-semibold">Send Test Message</h3>
              <p className="mt-1 text-xs muted">
                {settingsForm.watch("whatsapp_provider") === "twilio_whatsapp"
                  ? "Sends a test WhatsApp message via Twilio. The recipient must have joined the Twilio Sandbox."
                  : "Sends a test message via Meta Cloud API."}
              </p>
              <form className="mt-3 grid gap-3 md:grid-cols-2" onSubmit={onTestSend}>
                <label className="text-sm font-medium">
                  Destination Phone
                  <Input {...testSendForm.register("to_phone")} placeholder="+254700000000" />
                </label>
                <div className="md:col-span-2 flex items-center gap-3">
                  <Button type="submit" variant="secondary" disabled={testStatus === "sending"}>
                    {testStatus === "sending" ? "Sending..." : "Send Test Message"}
                  </Button>
                  {testStatus === "success" ? (
                    <span className="inline-flex items-center gap-1.5 rounded-md bg-[rgba(53,211,157,0.14)] px-3 py-1.5 text-xs font-semibold text-[var(--ok)]">
                      Message sent
                    </span>
                  ) : null}
                </div>
              </form>
              {testError ? (
                <div className="mt-3 rounded-md border border-[rgba(255,107,122,0.3)] bg-[rgba(255,107,122,0.08)] px-4 py-3">
                  <p className="text-xs font-semibold text-[var(--danger)]">{testError}</p>
                </div>
              ) : null}
              {testSummary ? <pre className="code-panel mt-3 overflow-auto p-3 text-xs">{testSummary}</pre> : null}
            </div>
          </section>

          <ScheduleManager />

          <div>
            <Button type="button" variant="primary" disabled={settingsForm.formState.isSubmitting} onClick={() => void onSave()}>
              {settingsForm.formState.isSubmitting ? "Saving..." : "Save Settings"}
            </Button>
          </div>
        </div>
      </main>
    </AuthGuard>
  );
}
