"use client";

import Link from "next/link";
import { useRouter } from "next/navigation";
import { useEffect } from "react";

import { AuthGuard } from "@/components/auth-guard";
import { useAuth } from "@/components/auth-provider";
import { Alert } from "@/components/ui/alert";

export default function AdminHomePage() {
  const router = useRouter();
  const { user, isReady } = useAuth();

  useEffect(() => {
    if (!isReady || !user) return;
    if (user.role !== "super_admin") {
      router.replace("/");
    }
  }, [isReady, user, router]);

  if (!isReady || !user) return null;

  if (user.role !== "super_admin") {
    return (
      <AuthGuard>
        <main className="mx-auto max-w-6xl p-4 md:p-6">
          <Alert tone="danger">Platform admin access required.</Alert>
        </main>
      </AuthGuard>
    );
  }

  return (
    <AuthGuard>
      <main className="mx-auto max-w-6xl p-4 md:p-6">
        <header className="mb-6">
          <p className="text-xs uppercase tracking-[0.14em] text-[var(--text-muted)]">
            DataSoko Platform
          </p>
          <h1 className="mt-1 text-2xl font-semibold tracking-tight">Admin Console</h1>
          <p className="mt-2 text-sm muted">
            Platform-wide view of users, organizations, and SMEs.
          </p>
        </header>

        <section className="grid gap-4 md:grid-cols-3">
          <Link
            href="/admin/users"
            className="card p-5 hover:border-[var(--accent)] transition-colors"
          >
            <h2 className="text-base font-semibold">Users</h2>
            <p className="mt-1 text-sm muted">Every user across every organization.</p>
          </Link>
          <Link
            href="/admin/organizations"
            className="card p-5 hover:border-[var(--accent)] transition-colors"
          >
            <h2 className="text-base font-semibold">Organizations</h2>
            <p className="mt-1 text-sm muted">Create and audit tenants.</p>
          </Link>
          <Link
            href="/admin/businesses"
            className="card p-5 hover:border-[var(--accent)] transition-colors"
          >
            <h2 className="text-base font-semibold">SMEs</h2>
            <p className="mt-1 text-sm muted">Every business on the platform.</p>
          </Link>
        </section>
      </main>
    </AuthGuard>
  );
}
