"use client";

import { TrendingDown, TrendingUp } from "lucide-react";
import { useYoyByCity } from "@/hooks/useStats";
import { ChartCard, fmtNum } from "./ChartCard";

export function YoyTable() {
  const { data = [], isLoading } = useYoyByCity(20);

  return (
    <ChartCard title="Heating cities" subtitle="YoY ₪/m² change · top 20" className="h-96">
      {isLoading ? (
        <div className="flex h-64 items-center justify-center text-xs text-[var(--fg-dim)]">Loading…</div>
      ) : (
        <div className="overflow-y-auto" style={{ maxHeight: 320 }}>
          <table className="w-full text-xs">
            <thead className="sticky top-0 bg-[var(--bg-elev)]/95 backdrop-blur">
              <tr className="border-b border-[var(--border)] text-[var(--fg-dim)]">
                <th className="py-2 text-left font-normal">City</th>
                <th className="py-2 text-right font-normal">YoY</th>
                <th className="py-2 text-right font-normal">Current ₪/m²</th>
                <th className="py-2 text-right font-normal">Deals</th>
              </tr>
            </thead>
            <tbody>
              {data.map((r, i) => (
                <tr
                  key={r.city}
                  className={`border-b border-[var(--border)]/60 transition-colors hover:bg-[var(--bg-elev-2)] ${
                    i % 2 === 1 ? "bg-[var(--bg-elev-2)]/40" : ""
                  }`}
                >
                  <td className="py-1.5 text-[var(--fg)]">{r.city}</td>
                  <td
                    className={`tabular py-1.5 text-right ${
                      r.yoy_pct >= 0 ? "text-[var(--up)]" : "text-[var(--down)]"
                    }`}
                  >
                    <span className="inline-flex items-center gap-1">
                      {r.yoy_pct >= 0 ? (
                        <TrendingUp className="h-3 w-3" />
                      ) : (
                        <TrendingDown className="h-3 w-3" />
                      )}
                      {r.yoy_pct >= 0 ? "+" : ""}
                      {r.yoy_pct.toFixed(1)}%
                    </span>
                  </td>
                  <td className="tabular py-1.5 text-right text-[var(--fg-muted)]">{fmtNum(r.current_avg)}</td>
                  <td className="tabular py-1.5 text-right text-[var(--fg-dim)]">{fmtNum(r.current_count)}</td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      )}
    </ChartCard>
  );
}
