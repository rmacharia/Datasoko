"use client";

import Link from "next/link";
import { useEffect, useMemo, useState } from "react";

import { useAuth } from "@/components/auth-provider";
import { useSettings } from "@/components/settings-provider";
import { Button } from "@/components/ui/button";
import { getHealth, isApiError } from "@/lib/api";

const links = [
  { href: "/", label: "Overview" },
  { href: "/upload", label: "Upload" },
  { href: "/reports", label: "Reports" },
  { href: "/jobs", label: "Jobs" },
  { href: "/settings", label: "Settings" },
];

export function InternalHeader() {
  const { token, logout } = useAuth();
  const { enhancedMode, effectiveEnhancedMode, setEnhancedMode } = useSettings();

  const [reachable, setReachable] = useState<boolean | null>(null);

  useEffect(() => {
    let isMounted = true;

    const ping = async () => {
      try {
        await getHealth();
        if (isMounted) setReachable(true);
      } catch (error) {
        if (isApiError(error)) {
          if (isMounted) setReachable(false);
          return;
        }
        if (isMounted) setReachable(false);
      }
    };

    void ping();
    const id = window.setInterval(() => void ping(), 15000);
    return () => {
      isMounted = false;
      window.clearInterval(id);
    };
  }, []);

  const reachabilityLabel = useMemo(() => {
    if (reachable === null) return { text: "Checking", cls: "badge badge-warn" };
    if (reachable) return { text: "Backend Reachable", cls: "badge badge-ok" };
    return { text: "Backend Offline", cls: "badge badge-danger" };
  }, [reachable]);

  return (
    <header className="console-bar sticky top-0 z-40">
      <div className="mx-auto flex max-w-6xl flex-wrap items-center justify-between gap-3 px-4 py-3">
        <div>
          <div className="text-xs uppercase tracking-[0.12em] text-[var(--text-muted)]">DataSoko Internal</div>
          <div className="text-lg font-semibold">Ops Console</div>
        </div>

        <div className="flex flex-wrap items-center gap-2">
          <span className="badge border border-[var(--border-bright)] bg-[rgba(55,181,255,0.12)] text-[var(--accent)]">DEV</span>
          <span className={reachabilityLabel.cls}>{reachabilityLabel.text}</span>

          <label className="inline-flex items-center gap-2 rounded-md border border-[var(--border)] bg-[rgba(10,19,33,0.8)] px-3 py-1 text-xs font-semibold">
            <input
              type="checkbox"
              checked={enhancedMode}
              onChange={(event) => setEnhancedMode(event.target.checked)}
              aria-label="Enhanced Mode"
            />
            Enhanced Mode
            {enhancedMode && !effectiveEnhancedMode ? <span className="muted">(reduced motion active)</span> : null}
          </label>
        </div>

        {token ? (
          <nav aria-label="Primary" className="flex flex-wrap items-center gap-2">
            {links.map((item) => (
              <Link
                key={item.href}
                className="rounded-md border border-transparent px-3 py-2 text-sm font-semibold text-[var(--text-muted)] transition hover:border-[var(--border)] hover:bg-[rgba(79,121,199,0.14)] hover:text-[var(--text)]"
                href={item.href}
              >
                {item.label}
              </Link>
            ))}
            <Button variant="ghost" onClick={logout} className="ml-1">
              Log out
            </Button>
          </nav>
        ) : null}
      </div>
    </header>
  );
}
