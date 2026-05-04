"use client";

import { useEffect, useState } from "react";
import { zodResolver } from "@hookform/resolvers/zod";
import { useForm } from "react-hook-form";
import { z } from "zod";

import { AuthGuard } from "@/components/auth-guard";
import { useAuth } from "@/components/auth-provider";
import { SystemContext } from "@/components/system-context";
import { useToast } from "@/components/toast-provider";
import { Alert } from "@/components/ui/alert";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import {
  createUser,
  deleteUser,
  getUsers,
  isApiError,
  updateUser,
  type ManagedUser,
} from "@/lib/api";

const createUserSchema = z.object({
  email: z.string().email("Enter a valid email."),
  password: z.string().min(6, "Min 6 characters."),
  role: z.enum(["admin", "sme"]),
  business_id: z.string().optional(),
});

type CreateUserForm = z.infer<typeof createUserSchema>;

export default function UsersPage() {
  const { token, user } = useAuth();
  const { pushToast } = useToast();

  const [users, setUsers] = useState<ManagedUser[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  const form = useForm<CreateUserForm>({
    resolver: zodResolver(createUserSchema),
    defaultValues: { email: "", password: "", role: "sme", business_id: "" },
  });

  const watchRole = form.watch("role");

  useEffect(() => {
    if (!token) return;
    let mounted = true;
    setLoading(true);
    void getUsers(token)
      .then((res) => { if (mounted) setUsers(res); })
      .catch((err) => { if (mounted) setError(isApiError(err) ? err.message : "Failed to load users"); })
      .finally(() => { if (mounted) setLoading(false); });
    return () => { mounted = false; };
  }, [token]);

  const onCreateUser = form.handleSubmit(async (values) => {
    if (!token) return;
    setError(null);
    try {
      const created = await createUser(token, {
        email: values.email,
        password: values.password,
        role: values.role,
        business_id: values.role === "sme" ? values.business_id?.trim() || undefined : undefined,
      });
      setUsers((prev) => [created, ...prev]);
      form.reset();
      pushToast(`User "${created.email}" created`, "success");
    } catch (err) {
      const msg = isApiError(err) ? err.message : "Failed to create user";
      setError(msg);
      pushToast(msg, "danger");
    }
  });

  const onToggleActive = async (u: ManagedUser) => {
    if (!token) return;
    try {
      if (u.is_active) {
        await deleteUser(token, u.id);
        setUsers((prev) => prev.map((x) => x.id === u.id ? { ...x, is_active: false } : x));
        pushToast("User disabled", "info");
      } else {
        await updateUser(token, u.id, { is_active: true });
        setUsers((prev) => prev.map((x) => x.id === u.id ? { ...x, is_active: true } : x));
        pushToast("User re-enabled", "success");
      }
    } catch (err) {
      pushToast(isApiError(err) ? err.message : "Failed to update user", "danger");
    }
  };

  if (user?.role !== "admin") {
    return (
      <AuthGuard>
        <main className="mx-auto max-w-6xl p-4 md:p-6">
          <Alert tone="danger">Admin access required to manage users.</Alert>
        </main>
      </AuthGuard>
    );
  }

  return (
    <AuthGuard>
      <main className="mx-auto max-w-6xl p-4 md:p-6">
        <SystemContext
          title="User Management"
          subtitle="Create and manage users for your organization."
          businessId="all"
        />

        {error ? <Alert tone="danger">{error}</Alert> : null}

        {/* Create User Form */}
        <section className="mt-4 card p-6">
          <h2 className="text-lg font-semibold">Create User</h2>
          <p className="mt-1 text-sm muted">Add a new admin or SME user to this organization.</p>

          <form className="mt-4 grid gap-4 md:grid-cols-2" onSubmit={onCreateUser}>
            <label className="text-sm font-medium">
              Email <span className="text-[var(--danger)]">*</span>
              <Input type="email" {...form.register("email")} placeholder="user@company.com" className="mt-1" />
              {form.formState.errors.email ? (
                <p className="mt-1 text-xs text-[var(--danger)]">{form.formState.errors.email.message}</p>
              ) : null}
            </label>

            <label className="text-sm font-medium">
              Password <span className="text-[var(--danger)]">*</span>
              <Input type="password" autoComplete="new-password" {...form.register("password")} placeholder="Min. 6 characters" className="mt-1" />
              {form.formState.errors.password ? (
                <p className="mt-1 text-xs text-[var(--danger)]">{form.formState.errors.password.message}</p>
              ) : null}
            </label>

            <label className="text-sm font-medium">
              Role <span className="text-[var(--danger)]">*</span>
              <select
                {...form.register("role")}
                className="mt-1 w-full rounded-md border border-[var(--border)] bg-[rgba(11,21,37,0.9)] px-3 py-2 text-sm"
              >
                <option value="admin">Admin</option>
                <option value="sme">SME</option>
              </select>
            </label>

            {watchRole === "sme" ? (
              <label className="text-sm font-medium">
                Business ID <span className="text-[var(--danger)]">*</span>
                <Input {...form.register("business_id")} placeholder="biz_001" className="mt-1" />
              </label>
            ) : (
              <div />
            )}

            <div className="md:col-span-2">
              <Button type="submit" variant="primary" disabled={form.formState.isSubmitting}>
                {form.formState.isSubmitting ? "Creating..." : "Create User"}
              </Button>
            </div>
          </form>
        </section>

        {/* Users Table */}
        <section className="mt-4 card p-6">
          <h2 className="text-lg font-semibold">All Users</h2>
          {loading ? (
            <p className="mt-3 text-sm muted">Loading users...</p>
          ) : users.length > 0 ? (
            <div className="mt-4 overflow-x-auto rounded-md border border-[var(--border)]">
              <table className="w-full text-sm">
                <thead>
                  <tr className="border-b border-[var(--border)] bg-[rgba(10,19,33,0.7)] text-left">
                    <th className="px-4 py-2 font-semibold">Email</th>
                    <th className="px-4 py-2 font-semibold">Role</th>
                    <th className="px-4 py-2 font-semibold">Business</th>
                    <th className="px-4 py-2 font-semibold">Status</th>
                    <th className="px-4 py-2 font-semibold">Created</th>
                    <th className="px-4 py-2 font-semibold">Actions</th>
                  </tr>
                </thead>
                <tbody>
                  {users.map((u) => (
                    <tr key={u.id} className="border-b border-[var(--border)] last:border-0 hover:bg-[rgba(79,121,199,0.07)]">
                      <td className="px-4 py-2">{u.email}</td>
                      <td className="px-4 py-2">
                        <span className={`badge ${u.role === "admin" ? "badge-ok" : "badge-warn"}`}>
                          {u.role}
                        </span>
                      </td>
                      <td className="px-4 py-2 font-mono text-xs text-[var(--accent)]">
                        {u.business_id || <span className="muted">All</span>}
                      </td>
                      <td className="px-4 py-2">
                        <span className={`badge ${u.is_active ? "badge-ok" : "badge-danger"}`}>
                          {u.is_active ? "Active" : "Disabled"}
                        </span>
                      </td>
                      <td className="px-4 py-2 text-xs muted">
                        {u.created_at ? new Date(u.created_at).toLocaleDateString() : "—"}
                      </td>
                      <td className="px-4 py-2">
                        {u.id !== user?.id ? (
                          <button
                            type="button"
                            onClick={() => void onToggleActive(u)}
                            className={`text-xs underline ${u.is_active ? "text-[var(--danger)]" : "text-[var(--ok)]"}`}
                          >
                            {u.is_active ? "Disable" : "Enable"}
                          </button>
                        ) : (
                          <span className="text-xs muted">You</span>
                        )}
                      </td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
          ) : (
            <p className="mt-3 text-sm muted">No users found.</p>
          )}
        </section>
      </main>
    </AuthGuard>
  );
}
