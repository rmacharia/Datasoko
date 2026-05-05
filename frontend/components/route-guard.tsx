"use client";

import { usePathname, useRouter } from "next/navigation";
import { useEffect } from "react";

import { useAuth } from "@/components/auth-provider";

const PUBLIC_PATHS = ["/login", "/setup"];

function isPublic(pathname: string): boolean {
  return PUBLIC_PATHS.some((p) => pathname === p || pathname.startsWith(`${p}/`));
}

function isAdminPath(pathname: string): boolean {
  return pathname === "/admin" || pathname.startsWith("/admin/");
}

/**
 * Enforces the platform-vs-tenant split at the routing layer:
 *   - super_admin may only visit /admin/* routes; anything else bounces to /admin
 *   - tenant users (admin, sme_user) may never hit /admin/* routes
 * Public auth pages (/login, /setup) stay open to everyone.
 */
export function RouteGuard({ children }: { children: React.ReactNode }) {
  const { user, isReady } = useAuth();
  const pathname = usePathname();
  const router = useRouter();

  useEffect(() => {
    if (!isReady) return;
    if (!pathname) return;
    if (isPublic(pathname)) return;
    if (!user) return;

    const onAdminPath = isAdminPath(pathname);

    if (user.role === "super_admin" && !onAdminPath) {
      router.replace("/admin");
      return;
    }
    if (user.role !== "super_admin" && onAdminPath) {
      router.replace("/");
      return;
    }
  }, [isReady, pathname, user, router]);

  return <>{children}</>;
}
