"use client";

import { zodResolver } from "@hookform/resolvers/zod";
import { useRouter } from "next/navigation";
import { useEffect } from "react";
import { useForm } from "react-hook-form";
import { z } from "zod";

import { useAuth } from "@/components/auth-provider";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";

const loginSchema = z.object({
  adminToken: z.string().min(12, "Enter a valid admin token."),
  remember: z.boolean().default(true),
});

type LoginForm = z.infer<typeof loginSchema>;

export default function LoginPage() {
  const router = useRouter();
  const { token, login, isReady } = useAuth();

  const {
    register,
    handleSubmit,
    formState: { errors, isSubmitting },
  } = useForm<LoginForm>({
    resolver: zodResolver(loginSchema),
    defaultValues: { adminToken: "", remember: true },
  });

  useEffect(() => {
    if (isReady && token) {
      router.replace("/");
    }
  }, [isReady, router, token]);

  const onSubmit = async (values: LoginForm) => {
    login(values.adminToken, values.remember);
    router.replace("/");
  };

  return (
    <main className="mx-auto flex min-h-screen max-w-5xl items-center justify-center p-6">
      <section className="card card-glow w-full max-w-md p-8">
        <div className="mb-6">
          <p className="text-xs uppercase tracking-[0.14em] text-[var(--text-muted)]">DataSoko Internal</p>
          <h1 className="mt-1 text-2xl font-semibold tracking-tight">Admin Login</h1>
          <p className="mt-2 text-sm muted">
            Authenticate with your <code className="rounded bg-[rgba(79,121,199,0.15)] px-1.5 py-0.5 text-xs font-medium text-[var(--accent)]">ADMIN_TOKEN</code> from secure ops storage.
          </p>
        </div>

        <form className="space-y-4" onSubmit={handleSubmit(onSubmit)}>
          <label className="block text-sm font-medium" htmlFor="adminToken">
            Admin Token
          </label>
          <Input
            id="adminToken"
            type="password"
            autoComplete="current-password"
            placeholder="Enter admin token..."
            aria-invalid={Boolean(errors.adminToken)}
            aria-describedby={errors.adminToken ? "adminToken-error" : undefined}
            {...register("adminToken")}
          />
          {errors.adminToken ? (
            <p id="adminToken-error" className="text-sm text-[var(--danger)]">
              {errors.adminToken.message}
            </p>
          ) : null}

          <label className="flex items-center gap-2 text-sm">
            <input type="checkbox" {...register("remember")} />
            Keep token in this browser session
          </label>

          <Button type="submit" variant="primary" disabled={isSubmitting} className="w-full">
            {isSubmitting ? "Authenticating..." : "Continue"}
          </Button>
        </form>
      </section>
    </main>
  );
}
