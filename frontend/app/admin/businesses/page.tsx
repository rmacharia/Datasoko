"use client";

import { useRouter } from "next/navigation";
import { useEffect, useState } from "react";

import { AuthGuard } from "@/components/auth-guard";
import { useAuth } from "@/components/auth-provider";
import { Alert } from "@/components/ui/alert";
import { getPlatformBusinesses, isApiError, type PlatformBusiness } from "@/lib/api";

export default function AdminBusinessesPage() {
  const router = useRouter();
  const { token, user, isReady } = useAuth();
  const [businesses, setBusinesses] = useState<PlatformBusiness[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    if (!isReady || !user) return;
    if (user.role !== "super_admin") router.replace("/");
  }, [isReady, user, router]);

  useEffect(() => {
    if (!token || user?.role !== "super_admin") return;
    let mounted = true;
    setLoading(true);
    void getPlatformBusinesses(token)
      .then((res) => { if (mounted) setBusinesses(res); })
      .catch((err) => { if (mounted) setError(isApiError(err) ? err.message : "Failed to load businesses"); })
      .finally(() => { if (mounted) setLoading(false); });
    return () => { mounted = false; };
  }, [token, user?.role]);

  if (!isReady || !user || user.role !== "super_admin") return null;

  return (
    <AuthGuard>
      <main className="mx-auto max-w-6xl p-4 md:p-6">
        <header className="mb-6">
          <p className="text-xs uppercase tracking-[0.14em] text-[var(--text-muted)]">Platform</p>
          <h1 className="mt-1 text-2xl font-semibold tracking-tight">All SMEs</h1>
          <p className="mt-2 text-sm muted">Every business across every organization.</p>
        </header>

        {error ? <Alert tone="danger">{error}</Alert> : null}

        <section className="card p-6">
          {loading ? (
            <p className="text-sm muted">Loading...</p>
          ) : businesses.length > 0 ? (
            <div className="overflow-x-auto rounded-md border border-[var(--border)]">
              <table className="w-full text-sm">
                <thead>
                  <tr className="border-b border-[var(--border)] bg-[rgba(10,19,33,0.7)] text-left">
                    <th className="px-4 py-2 font-semibold">ID</th>
                    <th className="px-4 py-2 font-semibold">Name</th>
                    <th className="px-4 py-2 font-semibold">Organization</th>
                    <th className="px-4 py-2 font-semibold">WhatsApp</th>
                    <th className="px-4 py-2 font-semibold">Created</th>
                  </tr>
                </thead>
                <tbody>
                  {businesses.map((b) => (
                    <tr key={b.id} className="border-b border-[var(--border)] last:border-0 hover:bg-[rgba(79,121,199,0.07)]">
                      <td className="px-4 py-2 font-mono text-xs text-[var(--accent)]">{b.id}</td>
                      <td className="px-4 py-2">{b.name ?? "—"}</td>
                      <td className="px-4 py-2 font-mono text-xs">{b.organization_id}</td>
                      <td className="px-4 py-2 text-xs muted">{b.whatsapp_phone ?? "—"}</td>
                      <td className="px-4 py-2 text-xs muted">{new Date(b.created_at).toLocaleDateString()}</td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
          ) : (
            <p className="text-sm muted">No businesses yet.</p>
          )}
        </section>
      </main>
    </AuthGuard>
  );
}
