"use client";

import { useCallback, useEffect, useState } from "react";

import { StatusCard } from "@/components/status-card";
import { useAuth } from "@/components/auth-provider";
import {
  getRecentUploads,
  isApiError,
  type RecentUpload,
} from "@/lib/api";

type Props = {
  onSelectUpload?: (upload: RecentUpload) => void;
};

const statusColors: Record<RecentUpload["status"], string> = {
  success: "text-[var(--ok)]",
  partial: "text-[var(--warn)]",
  failed: "text-[var(--danger)]",
};

const statusIcons: Record<RecentUpload["status"], string> = {
  success: "✓",
  partial: "○",
  failed: "✗",
};

export function RecentUploadsCard({ onSelectUpload }: Props) {
  const { token } = useAuth();
  const [uploads, setUploads] = useState<RecentUpload[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  const load = useCallback(async () => {
    if (!token) return;
    setLoading(true);
    setError(null);
    try {
      const res = await getRecentUploads(token, 5);
      setUploads(res.uploads);
    } catch (err) {
      setError(isApiError(err) ? err.message : "Failed to load recent uploads");
    } finally {
      setLoading(false);
    }
  }, [token]);

  useEffect(() => { void load(); }, [load]);

  const cardStatus = error ? "error" : loading ? "warn" : "ok";

  return (
    <StatusCard title="Recent Uploads" status={cardStatus}>
      {loading ? (
        <p className="muted text-sm">Loading uploads...</p>
      ) : error ? (
        <p className="text-xs text-[var(--danger)]">{error}</p>
      ) : uploads.length === 0 ? (
        <p className="muted text-sm">No uploads recorded yet.</p>
      ) : (
        <ul className="space-y-2">
          {uploads.map((u, i) => (
            <li key={`${u.business_id}-${u.timestamp}-${i}`}>
              <button
                type="button"
                onClick={() => onSelectUpload?.(u)}
                className="w-full rounded-md border border-[var(--border)] bg-[rgba(10,19,33,0.6)] px-3 py-2 text-left text-xs transition-colors hover:border-[var(--border-bright)] hover:bg-[rgba(10,19,33,0.85)]"
              >
                <div className="flex items-center justify-between gap-2">
                  <span className="font-mono font-medium">{u.business_id}</span>
                  <span className={`font-semibold ${statusColors[u.status]}`}>
                    {statusIcons[u.status]} {u.status}
                  </span>
                </div>
                <div className="mt-1 flex items-center justify-between gap-2 muted">
                  <span>{new Date(u.timestamp).toLocaleString()}</span>
                  <span className="tabular-nums">{u.record_count} rows</span>
                </div>
              </button>
            </li>
          ))}
        </ul>
      )}
    </StatusCard>
  );
}
