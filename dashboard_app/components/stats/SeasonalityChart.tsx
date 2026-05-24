"use client";

import {
  Bar,
  BarChart,
  CartesianGrid,
  ResponsiveContainer,
  Tooltip,
  XAxis,
  YAxis,
} from "recharts";
import { useSeasonality } from "@/hooks/useStats";
import { ChartCard, fmtNum } from "./ChartCard";
import { CHART_COLORS, axisProps, gridProps, tooltipStyle } from "@/lib/chart-theme";

const MONTHS = ["Jan", "Feb", "Mar", "Apr", "May", "Jun", "Jul", "Aug", "Sep", "Oct", "Nov", "Dec"];

export function SeasonalityChart({ city }: { city?: string }) {
  const { data = [], isLoading } = useSeasonality(city);

  const chart = data.map((r) => ({
    label: MONTHS[r.month - 1] ?? String(r.month),
    count: r.count,
    avg_price: r.avg_price,
  }));

  return (
    <ChartCard title="Seasonality" subtitle="Transactions by month" className="h-72">
      {isLoading ? (
        <div className="flex h-48 items-center justify-center text-xs text-[--fg-dim]">Loading…</div>
      ) : (
        <ResponsiveContainer width="100%" height={210}>
          <BarChart data={chart} margin={{ top: 5, right: 10, left: 10, bottom: 5 }}>
            <CartesianGrid {...gridProps} />
            <XAxis dataKey="label" {...axisProps} />
            <YAxis {...axisProps} tickFormatter={(v) => fmtNum(v)} />
            <Tooltip
              contentStyle={tooltipStyle}
              formatter={(value: number) => [fmtNum(value), "Transactions"]}
            />
            <Bar dataKey="count" fill={CHART_COLORS.up} radius={[4, 4, 0, 0]} />
          </BarChart>
        </ResponsiveContainer>
      )}
    </ChartCard>
  );
}
