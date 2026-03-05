"use client";

import Link from "next/link";

import { useAuth } from "@/components/auth-provider";
import { Button } from "@/components/ui/button";

export function AuthGuard({ children }: { children: React.ReactNode }) {
  const { token, isReady } = useAuth();

  if (!isReady) {
    return <main className="mx-auto max-w-5xl p-6 text-sm muted">Loading admin session...</main>;
  }

  if (!token) {
    return (
      <main className="mx-auto flex min-h-screen max-w-5xl items-center justify-center p-6">
        <section className="card w-full max-w-md p-6">
          <h1 className="text-xl font-semibold">Admin Access Required</h1>
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
