import type { SelectHTMLAttributes } from "react";

type Props = SelectHTMLAttributes<HTMLSelectElement> & {
  children: React.ReactNode;
};

export function Select({ className = "", children, ...props }: Props) {
  return (
    <select
      className={`w-full rounded-md border border-[var(--border)] bg-[rgba(11,21,37,0.9)] px-3 py-2 text-sm text-[var(--text)] shadow-[inset_0_0_0_1px_rgba(79,121,199,0.15)] transition focus:border-[var(--accent)] focus:shadow-[0_0_0_2px_rgba(55,181,255,0.35)] ${className}`}
      {...props}
    >
      {children}
    </select>
  );
}
