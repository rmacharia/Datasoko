import type { AuthUser } from "@/lib/api";

const PUBLIC_PATHS = ["/login", "/setup"];

export function isPublicPath(pathname: string): boolean {
  return PUBLIC_PATHS.some((path) => pathname === path || pathname.startsWith(`${path}/`));
}

export function isAdminPath(pathname: string): boolean {
  return pathname === "/admin" || pathname.startsWith("/admin/");
}

export function getPostLoginPath(user: AuthUser): string {
  if (user.role === "super_admin") return "/admin";
  return "/";
}

export function getRouteRedirect(
  pathname: string,
  user: AuthUser | null,
  selectedOrgId: string | null,
): string | null {
  if (isPublicPath(pathname)) {
    return user ? getPostLoginPath(user) : null;
  }

  if (!user) {
    return "/login";
  }

  const onAdminPath = isAdminPath(pathname);

  if (user.role === "super_admin") {
    if (onAdminPath) return null;
    return selectedOrgId === null ? "/admin" : null;
  }

  if (onAdminPath) {
    return "/";
  }

  return null;
}
