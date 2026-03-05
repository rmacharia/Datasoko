"use client";

import React from "react";
import { AnimatePresence, motion, useReducedMotion } from "framer-motion";
import { useState } from "react";

type Props = {
  title: string;
  value: unknown;
  defaultCollapsed?: boolean;
};

export function JsonPanel({ title, value, defaultCollapsed = true }: Props) {
  const [open, setOpen] = useState(!defaultCollapsed);
  const reduce = useReducedMotion();

  return (
    <section className="card p-5">
      <div className="flex items-center justify-between gap-2">
        <h2 className="text-lg font-semibold">{title}</h2>
        <button
          type="button"
          className="rounded-md border border-[var(--border)] px-2 py-1 text-xs font-semibold"
          onClick={() => setOpen((prev) => !prev)}
          aria-expanded={open}
        >
          {open ? "Collapse" : "Expand"}
        </button>
      </div>

      <AnimatePresence initial={false}>
        {open ? (
          <motion.div
            key="body"
            initial={reduce ? false : { height: 0, opacity: 0 }}
            animate={reduce ? { height: "auto", opacity: 1 } : { height: "auto", opacity: 1 }}
            exit={reduce ? { height: 0, opacity: 1 } : { height: 0, opacity: 0 }}
            transition={reduce ? { duration: 0 } : { duration: 0.2, ease: "easeOut" }}
            className="overflow-hidden"
          >
            <pre className="code-panel mt-3 max-h-96 overflow-auto p-4 text-xs">{JSON.stringify(value, null, 2)}</pre>
          </motion.div>
        ) : null}
      </AnimatePresence>
    </section>
  );
}
