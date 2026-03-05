import { describe, expect, it } from "vitest";

import type { AdminSettingsResponse } from "@/lib/api";
import { toSettingsFormDefaults } from "@/lib/settings";

describe("settings secrets safety", () => {
  it("keeps secret form fields empty even when server reports saved secrets", () => {
    const payload: AdminSettingsResponse = {
      operational: {
        default_business_id: "biz_001",
        default_currency: "KES",
        timezone: "Africa/Nairobi",
        report_schedule_day: "Friday",
        report_schedule_time: "18:00",
      },
      ai: {
        provider: "azure_openai",
        model: "gpt-4.1-mini",
        temperature: 0.2,
        max_output_tokens: 700,
        strict_json_only: true,
        metrics_only_fallback: true,
        has_api_key: true,
      },
      whatsapp: {
        provider: "meta_cloud_api",
        phone_number_id: "12345",
        business_account_id: null,
        sender_display_name: null,
        webhook_callback_url: "https://example.com/webhook",
        has_access_token: true,
        has_webhook_verify_token: true,
      },
    };

    const defaults = toSettingsFormDefaults(payload);
    expect(defaults.ai_api_key).toBe("");
    expect(defaults.whatsapp_access_token).toBe("");
    expect(defaults.whatsapp_webhook_verify_token).toBe("");
  });
});
