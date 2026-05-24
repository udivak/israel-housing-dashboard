"use client";

import { useState } from "react";
import {
  Bar,
  BarChart,
  CartesianGrid,
  ResponsiveContainer,
  Tooltip,
  XAxis,
  YAxis,
} from "recharts";
import { useByRegion } from "@/hooks/useStats";
import { ChartCard, fmtNum } from "./ChartCard";
import { CHART_COLORS, axisProps, gridProps, tooltipStyle } from "@/lib/chart-theme";

export function TopCitiesChart() {
  const [level, setLevel] = useState<"city" | "neighborhood">("city");
  const { data = [], isLoading } = useByRegion(level, "avg_price_per_sqm", 15);

  return (
    <ChartCard
      title="Most expensive cities & neighborhoods"
      subtitle={`By avg ₪/m² · top 15 ${level === "city" ? "cities" : "neighborhoods"}`}
      className="h-96"
    >
      <div className="mb-2 flex gap-1">
        <button
          onClick={() => setLevel("city")}
          className={`rounded-md px-2 py-1 text-xs transition-colors ${
            level === "city"
              ? "bg-[--accent-1]/15 text-[--accent-1]"
              : "text-[--fg-muted] hover:bg-[--bg-elev-2]"
          }`}
        >
          Cities
        </button>
        <button
          onClick={() => setLevel("neighborhood")}
          className={`rounded-md px-2 py-1 text-xs transition-colors ${
            level === "neighborhood"
              ? "bg-[--accent-1]/15 text-[--accent-1]"
              : "text-[--fg-muted] hover:bg-[--bg-elev-2]"
          }`}
        >
          Neighborhoods
        </button>
      </div>
      {isLoading ? (
        <div className="flex h-64 items-center justify-center text-xs text-[--fg-dim]">Loading…</div>
      ) : (
        <ResponsiveContainer width="100%" height={300}>
          <BarChart data={data} layout="vertical" margin={{ top: 5, right: 10, left: 80, bottom: 5 }}>
            <CartesianGrid {...gridProps} />
            <XAxis type="number" {...axisProps} tickFormatter={(v) => fmtNum(v)} />
            <YAxis dataKey="region" type="category" {...axisProps} width={75} />
            <Tooltip
              contentStyle={tooltipStyle}
              formatter={(value: number) => [fmtNum(value) + " ₪/m²", "avg"]}
            />
            <Bar dataKey="avg_price_per_sqm" fill={CHART_COLORS.accent1} radius={[0, 4, 4, 0]} />
          </BarChart>
        </ResponsiveContainer>
      )}
    </ChartCard>
  );
}
