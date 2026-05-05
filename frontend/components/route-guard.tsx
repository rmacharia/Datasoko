"use client";

import { usePathname, useRouter } from "next/navigation";
import { useEffect } from "react";

import { useAuth } from "@/components/auth-provider";
import { useOrg } from "@/components/org-provider";

const PUBLIC_PATHS = ["/login", "/setup"];

function isPublic(pathname: string): boolean {
  return PUBLIC_PATHS.some((p) => pathname === p || pathname.startsWith(`${p}/`));
}

function isAdminPath(pathname: string): boolean {
  return pathname === "/admin" || pathname.startsWith("/admin/");
}

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

  useEffect(() => {
    if (!isReady) return;
    if (!pathname) return;
    if (isPublic(pathname)) return;
    if (!user) return;

    const onAdminPath = isAdminPath(pathname);

    if (user.role === "super_admin") {
      if (onAdminPath) {
        // Platform Mode — always allow /admin/*
        return;
      }
      // Tenant route: only allow when an org has been selected
      if (selectedOrgId === null) {
        router.replace("/admin");
      }
      return;
    }

    // Non-super_admin users must never visit /admin/*
    if (onAdminPath) {
      router.replace("/");
    }
  }, [isReady, pathname, user, selectedOrgId, router]);

  return <>{children}</>;
}
