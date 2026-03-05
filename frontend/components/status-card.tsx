import type { ReactNode } from "react";

type Props = {
  title: string;
  status: "ok" | "warn" | "error";
  children: ReactNode;
};

const badgeClasses: Record<Props["status"], string> = {
  ok: "badge badge-ok",
  warn: "badge badge-warn",
  error: "badge badge-danger",
};

const labels: Record<Props["status"], string> = {
  ok: "Nominal",
  warn: "Degraded",
  error: "Fault",
};

const icons: Record<Props["status"], string> = {
  ok: "◉",
  warn: "◈",
  error: "◎",
};

export function StatusCard({ title, status, children }: Props) {
  return (
    <article className="card p-5" aria-live="polite">
      <header className="mb-4 flex items-center justify-between gap-2">
        <h2 className="flex items-center gap-2 text-base font-semibold">
          <span className="text-[var(--accent)]" aria-hidden="true">
            {icons[status]}
          </span>
          {title}
        </h2>
        <span className={badgeClasses[status]}>{labels[status]}</span>
      </header>
      <div className="text-sm text-[var(--text)]">{children}</div>
    </article>
  );
}
