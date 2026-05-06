"use client";

import { usePathname, useRouter } from "next/navigation";
import { useEffect } from "react";

import { useAuth } from "@/components/auth-provider";
import { useOrg } from "@/components/org-provider";
import { getRouteRedirect } from "@/lib/routing";

/**
 * Enforces the platform-vs-tenant split at the routing layer:
 *   - super_admin on /admin/* → always allowed (Platform Mode)
 *   - super_admin on tenant routes → allowed only when selectedOrgId is set (Tenant Mode);
 *     otherwise bounces to /admin so they must choose an org first
 *   - tenant users (admin, sme_user) may never hit /admin/* routes
 * Public auth pages (/login, /setup) stay open to everyone.
 */
export function RouteGuard({ children }: { children: React.ReactNode }) {
  const { user, isReady } = useAuth();
  const { selectedOrgId } = useOrg();
  const pathname = usePathname();
  const router = useRouter();
  const redirectTo = isReady && pathname ? getRouteRedirect(pathname, user, selectedOrgId) : null;

  useEffect(() => {
    if (!isReady) return;
    if (!pathname) return;

    if (redirectTo && redirectTo !== pathname) {
      router.replace(redirectTo);
    }
  }, [isReady, pathname, redirectTo, router]);

  if (redirectTo && redirectTo !== pathname) {
    return null;
  }

  return <>{children}</>;
}
