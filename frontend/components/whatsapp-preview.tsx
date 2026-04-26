"use client";

import React from "react";
import { Button } from "@/components/ui/button";

type Props = {
  message: string;
  onCopy: () => void;
  copyDisabled?: boolean;
};

export function WhatsAppPreview({ message, onCopy, copyDisabled = false }: Props) {
  return (
    <article className="card p-5">
      <div className="mb-3 flex items-center justify-between gap-2">
        <h2 className="text-lg font-semibold">WhatsApp Preview</h2>
        <Button type="button" variant="secondary" onClick={onCopy} disabled={copyDisabled}>
          Copy WhatsApp Message
        </Button>
      </div>

      <div className="mx-auto w-full max-w-sm rounded-[1.25rem] border border-[#405f88] bg-[#0a1523] p-3 shadow-inner">
        <div className="h-[1.1rem] w-16 rounded-full bg-[#304967]" aria-hidden="true" />
        <div className="mt-3 rounded-xl bg-[#123526] p-3 text-sm leading-relaxed text-[#dbffe9]">
          <pre className="whitespace-pre-wrap break-words font-sans">{message || "No preview available."}</pre>
        </div>
      </div>
    </article>
  );
}
