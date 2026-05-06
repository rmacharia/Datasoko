import { describe, expect, it } from "vitest";

import { tenantContextFromUser } from "@/lib/org-session";
import type { AuthUser } from "@/lib/api";

const user: AuthUser = {
  id: "u1",
  email: "tenant@example.com",
  role: "admin",
  organization_id: "org1",
  business_id: null,
};

describe("tenant context from authenticated user", () => {
  it("clears stale business context for org admins", () => {
    expect(tenantContextFromUser(user)).toEqual({ orgId: "org1", bizId: null });
  });

  it("uses assigned org and business for sme users", () => {
    expect(
      tenantContextFromUser({
        ...user,
        role: "sme_user",
        business_id: "biz1",
      }),
    ).toEqual({ orgId: "org1", bizId: "biz1" });
  });

  it("does not invent tenant context for super admins", () => {
    expect(
      tenantContextFromUser({
        ...user,
        role: "super_admin",
        organization_id: null,
        business_id: null,
      }),
    ).toEqual({ orgId: null, bizId: null });
  });
});
