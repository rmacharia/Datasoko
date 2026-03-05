import { config } from "@/lib/config";

export function readStoredToken(): string | null {
  if (typeof window === "undefined") {
    return null;
  }
  return window.sessionStorage.getItem(config.sessionTokenKey);
}

export function writeStoredToken(token: string): void {
  if (typeof window === "undefined") {
    return;
  }
  window.sessionStorage.setItem(config.sessionTokenKey, token);
}

export function clearStoredToken(): void {
  if (typeof window === "undefined") {
    return;
  }
  window.sessionStorage.removeItem(config.sessionTokenKey);
}
