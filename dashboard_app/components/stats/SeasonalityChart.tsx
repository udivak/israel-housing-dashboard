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
import { useLocale } from "@/lib/i18n/LocaleProvider";
import type { Messages } from "@/lib/i18n/en";
import { CHART_COLORS, axisProps, gridProps, tooltipStyle } from "@/lib/chart-theme";

const MONTH_KEYS: (keyof Messages)[] = [
  "chart.mon1", "chart.mon2", "chart.mon3", "chart.mon4", "chart.mon5", "chart.mon6",
  "chart.mon7", "chart.mon8", "chart.mon9", "chart.mon10", "chart.mon11", "chart.mon12",
];

export function SeasonalityChart({ city }: { city?: string }) {
  const { data = [], isLoading } = useSeasonality(city);
  const { t } = useLocale();

  const chart = data.map((r) => ({
    label: MONTH_KEYS[r.month - 1] ? t(MONTH_KEYS[r.month - 1]) : String(r.month),
    count: r.count,
    avg_price: r.avg_price,
  }));

  return (
    <ChartCard title={t("chart.seasonalityTitle")} subtitle={t("chart.seasonalitySubtitle")} className="h-72">
      {isLoading ? (
        <div className="flex h-48 items-center justify-center text-xs text-[var(--fg-dim)]">{t("common.loading")}</div>
      ) : (
        <ResponsiveContainer width="100%" height={210}>
          <BarChart data={chart} margin={{ top: 5, right: 10, left: 10, bottom: 5 }}>
            <CartesianGrid {...gridProps} />
            <XAxis dataKey="label" {...axisProps} />
            <YAxis {...axisProps} tickFormatter={(v) => fmtNum(v)} />
            <Tooltip
              contentStyle={tooltipStyle}
              formatter={(value: number) => [fmtNum(value), t("kpi.transactions")]}
            />
            <Bar dataKey="count" fill={CHART_COLORS.up} radius={[4, 4, 0, 0]} />
          </BarChart>
        </ResponsiveContainer>
      )}
    </ChartCard>
  );
}
