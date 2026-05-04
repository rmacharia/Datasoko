"use client";

import { motion, useReducedMotion } from "framer-motion";
import { useCallback, useEffect, useMemo, useState } from "react";
import { useRouter } from "next/navigation";

import { AuthGuard } from "@/components/auth-guard";
import { useAuth } from "@/components/auth-provider";
import { useOrg } from "@/components/org-provider";
import { useSettings } from "@/components/settings-provider";
import { StatusCard } from "@/components/status-card";
import { SystemContext } from "@/components/system-context";
import { Alert } from "@/components/ui/alert";
import { Button } from "@/components/ui/button";
import {
  getAdminStatus,
  getBilling,
  getBusinesses,
  isApiError,
  type AdminStatusResponse,
  type BillingResponse,
  type BusinessesResponse,
} from "@/lib/api";

type LoadState<T> = {
  loading: boolean;
  data: T | null;
  error: string | null;
};

export default function OverviewPage() {
  const router = useRouter();
  const { token } = useAuth();
  const { organizationId, activeBusinessId } = useOrg();
  const { effectiveEnhancedMode } = useSettings();
  const prefersReducedMotion = useReducedMotion();

  const [statusState, setStatusState] = useState<LoadState<AdminStatusResponse>>({
    loading: false,
    data: null,
    error: null,
  });
  const [billingState, setBillingState] = useState<LoadState<BillingResponse>>({ loading: false, data: null, error: null });
  const [bizState, setBizState] = useState<LoadState<BusinessesResponse>>({ loading: false, data: null, error: null });
  const [onboardingChecked, setOnboardingChecked] = useState(false);

  useEffect(() => {
    if (!token) return;
    let mounted = true;
    getBilling(organizationId)
      .then(() => { if (mounted) setOnboardingChecked(true); })
      .catch((err) => {
        if (!mounted) return;
        if (isApiError(err) && err.status === 404) {
          router.replace("/onboarding");
          return;
        }
        setOnboardingChecked(true);
      });
    return () => { mounted = false; };
  }, [token, organizationId, router]);

  const load = useCallback(async () => {
    if (!token) return;

    setStatusState({ loading: true, data: null, error: null });
    setBillingState({ loading: true, data: null, error: null });
    setBizState({ loading: true, data: null, error: null });

    try {
      const [statusData, billingData, bizData] = await Promise.all([
        getAdminStatus(token),
        getBilling(organizationId),
        getBusinesses(organizationId),
      ]);
      setStatusState({ loading: false, data: statusData, error: null });
      setBillingState({ loading: false, data: billingData, error: null });
      setBizState({ loading: false, data: bizData, error: null });
    } catch (err) {
      const msg = isApiError(err) ? err.message : "Failed to load dashboard data.";
      setStatusState((prev) => prev.data ? prev : { loading: false, data: null, error: msg });
      setBillingState((prev) => prev.data ? prev : { loading: false, data: null, error: msg });
      setBizState((prev) => prev.data ? prev : { loading: false, data: null, error: msg });
    }
  }, [token, organizationId]);

  useEffect(() => {
    if (onboardingChecked) void load();
  }, [load, onboardingChecked]);

  const pageStatus = useMemo(() => {
    if (statusState.error) return "error" as const;
    if (statusState.loading) return "warn" as const;
    if (!statusState.data?.db.connected) return "warn" as const;
    return "ok" as const;
  }, [statusState.data?.db.connected, statusState.error, statusState.loading]);

  const version = statusState.data?.version;
  const db = statusState.data?.db;
  const lastRun = statusState.data?.last_run;

  const lastSmeAdded = useMemo(() => {
    const list = bizState.data?.businesses;
    if (!list || list.length === 0) return null;
    return [...list].sort((a, b) => new Date(b.created_at).getTime() - new Date(a.created_at).getTime())[0];
  }, [bizState.data]);

  function ErrorBadge({ message }: { message: string }) {
    return (
      <span className="inline-flex items-center gap-1 rounded-md bg-[rgba(255,60,60,0.15)] px-2 py-0.5 text-xs font-semibold text-[var(--danger)]">
        {message}
      </span>
    );
  }

  if (!onboardingChecked) {
    return (
      <AuthGuard>
        <main className="mx-auto max-w-6xl p-4 md:p-6">
          <p className="text-sm muted">Checking subscription status...</p>
        </main>
      </AuthGuard>
    );
  }

  return (
    <AuthGuard>
      <main className="mx-auto max-w-6xl p-4 md:p-6">
        <SystemContext
          title="Ops Overview"
          subtitle="System telemetry for ingestion, reporting, and job runtime health."
          businessId={activeBusinessId}
        />

        <motion.section
          initial={prefersReducedMotion ? false : { opacity: 0, y: 8 }}
          animate={{ opacity: 1, y: 0 }}
          transition={prefersReducedMotion ? { duration: 0 } : { duration: 0.2, ease: "easeOut" }}
        >
          <div className="mb-6 flex flex-wrap items-end justify-between gap-3">
            <div>
              <h2 className="text-xl font-semibold">Live Runtime Status</h2>
              <p className="mt-1 text-sm muted">Internal run-state visibility. No customer-facing views.</p>
            </div>
            <Button variant="secondary" onClick={() => void load()}>
              Refresh
            </Button>
          </div>

          {statusState.error ? <Alert tone="danger">{statusState.error}</Alert> : null}

          {/* Row 1: System health cards — always visible */}
          <section className="mt-4 grid gap-4 md:grid-cols-2 lg:grid-cols-4">
            <StatusCard title="Backend Health" status={statusState.data?.backend_health === "ok" ? "ok" : "warn"}>
              {statusState.error ? (
                <ErrorBadge message="Data unavailable" />
              ) : (
                <p>
                  API status: <strong>{statusState.data?.backend_health ?? (statusState.loading ? "checking..." : "unknown")}</strong>
                </p>
              )}
            </StatusCard>

            <StatusCard title="Backend Version" status={version ? "ok" : statusState.loading ? "warn" : "error"}>
              {statusState.error ? (
                <ErrorBadge message="Data unavailable" />
              ) : version ? (
                <dl className="space-y-1">
                  <div>
                    <dt className="inline muted">App:</dt> <dd className="inline font-medium">{version.app_version}</dd>
                  </div>
                  <div>
                    <dt className="inline muted">Schema:</dt> <dd className="inline font-medium">{version.schema_version}</dd>
                  </div>
                  <div>
                    <dt className="inline muted">Normalizer:</dt> <dd className="inline font-medium">{version.normalizer_version}</dd>
                  </div>
                </dl>
              ) : (
                <p className="muted">Unavailable</p>
              )}
            </StatusCard>

            <StatusCard title="DB Connectivity" status={db?.connected ? "ok" : db ? "error" : "warn"}>
              {statusState.error ? (
                <ErrorBadge message="Data unavailable" />
              ) : (
                <>
                  <p>
                    Database: <strong>{db?.connected ? "connected" : statusState.loading ? "checking..." : "disconnected"}</strong>
                  </p>
                  {db?.error ? <p className="mt-1 text-[var(--danger)]">{db.error}</p> : null}
                </>
              )}
            </StatusCard>

            <StatusCard title="Last Run" status={lastRun ? "ok" : pageStatus === "error" ? "error" : "warn"}>
              {statusState.error ? (
                <ErrorBadge message="Data unavailable" />
              ) : lastRun ? (
                <dl className="space-y-1">
                  <div>
                    <dt className="inline muted">Source:</dt> <dd className="inline font-medium">{lastRun.source ?? "unknown"}</dd>
                  </div>
                  <div>
                    <dt className="inline muted">Business:</dt> <dd className="inline font-medium">{lastRun.business_id ?? "n/a"}</dd>
                  </div>
                  <div>
                    <dt className="inline muted">Timestamp:</dt> <dd className="inline font-medium">{lastRun.timestamp ?? "n/a"}</dd>
                  </div>
                </dl>
              ) : (
                <p className="muted">No run has been recorded yet.</p>
              )}
            </StatusCard>
          </section>

          {/* Row 2: Operational cards — visible only in enhanced mode */}
          {effectiveEnhancedMode ? (
            <section className="mt-4 grid gap-4 md:grid-cols-3">
              <StatusCard
                title="SME Summary"
                status={bizState.error ? "error" : bizState.loading ? "warn" : "ok"}
              >
                {bizState.error ? (
                  <ErrorBadge message="Data unavailable" />
                ) : bizState.loading ? (
                  <p className="muted">Loading...</p>
                ) : (
                  <dl className="space-y-1">
                    <div>
                      <dt className="inline muted">Total SMEs:</dt>{" "}
                      <dd className="inline text-2xl font-bold tabular-nums text-[var(--accent)]">
                        {bizState.data?.businesses.length ?? 0}
                      </dd>
                    </div>
                    <div>
                      <dt className="inline muted">Active SME:</dt>{" "}
                      <dd className="inline font-mono font-medium">{activeBusinessId}</dd>
                    </div>
                  </dl>
                )}
              </StatusCard>

              <StatusCard
                title="Billing Summary"
                status={
                  billingState.error ? "error"
                  : billingState.loading ? "warn"
                  : billingState.data?.active ? "ok"
                  : "error"
                }
              >
                {billingState.error ? (
                  <ErrorBadge message="Data unavailable" />
                ) : billingState.loading ? (
                  <p className="muted">Loading...</p>
                ) : billingState.data ? (
                  <dl className="space-y-1">
                    <div>
                      <dt className="inline muted">Plan:</dt>{" "}
                      <dd className="inline font-semibold capitalize">{billingState.data.plan ?? "—"}</dd>
                    </div>
                    <div>
                      <dt className="inline muted">Status:</dt>{" "}
                      <dd className={`inline font-semibold ${billingState.data.active ? "text-[var(--ok)]" : "text-[var(--danger)]"}`}>
                        {billingState.data.status ?? "—"}
                      </dd>
                    </div>
                    <div>
                      <dt className="inline muted">Days left:</dt>{" "}
                      <dd className={`inline tabular-nums font-semibold ${billingState.data.days_remaining < 7 ? "text-[var(--warn)]" : ""}`}>
                        {billingState.data.days_remaining}
                      </dd>
                      {billingState.data.days_remaining < 7 ? (
                        <span className="ml-2 inline-flex items-center rounded-md bg-[rgba(255,200,87,0.18)] px-2 py-0.5 text-xs font-semibold text-[var(--warn)]">
                          Expiring soon
                        </span>
                      ) : null}
                    </div>
                  </dl>
                ) : null}
              </StatusCard>

              <StatusCard
                title="Activity"
                status={bizState.error && billingState.error ? "error" : "ok"}
              >
                {bizState.error && billingState.error ? (
                  <ErrorBadge message="Data unavailable" />
                ) : (
                  <dl className="space-y-1">
                    <div>
                      <dt className="inline muted">Last SME added:</dt>{" "}
                      <dd className="inline font-medium">
                        {lastSmeAdded ? `${lastSmeAdded.id} (${new Date(lastSmeAdded.created_at).toLocaleDateString()})` : "—"}
                      </dd>
                    </div>
                    <div>
                      <dt className="inline muted">Last upload:</dt>{" "}
                      <dd className="inline font-medium muted">—</dd>
                    </div>
                    <div>
                      <dt className="inline muted">Last report:</dt>{" "}
                      <dd className="inline font-medium muted">—</dd>
                    </div>
                  </dl>
                )}
              </StatusCard>
            </section>
          ) : null}
        </motion.section>
      </main>
    </AuthGuard>
  );
}
