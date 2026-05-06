import { describe, expect, it } from "vitest";

import { getPostLoginPath, getRouteRedirect } from "@/lib/routing";
import type { AuthUser } from "@/lib/api";

const baseUser: AuthUser = {
  id: "u1",
  email: "user@example.com",
  role: "admin",
  organization_id: "org1",
  business_id: null,
};

describe("auth routing decisions", () => {
  it("sends tenant users to overview after login", () => {
    expect(getPostLoginPath({ ...baseUser, role: "admin" })).toBe("/");
    expect(getPostLoginPath({ ...baseUser, role: "sme_user", business_id: "biz1" })).toBe("/");
  });

  it("sends platform users to the platform console after login", () => {
    expect(getPostLoginPath({ ...baseUser, role: "super_admin", organization_id: null })).toBe("/admin");
  });

  it("redirects direct protected-page visits to login when anonymous", () => {
    expect(getRouteRedirect("/reports", null, null)).toBe("/login");
    expect(getRouteRedirect("/admin/users", null, null)).toBe("/login");
  });

  it("redirects authenticated users away from public auth pages", () => {
    expect(getRouteRedirect("/login", { ...baseUser, role: "admin" }, null)).toBe("/");
    expect(getRouteRedirect("/setup", { ...baseUser, role: "super_admin", organization_id: null }, null)).toBe("/admin");
  });

  it("keeps tenant users out of platform admin routes", () => {
    expect(getRouteRedirect("/admin/businesses", baseUser, null)).toBe("/");
  });

  it("requires super admins to choose an org before tenant routes", () => {
    const superAdmin = { ...baseUser, role: "super_admin" as const, organization_id: null };
    expect(getRouteRedirect("/", superAdmin, null)).toBe("/admin");
    expect(getRouteRedirect("/", superAdmin, "org1")).toBe(null);
  });
});
