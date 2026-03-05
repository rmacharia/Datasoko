import type { InputHTMLAttributes } from "react";

type Props = InputHTMLAttributes<HTMLInputElement>;

export function Input({ className = "", ...props }: Props) {
  return (
    <input
      className={`mt-1 w-full rounded-md border border-[var(--border)] bg-[rgba(11,21,37,0.9)] px-3 py-2 text-sm text-[var(--text)] placeholder:text-[var(--text-muted)] shadow-[inset_0_0_0_1px_rgba(79,121,199,0.15)] transition focus:border-[var(--accent)] focus:shadow-[0_0_0_2px_rgba(55,181,255,0.35)] ${className}`}
      {...props}
    />
  );
}
