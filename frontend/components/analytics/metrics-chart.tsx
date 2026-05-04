"use client";

import {
  LineChart,
  Line,
  XAxis,
  YAxis,
  CartesianGrid,
  Tooltip,
  ResponsiveContainer,
  Legend,
} from "recharts";
import type { AnalyticsTrendPoint } from "@/lib/api";

type Props = {
  revenueTrend: AnalyticsTrendPoint[];
  expensesTrend: AnalyticsTrendPoint[];
  profitTrend: AnalyticsTrendPoint[];
};

function formatDate(dateStr: string): string {
  const d = new Date(dateStr);
  return d.toLocaleDateString("en-KE", { month: "short", day: "numeric" });
}

function formatCurrency(value: number): string {
  if (value >= 1_000_000) return `${(value / 1_000_000).toFixed(1)}M`;
  if (value >= 1_000) return `${(value / 1_000).toFixed(0)}K`;
  return value.toFixed(0);
}

export function MetricsChart({ revenueTrend, expensesTrend, profitTrend }: Props) {
  const data = revenueTrend.map((point, i) => ({
    date: formatDate(point.date),
    revenue: point.value,
    expenses: expensesTrend[i]?.value ?? 0,
    profit: profitTrend[i]?.value ?? 0,
  }));

  if (data.length === 0) {
    return (
      <div className="flex h-64 items-center justify-center rounded-lg border border-[var(--border)] bg-[rgba(10,19,33,0.6)]">
        <p className="text-sm muted">No data yet — upload data to see insights</p>
      </div>
    );
  }

  return (
    <div className="h-72 w-full">
      <ResponsiveContainer width="100%" height="100%">
        <LineChart data={data} margin={{ top: 8, right: 16, left: 0, bottom: 0 }}>
          <CartesianGrid strokeDasharray="3 3" stroke="rgba(42,59,86,0.5)" />
          <XAxis
            dataKey="date"
            tick={{ fill: "var(--text-muted)", fontSize: 11 }}
            axisLine={{ stroke: "var(--border)" }}
            tickLine={false}
          />
          <YAxis
            tickFormatter={formatCurrency}
            tick={{ fill: "var(--text-muted)", fontSize: 11 }}
            axisLine={{ stroke: "var(--border)" }}
            tickLine={false}
            width={50}
          />
          <Tooltip
            contentStyle={{
              backgroundColor: "var(--surface-elevated)",
              border: "1px solid var(--border)",
              borderRadius: "8px",
              fontSize: "12px",
              color: "var(--text)",
            }}
            formatter={(value) => [`KES ${Number(value).toLocaleString()}`]}
          />
          <Legend
            wrapperStyle={{ fontSize: "11px", color: "var(--text-muted)" }}
          />
          <Line
            type="monotone"
            dataKey="revenue"
            stroke="#37b5ff"
            strokeWidth={2}
            dot={false}
            name="Revenue"
          />
          <Line
            type="monotone"
            dataKey="expenses"
            stroke="#ff6b7a"
            strokeWidth={2}
            dot={false}
            name="Expenses"
          />
          <Line
            type="monotone"
            dataKey="profit"
            stroke="#35d39d"
            strokeWidth={2}
            dot={false}
            name="Profit"
          />
        </LineChart>
      </ResponsiveContainer>
    </div>
  );
}
