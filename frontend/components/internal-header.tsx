"use client";

import Link from "next/link";
import { usePathname } from "next/navigation";
import { useEffect, useMemo, useState } from "react";

import { useAuth } from "@/components/auth-provider";
import { useOrg } from "@/components/org-provider";
import { useSettings } from "@/components/settings-provider";
import { Button } from "@/components/ui/button";
import { getHealth, getPlatformBusinesses, getPlatformOrganizations, isApiError } from "@/lib/api";
import type { PlatformBusiness, PlatformOrganization } from "@/lib/api";

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

function linksForRole(role: string | undefined, isPlatform: boolean) {
  if (role === "super_admin") return isPlatform ? superAdminLinks : orgAdminLinks;
  if (role === "sme_user") return smeLinks;
  return orgAdminLinks;
}

export function InternalHeader() {
  const { token, user, logout } = useAuth();
  const { enhancedMode, effectiveEnhancedMode, setEnhancedMode } = useSettings();
  const {
    organizationId,
    activeBusinessId,
    isPlatform,
    selectedOrgId,
    selectedBusinessId,
    setSelectedOrg,
    setSelectedBusiness,
  } = useOrg();
  const pathname = usePathname();

  const [reachable, setReachable] = useState<boolean | null>(null);
  const [orgs, setOrgs] = useState<Array<{ id: string; name: string | null }>>([]);
  const [businesses, setBusinesses] = useState<Array<{ id: string; name: string | null }>>([]);

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

  // Load orgs for super_admin
  useEffect(() => {
    if (!token || user?.role !== "super_admin") return;

    let isMounted = true;

    const loadOrgs = async () => {
      try {
        const data: PlatformOrganization[] = await getPlatformOrganizations(token);
        if (isMounted) {
          setOrgs(data.map((o) => ({ id: o.id, name: o.name })));
        }
      } catch {
        // Silently fail — the dropdown will just be empty
      }
    };

    void loadOrgs();
    return () => {
      isMounted = false;
    };
  }, [token, user?.role]);

  // Load businesses when selectedOrgId changes (super_admin only)
  useEffect(() => {
    if (!token || user?.role !== "super_admin" || !selectedOrgId) {
      setBusinesses([]);
      return;
    }

    let isMounted = true;

    const loadBusinesses = async () => {
      try {
        const data: PlatformBusiness[] = await getPlatformBusinesses(token);
        if (isMounted) {
          // Filter to only businesses belonging to the selected org
          const filtered = data
            .filter((b) => b.organization_id === selectedOrgId)
            .map((b) => ({ id: b.id, name: b.name }));
          setBusinesses(filtered);
        }
      } catch {
        if (isMounted) setBusinesses([]);
      }
    };

    void loadBusinesses();
    return () => {
      isMounted = false;
    };
  }, [token, user?.role, selectedOrgId]);

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

          {user?.role === "super_admin" && token ? (
            <div className="flex flex-wrap items-center gap-2 border-t border-[var(--border)] pt-2 w-full">
              {/* Mode badge */}
              {isPlatform ? (
                <span className="badge" style={{ background: "rgba(55,181,255,0.18)", color: "var(--accent)", border: "1px solid rgba(55,181,255,0.35)" }}>
                  Platform Mode
                </span>
              ) : (
                <span className="badge" style={{ background: "rgba(34,197,94,0.18)", color: "#22c55e", border: "1px solid rgba(34,197,94,0.35)" }}>
                  Tenant Mode
                </span>
              )}

              {/* Platform Mode button (shown in tenant mode to go back) */}
              {!isPlatform && (
                <button
                  onClick={() => setSelectedOrg(null)}
                  className="rounded-md border border-[var(--border)] bg-[rgba(10,19,33,0.8)] px-2.5 py-1 text-xs hover:bg-[rgba(79,121,199,0.14)]"
                >
                  Platform Mode
                </button>
              )}

              {/* Org dropdown */}
              <select
                value={selectedOrgId ?? ""}
                onChange={(e) => setSelectedOrg(e.target.value || null)}
                className="rounded-md border border-[var(--border)] bg-[rgba(10,19,33,0.8)] px-2 py-1 text-xs text-[var(--text)]"
                aria-label="Select organization"
              >
                <option value="">— Select Org —</option>
                {orgs.map((o) => (
                  <option key={o.id} value={o.id}>{o.name ?? o.id}</option>
                ))}
              </select>

              {/* SME dropdown (only if org selected) */}
              {selectedOrgId && (
                <select
                  value={selectedBusinessId ?? ""}
                  onChange={(e) => setSelectedBusiness(e.target.value || null)}
                  className="rounded-md border border-[var(--border)] bg-[rgba(10,19,33,0.8)] px-2 py-1 text-xs text-[var(--text)]"
                  aria-label="Select SME"
                >
                  <option value="">— Select SME —</option>
                  {businesses.map((b) => (
                    <option key={b.id} value={b.id}>{b.name ?? b.id}</option>
                  ))}
                </select>
              )}
            </div>
          ) : null}
        </div>

        {token ? (
          <nav aria-label="Primary" className="flex flex-wrap items-center gap-2">
            {linksForRole(user?.role, isPlatform).map((item) => {
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

      {/* Tenant mode banner */}
      {user?.role === "super_admin" && !isPlatform ? (
        <div className="mx-auto flex max-w-6xl items-center justify-between gap-3 px-4 py-2 border-t border-[rgba(34,197,94,0.3)] bg-[rgba(34,197,94,0.07)]">
          <span className="text-xs text-[#22c55e] font-semibold">
            Viewing as: {selectedOrgId}{selectedBusinessId ? ` / ${selectedBusinessId}` : ""}
          </span>
          <button
            onClick={() => { setSelectedOrg(null); }}
            className="rounded-md border border-[rgba(34,197,94,0.3)] bg-[rgba(10,19,33,0.8)] px-2.5 py-1 text-xs text-[#22c55e] hover:bg-[rgba(34,197,94,0.14)]"
          >
            Exit Tenant View →
          </button>
        </div>
      ) : null}
    </header>
  );
}
