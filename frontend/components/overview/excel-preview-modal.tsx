"use client";

import { useEffect, useRef } from "react";
import type { RecentUpload } from "@/lib/api";

type Props = {
  upload: RecentUpload;
  onClose: () => void;
};

export function ExcelPreviewModal({ upload, onClose }: Props) {
  const dialogRef = useRef<HTMLDialogElement>(null);

  useEffect(() => {
    const dialog = dialogRef.current;
    if (!dialog) return;
    dialog.showModal();
    return () => { dialog.close(); };
  }, []);

  const rows = upload.parsed_data ?? [];
  const columns = rows.length > 0 ? Object.keys(rows[0]) : [];

  return (
    <dialog
      ref={dialogRef}
      onClose={onClose}
      className="w-full max-w-3xl rounded-lg border border-[var(--border)] bg-[var(--bg)] p-0 text-[var(--text)] shadow-xl backdrop:bg-black/60"
    >
      <div className="flex items-center justify-between border-b border-[var(--border)] px-5 py-4">
        <div>
          <h2 className="text-base font-semibold">Upload Preview</h2>
          <p className="mt-0.5 text-xs muted">
            {upload.business_id} &middot; {upload.dataset} &middot;{" "}
            {new Date(upload.timestamp).toLocaleString()} &middot; {upload.record_count} rows
          </p>
        </div>
        <button
          type="button"
          onClick={onClose}
          className="rounded-md p-1.5 text-[var(--text-muted)] transition-colors hover:bg-[var(--surface)] hover:text-[var(--text)]"
          aria-label="Close"
        >
          &#x2715;
        </button>
      </div>

      <div className="max-h-[60vh] overflow-auto p-5">
        {rows.length === 0 ? (
          <p className="muted text-sm">No parsed data available for this upload.</p>
        ) : (
          <table className="w-full border-collapse text-xs">
            <thead>
              <tr>
                {columns.map((col) => (
                  <th
                    key={col}
                    className="sticky top-0 border-b border-[var(--border)] bg-[var(--surface)] px-3 py-2 text-left font-semibold text-[var(--text-muted)]"
                  >
                    {col}
                  </th>
                ))}
              </tr>
            </thead>
            <tbody>
              {rows.map((row, i) => (
                <tr
                  key={i}
                  className="border-b border-[var(--border)] transition-colors hover:bg-[var(--surface)]"
                >
                  {columns.map((col) => (
                    <td key={col} className="px-3 py-1.5 tabular-nums">
                      {String(row[col] ?? "")}
                    </td>
                  ))}
                </tr>
              ))}
            </tbody>
          </table>
        )}
      </div>
    </dialog>
  );
}
