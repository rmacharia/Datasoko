import { afterEach, describe, expect, it, vi } from "vitest";

import { getAdminReports, isApiError } from "@/lib/api";

describe("isApiError", () => {
  it("returns true for normalized api error", () => {
    expect(isApiError({ status: 400, message: "bad request" })).toBe(true);
  });

  it("returns false for unknown object", () => {
    expect(isApiError({ detail: "x" })).toBe(false);
  });
});

describe("getAdminReports", () => {
  afterEach(() => {
    vi.restoreAllMocks();
  });

  it("sends token and query params to /admin/reports", async () => {
    const fetchMock = vi.fn().mockResolvedValue({
      ok: true,
      headers: { get: () => "application/json" },
      json: async () => ({
        business_id: "biz_001",
        week_start: "2026-03-02",
        week_end: "2026-03-08",
        metrics_json: {},
        llm_narration_json: null,
        whatsapp_preview: { message: "ok" },
      }),
    });
    vi.stubGlobal("fetch", fetchMock);

    await getAdminReports("token_123", {
      businessId: "biz_001",
      weekStart: "2026-03-02",
      weekEnd: "2026-03-08",
    });

    expect(fetchMock).toHaveBeenCalledTimes(1);
    const [url, options] = fetchMock.mock.calls[0];
    expect(String(url)).toContain("/admin/reports?");
    expect(String(url)).toContain("business_id=biz_001");
    expect(String(url)).toContain("week_start=2026-03-02");
    expect(String(url)).toContain("week_end=2026-03-08");
    const headers = new Headers(options.headers);
    expect(headers.get("Authorization")).toBe("Bearer token_123");
  });
});
