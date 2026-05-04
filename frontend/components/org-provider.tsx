"use client";

import { createContext, useContext, useEffect, useMemo, useState } from "react";

const ORG_ID_KEY = "datasoko_org_id";
const BIZ_ID_KEY = "datasoko_active_biz_id";

type OrgContextValue = {
  organizationId: string;
  activeBusinessId: string;
  setOrganizationId: (id: string) => void;
  setActiveBusinessId: (id: string) => void;
};

const OrgContext = createContext<OrgContextValue | undefined>(undefined);

export function OrgProvider({ children }: { children: React.ReactNode }) {
  const [organizationId, setOrgIdState] = useState("default_org");
  const [activeBusinessId, setBizIdState] = useState("biz_001");

  useEffect(() => {
    const storedOrg = window.localStorage.getItem(ORG_ID_KEY);
    const storedBiz = window.localStorage.getItem(BIZ_ID_KEY);
    if (storedOrg) setOrgIdState(storedOrg);
    if (storedBiz) setBizIdState(storedBiz);
  }, []);

  const value = useMemo<OrgContextValue>(
    () => ({
      organizationId,
      activeBusinessId,
      setOrganizationId: (id: string) => {
        setOrgIdState(id);
        window.localStorage.setItem(ORG_ID_KEY, id);
      },
      setActiveBusinessId: (id: string) => {
        setBizIdState(id);
        window.localStorage.setItem(BIZ_ID_KEY, id);
      },
    }),
    [organizationId, activeBusinessId],
  );

  return <OrgContext.Provider value={value}>{children}</OrgContext.Provider>;
}

export function useOrg(): OrgContextValue {
  const context = useContext(OrgContext);
  if (!context) throw new Error("useOrg must be used within OrgProvider");
  return context;
}
