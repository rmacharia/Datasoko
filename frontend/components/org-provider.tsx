"use client";

import { createContext, useContext, useEffect, useMemo, useState } from "react";

import { useAuth } from "@/components/auth-provider";

const ORG_ID_KEY = "datasoko_org_id";
const BIZ_ID_KEY = "datasoko_active_biz_id";

type OrgContextValue = {
  // For super_admin these are null — the platform has no tenant context.
  organizationId: string | null;
  activeBusinessId: string | null;
  isPlatform: boolean;
  setOrganizationId: (id: string) => void;
  setActiveBusinessId: (id: string) => void;
};

const OrgContext = createContext<OrgContextValue | undefined>(undefined);

export function OrgProvider({ children }: { children: React.ReactNode }) {
  const { user } = useAuth();
  const [organizationId, setOrgIdState] = useState<string | null>(null);
  const [activeBusinessId, setBizIdState] = useState<string | null>(null);

  useEffect(() => {
    if (user?.role === "super_admin") {
      // Platform users have no tenant. Clear any stale localStorage
      // from a previous tenant session so the UI never accidentally
      // queries tenant-scoped endpoints.
      setOrgIdState(null);
      setBizIdState(null);
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
      organizationId,
      activeBusinessId,
      isPlatform: user?.role === "super_admin",
      setOrganizationId: (id: string) => {
        setOrgIdState(id);
        window.localStorage.setItem(ORG_ID_KEY, id);
      },
      setActiveBusinessId: (id: string) => {
        setBizIdState(id);
        window.localStorage.setItem(BIZ_ID_KEY, id);
      },
    }),
    [organizationId, activeBusinessId, user?.role],
  );

  return <OrgContext.Provider value={value}>{children}</OrgContext.Provider>;
}

export function useOrg(): OrgContextValue {
  const context = useContext(OrgContext);
  if (!context) throw new Error("useOrg must be used within OrgProvider");
  return context;
}
