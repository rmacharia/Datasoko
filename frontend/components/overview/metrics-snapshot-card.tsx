"use client";

import { useCallback, useEffect, useState } from "react";

import { StatusCard } from "@/components/status-card";
import { useAuth } from "@/components/auth-provider";
import { useOrg } from "@/components/org-provider";
import {
  getWeeklyMetrics,
  isApiError,
  type WeeklyMetricsResponse,
} from "@/lib/api";

function TrendBadge({ delta }: { delta: number | null }) {
  if (delta === null || delta === undefined) return <span className="muted">--</span>;
  const positive = delta >= 0;
  return (
    <span
      className={`inline-flex items-center gap-0.5 rounded px-1.5 py-0.5 text-xs font-semibold tabular-nums ${
        positive
          ? "bg-[rgba(53,211,157,0.14)] text-[var(--ok)]"
          : "bg-[rgba(255,107,122,0.14)] text-[var(--danger)]"
      }`}
    >
      {positive ? "▲" : "▼"} {Math.abs(delta).toFixed(1)}%
    </span>
  );
}

function formatCurrency(value: number): string {
  return new Intl.NumberFormat("en-KE", {
    style: "currency",
    currency: "KES",
    minimumFractionDigits: 0,
    maximumFractionDigits: 0,
  }).format(value);
}

export function MetricsSnapshotCard() {
  const { token } = useAuth();
  const { activeBusinessId } = useOrg();
  const [metrics, setMetrics] = useState<WeeklyMetricsResponse | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  const load = useCallback(async () => {
    if (!token || !activeBusinessId) return;
    setLoading(true);
    setError(null);
    try {
      const res = await getWeeklyMetrics(token, activeBusinessId);
      setMetrics(res);
    } catch (err) {
      setError(isApiError(err) ? err.message : "Failed to load metrics");
    } finally {
      setLoading(false);
    }
  }, [token, activeBusinessId]);

  useEffect(() => { void load(); }, [load]);

  const cardStatus = error ? "error" : loading ? "warn" : "ok";

  return (
    <StatusCard title="Metrics Snapshot" status={cardStatus}>
      {loading ? (
        <p className="muted text-sm">Loading metrics...</p>
      ) : error ? (
        <p className="text-xs text-[var(--danger)]">{error}</p>
      ) : metrics ? (
        <div className="space-y-3">
          <div className="grid grid-cols-2 gap-3">
            <div>
              <p className="text-xs muted">Revenue</p>
              <p className="text-lg font-bold tabular-nums text-[var(--accent)]">
                {formatCurrency(metrics.revenue)}
              </p>
              <TrendBadge delta={metrics.wow_revenue_delta} />
            </div>
            <div>
              <p className="text-xs muted">Orders</p>
              <p className="text-lg font-bold tabular-nums text-[var(--accent)]">
                {metrics.order_count}
              </p>
              <TrendBadge delta={metrics.wow_order_delta} />
            </div>
          </div>
          <dl className="space-y-1 text-xs">
            <div>
              <dt className="inline muted">Avg order:</dt>{" "}
              <dd className="inline font-semibold tabular-nums">{formatCurrency(metrics.avg_order_value)}</dd>
            </div>
            <div>
              <dt className="inline muted">Top product:</dt>{" "}
              <dd className="inline font-semibold">{metrics.top_product ?? "N/A"}</dd>
            </div>
            <div>
              <dt className="inline muted">Repeat customers:</dt>{" "}
              <dd className="inline font-semibold tabular-nums">{metrics.repeat_customers}</dd>
            </div>
          </dl>
          <p className="text-[10px] muted">
            Week: {metrics.week_start} &mdash; {metrics.week_end}
          </p>
        </div>
      ) : (
        <p className="muted text-sm">No metrics data available.</p>
      )}
    </StatusCard>
  );
}
