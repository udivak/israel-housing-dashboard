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
      title="Average Price Over Time"
      subtitle={city ? `${city}` : "Country"}
      className="h-80"
    >
      <div className="mb-2 flex gap-1">
        {grans.map((g) => (
          <button
            key={g.value}
            onClick={() => setGranularity(g.value)}
            className={`rounded-md px-2 py-1 text-xs ${
              granularity === g.value
                ? "bg-cyan-500/20 text-cyan-300"
                : "text-zinc-400 hover:bg-white/5"
            }`}
          >
            {g.label}
          </button>
        ))}
      </div>
      {isLoading ? (
        <div className="flex h-48 items-center justify-center text-xs text-zinc-500">Loading…</div>
      ) : (
        <ResponsiveContainer width="100%" height={220}>
          <LineChart data={data} margin={{ top: 5, right: 10, left: 10, bottom: 5 }}>
            <CartesianGrid stroke="#3f3f46" strokeDasharray="3 3" />
            <XAxis dataKey="bucket" stroke="#71717a" fontSize={11} />
            <YAxis
              stroke="#71717a"
              fontSize={11}
              tickFormatter={(v) => fmtNum(v / 1000) + "K"}
            />
            <Tooltip
              contentStyle={{ backgroundColor: "#18181b", border: "1px solid #3f3f46", color: "#fff" }}
              formatter={(value: number, name) => [fmtNum(value), name]}
            />
            <Line type="monotone" dataKey="avg_price" stroke="#06b6d4" strokeWidth={2} dot={false} name="Avg Price" />
            <Line type="monotone" dataKey="avg_price_per_sqm" stroke="#a78bfa" strokeWidth={2} dot={false} name="₪/m²" />
          </LineChart>
        </ResponsiveContainer>
      )}
    </ChartCard>
  );
}
