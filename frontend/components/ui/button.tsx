import React from "react";
import type { ButtonHTMLAttributes, ReactNode } from "react";

type Variant = "primary" | "secondary" | "ghost";

type Props = ButtonHTMLAttributes<HTMLButtonElement> & {
  variant?: Variant;
  icon?: ReactNode;
};

const variantClass: Record<Variant, string> = {
  primary:
    "border border-transparent bg-[linear-gradient(130deg,var(--accent),var(--accent-strong))] text-[#041223] shadow-[0_6px_22px_rgba(55,181,255,0.45)] hover:brightness-110",
  secondary:
    "border border-[var(--border-bright)] bg-[rgba(22,40,63,0.9)] text-[var(--text)] hover:bg-[rgba(40,64,92,0.9)]",
  ghost: "border border-[var(--border)] bg-transparent text-[var(--text)] hover:bg-[rgba(79,121,199,0.15)]",
};

export function Button({ variant = "secondary", icon, className = "", children, ...props }: Props) {
  return (
    <button
      className={`inline-flex items-center justify-center gap-2 rounded-md px-4 py-2 text-sm font-semibold transition ${variantClass[variant]} ${className}`}
      {...props}
    >
      {icon ? <span aria-hidden="true">{icon}</span> : null}
      {children}
    </button>
  );
}
