"use client";

import { zodResolver } from "@hookform/resolvers/zod";
import { useRouter } from "next/navigation";
import { useEffect, useState } from "react";
import { useForm } from "react-hook-form";
import { z } from "zod";

import { useAuth } from "@/components/auth-provider";
import { useToast } from "@/components/toast-provider";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { authBootstrap, authStatus, isApiError } from "@/lib/api";

const setupSchema = z.object({
  email: z.string().email("Enter a valid email address."),
  password: z.string().min(6, "Password must be at least 6 characters."),
  confirmPassword: z.string().min(6),
  organization_id: z.string().min(1, "Organization ID is required."),
}).refine((data) => data.password === data.confirmPassword, {
  message: "Passwords do not match.",
  path: ["confirmPassword"],
});

type SetupForm = z.infer<typeof setupSchema>;

export default function SetupPage() {
  const router = useRouter();
  const { login } = useAuth();
  const { pushToast } = useToast();
  const [error, setError] = useState<string | null>(null);
  const [checking, setChecking] = useState(true);

  const {
    register,
    handleSubmit,
    formState: { errors, isSubmitting },
  } = useForm<SetupForm>({
    resolver: zodResolver(setupSchema),
    defaultValues: { email: "", password: "", confirmPassword: "", organization_id: "default_org" },
  });

  useEffect(() => {
    let mounted = true;
    void authStatus()
      .then((status) => {
        if (!mounted) return;
        if (status.initialized) {
          router.replace("/login");
        } else {
          setChecking(false);
        }
      })
      .catch(() => {
        if (mounted) setChecking(false);
      });
    return () => { mounted = false; };
  }, [router]);

  const onSubmit = async (values: SetupForm) => {
    setError(null);
    try {
      const response = await authBootstrap({
        email: values.email,
        password: values.password,
        organization_id: values.organization_id,
      });
      login(response.access_token, response.user);
      pushToast("System initialized! Welcome, admin.", "success");
      router.replace("/");
    } catch (err) {
      const msg = isApiError(err) ? err.message : "Bootstrap failed.";
      setError(msg);
      pushToast(msg, "danger");
    }
  };

  if (checking) {
    return (
      <main className="mx-auto flex min-h-screen max-w-5xl items-center justify-center p-6">
        <p className="text-sm muted loading-pulse">Checking system status...</p>
      </main>
    );
  }

  return (
    <main className="mx-auto flex min-h-screen max-w-5xl items-center justify-center p-6">
      <section className="card card-glow w-full max-w-md p-8">
        <div className="mb-6">
          <p className="text-xs uppercase tracking-[0.14em] text-[var(--text-muted)]">DataSoko</p>
          <h1 className="mt-1 text-2xl font-semibold tracking-tight">System Setup</h1>
          <p className="mt-2 text-sm muted">
            Create the first administrator account to initialize the system.
          </p>
        </div>

        <form className="space-y-4" onSubmit={handleSubmit(onSubmit)}>
          <div>
            <label className="block text-sm font-medium" htmlFor="organization_id">
              Organization ID
            </label>
            <Input
              id="organization_id"
              placeholder="my_company"
              {...register("organization_id")}
            />
            {errors.organization_id ? (
              <p className="mt-1 text-xs text-[var(--danger)]">{errors.organization_id.message}</p>
            ) : null}
          </div>

          <div>
            <label className="block text-sm font-medium" htmlFor="email">
              Admin Email
            </label>
            <Input
              id="email"
              type="email"
              autoComplete="email"
              placeholder="admin@company.com"
              {...register("email")}
            />
            {errors.email ? (
              <p className="mt-1 text-xs text-[var(--danger)]">{errors.email.message}</p>
            ) : null}
          </div>

          <div>
            <label className="block text-sm font-medium" htmlFor="password">
              Password
            </label>
            <Input
              id="password"
              type="password"
              autoComplete="new-password"
              placeholder="Min. 6 characters"
              {...register("password")}
            />
            {errors.password ? (
              <p className="mt-1 text-xs text-[var(--danger)]">{errors.password.message}</p>
            ) : null}
          </div>

          <div>
            <label className="block text-sm font-medium" htmlFor="confirmPassword">
              Confirm Password
            </label>
            <Input
              id="confirmPassword"
              type="password"
              autoComplete="new-password"
              placeholder="Re-enter password"
              {...register("confirmPassword")}
            />
            {errors.confirmPassword ? (
              <p className="mt-1 text-xs text-[var(--danger)]">{errors.confirmPassword.message}</p>
            ) : null}
          </div>

          {error ? (
            <div className="rounded-md border border-[rgba(255,107,122,0.3)] bg-[rgba(255,107,122,0.08)] px-4 py-2">
              <p className="text-xs text-[var(--danger)]">{error}</p>
            </div>
          ) : null}

          <Button type="submit" variant="primary" disabled={isSubmitting} className="w-full">
            {isSubmitting ? "Initializing..." : "Initialize System"}
          </Button>
        </form>

        <p className="mt-4 text-center text-xs muted">
          This page is only available when no users exist in the system.
        </p>
      </section>
    </main>
  );
}
