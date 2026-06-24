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
import { useDistribution } from "@/hooks/useStats";
import { ChartCard, fmtNum } from "./ChartCard";
import { useLocale } from "@/lib/i18n/LocaleProvider";
import type { Messages } from "@/lib/i18n/en";
import { CHART_COLORS, axisProps, gridProps, tooltipStyle } from "@/lib/chart-theme";

const FIELDS: {
  value: "price" | "price_per_sqm" | "rooms" | "area_sqm" | "year_built";
  key: keyof Messages;
}[] = [
  { value: "price", key: "chart.distPrice" },
  { value: "price_per_sqm", key: "property.pricePerSqm" },
  { value: "rooms", key: "property.rooms" },
  { value: "area_sqm", key: "property.area" },
  { value: "year_built", key: "pg.field.yearBuilt" },
];

type Field = (typeof FIELDS)[number]["value"];

export function DistributionChart({ city }: { city?: string }) {
  const [field, setField] = useState<Field>("price");
  const { data = [], isLoading } = useDistribution(field, 30, city);
  const { t } = useLocale();

  const chartData = data.map((b) => ({
    label: `${fmtNum(b.min)}–${fmtNum(b.max)}`,
    count: b.count,
  }));

  return (
    <ChartCard title={t("chart.distributionTitle")} subtitle={city ?? t("chart.countryWide")} className="h-80">
      <div className="mb-2 flex flex-wrap gap-1">
        {FIELDS.map((f) => (
          <button
            key={f.value}
            onClick={() => setField(f.value)}
            className={`rounded-md px-2 py-1 text-xs transition-colors ${
              field === f.value
                ? "bg-[var(--accent-1)]/15 text-[var(--accent-1)]"
                : "text-[var(--fg-muted)] hover:bg-[var(--bg-elev-2)]"
            }`}
          >
            {t(f.key)}
          </button>
        ))}
      </div>
      {isLoading ? (
        <div className="flex h-48 items-center justify-center text-xs text-[var(--fg-dim)]">{t("common.loading")}</div>
      ) : (
        <ResponsiveContainer width="100%" height={220}>
          <BarChart data={chartData} margin={{ top: 5, right: 10, left: 10, bottom: 5 }}>
            <CartesianGrid {...gridProps} />
            <XAxis dataKey="label" {...axisProps} interval="preserveStartEnd" />
            <YAxis {...axisProps} />
            <Tooltip
              contentStyle={tooltipStyle}
              formatter={(value: number) => [fmtNum(value), t("kpi.transactions")]}
            />
            <Bar dataKey="count" fill={CHART_COLORS.accent2} radius={[2, 2, 0, 0]} />
          </BarChart>
        </ResponsiveContainer>
      )}
    </ChartCard>
  );
}
