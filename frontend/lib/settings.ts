import type { AdminSettingsResponse } from "@/lib/api";

export type SettingsFormDefaults = {
  default_business_id: string;
  default_currency: string;
  timezone: string;
  report_schedule_day: string;
  report_schedule_time: string;
  ai_provider: "azure_openai" | "openai";
  ai_model: string;
  ai_temperature: number;
  ai_max_output_tokens: number;
  ai_strict_json_only: boolean;
  ai_metrics_only_fallback: boolean;
  ai_api_key: string;
  whatsapp_provider: string;
  whatsapp_phone_number_id: string;
  whatsapp_business_account_id: string;
  whatsapp_sender_display_name: string;
  whatsapp_webhook_callback_url: string;
  whatsapp_access_token: string;
  whatsapp_webhook_verify_token: string;
};

export function toSettingsFormDefaults(payload: AdminSettingsResponse): SettingsFormDefaults {
  return {
    default_business_id: payload.operational.default_business_id,
    default_currency: payload.operational.default_currency,
    timezone: payload.operational.timezone,
    report_schedule_day: payload.operational.report_schedule_day,
    report_schedule_time: payload.operational.report_schedule_time,
    ai_provider: payload.ai.provider === "openai" ? "openai" : "azure_openai",
    ai_model: payload.ai.model,
    ai_temperature: payload.ai.temperature,
    ai_max_output_tokens: payload.ai.max_output_tokens,
    ai_strict_json_only: payload.ai.strict_json_only,
    ai_metrics_only_fallback: payload.ai.metrics_only_fallback,
    ai_api_key: "",
    whatsapp_provider: payload.whatsapp.provider || "meta_cloud_api",
    whatsapp_phone_number_id: payload.whatsapp.phone_number_id ?? "",
    whatsapp_business_account_id: payload.whatsapp.business_account_id ?? "",
    whatsapp_sender_display_name: payload.whatsapp.sender_display_name ?? "",
    whatsapp_webhook_callback_url: payload.whatsapp.webhook_callback_url ?? "",
    whatsapp_access_token: "",
    whatsapp_webhook_verify_token: "",
  };
}
