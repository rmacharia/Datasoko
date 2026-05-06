import type { AuthUser } from "@/lib/api";

export function tenantContextFromUser(user: AuthUser | null): {
  orgId: string | null;
  bizId: string | null;
} {
  if (!user || user.role === "super_admin") {
    return { orgId: null, bizId: null };
  }
  return {
    orgId: user.organization_id ?? null,
    bizId: user.business_id ?? null,
  };
}
