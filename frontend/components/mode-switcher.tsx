"use client";

import { useEffect, useState } from "react";
import { useAuth } from "@/components/auth-provider";
import { useOrg } from "@/components/org-provider";
import { getPlatformBusinesses, getPlatformOrganizations } from "@/lib/api";
import type { PlatformBusiness, PlatformOrganization } from "@/lib/api";
import { Select } from "@/components/ui/select";

export function ModeSwitcher() {
  const { token, user } = useAuth();
  const {
    isPlatform,
    selectedOrgId,
    selectedBusinessId,
    setSelectedOrg,
    setSelectedBusiness,
  } = useOrg();

  const [orgs, setOrgs] = useState<Array<{ id: string; name: string | null }>>([]);
  const [businesses, setBusinesses] = useState<Array<{ id: string; name: string | null }>>([]);

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

  // Only render for super_admin
  if (user?.role !== "super_admin" || !token) return null;

  return (
    <div className="border-t border-[var(--border)] bg-[rgba(10,19,33,0.6)]">
      <div className="mx-auto flex max-w-6xl flex-wrap items-center gap-3 px-4 py-2">
        {/* Mode badge */}
        {isPlatform ? (
          <span
            className="badge"
            style={{
              background: "rgba(55,181,255,0.18)",
              color: "var(--accent)",
              border: "1px solid rgba(55,181,255,0.35)",
            }}
          >
            Platform Mode
          </span>
        ) : (
          <span
            className="badge"
            style={{
              background: "rgba(34,197,94,0.18)",
              color: "#22c55e",
              border: "1px solid rgba(34,197,94,0.35)",
            }}
          >
            ● Tenant Mode
          </span>
        )}

        {/* Org dropdown */}
        <Select
          value={selectedOrgId ?? ""}
          onChange={(e) => setSelectedOrg(e.target.value || null)}
          aria-label="Select organization"
          className="py-1 text-xs"
        >
          <option value="">— Select Org —</option>
          {orgs.map((o) => (
            <option key={o.id} value={o.id}>
              {o.name ?? o.id}
            </option>
          ))}
        </Select>

        {/* SME dropdown — only when org selected */}
        {selectedOrgId ? (
          <Select
            value={selectedBusinessId ?? ""}
            onChange={(e) => setSelectedBusiness(e.target.value || null)}
            aria-label="Select SME"
            className="py-1 text-xs"
          >
            <option value="">— Select SME —</option>
            {businesses.map((b) => (
              <option key={b.id} value={b.id}>
                {b.name ?? b.id}
              </option>
            ))}
          </Select>
        ) : null}

        {/* Viewing as / Exit — only in tenant mode */}
        {!isPlatform ? (
          <>
            <span className="ml-auto text-xs font-semibold text-[#22c55e]">
              Viewing as: {selectedOrgId}
              {selectedBusinessId ? ` / ${selectedBusinessId}` : ""}
            </span>
            <button
              onClick={() => setSelectedOrg(null)}
              className="rounded-md border border-[rgba(34,197,94,0.3)] bg-[rgba(10,19,33,0.8)] px-2.5 py-1 text-xs text-[#22c55e] hover:bg-[rgba(34,197,94,0.14)]"
            >
              Exit Tenant View →
            </button>
          </>
        ) : null}
      </div>
    </div>
  );
}
