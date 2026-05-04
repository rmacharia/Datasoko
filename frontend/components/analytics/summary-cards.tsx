"use client";

type Props = {
  revenue: number;
  expenses: number;
  profit: number;
};

function formatCurrency(value: number): string {
  return new Intl.NumberFormat("en-KE", {
    style: "currency",
    currency: "KES",
    minimumFractionDigits: 0,
    maximumFractionDigits: 0,
  }).format(value);
}

export function SummaryCards({ revenue, expenses, profit }: Props) {
  const profitPositive = profit >= 0;
  const margin = revenue > 0 ? ((profit / revenue) * 100).toFixed(1) : "0.0";

  return (
    <div className="grid gap-4 sm:grid-cols-2 lg:grid-cols-4">
      <div className="rounded-lg border border-[var(--border)] bg-[rgba(10,19,33,0.6)] p-4">
        <p className="text-xs muted">Total Revenue</p>
        <p className="mt-1 text-2xl font-bold tabular-nums text-[var(--accent)]">
          {formatCurrency(revenue)}
        </p>
      </div>
      <div className="rounded-lg border border-[var(--border)] bg-[rgba(10,19,33,0.6)] p-4">
        <p className="text-xs muted">Total Expenses</p>
        <p className="mt-1 text-2xl font-bold tabular-nums text-[var(--danger)]">
          {formatCurrency(expenses)}
        </p>
      </div>
      <div className="rounded-lg border border-[var(--border)] bg-[rgba(10,19,33,0.6)] p-4">
        <p className="text-xs muted">Net Profit</p>
        <p className={`mt-1 text-2xl font-bold tabular-nums ${profitPositive ? "text-[var(--ok)]" : "text-[var(--danger)]"}`}>
          {profitPositive ? "" : "-"}{formatCurrency(Math.abs(profit))}
        </p>
      </div>
      <div className="rounded-lg border border-[var(--border)] bg-[rgba(10,19,33,0.6)] p-4">
        <p className="text-xs muted">Profit Margin</p>
        <p className={`mt-1 text-2xl font-bold tabular-nums ${profitPositive ? "text-[var(--ok)]" : "text-[var(--danger)]"}`}>
          {margin}%
        </p>
      </div>
    </div>
  );
}
