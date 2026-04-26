export const config = {
  configuredApiBaseUrl: process.env.NEXT_PUBLIC_API_BASE_URL ?? "",
  sessionTokenKey: "datasoko_admin_token",
} as const;

function normalizeBaseUrl(url: string): string {
  return url.trim().replace(/\/+$/, "");
}

export function getApiBaseUrlCandidates(): string[] {
  const candidates: string[] = [];
  const configured = normalizeBaseUrl(config.configuredApiBaseUrl);
  if (configured) {
    candidates.push(configured);
  }

  if (typeof window !== "undefined") {
    const runtimeHostUrl = normalizeBaseUrl(`${window.location.protocol}//${window.location.hostname}:8000`);
    if (runtimeHostUrl) {
      candidates.push(runtimeHostUrl);
    }
  }

  candidates.push("http://localhost:8000");
  return Array.from(new Set(candidates));
}
