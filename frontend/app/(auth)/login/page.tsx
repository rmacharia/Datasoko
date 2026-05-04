"use client";

import { zodResolver } from "@hookform/resolvers/zod";
import Link from "next/link";
import { useRouter } from "next/navigation";
import { useEffect, useState } from "react";
import { useForm } from "react-hook-form";
import { z } from "zod";

import { useAuth } from "@/components/auth-provider";
import { useToast } from "@/components/toast-provider";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { authLogin, isApiError } from "@/lib/api";

const loginSchema = z.object({
  email: z.string().email("Enter a valid email address."),
  password: z.string().min(6, "Password must be at least 6 characters."),
});

type LoginForm = z.infer<typeof loginSchema>;

export default function LoginPage() {
  const router = useRouter();
  const { isAuthenticated, isReady, login } = useAuth();
  const { pushToast } = useToast();
  const [error, setError] = useState<string | null>(null);

  const {
    register,
    handleSubmit,
    formState: { errors, isSubmitting },
  } = useForm<LoginForm>({
    resolver: zodResolver(loginSchema),
    defaultValues: { email: "", password: "" },
  });

  useEffect(() => {
    if (isReady && isAuthenticated) {
      router.replace("/");
    }
  }, [isReady, isAuthenticated, router]);

  const onSubmit = async (values: LoginForm) => {
    setError(null);
    try {
      const response = await authLogin({ email: values.email, password: values.password });
      login(response.access_token, response.user);
      pushToast(`Welcome, ${response.user.email}`, "success");
      router.replace(response.user.role === "sme" ? "/reports" : "/");
    } catch (err) {
      const msg = isApiError(err) ? err.message : "Login failed. Check your credentials.";
      setError(msg);
      pushToast(msg, "danger");
    }
  };

  return (
    <main className="mx-auto flex min-h-screen max-w-5xl items-center justify-center p-6">
      <section className="card card-glow w-full max-w-md p-8">
        <div className="mb-6">
          <p className="text-xs uppercase tracking-[0.14em] text-[var(--text-muted)]">DataSoko</p>
          <h1 className="mt-1 text-2xl font-semibold tracking-tight">Sign In</h1>
          <p className="mt-2 text-sm muted">
            Enter your email and password to access the console.
          </p>
        </div>

        <form className="space-y-4" onSubmit={handleSubmit(onSubmit)}>
          <div>
            <label className="block text-sm font-medium" htmlFor="email">
              Email
            </label>
            <Input
              id="email"
              type="email"
              autoComplete="email"
              placeholder="you@company.com"
              aria-invalid={Boolean(errors.email)}
              {...register("email")}
            />
            {errors.email ? (
              <p className="mt-1 text-sm text-[var(--danger)]">{errors.email.message}</p>
            ) : null}
          </div>

          <div>
            <label className="block text-sm font-medium" htmlFor="password">
              Password
            </label>
            <Input
              id="password"
              type="password"
              autoComplete="current-password"
              placeholder="Enter password..."
              aria-invalid={Boolean(errors.password)}
              {...register("password")}
            />
            {errors.password ? (
              <p className="mt-1 text-sm text-[var(--danger)]">{errors.password.message}</p>
            ) : null}
          </div>

          {error ? (
            <div className="rounded-md border border-[rgba(255,107,122,0.3)] bg-[rgba(255,107,122,0.08)] px-4 py-2">
              <p className="text-xs text-[var(--danger)]">{error}</p>
            </div>
          ) : null}

          <Button type="submit" variant="primary" disabled={isSubmitting} className="w-full">
            {isSubmitting ? "Signing in..." : "Sign In"}
          </Button>
        </form>

        <p className="mt-4 text-center text-xs muted">
          First time?{" "}
          <Link href="/setup" className="text-[var(--accent)] underline">
            Initialize the system
          </Link>
        </p>
      </section>
    </main>
  );
}
