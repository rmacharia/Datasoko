"use client";

import type { AnalyticsActivity } from "@/lib/api";

type Props = {
  events: AnalyticsActivity[];
};

const typeStyles: Record<string, { icon: string; color: string }> = {
  upload: { icon: "↑", color: "text-[var(--accent)]" },
  report: { icon: "☆", color: "text-[#a78bfa]" },
  whatsapp: { icon: "✉", color: "text-[var(--ok)]" },
  error: { icon: "✗", color: "text-[var(--danger)]" },
};

function timeAgo(iso: string): string {
  const diff = Date.now() - new Date(iso).getTime();
  const mins = Math.floor(diff / 60_000);
  if (mins < 1) return "just now";
  if (mins < 60) return `${mins}m ago`;
  const hrs = Math.floor(mins / 60);
  if (hrs < 24) return `${hrs}h ago`;
  const days = Math.floor(hrs / 24);
  return `${days}d ago`;
}

export function ActivityTimeline({ events }: Props) {
  if (events.length === 0) {
    return (
      <div className="flex h-32 items-center justify-center rounded-lg border border-[var(--border)] bg-[rgba(10,19,33,0.6)]">
        <p className="text-sm muted">No activity recorded yet</p>
      </div>
    );
  }

  return (
    <ul className="space-y-2 max-h-80 overflow-y-auto">
      {events.map((ev, i) => {
        const style = typeStyles[ev.type] ?? typeStyles.error;
        return (
          <li
            key={`${ev.timestamp}-${i}`}
            className="flex items-start gap-2 rounded-md border border-[var(--border)] bg-[rgba(10,19,33,0.6)] px-3 py-2 text-xs"
          >
            <span className={`mt-0.5 shrink-0 ${style.color}`} aria-hidden="true">
              {style.icon}
            </span>
            <div className="min-w-0 flex-1">
              <div className="flex items-center gap-2">
                <p className="font-medium">{ev.message}</p>
                {ev.status === "failed" ? (
                  <span className="badge badge-danger text-[10px]">failed</span>
                ) : null}
              </div>
              <p className="muted mt-0.5">{timeAgo(ev.timestamp)}</p>
            </div>
          </li>
        );
      })}
    </ul>
  );
}
