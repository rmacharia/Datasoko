"use client";

import type { AnalyticsUpload } from "@/lib/api";

type Props = {
  uploads: AnalyticsUpload[];
};

const statusBadge: Record<string, string> = {
  processed: "badge badge-ok",
  partial: "badge badge-warn",
  failed: "badge badge-danger",
};

export function UploadsTable({ uploads }: Props) {
  if (uploads.length === 0) {
    return (
      <div className="flex h-32 items-center justify-center rounded-lg border border-[var(--border)] bg-[rgba(10,19,33,0.6)]">
        <p className="text-sm muted">No data yet — upload data to see insights</p>
      </div>
    );
  }

  return (
    <div className="overflow-x-auto rounded-lg border border-[var(--border)]">
      <table className="w-full text-xs">
        <thead>
          <tr className="border-b border-[var(--border)] bg-[rgba(10,19,33,0.7)] text-left">
            <th className="px-3 py-2 font-semibold">File Name</th>
            <th className="px-3 py-2 font-semibold">Dataset</th>
            <th className="px-3 py-2 font-semibold text-right">Rows</th>
            <th className="px-3 py-2 font-semibold text-right">Quality</th>
            <th className="px-3 py-2 font-semibold">Uploaded</th>
            <th className="px-3 py-2 font-semibold">Status</th>
          </tr>
        </thead>
        <tbody>
          {uploads.map((u, i) => (
            <tr
              key={`${u.file_name}-${u.uploaded_at}-${i}`}
              className="border-b border-[var(--border)] last:border-0 hover:bg-[rgba(79,121,199,0.07)]"
            >
              <td className="px-3 py-2 font-mono">{u.file_name}</td>
              <td className="px-3 py-2 capitalize">{u.dataset.replace("_", " ")}</td>
              <td className="px-3 py-2 text-right tabular-nums font-semibold">{u.rows}</td>
              <td className="px-3 py-2 text-right tabular-nums">
                {u.quality_score !== null ? `${u.quality_score}%` : "—"}
              </td>
              <td className="px-3 py-2 muted">
                {new Date(u.uploaded_at).toLocaleDateString()}
              </td>
              <td className="px-3 py-2">
                <span className={statusBadge[u.status] ?? "badge badge-ok"}>
                  {u.status}
                </span>
              </td>
            </tr>
          ))}
        </tbody>
      </table>
    </div>
  );
}
