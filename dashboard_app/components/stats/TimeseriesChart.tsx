"use client";

import { useState } from "react";
import {
  CartesianGrid,
  Line,
  LineChart,
  ResponsiveContainer,
  Tooltip,
  XAxis,
  YAxis,
} from "recharts";
import { useTimeseries } from "@/hooks/useStats";
import { ChartCard, fmtNum } from "./ChartCard";
import { CHART_COLORS, axisProps, gridProps, tooltipStyle } from "@/lib/chart-theme";

const grans = [
  { value: "month" as const, label: "Month" },
  { value: "quarter" as const, label: "Quarter" },
  { value: "year" as const, label: "Year" },
];

export function TimeseriesChart({ city }: { city?: string }) {
  const [granularity, setGranularity] = useState<"month" | "quarter" | "year">("year");
  const { data = [], isLoading } = useTimeseries(granularity, city);

  return (
    <ChartCard
      title="Average price over time"
      subtitle={city ? city : "Country-wide"}
      className="h-80"
    >
      <div className="mb-2 flex gap-1">
        {grans.map((g) => (
          <button
            key={g.value}
            onClick={() => setGranularity(g.value)}
            className={`rounded-md px-2 py-1 text-xs transition-colors ${
              granularity === g.value
                ? "bg-[var(--accent-1)]/15 text-[var(--accent-1)]"
                : "text-[var(--fg-muted)] hover:bg-[var(--bg-elev-2)]"
            }`}
          >
            {g.label}
          </button>
        ))}
      </div>
      {isLoading ? (
        <div className="flex h-48 items-center justify-center text-xs text-[var(--fg-dim)]">Loading…</div>
      ) : (
        <ResponsiveContainer width="100%" height={220}>
          <LineChart data={data} margin={{ top: 5, right: 10, left: 10, bottom: 5 }}>
            <CartesianGrid {...gridProps} />
            <XAxis dataKey="bucket" {...axisProps} />
            <YAxis {...axisProps} tickFormatter={(v) => fmtNum(v / 1000) + "K"} />
            <Tooltip
              contentStyle={tooltipStyle}
              formatter={(value: number, name) => [fmtNum(value), name]}
            />
            <Line
              type="monotone"
              dataKey="avg_price"
              stroke={CHART_COLORS.accent1}
              strokeWidth={2}
              dot={false}
              name="Avg price"
            />
            <Line
              type="monotone"
              dataKey="avg_price_per_sqm"
              stroke={CHART_COLORS.accent2}
              strokeWidth={2}
              dot={false}
              name="₪/m²"
            />
          </LineChart>
        </ResponsiveContainer>
      )}
    </ChartCard>
  );
}
