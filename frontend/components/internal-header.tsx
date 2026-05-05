"use client";

import Link from "next/link";
import { usePathname } from "next/navigation";
import { useEffect, useMemo, useState } from "react";

import { useAuth } from "@/components/auth-provider";
import { useOrg } from "@/components/org-provider";
import { useSettings } from "@/components/settings-provider";
import { Button } from "@/components/ui/button";
import { getHealth, isApiError } from "@/lib/api";

const superAdminLinks = [
  { href: "/admin", label: "Admin" },
  { href: "/admin/users", label: "Users" },
  { href: "/admin/organizations", label: "Organizations" },
  { href: "/admin/businesses", label: "SMEs" },
];

const orgAdminLinks = [
  { href: "/", label: "Overview" },
  { href: "/upload", label: "Upload" },
  { href: "/reports", label: "Reports" },
  { href: "/jobs", label: "Jobs" },
  { href: "/users", label: "Users" },
  { href: "/settings", label: "Settings" },
];

const smeLinks = [
  { href: "/", label: "Overview" },
  { href: "/upload", label: "Upload" },
  { href: "/reports", label: "Reports" },
];

function linksForRole(role: string | undefined) {
  if (role === "super_admin") return superAdminLinks;
  if (role === "sme_user") return smeLinks;
  return orgAdminLinks;
}

export function InternalHeader() {
  const { token, user, logout } = useAuth();
  const { enhancedMode, effectiveEnhancedMode, setEnhancedMode } = useSettings();
  const { organizationId, activeBusinessId } = useOrg();
  const pathname = usePathname();

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
          {token && user?.role !== "super_admin" ? (
            <>
              <span className="rounded-md border border-[var(--border)] bg-[rgba(10,19,33,0.85)] px-2.5 py-1 text-xs">
                <span className="muted">Org:</span>{" "}
                <span className="font-semibold text-[var(--text)]">{organizationId}</span>
              </span>
              <span className="rounded-md border border-[var(--border)] bg-[rgba(10,19,33,0.85)] px-2.5 py-1 text-xs">
                <span className="muted">SME:</span>{" "}
                <span className="font-semibold text-[var(--text)]">{activeBusinessId}</span>
              </span>
            </>
          ) : null}

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
            {linksForRole(user?.role).map((item) => {
              const isActive = item.href === "/" ? pathname === "/" : pathname.startsWith(item.href);
              return (
                <Link
                  key={item.href}
                  className={`rounded-md border border-transparent px-3 py-2 text-sm font-semibold transition hover:border-[var(--border)] hover:bg-[rgba(79,121,199,0.14)] hover:text-[var(--text)] ${
                    isActive ? "nav-link-active" : "text-[var(--text-muted)]"
                  }`}
                  href={item.href}
                  aria-current={isActive ? "page" : undefined}
                >
                  {item.label}
                </Link>
              );
            })}
            {user ? (
              <span className="rounded-md border border-[var(--border)] bg-[rgba(10,19,33,0.85)] px-2.5 py-1 text-xs">
                <span className="muted">{user.email}</span>{" "}
                <span className={`font-semibold uppercase ${user.role === "super_admin" || user.role === "admin" ? "text-[var(--accent)]" : "text-[var(--ok)]"}`}>
                  {user.role}
                </span>
              </span>
            ) : null}
            <Button variant="ghost" onClick={logout} className="ml-1">
              Log out
            </Button>
          </nav>
        ) : null}
      </div>
    </header>
  );
}
