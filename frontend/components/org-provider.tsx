"use client";

import { createContext, useContext, useEffect, useMemo, useState } from "react";

import { useAuth } from "@/components/auth-provider";

const ORG_ID_KEY = "datasoko_org_id";
const BIZ_ID_KEY = "datasoko_active_biz_id";
const CONTEXT_KEY = "datasoko_context";

type SuperAdminContext = {
  orgId: string | null;
  bizId: string | null;
};

type OrgContextValue = {
  // For non-super_admin: populated from JWT. For super_admin: mirrors selectedOrgId/selectedBusinessId.
  organizationId: string | null;
  activeBusinessId: string | null;
  isPlatform: boolean;
  // super_admin context switching
  selectedOrgId: string | null;
  selectedBusinessId: string | null;
  setSelectedOrg: (orgId: string | null) => void;
  setSelectedBusiness: (bizId: string | null) => void;
  // Non-super_admin setters (preserved for existing flows)
  setOrganizationId: (id: string) => void;
  setActiveBusinessId: (id: string) => void;
};

const OrgContext = createContext<OrgContextValue | undefined>(undefined);

export function OrgProvider({ children }: { children: React.ReactNode }) {
  const { user } = useAuth();

  // State for non-super_admin users (populated from JWT)
  const [orgIdState, setOrgIdState] = useState<string | null>(null);
  const [bizIdState, setBizIdState] = useState<string | null>(null);

  // State for super_admin context switching (persisted to datasoko_context)
  const [selectedOrgId, setSelectedOrgId] = useState<string | null>(null);
  const [selectedBusinessId, setSelectedBusinessId] = useState<string | null>(null);

  useEffect(() => {
    if (user?.role === "super_admin") {
      // Restore super_admin's chosen context from localStorage.
      // Do NOT clear it — the selection is intentional and survives page reloads.
      try {
        const raw = window.localStorage.getItem(CONTEXT_KEY);
        if (raw) {
          const ctx = JSON.parse(raw) as SuperAdminContext;
          setSelectedOrgId(ctx.orgId ?? null);
          setSelectedBusinessId(ctx.bizId ?? null);
        }
      } catch {
        // Corrupt entry — ignore; state stays null
      }
      return;
    }

    if (user) {
      if (user.organization_id) setOrgIdState(user.organization_id);
      if (user.business_id) setBizIdState(user.business_id);
      return;
    }

    // No user (e.g. login screen) — fall back to localStorage so the
    // form can preselect the last-used org.
    const storedOrg = window.localStorage.getItem(ORG_ID_KEY);
    const storedBiz = window.localStorage.getItem(BIZ_ID_KEY);
    if (storedOrg) setOrgIdState(storedOrg);
    if (storedBiz) setBizIdState(storedBiz);
  }, [user]);

  const value = useMemo<OrgContextValue>(
    () => ({
      // Expose the right IDs depending on role
      organizationId: user?.role === "super_admin" ? selectedOrgId : orgIdState,
      activeBusinessId:
        user?.role === "super_admin" ? selectedBusinessId : bizIdState,
      // isPlatform: true when super_admin has no selected org (pure platform mode)
      isPlatform:
        user?.role === "super_admin" ? selectedOrgId === null : false,

      // super_admin context
      selectedOrgId,
      selectedBusinessId,

      setSelectedOrg: (orgId: string | null) => {
        setSelectedOrgId(orgId);
        setSelectedBusinessId(null); // reset business when org changes
        if (orgId === null) {
          // Clearing org → remove key entirely (platform mode)
          window.localStorage.removeItem(CONTEXT_KEY);
        } else {
          const ctx: SuperAdminContext = { orgId, bizId: null };
          window.localStorage.setItem(CONTEXT_KEY, JSON.stringify(ctx));
        }
      },

      setSelectedBusiness: (bizId: string | null) => {
        setSelectedBusinessId(bizId);
        const ctx: SuperAdminContext = { orgId: selectedOrgId, bizId };
        window.localStorage.setItem(CONTEXT_KEY, JSON.stringify(ctx));
      },

      // Non-super_admin setters — preserved for existing flows
      setOrganizationId: (id: string) => {
        setOrgIdState(id);
        window.localStorage.setItem(ORG_ID_KEY, id);
      },
      setActiveBusinessId: (id: string) => {
        setBizIdState(id);
        window.localStorage.setItem(BIZ_ID_KEY, id);
      },
    }),
    [orgIdState, bizIdState, selectedOrgId, selectedBusinessId, user?.role],
  );

  return <OrgContext.Provider value={value}>{children}</OrgContext.Provider>;
}

export function useOrg(): OrgContextValue {
  const context = useContext(OrgContext);
  if (!context) throw new Error("useOrg must be used within OrgProvider");
  return context;
}
