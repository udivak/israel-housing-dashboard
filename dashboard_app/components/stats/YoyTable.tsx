"use client";

import { TrendingDown, TrendingUp } from "lucide-react";
import { useYoyByCity } from "@/hooks/useStats";
import { ChartCard, fmtNum } from "./ChartCard";

export function YoyTable() {
  const { data = [], isLoading } = useYoyByCity(20);

  return (
    <ChartCard
      title="Heating Cities"
      subtitle="YoY ₪/m² change · top 20"
      className="h-96"
    >
      {isLoading ? (
        <div className="flex h-64 items-center justify-center text-xs text-zinc-500">Loading…</div>
      ) : (
        <div className="overflow-y-auto" style={{ maxHeight: 320 }}>
          <table className="w-full text-xs">
            <thead className="sticky top-0 bg-zinc-900/95 backdrop-blur">
              <tr className="border-b border-white/10 text-zinc-400">
                <th className="py-2 text-right font-normal">City</th>
                <th className="py-2 text-right font-normal">YoY</th>
                <th className="py-2 text-right font-normal">Current ₪/m²</th>
                <th className="py-2 text-right font-normal">Deals</th>
              </tr>
            </thead>
            <tbody>
              {data.map((r) => (
                <tr key={r.city} className="border-b border-white/5 hover:bg-white/5">
                  <td className="py-1.5 text-white">{r.city}</td>
                  <td className={`py-1.5 ${r.yoy_pct >= 0 ? "text-emerald-400" : "text-rose-400"}`}>
                    <span className="inline-flex items-center gap-1">
                      {r.yoy_pct >= 0 ? <TrendingUp className="h-3 w-3" /> : <TrendingDown className="h-3 w-3" />}
                      {r.yoy_pct.toFixed(1)}%
                    </span>
                  </td>
                  <td className="py-1.5 text-zinc-300">{fmtNum(r.current_avg)}</td>
                  <td className="py-1.5 text-zinc-500">{fmtNum(r.current_count)}</td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      )}
    </ChartCard>
  );
}
