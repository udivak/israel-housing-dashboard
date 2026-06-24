"use client";

import { TrendingDown, TrendingUp } from "lucide-react";
import { useYoyByCity } from "@/hooks/useStats";
import { ChartCard, fmtNum } from "./ChartCard";
import { useLocale } from "@/lib/i18n/LocaleProvider";

export function YoyTable() {
  const { data = [], isLoading } = useYoyByCity(20);
  const { t } = useLocale();

  return (
    <ChartCard title={t("chart.yoyTitle")} subtitle={t("chart.yoySubtitle")} className="h-96">
      {isLoading ? (
        <div className="flex h-64 items-center justify-center text-xs text-[var(--fg-dim)]">{t("common.loading")}</div>
      ) : (
        <div className="overflow-y-auto" style={{ maxHeight: 320 }}>
          <table className="w-full text-xs">
            <thead className="sticky top-0 bg-[var(--bg-elev)]/95 backdrop-blur">
              <tr className="border-b border-[var(--border)] text-[var(--fg-dim)]">
                <th className="py-2 text-start font-normal">{t("chart.colCity")}</th>
                <th className="py-2 text-end font-normal">{t("chart.colYoy")}</th>
                <th className="py-2 text-end font-normal">{t("chart.colCurrent")}</th>
                <th className="py-2 text-end font-normal">{t("chart.colDeals")}</th>
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
                    className={`tabular py-1.5 text-end ${
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
                  <td className="tabular py-1.5 text-end text-[var(--fg-muted)]">{fmtNum(r.current_avg)}</td>
                  <td className="tabular py-1.5 text-end text-[var(--fg-dim)]">{fmtNum(r.current_count)}</td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      )}
    </ChartCard>
  );
}
