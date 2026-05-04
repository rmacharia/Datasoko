"use client";

import Link from "next/link";

import { useAuth } from "@/components/auth-provider";
import { Button } from "@/components/ui/button";

export function AuthGuard({ children }: { children: React.ReactNode }) {
  const { token, isReady } = useAuth();

  if (!isReady) {
    return (
      <main className="mx-auto max-w-5xl p-6">
        <p className="text-sm muted loading-pulse">Loading admin session...</p>
      </main>
    );
  }

  if (!token) {
    return (
      <main className="mx-auto flex min-h-screen max-w-5xl items-center justify-center p-6">
        <section className="card card-glow w-full max-w-md p-8">
          <p className="text-xs uppercase tracking-[0.14em] text-[var(--text-muted)]">DataSoko Internal</p>
          <h1 className="mt-1 text-xl font-semibold">Admin Access Required</h1>
          <p className="mt-2 text-sm muted">Sign in with the internal admin token to continue.</p>
          <Link href="/login" className="mt-5 inline-flex">
            <Button variant="primary">Go to Login</Button>
          </Link>
        </section>
      </main>
    );
  }

  return <>{children}</>;
}
