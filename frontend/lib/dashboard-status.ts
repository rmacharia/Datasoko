import type { AdminStatusResponse, HealthResponse, VersionResponse } from "@/lib/api";

export function buildTenantRuntimeStatus(
  health: HealthResponse,
  version: VersionResponse,
): AdminStatusResponse {
  return {
    backend_health: health.status,
    version,
    db: {
      connected: health.status === "ok",
      error: null,
    },
    last_run: null,
  };
}
