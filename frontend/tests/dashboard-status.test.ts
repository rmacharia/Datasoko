import { describe, expect, it } from "vitest";

import { buildTenantRuntimeStatus } from "@/lib/dashboard-status";

describe("tenant dashboard runtime status", () => {
  it("builds overview status without platform-only admin diagnostics", () => {
    const status = buildTenantRuntimeStatus(
      { status: "ok" },
      {
        app_version: "0.1.0",
        schema_version: "1.0",
        normalizer_version: "1.0",
        contract_version: "1.0",
      },
    );

    expect(status.backend_health).toBe("ok");
    expect(status.version.app_version).toBe("0.1.0");
    expect(status.db.connected).toBe(true);
    expect(status.db.error).toBeNull();
    expect(status.last_run).toBeNull();
  });
});
