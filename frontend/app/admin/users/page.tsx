"use client";

import { useRouter } from "next/navigation";
import { useEffect, useState } from "react";

import { AuthGuard } from "@/components/auth-guard";
import { useAuth } from "@/components/auth-provider";
import { Alert } from "@/components/ui/alert";
import { getUsers, isApiError, type ManagedUser } from "@/lib/api";

export default function AdminUsersPage() {
  const router = useRouter();
  const { token, user, isReady } = useAuth();
  const [users, setUsers] = useState<ManagedUser[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    if (!isReady || !user) return;
    if (user.role !== "super_admin") {
      router.replace("/");
    }
  }, [isReady, user, router]);

  useEffect(() => {
    if (!token || user?.role !== "super_admin") return;
    let mounted = true;
    setLoading(true);
    void getUsers(token)
      .then((res) => { if (mounted) setUsers(res); })
      .catch((err) => { if (mounted) setError(isApiError(err) ? err.message : "Failed to load users"); })
      .finally(() => { if (mounted) setLoading(false); });
    return () => { mounted = false; };
  }, [token, user?.role]);

  if (!isReady || !user || user.role !== "super_admin") return null;

  return (
    <AuthGuard>
      <main className="mx-auto max-w-6xl p-4 md:p-6">
        <header className="mb-6">
          <p className="text-xs uppercase tracking-[0.14em] text-[var(--text-muted)]">
            Platform
          </p>
          <h1 className="mt-1 text-2xl font-semibold tracking-tight">All Users</h1>
          <p className="mt-2 text-sm muted">
            Cross-organization view of every user on the platform.
          </p>
        </header>

        {error ? <Alert tone="danger">{error}</Alert> : null}

        <section className="card p-6">
          {loading ? (
            <p className="text-sm muted">Loading users...</p>
          ) : users.length > 0 ? (
            <div className="overflow-x-auto rounded-md border border-[var(--border)]">
              <table className="w-full text-sm">
                <thead>
                  <tr className="border-b border-[var(--border)] bg-[rgba(10,19,33,0.7)] text-left">
                    <th className="px-4 py-2 font-semibold">Email</th>
                    <th className="px-4 py-2 font-semibold">Role</th>
                    <th className="px-4 py-2 font-semibold">Organization</th>
                    <th className="px-4 py-2 font-semibold">Business</th>
                    <th className="px-4 py-2 font-semibold">Status</th>
                    <th className="px-4 py-2 font-semibold">Created</th>
                  </tr>
                </thead>
                <tbody>
                  {users.map((u) => (
                    <tr key={u.id} className="border-b border-[var(--border)] last:border-0 hover:bg-[rgba(79,121,199,0.07)]">
                      <td className="px-4 py-2">{u.email}</td>
                      <td className="px-4 py-2">
                        <span className={`badge ${u.role === "super_admin" ? "badge-ok" : u.role === "admin" ? "badge-ok" : "badge-warn"}`}>
                          {u.role}
                        </span>
                      </td>
                      <td className="px-4 py-2 font-mono text-xs">
                        {u.organization_id ?? <span className="muted">—</span>}
                      </td>
                      <td className="px-4 py-2 font-mono text-xs text-[var(--accent)]">
                        {u.business_id || <span className="muted">—</span>}
                      </td>
                      <td className="px-4 py-2">
                        <span className={`badge ${u.is_active ? "badge-ok" : "badge-danger"}`}>
                          {u.is_active ? "Active" : "Disabled"}
                        </span>
                      </td>
                      <td className="px-4 py-2 text-xs muted">
                        {u.created_at ? new Date(u.created_at).toLocaleDateString() : "—"}
                      </td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
          ) : (
            <p className="text-sm muted">No users found.</p>
          )}
        </section>
      </main>
    </AuthGuard>
  );
}
