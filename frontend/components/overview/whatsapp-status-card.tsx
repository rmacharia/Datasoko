"use client";

import { useCallback, useEffect, useState } from "react";

import { StatusCard } from "@/components/status-card";
import { useAuth } from "@/components/auth-provider";
import {
  getWhatsAppStatus,
  isApiError,
  type WhatsAppStatusResponse,
} from "@/lib/api";

const deliveryColors: Record<string, string> = {
  delivered: "text-[var(--ok)]",
  sent: "text-[var(--accent)]",
  failed: "text-[var(--danger)]",
};

export function WhatsAppStatusCard() {
  const { token } = useAuth();
  const [data, setData] = useState<WhatsAppStatusResponse | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  const load = useCallback(async () => {
    if (!token) return;
    setLoading(true);
    setError(null);
    try {
      const res = await getWhatsAppStatus(token);
      setData(res);
    } catch (err) {
      if (isApiError(err) && err.status === 404) {
        setData({ last_sent: null });
      } else {
        setError(isApiError(err) ? err.message : "Failed to load WhatsApp status");
      }
    } finally {
      setLoading(false);
    }
  }, [token]);

  useEffect(() => { void load(); }, [load]);

  const cardStatus = error ? "error" : loading ? "warn" : data?.last_sent ? "ok" : "warn";
  const last = data?.last_sent;

  return (
    <StatusCard title="WhatsApp Delivery" status={cardStatus}>
      {loading ? (
        <p className="muted text-sm">Checking WhatsApp status...</p>
      ) : error ? (
        <p className="text-xs text-[var(--danger)]">{error}</p>
      ) : last ? (
        <div className="space-y-2">
          <dl className="space-y-1 text-xs">
            <div>
              <dt className="inline muted">Phone:</dt>{" "}
              <dd className="inline font-mono font-medium">{last.phone}</dd>
            </div>
            <div>
              <dt className="inline muted">Sent:</dt>{" "}
              <dd className="inline font-medium">{new Date(last.timestamp).toLocaleString()}</dd>
            </div>
            <div>
              <dt className="inline muted">Status:</dt>{" "}
              <dd className={`inline font-semibold capitalize ${deliveryColors[last.status] ?? ""}`}>
                {last.status}
              </dd>
            </div>
            <div>
              <dt className="inline muted">Business:</dt>{" "}
              <dd className="inline font-mono font-medium">{last.business_id}</dd>
            </div>
          </dl>
          <div className="rounded-md border border-[var(--border)] bg-[rgba(10,19,33,0.6)] px-3 py-2">
            <p className="text-[10px] muted mb-1">Message preview</p>
            <p className="text-xs leading-relaxed line-clamp-3">{last.preview_text}</p>
          </div>
        </div>
      ) : (
        <div className="space-y-2">
          <p className="muted text-sm">No WhatsApp messages sent yet.</p>
          <p className="text-[10px] muted italic">
            Configure WhatsApp in Settings to enable report delivery.
          </p>
        </div>
      )}
    </StatusCard>
  );
}
