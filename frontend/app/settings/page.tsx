"use client";

import { zodResolver } from "@hookform/resolvers/zod";
import { useRouter } from "next/navigation";
import { useEffect, useState } from "react";
import { useForm } from "react-hook-form";
import { z } from "zod";

import { AuthGuard } from "@/components/auth-guard";
import { useAuth } from "@/components/auth-provider";
import { useSettings, type ThemePreference } from "@/components/settings-provider";
import { SystemContext } from "@/components/system-context";
import { useToast } from "@/components/toast-provider";
import { Alert } from "@/components/ui/alert";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import {
  getAdminSettings,
  isApiError,
  sendAdminWhatsAppTest,
  updateAdminSettings,
  type AdminSettingsResponse,
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
  whatsapp_webhook_callback_url: z.string().url("Use a valid URL.").or(z.literal("")),
  whatsapp_access_token: z.string().optional(),
  whatsapp_webhook_verify_token: z.string().optional(),
});

const testSendSchema = z.object({
  to_phone: z.string().min(6),
});

type SettingsForm = z.infer<typeof settingsSchema>;
type TestSendForm = z.infer<typeof testSendSchema>;

export default function SettingsPage() {
  const router = useRouter();
  const { token, logout } = useAuth();
  const { theme, setTheme, enhancedMode, setEnhancedMode } = useSettings();
  const { pushToast } = useToast();

  const [error, setError] = useState<string | null>(null);
  const [loading, setLoading] = useState(false);
  const [settingsState, setSettingsState] = useState<AdminSettingsResponse | null>(null);
  const [testSummary, setTestSummary] = useState<string | null>(null);

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
      whatsapp_provider: "meta_cloud_api",
      whatsapp_phone_number_id: "",
      whatsapp_business_account_id: "",
      whatsapp_sender_display_name: "",
      whatsapp_webhook_callback_url: "",
      whatsapp_access_token: "",
      whatsapp_webhook_verify_token: "",
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
          logout();
          router.replace("/login");
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
  }, [token, logout, router, settingsForm]);

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
      if (isApiError(requestError) && requestError.status === 401) {
        logout();
        router.replace("/login");
        return;
      }
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
    try {
      const result = await sendAdminWhatsAppTest(token, {
        to_phone: values.to_phone,
        message: "DataSoko internal integration test message. No business data included.",
      });
      setTestSummary(JSON.stringify(result.provider_response_summary, null, 2));
      pushToast(`Test send status: ${result.status}`, result.status === "sent" ? "success" : "warning");
    } catch (requestError) {
      if (isApiError(requestError) && requestError.status === 401) {
        logout();
        router.replace("/login");
        return;
      }
      const message = isApiError(requestError) ? requestError.message : "Failed to send WhatsApp test.";
      setError(message);
      pushToast(message, "danger");
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

        <section className="mt-4 card p-6">
          <h2 className="text-lg font-semibold">Appearance</h2>
          <p className="mt-1 text-sm muted">Theme and internal visual enhancements.</p>
          <div className="mt-4 grid gap-4 md:grid-cols-2">
            <label className="text-sm font-medium" htmlFor="theme">
              Theme
              <select
                id="theme"
                value={theme}
                onChange={(event) => setTheme(event.target.value as ThemePreference)}
                className="mt-1 w-full rounded-md border border-[var(--border)] bg-[rgba(11,21,37,0.9)] px-3 py-2 text-sm"
              >
                <option value="system">System</option>
                <option value="dark">Dark</option>
                <option value="light">Light</option>
              </select>
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
                <select
                  {...settingsForm.register("ai_provider")}
                  className="mt-1 w-full rounded-md border border-[var(--border)] bg-[rgba(11,21,37,0.9)] px-3 py-2 text-sm"
                >
                  <option value="azure_openai">Azure OpenAI</option>
                  <option value="openai">OpenAI</option>
                </select>
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
                <select
                  {...settingsForm.register("whatsapp_provider")}
                  className="mt-1 w-full rounded-md border border-[var(--border)] bg-[rgba(11,21,37,0.9)] px-3 py-2 text-sm"
                >
                  <option value="meta_cloud_api">Meta Cloud API</option>
                  <option value="twilio_whatsapp">Twilio WhatsApp (future)</option>
                </select>
              </label>
              <label className="text-sm font-medium">
                Phone Number ID
                <Input {...settingsForm.register("whatsapp_phone_number_id")} />
              </label>
              <label className="text-sm font-medium">
                Business Account ID
                <Input {...settingsForm.register("whatsapp_business_account_id")} />
              </label>
              <label className="text-sm font-medium">
                Sender Display Name
                <Input {...settingsForm.register("whatsapp_sender_display_name")} />
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

            <div className="mt-6 border-t border-[var(--border)] pt-5">
              <h3 className="text-base font-semibold">Test Send</h3>
              <form className="mt-3 grid gap-3 md:grid-cols-2" onSubmit={onTestSend}>
                <label className="text-sm font-medium">
                  Test Destination Phone
                  <Input {...testSendForm.register("to_phone")} placeholder="+254700000000" />
                </label>
                <p className="text-sm muted md:col-span-2">
                  Template: DataSoko internal integration test message. No business data included.
                </p>
                <div className="md:col-span-2">
                  <Button type="submit" variant="secondary" disabled={testSendForm.formState.isSubmitting}>
                    {testSendForm.formState.isSubmitting ? "Sending..." : "Send Test Message"}
                  </Button>
                </div>
              </form>
              {testSummary ? <pre className="code-panel mt-3 overflow-auto p-3 text-xs">{testSummary}</pre> : null}
            </div>
          </section>

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
