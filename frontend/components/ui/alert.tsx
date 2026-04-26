import type { ReactNode } from "react";

type Tone = "info" | "success" | "warning" | "danger";

type Props = {
  tone?: Tone;
  children: ReactNode;
};

const toneClass: Record<Tone, string> = {
  info: "border-[rgba(55,181,255,0.5)] bg-[rgba(55,181,255,0.1)] text-[#b7e7ff]",
  success: "border-[rgba(53,211,157,0.5)] bg-[rgba(53,211,157,0.12)] text-[#a5f0d2]",
  warning: "border-[rgba(255,200,87,0.5)] bg-[rgba(255,200,87,0.12)] text-[#ffe2a0]",
  danger: "border-[rgba(255,107,122,0.5)] bg-[rgba(255,107,122,0.12)] text-[#ffc4cc]",
};

export function Alert({ tone = "info", children }: Props) {
  return <div className={`rounded-md border px-3 py-2 text-sm ${toneClass[tone]}`}>{children}</div>;
}
