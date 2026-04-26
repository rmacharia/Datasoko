"use client";

import dynamic from "next/dynamic";
import { motion, useReducedMotion } from "framer-motion";
import { useCallback, useEffect, useMemo, useState } from "react";

import { AuthGuard } from "@/components/auth-guard";
import { useAuth } from "@/components/auth-provider";
import { DataShelfFallback } from "@/components/overview/data-shelf-fallback";
import { useSettings } from "@/components/settings-provider";
import { StatusCard } from "@/components/status-card";
import { SystemContext } from "@/components/system-context";
import { Alert } from "@/components/ui/alert";
import { Button } from "@/components/ui/button";
import { getAdminStatus, isApiError, type AdminStatusResponse } from "@/lib/api";

const DataShelf3D = dynamic(() => import("@/components/overview/data-shelf-3d").then((m) => m.DataShelf3D), {
  ssr: false,
  loading: () => <DataShelfFallback />,
});

type LoadState<T> = {
  loading: boolean;
  data: T | null;
  error: string | null;
};

export default function OverviewPage() {
  const { token } = useAuth();
  const { effectiveEnhancedMode } = useSettings();
  const prefersReducedMotion = useReducedMotion();

  const [statusState, setStatusState] = useState<LoadState<AdminStatusResponse>>({
    loading: false,
    data: null,
    error: null,
  });
  const [webglSupported, setWebglSupported] = useState(false);

  useEffect(() => {
    if (typeof window === "undefined") return;
    const canvas = document.createElement("canvas");
    setWebglSupported(Boolean(canvas.getContext("webgl") || canvas.getContext("experimental-webgl")));
  }, []);

  const load = useCallback(async () => {
    if (!token) return;

    setStatusState({ loading: true, data: null, error: null });

    try {
      const status = await getAdminStatus(token);
      setStatusState({ loading: false, data: status, error: null });
    } catch (error) {
      const message = isApiError(error) ? error.message : "Failed to load /admin/status.";
      setStatusState({ loading: false, data: null, error: message });
    }
  }, [token]);

  useEffect(() => {
    void load();
  }, [load]);

  const pageStatus = useMemo(() => {
    if (statusState.error) return "error" as const;
    if (statusState.loading) return "warn" as const;
    if (!statusState.data?.db.connected) return "warn" as const;
    return "ok" as const;
  }, [statusState.data?.db.connected, statusState.error, statusState.loading]);

  const version = statusState.data?.version;
  const db = statusState.data?.db;
  const lastRun = statusState.data?.last_run;

  return (
    <AuthGuard>
      <main className="mx-auto max-w-6xl p-4 md:p-6">
        <SystemContext
          title="Ops Overview"
          subtitle="System telemetry for ingestion, reporting, and job runtime health."
          businessId={lastRun?.business_id ?? "biz_001"}
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

          <section className="mt-4 grid gap-4 md:grid-cols-2 lg:grid-cols-4">
            <StatusCard title="Backend Health" status={statusState.data?.backend_health === "ok" ? "ok" : "warn"}>
              <p>
                API status: <strong>{statusState.data?.backend_health ?? (statusState.loading ? "checking..." : "unknown")}</strong>
              </p>
            </StatusCard>

            <StatusCard title="Backend Version" status={version ? "ok" : statusState.loading ? "warn" : "error"}>
              {version ? (
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
              <p>
                Database: <strong>{db?.connected ? "connected" : statusState.loading ? "checking..." : "disconnected"}</strong>
              </p>
              {db?.error ? <p className="mt-1 text-[var(--danger)]">{db.error}</p> : null}
            </StatusCard>

            <StatusCard title="Last Run" status={lastRun ? "ok" : pageStatus === "error" ? "error" : "warn"}>
              {lastRun ? (
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

          <section className="mt-6">
            {effectiveEnhancedMode && webglSupported ? <DataShelf3D /> : <DataShelfFallback />}
          </section>
        </motion.section>
      </main>
    </AuthGuard>
  );
}
