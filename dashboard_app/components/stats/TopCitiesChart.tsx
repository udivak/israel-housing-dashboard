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
import { useLocale } from "@/lib/i18n/LocaleProvider";
import { CHART_COLORS, axisProps, gridProps, tooltipStyle } from "@/lib/chart-theme";

export function TopCitiesChart() {
  const [level, setLevel] = useState<"city" | "neighborhood">("city");
  const { data = [], isLoading } = useByRegion(level, "avg_price_per_sqm", 15);
  const { t } = useLocale();

  return (
    <ChartCard
      title={t("chart.topCitiesTitle")}
      subtitle={t("chart.topCitiesSubtitle", {
        level: level === "city" ? t("chart.citiesWord") : t("chart.neighborhoodsWord"),
      })}
      className="h-96"
    >
      <div className="mb-2 flex gap-1">
        <button
          onClick={() => setLevel("city")}
          className={`rounded-md px-2 py-1 text-xs transition-colors ${
            level === "city"
              ? "bg-[var(--accent-1)]/15 text-[var(--accent-1)]"
              : "text-[var(--fg-muted)] hover:bg-[var(--bg-elev-2)]"
          }`}
        >
          {t("chart.cities")}
        </button>
        <button
          onClick={() => setLevel("neighborhood")}
          className={`rounded-md px-2 py-1 text-xs transition-colors ${
            level === "neighborhood"
              ? "bg-[var(--accent-1)]/15 text-[var(--accent-1)]"
              : "text-[var(--fg-muted)] hover:bg-[var(--bg-elev-2)]"
          }`}
        >
          {t("chart.neighborhoods")}
        </button>
      </div>
      {isLoading ? (
        <div className="flex h-64 items-center justify-center text-xs text-[var(--fg-dim)]">{t("common.loading")}</div>
      ) : (
        <ResponsiveContainer width="100%" height={300}>
          <BarChart data={data} layout="vertical" margin={{ top: 5, right: 10, left: 80, bottom: 5 }}>
            <CartesianGrid {...gridProps} />
            <XAxis type="number" {...axisProps} tickFormatter={(v) => fmtNum(v)} />
            <YAxis dataKey="region" type="category" {...axisProps} width={75} />
            <Tooltip
              contentStyle={tooltipStyle}
              formatter={(value: number) => [fmtNum(value) + " " + t("property.pricePerSqm"), t("chart.avg")]}
            />
            <Bar dataKey="avg_price_per_sqm" fill={CHART_COLORS.accent1} radius={[0, 4, 4, 0]} />
          </BarChart>
        </ResponsiveContainer>
      )}
    </ChartCard>
  );
}
