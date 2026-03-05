import { motion, useReducedMotion } from "framer-motion";

type Props = {
  title: string;
  subtitle: string;
  businessId: string;
  timezone?: string;
  currency?: string;
};

export function SystemContext({ title, subtitle, businessId, timezone = "Africa/Nairobi (EAT)", currency = "KES" }: Props) {
  const reduce = useReducedMotion();

  return (
    <motion.section
      className="mb-6 card card-glow p-5"
      initial={reduce ? false : { opacity: 0, y: 6 }}
      animate={{ opacity: 1, y: 0 }}
      transition={reduce ? { duration: 0 } : { duration: 0.2, ease: "easeOut" }}
    >
      <div className="flex flex-wrap items-end justify-between gap-3">
        <div>
          <h1 className="text-2xl font-semibold tracking-tight">{title}</h1>
          <p className="mt-1 text-sm muted">{subtitle}</p>
        </div>
        <dl className="grid grid-cols-3 gap-2 text-xs">
          <div className="rounded-md border border-[var(--border)] bg-[rgba(10,19,33,0.85)] px-3 py-2">
            <dt className="muted">Business</dt>
            <dd className="font-semibold">{businessId}</dd>
          </div>
          <div className="rounded-md border border-[var(--border)] bg-[rgba(10,19,33,0.85)] px-3 py-2">
            <dt className="muted">Timezone</dt>
            <dd className="font-semibold">{timezone}</dd>
          </div>
          <div className="rounded-md border border-[var(--border)] bg-[rgba(10,19,33,0.85)] px-3 py-2">
            <dt className="muted">Currency</dt>
            <dd className="font-semibold">{currency}</dd>
          </div>
        </dl>
      </div>
    </motion.section>
  );
}
