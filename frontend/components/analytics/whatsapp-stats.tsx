"use client";

import type { AnalyticsWhatsAppStats } from "@/lib/api";

type Props = {
  stats: AnalyticsWhatsAppStats;
};

export function WhatsAppStats({ stats }: Props) {
  const hasData = stats.total_sent > 0;

  if (!hasData) {
    return (
      <div className="flex h-32 items-center justify-center rounded-lg border border-[var(--border)] bg-[rgba(10,19,33,0.6)]">
        <p className="text-sm muted">No WhatsApp messages sent yet</p>
      </div>
    );
  }

  return (
    <div className="grid gap-4 sm:grid-cols-3">
      <div className="rounded-lg border border-[var(--border)] bg-[rgba(10,19,33,0.6)] p-4">
        <p className="text-xs muted">Total Sent</p>
        <p className="mt-1 text-2xl font-bold tabular-nums text-[var(--accent)]">
          {stats.total_sent}
        </p>
      </div>
      <div className="rounded-lg border border-[var(--border)] bg-[rgba(10,19,33,0.6)] p-4">
        <p className="text-xs muted">Last Sent</p>
        <p className="mt-1 text-sm font-semibold">
          {stats.last_sent ? new Date(stats.last_sent).toLocaleString() : "—"}
        </p>
      </div>
      <div className="rounded-lg border border-[var(--border)] bg-[rgba(10,19,33,0.6)] p-4">
        <p className="text-xs muted">Success Rate</p>
        <p className={`mt-1 text-2xl font-bold tabular-nums ${
          stats.success_rate >= 90 ? "text-[var(--ok)]"
          : stats.success_rate >= 70 ? "text-[var(--warn)]"
          : "text-[var(--danger)]"
        }`}>
          {stats.success_rate}%
        </p>
      </div>
    </div>
  );
}
