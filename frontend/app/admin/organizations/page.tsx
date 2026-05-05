"use client";

import { useRouter } from "next/navigation";
import { useEffect, useState } from "react";

import { AuthGuard } from "@/components/auth-guard";
import { useAuth } from "@/components/auth-provider";
import { useOrg } from "@/components/org-provider";
import { useToast } from "@/components/toast-provider";
import { Alert } from "@/components/ui/alert";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import {
  createPlatformOrganization,
  getPlatformOrganizations,
  isApiError,
  type PlatformOrganization,
} from "@/lib/api";

export default function AdminOrganizationsPage() {
  const router = useRouter();
  const { token, user, isReady } = useAuth();
  const { setSelectedOrg } = useOrg();
  const { pushToast } = useToast();

  const [orgs, setOrgs] = useState<PlatformOrganization[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  const [name, setName] = useState("");
  const [orgId, setOrgId] = useState("");
  const [adminEmail, setAdminEmail] = useState("");
  const [adminPassword, setAdminPassword] = useState("");
  const [submitting, setSubmitting] = useState(false);

  useEffect(() => {
    if (!isReady || !user) return;
    if (user.role !== "super_admin") router.replace("/");
  }, [isReady, user, router]);

  const load = async () => {
    if (!token) return;
    setLoading(true);
    try {
      const res = await getPlatformOrganizations(token);
      setOrgs(res);
    } catch (err) {
      setError(isApiError(err) ? err.message : "Failed to load organizations");
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    void load();
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [token]);

  const onCreate = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!token || !name.trim() || !adminEmail.trim() || adminPassword.length < 6) return;
    setSubmitting(true);
    setError(null);
    try {
      const res = await createPlatformOrganization(token, {
        name: name.trim(),
        organization_id: orgId.trim() || undefined,
        admin_email: adminEmail.trim(),
        admin_password: adminPassword,
      });
      pushToast(`Organization "${res.organization_id}" created`, "success");
      setName(""); setOrgId(""); setAdminEmail(""); setAdminPassword("");
      void load();
    } catch (err) {
      const msg = isApiError(err) ? err.message : "Failed to create organization";
      setError(msg);
      pushToast(msg, "danger");
    } finally {
      setSubmitting(false);
    }
  };

  if (!isReady || !user || user.role !== "super_admin") return null;

  return (
    <AuthGuard>
      <main className="mx-auto max-w-6xl p-4 md:p-6">
        <header className="mb-6">
          <p className="text-xs uppercase tracking-[0.14em] text-[var(--text-muted)]">Platform</p>
          <h1 className="mt-1 text-2xl font-semibold tracking-tight">Organizations</h1>
          <p className="mt-2 text-sm muted">Create tenants and their first admin user.</p>
        </header>

        {error ? <Alert tone="danger">{error}</Alert> : null}

        <section className="card p-6 mb-6">
          <h2 className="text-lg font-semibold">Create Organization</h2>
          <form className="mt-4 grid gap-4 md:grid-cols-2" onSubmit={(e) => void onCreate(e)}>
            <label className="text-sm font-medium">
              Organization Name *
              <Input value={name} onChange={(e) => setName(e.target.value)} placeholder="Acme Ltd" className="mt-1" required />
            </label>
            <label className="text-sm font-medium">
              Organization ID (optional)
              <Input value={orgId} onChange={(e) => setOrgId(e.target.value)} placeholder="acme_ltd" className="mt-1" />
            </label>
            <label className="text-sm font-medium">
              Admin Email *
              <Input type="email" value={adminEmail} onChange={(e) => setAdminEmail(e.target.value)} placeholder="admin@acme.com" className="mt-1" required />
            </label>
            <label className="text-sm font-medium">
              Admin Password *
              <Input type="password" value={adminPassword} onChange={(e) => setAdminPassword(e.target.value)} placeholder="Min. 6 characters" className="mt-1" required minLength={6} />
            </label>
            <div className="md:col-span-2">
              <Button type="submit" variant="primary" disabled={submitting}>
                {submitting ? "Creating..." : "Create Organization"}
              </Button>
            </div>
          </form>
        </section>

        <section className="card p-6">
          <h2 className="text-lg font-semibold">All Organizations</h2>
          {loading ? (
            <p className="mt-3 text-sm muted">Loading...</p>
          ) : orgs.length > 0 ? (
            <div className="mt-4 overflow-x-auto rounded-md border border-[var(--border)]">
              <table className="w-full text-sm">
                <thead>
                  <tr className="border-b border-[var(--border)] bg-[rgba(10,19,33,0.7)] text-left">
                    <th className="px-4 py-2 font-semibold">ID</th>
                    <th className="px-4 py-2 font-semibold">Name</th>
                    <th className="px-4 py-2 font-semibold">Users</th>
                    <th className="px-4 py-2 font-semibold">SMEs</th>
                    <th className="px-4 py-2 font-semibold">Plan</th>
                    <th className="px-4 py-2 font-semibold">Status</th>
                    <th className="px-4 py-2 font-semibold">Created</th>
                    <th className="px-4 py-2 font-semibold">Actions</th>
                  </tr>
                </thead>
                <tbody>
                  {orgs.map((o) => (
                    <tr key={o.id} className="border-b border-[var(--border)] last:border-0 hover:bg-[rgba(79,121,199,0.07)]">
                      <td className="px-4 py-2 font-mono text-xs">{o.id}</td>
                      <td className="px-4 py-2">{o.name ?? "—"}</td>
                      <td className="px-4 py-2 tabular-nums">{o.user_count}</td>
                      <td className="px-4 py-2 tabular-nums">{o.business_count}</td>
                      <td className="px-4 py-2 capitalize">{o.plan ?? "—"}</td>
                      <td className="px-4 py-2">
                        <span className={`badge ${o.status === "active" ? "badge-ok" : "badge-warn"}`}>
                          {o.status ?? "—"}
                        </span>
                      </td>
                      <td className="px-4 py-2 text-xs muted">{new Date(o.created_at).toLocaleDateString()}</td>
                      <td className="px-4 py-2">
                        {user.role === "super_admin" && (
                          <button
                            onClick={() => { setSelectedOrg(o.id); router.push("/"); }}
                            className="rounded-md border border-[var(--border)] bg-[rgba(10,19,33,0.8)] px-2.5 py-1 text-xs hover:bg-[rgba(79,121,199,0.14)]"
                          >
                            View as user →
                          </button>
                        )}
                      </td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
          ) : (
            <p className="mt-3 text-sm muted">No organizations yet.</p>
          )}
        </section>
      </main>
    </AuthGuard>
  );
}
