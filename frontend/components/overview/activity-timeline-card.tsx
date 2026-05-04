"use client";

import { StatusCard } from "@/components/status-card";

type ActivityEvent = {
  id: string;
  type: "report_generated" | "report_sent" | "upload" | "failure";
  message: string;
  timestamp: string;
};

const typeStyles: Record<ActivityEvent["type"], { icon: string; color: string }> = {
  report_generated: { icon: "☆", color: "text-[var(--accent)]" },
  report_sent: { icon: "✉", color: "text-[var(--ok)]" },
  upload: { icon: "↑", color: "text-[var(--accent)]" },
  failure: { icon: "✗", color: "text-[var(--danger)]" },
};

const MOCK_EVENTS: ActivityEvent[] = [
  {
    id: "1",
    type: "report_generated",
    message: "Weekly report generated for biz_001",
    timestamp: new Date(Date.now() - 1_800_000).toISOString(),
  },
  {
    id: "2",
    type: "report_sent",
    message: "WhatsApp report delivered to +254700100200",
    timestamp: new Date(Date.now() - 3_600_000).toISOString(),
  },
  {
    id: "3",
    type: "upload",
    message: "Excel upload processed — 142 rows ingested",
    timestamp: new Date(Date.now() - 7_200_000).toISOString(),
  },
  {
    id: "4",
    type: "failure",
    message: "M-Pesa CSV parsing failed — invalid header row",
    timestamp: new Date(Date.now() - 14_400_000).toISOString(),
  },
  {
    id: "5",
    type: "report_generated",
    message: "Weekly report generated for biz_002",
    timestamp: new Date(Date.now() - 28_800_000).toISOString(),
  },
];

function timeAgo(iso: string): string {
  const diff = Date.now() - new Date(iso).getTime();
  const mins = Math.floor(diff / 60_000);
  if (mins < 60) return `${mins}m ago`;
  const hrs = Math.floor(mins / 60);
  if (hrs < 24) return `${hrs}h ago`;
  return `${Math.floor(hrs / 24)}d ago`;
}

export function ActivityTimelineCard() {
  const events = MOCK_EVENTS;

  return (
    <StatusCard title="Activity Timeline" status="ok">
      <ul className="space-y-2">
        {events.map((ev) => {
          const style = typeStyles[ev.type];
          return (
            <li
              key={ev.id}
              className="flex items-start gap-2 rounded-md border border-[var(--border)] bg-[rgba(10,19,33,0.6)] px-3 py-2 text-xs"
            >
              <span className={`mt-0.5 shrink-0 ${style.color}`} aria-hidden="true">
                {style.icon}
              </span>
              <div className="min-w-0 flex-1">
                <p className="font-medium">{ev.message}</p>
                <p className="muted mt-0.5">{timeAgo(ev.timestamp)}</p>
              </div>
            </li>
          );
        })}
      </ul>
      <p className="mt-2 text-[10px] muted italic">Mock data — will connect to live events feed</p>
    </StatusCard>
  );
}
