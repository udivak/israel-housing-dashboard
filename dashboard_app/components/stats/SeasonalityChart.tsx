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

const MONTHS = ["ינו", "פבר", "מרץ", "אפר", "מאי", "יוני", "יולי", "אוג", "ספט", "אוק", "נוב", "דצמ"];

export function SeasonalityChart({ city }: { city?: string }) {
  const { data = [], isLoading } = useSeasonality(city);

  const chart = data.map((r) => ({
    label: MONTHS[r.month - 1] ?? String(r.month),
    count: r.count,
    avg_price: r.avg_price,
  }));

  return (
    <ChartCard
      title="עונתיות"
      subtitle="עסקאות לפי חודש בשנה"
      className="h-72"
    >
      {isLoading ? (
        <div className="flex h-48 items-center justify-center text-xs text-zinc-500">טוען…</div>
      ) : (
        <ResponsiveContainer width="100%" height={210}>
          <BarChart data={chart} margin={{ top: 5, right: 10, left: 10, bottom: 5 }}>
            <CartesianGrid stroke="#3f3f46" strokeDasharray="3 3" />
            <XAxis dataKey="label" stroke="#71717a" fontSize={11} />
            <YAxis stroke="#71717a" fontSize={11} tickFormatter={(v) => fmtNum(v)} />
            <Tooltip
              contentStyle={{ backgroundColor: "#18181b", border: "1px solid #3f3f46", color: "#fff" }}
              formatter={(value: number) => [fmtNum(value), "עסקאות"]}
            />
            <Bar dataKey="count" fill="#22d3ee" radius={[4, 4, 0, 0]} />
          </BarChart>
        </ResponsiveContainer>
      )}
    </ChartCard>
  );
}
