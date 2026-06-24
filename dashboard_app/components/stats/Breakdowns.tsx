"use client";

import { Cell, Pie, PieChart, ResponsiveContainer, Tooltip } from "recharts";
import { usePropertyTypeBreakdown, useSourceBreakdown } from "@/hooks/useStats";
import { ChartCard, fmtNum } from "./ChartCard";
import { useLocale } from "@/lib/i18n/LocaleProvider";
import { CHART_SERIES, tooltipStyle, tooltipItemStyle } from "@/lib/chart-theme";

const pct = (v: number, total: number) => (total ? `${((v / total) * 100).toFixed(1)}%` : "0%");

export function SourceBreakdown() {
  const { data = [], isLoading } = useSourceBreakdown();
  const { t } = useLocale();
  const total = data.reduce((s, r) => s + r.count, 0);

  return (
    <ChartCard title={t("chart.bySource")} subtitle={t("chart.records", { count: fmtNum(total) })} className="h-72">
      {isLoading ? (
        <div className="flex h-48 items-center justify-center text-xs text-[var(--fg-dim)]">{t("common.loading")}</div>
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
                  <Cell key={i} fill={CHART_SERIES[i % CHART_SERIES.length]} />
                ))}
              </Pie>
              <Tooltip
                contentStyle={tooltipStyle}
                itemStyle={tooltipItemStyle}
                formatter={(v: number, n) => [`${fmtNum(v)} (${pct(v, total)})`, n]}
              />
            </PieChart>
          </ResponsiveContainer>
          <ul className="flex flex-col justify-center gap-1.5 text-xs">
            {data.map((r, i) => (
              <li key={r.source} className="flex items-center gap-2">
                <span
                  className="h-2.5 w-2.5 rounded-sm"
                  style={{ backgroundColor: CHART_SERIES[i % CHART_SERIES.length] }}
                />
                <span className="flex-1 truncate text-[var(--fg-muted)]">{r.source}</span>
                <span className="tabular text-[var(--fg-dim)]">{fmtNum(r.count)}</span>
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
  const { t } = useLocale();
  const top = data.slice(0, 8);
  const total = top.reduce((s, r) => s + r.count, 0);

  return (
    <ChartCard title={t("chart.byPropertyType")} subtitle={city ?? t("chart.countryWide")} className="h-72">
      {isLoading ? (
        <div className="flex h-48 items-center justify-center text-xs text-[var(--fg-dim)]">{t("common.loading")}</div>
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
                  <Cell key={i} fill={CHART_SERIES[i % CHART_SERIES.length]} />
                ))}
              </Pie>
              <Tooltip
                contentStyle={tooltipStyle}
                itemStyle={tooltipItemStyle}
                formatter={(v: number, n) => [`${fmtNum(v)} (${pct(v, total)})`, n]}
              />
            </PieChart>
          </ResponsiveContainer>
          <ul className="flex flex-col justify-center gap-1.5 text-xs">
            {top.map((r, i) => (
              <li key={r.type} className="flex items-center gap-2">
                <span
                  className="h-2.5 w-2.5 rounded-sm"
                  style={{ backgroundColor: CHART_SERIES[i % CHART_SERIES.length] }}
                />
                <span className="flex-1 truncate text-[var(--fg-muted)]">{r.type}</span>
                <span className="tabular text-[var(--fg-dim)]">{fmtNum(r.count)}</span>
              </li>
            ))}
          </ul>
        </div>
      )}
    </ChartCard>
  );
}
