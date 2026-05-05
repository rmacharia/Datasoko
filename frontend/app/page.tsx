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
import { MetricsChart } from "@/components/analytics/metrics-chart";
import { SummaryCards } from "@/components/analytics/summary-cards";
import { UploadsTable } from "@/components/analytics/uploads-table";
import { WhatsAppStats } from "@/components/analytics/whatsapp-stats";
import { ActivityTimeline } from "@/components/analytics/activity-timeline";
import {
  getAdminStatus,
  getAnalyticsActivity,
  getAnalyticsCosts,
  getAnalyticsMetrics,
  getAnalyticsUploads,
  getAnalyticsWhatsApp,
  getBilling,
  getBusinesses,
  getSchedules,
  isApiError,
  type AdminStatusResponse,
  type AnalyticsActivity,
  type AnalyticsCostsResponse,
  type AnalyticsMetricsResponse,
  type AnalyticsUpload,
  type AnalyticsWhatsAppStats,
  type BillingResponse,
  type BusinessesResponse,
  type Schedule,
} from "@/lib/api";

type LoadState<T> = {
  loading: boolean;
  data: T | null;
  error: string | null;
};

export default function OverviewPage() {
  const router = useRouter();
  const { token, user, isReady, isAuthenticated } = useAuth();
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

  // Analytics state
  const [analyticsMetrics, setAnalyticsMetrics] = useState<LoadState<AnalyticsMetricsResponse>>({ loading: false, data: null, error: null });
  const [analyticsUploads, setAnalyticsUploads] = useState<LoadState<AnalyticsUpload[]>>({ loading: false, data: null, error: null });
  const [analyticsWhatsApp, setAnalyticsWhatsApp] = useState<LoadState<AnalyticsWhatsAppStats>>({ loading: false, data: null, error: null });
  const [analyticsActivity, setAnalyticsActivity] = useState<LoadState<AnalyticsActivity[]>>({ loading: false, data: null, error: null });
  const [analyticsCosts, setAnalyticsCosts] = useState<LoadState<AnalyticsCostsResponse>>({ loading: false, data: null, error: null });
  const [schedulesState, setSchedulesState] = useState<LoadState<Schedule[]>>({ loading: false, data: null, error: null });

  useEffect(() => {
    if (!isReady || !isAuthenticated || !user) return;
    // Super admins are platform-scoped and have no tenant — send them to
    // the admin console and never run the tenant-onboarding check.
    if (user.role === "super_admin") {
      router.replace("/admin");
      return;
    }
    let mounted = true;
    if (!user.organization_id) {
      setOnboardingChecked(true);
      return () => { mounted = false; };
    }
    getBilling(user.organization_id)
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
  }, [isReady, isAuthenticated, user, router]);

  const load = useCallback(async () => {
    if (!token) return;

    setStatusState({ loading: true, data: null, error: null });
    setBillingState({ loading: true, data: null, error: null });
    setBizState({ loading: true, data: null, error: null });

    try {
      const [statusData, billingData, bizData] = await Promise.all([
        getAdminStatus(token),
        getBilling(token, organizationId),
        getBusinesses(token, organizationId),
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

  const loadAnalytics = useCallback(async () => {
    if (!token) return;

    if (!activeBusinessId) return;
    const params = { businessId: activeBusinessId };

    setAnalyticsMetrics({ loading: true, data: null, error: null });
    setAnalyticsUploads({ loading: true, data: null, error: null });
    setAnalyticsWhatsApp({ loading: true, data: null, error: null });
    setAnalyticsActivity({ loading: true, data: null, error: null });
    setAnalyticsCosts({ loading: true, data: null, error: null });
    setSchedulesState({ loading: true, data: null, error: null });

    try {
      const [metrics, uploads, whatsapp, activity, costs, schedules] = await Promise.all([
        getAnalyticsMetrics(token, params),
        getAnalyticsUploads(token, params),
        getAnalyticsWhatsApp(token, params),
        getAnalyticsActivity(token, params),
        getAnalyticsCosts(token),
        getSchedules(token),
      ]);
      setAnalyticsMetrics({ loading: false, data: metrics, error: null });
      setAnalyticsUploads({ loading: false, data: uploads, error: null });
      setAnalyticsWhatsApp({ loading: false, data: whatsapp, error: null });
      setAnalyticsActivity({ loading: false, data: activity, error: null });
      setAnalyticsCosts({ loading: false, data: costs, error: null });
      setSchedulesState({ loading: false, data: schedules, error: null });
    } catch (err) {
      const msg = isApiError(err) ? err.message : "Failed to load analytics.";
      setAnalyticsMetrics((prev) => prev.data ? prev : { loading: false, data: null, error: msg });
      setAnalyticsUploads((prev) => prev.data ? prev : { loading: false, data: null, error: msg });
      setAnalyticsWhatsApp((prev) => prev.data ? prev : { loading: false, data: null, error: msg });
      setAnalyticsActivity((prev) => prev.data ? prev : { loading: false, data: null, error: msg });
      setAnalyticsCosts((prev) => prev.data ? prev : { loading: false, data: null, error: msg });
      setSchedulesState((prev) => prev.data ? prev : { loading: false, data: null, error: msg });
    }
  }, [token, activeBusinessId]);

  useEffect(() => {
    if (onboardingChecked) void load();
  }, [load, onboardingChecked]);

  useEffect(() => {
    if (onboardingChecked && effectiveEnhancedMode) void loadAnalytics();
  }, [loadAnalytics, onboardingChecked, effectiveEnhancedMode]);

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
          <p className="text-sm muted loading-pulse">Checking subscription status...</p>
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
            <Button variant="secondary" onClick={() => { void load(); void loadAnalytics(); }}>
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

          {/* Row 2+: Analytics Cockpit — visible only in enhanced mode */}
          {effectiveEnhancedMode ? (
            <>
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
                        <dd className="inline font-medium">
                          {analyticsUploads.data?.[0]
                            ? new Date(analyticsUploads.data[0].uploaded_at).toLocaleDateString()
                            : "—"}
                        </dd>
                      </div>
                      <div>
                        <dt className="inline muted">Last report:</dt>{" "}
                        <dd className="inline font-medium">
                          {analyticsActivity.data?.find(e => e.type === "report")
                            ? new Date(analyticsActivity.data.find(e => e.type === "report")!.timestamp).toLocaleDateString()
                            : "—"}
                        </dd>
                      </div>
                    </dl>
                  )}
                </StatusCard>
              </section>

              {/* Analytics Cockpit */}
              <div className="mt-8 mb-4 flex flex-wrap items-end justify-between gap-3">
                <div>
                  <h2 className="text-xl font-semibold">Analytics Cockpit</h2>
                  <p className="mt-1 text-sm muted">
                    Live metrics for <span className="font-mono text-[var(--accent)]">{activeBusinessId}</span>
                  </p>
                </div>
              </div>

              {/* Financial Summary */}
              {analyticsMetrics.loading ? (
                <p className="text-sm muted">Loading metrics...</p>
              ) : analyticsMetrics.error ? (
                <Alert tone="danger">{analyticsMetrics.error}</Alert>
              ) : analyticsMetrics.data ? (
                <>
                  <SummaryCards
                    revenue={analyticsMetrics.data.totals.revenue}
                    expenses={analyticsMetrics.data.totals.expenses}
                    profit={analyticsMetrics.data.totals.profit}
                  />
                  <div className="mt-4 card p-5">
                    <h3 className="mb-3 text-base font-semibold">Revenue / Expenses / Profit Trend</h3>
                    <MetricsChart
                      revenueTrend={analyticsMetrics.data.revenue_trend}
                      expensesTrend={analyticsMetrics.data.expenses_trend}
                      profitTrend={analyticsMetrics.data.profit_trend}
                    />
                  </div>
                </>
              ) : null}

              {/* Uploads + WhatsApp */}
              <section className="mt-6 grid gap-4 lg:grid-cols-2">
                <div className="card p-5">
                  <h3 className="mb-3 text-base font-semibold">Recent Uploads</h3>
                  {analyticsUploads.loading ? (
                    <p className="text-sm muted">Loading uploads...</p>
                  ) : analyticsUploads.error ? (
                    <ErrorBadge message="Data unavailable" />
                  ) : (
                    <UploadsTable uploads={analyticsUploads.data ?? []} />
                  )}
                </div>

                <div className="card p-5">
                  <h3 className="mb-3 text-base font-semibold">WhatsApp Delivery</h3>
                  {analyticsWhatsApp.loading ? (
                    <p className="text-sm muted">Loading WhatsApp stats...</p>
                  ) : analyticsWhatsApp.error ? (
                    <ErrorBadge message="Data unavailable" />
                  ) : analyticsWhatsApp.data ? (
                    <WhatsAppStats stats={analyticsWhatsApp.data} />
                  ) : null}
                </div>
              </section>

              {/* Scheduled Jobs + Cost Tracking */}
              <section className="mt-4 grid gap-4 lg:grid-cols-2">
                <div className="card p-5">
                  <h3 className="mb-3 text-base font-semibold">Scheduled Jobs</h3>
                  {schedulesState.loading ? (
                    <p className="text-sm muted">Loading schedules...</p>
                  ) : schedulesState.error ? (
                    <ErrorBadge message="Data unavailable" />
                  ) : schedulesState.data && schedulesState.data.length > 0 ? (
                    <dl className="space-y-2">
                      <div>
                        <dt className="inline muted text-sm">Active Schedules:</dt>{" "}
                        <dd className="inline text-2xl font-bold tabular-nums text-[var(--accent)]">
                          {schedulesState.data.filter((s) => s.is_active).length}
                        </dd>
                        <span className="ml-2 text-sm muted">/ {schedulesState.data.length} total</span>
                      </div>
                      <div className="mt-2 space-y-1">
                        {schedulesState.data.filter((s) => s.is_active).slice(0, 3).map((s) => (
                          <div key={s.id} className="flex items-center gap-2 rounded border border-[var(--border)] bg-[rgba(10,19,33,0.4)] px-3 py-1.5 text-xs">
                            <span className="capitalize font-medium">{s.frequency}</span>
                            <span className="muted">at {s.time_of_day}</span>
                            <span className="ml-auto font-mono text-[var(--accent)]">
                              {s.business_id || "All SMEs"}
                            </span>
                          </div>
                        ))}
                      </div>
                    </dl>
                  ) : (
                    <p className="text-sm muted">No schedules configured. Set up in Settings.</p>
                  )}
                </div>

                <div className="card p-5">
                  <h3 className="mb-3 text-base font-semibold">WhatsApp Costs</h3>
                  {analyticsCosts.loading ? (
                    <p className="text-sm muted">Loading costs...</p>
                  ) : analyticsCosts.error ? (
                    <ErrorBadge message="Data unavailable" />
                  ) : analyticsCosts.data ? (
                    <dl className="space-y-2">
                      <div className="grid grid-cols-3 gap-3">
                        <div>
                          <dt className="text-xs muted">Messages Sent</dt>
                          <dd className="text-xl font-bold tabular-nums text-[var(--accent)]">
                            {analyticsCosts.data.messages_sent}
                          </dd>
                        </div>
                        <div>
                          <dt className="text-xs muted">Total Cost</dt>
                          <dd className="text-xl font-bold tabular-nums">
                            ${analyticsCosts.data.total_cost.toFixed(2)}
                          </dd>
                        </div>
                        <div>
                          <dt className="text-xs muted">Avg Cost</dt>
                          <dd className="text-xl font-bold tabular-nums">
                            ${analyticsCosts.data.avg_cost.toFixed(4)}
                          </dd>
                        </div>
                      </div>
                      {analyticsCosts.data.last_7_days.length > 0 ? (
                        <div className="mt-2 space-y-1">
                          {analyticsCosts.data.last_7_days.map((d) => (
                            <div key={d.date} className="flex items-center justify-between text-xs">
                              <span className="muted">{new Date(d.date).toLocaleDateString("en-KE", { weekday: "short", month: "short", day: "numeric" })}</span>
                              <span className="tabular-nums">{d.count} msg{d.count !== 1 ? "s" : ""}</span>
                              <span className="tabular-nums font-medium">${d.cost.toFixed(4)}</span>
                            </div>
                          ))}
                        </div>
                      ) : (
                        <p className="mt-2 text-xs muted">No messages in the last 7 days.</p>
                      )}
                    </dl>
                  ) : (
                    <p className="text-sm muted">No cost data available.</p>
                  )}
                </div>
              </section>

              {/* Activity Timeline */}
              <section className="mt-4 card p-5">
                <h3 className="mb-3 text-base font-semibold">Activity Timeline</h3>
                {analyticsActivity.loading ? (
                  <p className="text-sm muted">Loading activity...</p>
                ) : analyticsActivity.error ? (
                  <ErrorBadge message="Data unavailable" />
                ) : (
                  <ActivityTimeline events={analyticsActivity.data ?? []} />
                )}
              </section>
            </>
          ) : null}
        </motion.section>
      </main>
    </AuthGuard>
  );
}
