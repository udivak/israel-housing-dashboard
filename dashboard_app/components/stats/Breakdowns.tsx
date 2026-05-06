"use client";

import { Cell, Pie, PieChart, ResponsiveContainer, Tooltip } from "recharts";
import { usePropertyTypeBreakdown, useSourceBreakdown } from "@/hooks/useStats";
import { ChartCard, fmtNum } from "./ChartCard";

const COLORS = ["#06b6d4", "#a78bfa", "#f97316", "#22c55e", "#eab308", "#ef4444", "#ec4899", "#14b8a6"];

export function SourceBreakdown() {
  const { data = [], isLoading } = useSourceBreakdown();
  const total = data.reduce((s, r) => s + r.count, 0);

  return (
    <ChartCard title="Breakdown by Source" subtitle={`${fmtNum(total)} records`} className="h-72">
      {isLoading ? (
        <div className="flex h-48 items-center justify-center text-xs text-zinc-500">Loading…</div>
      ) : (
        <div className="grid grid-cols-2 gap-3">
          <ResponsiveContainer width="100%" height={200}>
            <PieChart>
              <Pie
                data={data}
                dataKey="count"
                nameKey="source"
                innerRadius={45}
                outerRadius={75}
                paddingAngle={2}
              >
                {data.map((_, i) => (
                  <Cell key={i} fill={COLORS[i % COLORS.length]} />
                ))}
              </Pie>
              <Tooltip
                contentStyle={{ backgroundColor: "#18181b", border: "1px solid #3f3f46", color: "#fff" }}
                formatter={(v: number, n) => [fmtNum(v), n]}
              />
            </PieChart>
          </ResponsiveContainer>
          <ul className="flex flex-col justify-center gap-1.5 text-xs">
            {data.map((r, i) => (
              <li key={r.source} className="flex items-center gap-2">
                <span
                  className="h-2.5 w-2.5 rounded-sm"
                  style={{ backgroundColor: COLORS[i % COLORS.length] }}
                />
                <span className="flex-1 truncate text-zinc-300">{r.source}</span>
                <span className="text-zinc-500">{fmtNum(r.count)}</span>
              </li>
            ))}
          </ul>
        </div>
      )}
    </ChartCard>
  );
}

export function PropertyTypeBreakdown({ city }: { city?: string }) {
  const { data = [], isLoading } = usePropertyTypeBreakdown(city);
  const top = data.slice(0, 8);

  return (
    <ChartCard title="Breakdown by Property Type" subtitle={city ?? "Country"} className="h-72">
      {isLoading ? (
        <div className="flex h-48 items-center justify-center text-xs text-zinc-500">Loading…</div>
      ) : (
        <div className="grid grid-cols-2 gap-3">
          <ResponsiveContainer width="100%" height={200}>
            <PieChart>
              <Pie
                data={top}
                dataKey="count"
                nameKey="type"
                innerRadius={45}
                outerRadius={75}
                paddingAngle={2}
              >
                {top.map((_, i) => (
                  <Cell key={i} fill={COLORS[i % COLORS.length]} />
                ))}
              </Pie>
              <Tooltip
                contentStyle={{ backgroundColor: "#18181b", border: "1px solid #3f3f46", color: "#fff" }}
                formatter={(v: number, n) => [fmtNum(v), n]}
              />
            </PieChart>
          </ResponsiveContainer>
          <ul className="flex flex-col justify-center gap-1.5 text-xs">
            {top.map((r, i) => (
              <li key={r.type} className="flex items-center gap-2">
                <span
                  className="h-2.5 w-2.5 rounded-sm"
                  style={{ backgroundColor: COLORS[i % COLORS.length] }}
                />
                <span className="flex-1 truncate text-zinc-300">{r.type}</span>
                <span className="text-zinc-500">{fmtNum(r.count)}</span>
              </li>
            ))}
          </ul>
        </div>
      )}
    </ChartCard>
  );
}
