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
import { useLocale } from "@/lib/i18n/LocaleProvider";
import type { Messages } from "@/lib/i18n/en";
import { CHART_COLORS, axisProps, gridProps, tooltipStyle } from "@/lib/chart-theme";

const grans: { value: "month" | "quarter" | "year"; key: keyof Messages }[] = [
  { value: "month", key: "chart.month" },
  { value: "quarter", key: "chart.quarter" },
  { value: "year", key: "chart.year" },
];

export function TimeseriesChart({ city }: { city?: string }) {
  const [granularity, setGranularity] = useState<"month" | "quarter" | "year">("year");
  const { data = [], isLoading } = useTimeseries(granularity, city);
  const { t } = useLocale();

  return (
    <ChartCard
      title={t("chart.timeseriesTitle")}
      subtitle={city ? city : t("chart.countryWide")}
      className="h-80"
    >
      <div className="mb-2 flex gap-1">
        {grans.map((g) => (
          <button
            key={g.value}
            onClick={() => setGranularity(g.value)}
            className={`rounded-md px-2 py-1 text-xs transition-colors ${
              granularity === g.value
                ? "bg-[var(--accent-1)]/15 text-[var(--accent-1)]"
                : "text-[var(--fg-muted)] hover:bg-[var(--bg-elev-2)]"
            }`}
          >
            {t(g.key)}
          </button>
        ))}
      </div>
      {isLoading ? (
        <div className="flex h-48 items-center justify-center text-xs text-[var(--fg-dim)]">{t("common.loading")}</div>
      ) : (
        <ResponsiveContainer width="100%" height={220}>
          <LineChart data={data} margin={{ top: 5, right: 10, left: 10, bottom: 5 }}>
            <CartesianGrid {...gridProps} />
            <XAxis dataKey="bucket" {...axisProps} />
            <YAxis {...axisProps} tickFormatter={(v) => fmtNum(v / 1000) + "K"} />
            <Tooltip
              contentStyle={tooltipStyle}
              formatter={(value: number, name) => [fmtNum(value), name]}
            />
            <Line
              type="monotone"
              dataKey="avg_price"
              stroke={CHART_COLORS.accent1}
              strokeWidth={2}
              dot={false}
              name={t("kpi.avgPrice")}
            />
            <Line
              type="monotone"
              dataKey="avg_price_per_sqm"
              stroke={CHART_COLORS.accent2}
              strokeWidth={2}
              dot={false}
              name={t("property.pricePerSqm")}
            />
          </LineChart>
        </ResponsiveContainer>
      )}
    </ChartCard>
  );
}
