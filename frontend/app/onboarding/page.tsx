"use client";

import { motion, useReducedMotion } from "framer-motion";
import { useRouter } from "next/navigation";
import { useState } from "react";

import { useOrg } from "@/components/org-provider";
import { Alert } from "@/components/ui/alert";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { isApiError, onboard } from "@/lib/api";

export default function OnboardingPage() {
  const router = useRouter();
  const { setOrganizationId } = useOrg();
  const reduce = useReducedMotion();

  const [orgId, setOrgId] = useState("");
  const [name, setName] = useState("");
  const [plan, setPlan] = useState("starter");
  const [error, setError] = useState<string | null>(null);
  const [submitting, setSubmitting] = useState(false);

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!orgId.trim() || !name.trim()) return;

    setError(null);
    setSubmitting(true);
    try {
      const result = await onboard({
        organization_id: orgId.trim(),
        name: name.trim(),
        plan,
      });
      setOrganizationId(result.organization_id);
      router.replace("/");
    } catch (err) {
      if (isApiError(err) && err.status === 409) {
        // Already onboarded — accept it and navigate
        setOrganizationId(orgId.trim());
        router.replace("/");
        return;
      }
      setError(isApiError(err) ? err.message : "Onboarding failed. Try again.");
    } finally {
      setSubmitting(false);
    }
  };

  return (
    <main className="mx-auto flex min-h-screen max-w-lg items-center p-6 md:p-10">
      <motion.div
        className="w-full"
        initial={reduce ? false : { opacity: 0, y: 12 }}
        animate={{ opacity: 1, y: 0 }}
        transition={reduce ? { duration: 0 } : { duration: 0.22, ease: "easeOut" }}
      >
        <div className="mb-8">
          <p className="text-xs uppercase tracking-[0.14em] text-[var(--text-muted)]">DataSoko Internal</p>
          <h1 className="mt-1 text-2xl font-semibold tracking-tight">Set Up Your Organization</h1>
          <p className="mt-2 text-sm muted">
            Create an organization to manage SMEs and billing. This runs once per deployment.
          </p>
        </div>

        {error ? (
          <div className="mb-5">
            <Alert tone="danger">{error}</Alert>
          </div>
        ) : null}

        <form onSubmit={(e) => void handleSubmit(e)} className="card card-glow p-6 space-y-5">
          <label className="block text-sm font-medium">
            Organization ID
            <Input
              className="mt-1"
              value={orgId}
              onChange={(e) => setOrgId(e.target.value)}
              placeholder="e.g. org_acme"
              required
              minLength={1}
            />
            <p className="mt-1 text-xs muted">Unique slug for your org. Cannot be changed later.</p>
          </label>

          <label className="block text-sm font-medium">
            Organization Name
            <Input
              className="mt-1"
              value={name}
              onChange={(e) => setName(e.target.value)}
              placeholder="e.g. Acme Ltd"
              required
              minLength={1}
            />
          </label>

          <label className="block text-sm font-medium">
            Plan
            <select
              className="mt-1 w-full rounded-md border border-[var(--border)] bg-[rgba(11,21,37,0.9)] px-3 py-2 text-sm"
              value={plan}
              onChange={(e) => setPlan(e.target.value)}
            >
              <option value="starter">Starter</option>
              <option value="growth">Growth</option>
              <option value="enterprise">Enterprise</option>
            </select>
          </label>

          <Button type="submit" variant="primary" disabled={submitting} className="w-full">
            {submitting ? "Setting up..." : "Create Organization"}
          </Button>
        </form>

        <p className="mt-5 text-center text-xs muted">
          Already onboarded?{" "}
          <button
            type="button"
            className="underline text-[var(--accent)] hover:text-[var(--focus)] transition-colors"
            onClick={() => router.replace("/")}
          >
            Skip to dashboard
          </button>
        </p>
      </motion.div>
    </main>
  );
}
