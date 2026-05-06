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

export function TopCitiesChart() {
  const [level, setLevel] = useState<"city" | "neighborhood">("city");
  const { data = [], isLoading } = useByRegion(level, "avg_price_per_sqm", 15);

  return (
    <ChartCard
      title="הערים/שכונות היקרות ביותר"
      subtitle={`לפי ₪/m² ממוצע · top 15 ${level === "city" ? "ערים" : "שכונות"}`}
      className="h-96"
    >
      <div className="mb-2 flex gap-1">
        <button
          onClick={() => setLevel("city")}
          className={`rounded-md px-2 py-1 text-xs ${
            level === "city" ? "bg-cyan-500/20 text-cyan-300" : "text-zinc-400 hover:bg-white/5"
          }`}
        >
          ערים
        </button>
        <button
          onClick={() => setLevel("neighborhood")}
          className={`rounded-md px-2 py-1 text-xs ${
            level === "neighborhood" ? "bg-cyan-500/20 text-cyan-300" : "text-zinc-400 hover:bg-white/5"
          }`}
        >
          שכונות
        </button>
      </div>
      {isLoading ? (
        <div className="flex h-64 items-center justify-center text-xs text-zinc-500">טוען…</div>
      ) : (
        <ResponsiveContainer width="100%" height={300}>
          <BarChart data={data} layout="vertical" margin={{ top: 5, right: 10, left: 80, bottom: 5 }}>
            <CartesianGrid stroke="#3f3f46" strokeDasharray="3 3" />
            <XAxis type="number" stroke="#71717a" fontSize={11} tickFormatter={(v) => fmtNum(v)} />
            <YAxis dataKey="region" type="category" stroke="#71717a" fontSize={11} width={75} />
            <Tooltip
              contentStyle={{ backgroundColor: "#18181b", border: "1px solid #3f3f46", color: "#fff" }}
              formatter={(value: number) => [fmtNum(value) + " ₪/m²", "ממוצע"]}
            />
            <Bar dataKey="avg_price_per_sqm" fill="#06b6d4" radius={[0, 4, 4, 0]} />
          </BarChart>
        </ResponsiveContainer>
      )}
    </ChartCard>
  );
}
