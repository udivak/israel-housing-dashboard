"use client";

import { useState } from "react";
import { Building2, Coins, MapPin, TrendingUp } from "lucide-react";
import { TimeseriesChart } from "./TimeseriesChart";
import { TopCitiesChart } from "./TopCitiesChart";
import { DistributionChart } from "./DistributionChart";
import { YoyTable } from "./YoyTable";
import { SeasonalityChart } from "./SeasonalityChart";
import { SourceBreakdown, PropertyTypeBreakdown } from "./Breakdowns";
import { KpiCard } from "@/components/ui/KpiCard";
import { Section } from "@/components/ui/Section";
import { useStatsSummary } from "@/hooks/useStatsSummary";
import { useLocale } from "@/lib/i18n/LocaleProvider";
import { formatCurrency, formatNumber } from "@/lib/format";

export function StatsClient() {
  const [city, setCity] = useState<string>("");
  const { data: summary, isLoading } = useStatsSummary(city ? { city } : {});
  const { t } = useLocale();

  return (
    <div className="px-6 py-10 space-y-10">
      <Section
        title={t("stats.title")}
        subtitle={city ? t("stats.filtered", { city }) : t("stats.defaultSubtitle")}
        eyebrow={t("stats.eyebrow")}
      >
        <div className="mb-6 flex flex-wrap items-center gap-3">
          <input
            value={city}
            onChange={(e) => setCity(e.target.value)}
            placeholder={t("stats.filterPlaceholder")}
            className="w-64 rounded-md border border-[var(--border)] bg-[var(--bg-elev)] px-3 py-1.5 text-sm text-[var(--fg)] placeholder:text-[var(--fg-dim)] focus:border-[var(--accent-1)]/50 focus:outline-none"
          />
        </div>
        <div className="grid grid-cols-2 gap-3 sm:gap-4 lg:grid-cols-4">
          <KpiCard
            label={t("kpi.transactions")}
            icon={Building2}
            value={isLoading ? "…" : formatNumber(summary?.count)}
            hint={city || t("stats.allCities")}
          />
          <KpiCard
            label={t("kpi.avgPrice")}
            icon={Coins}
            value={isLoading ? "…" : formatCurrency(summary?.avg_price)}
          />
          <KpiCard
            label={t("kpi.avgPricePerSqm")}
            icon={TrendingUp}
            value={isLoading ? "…" : formatCurrency(summary?.avg_price_per_sqm)}
          />
          <KpiCard
            label={t("stats.citiesInScope")}
            icon={MapPin}
            value={isLoading ? "…" : formatNumber(summary?.distinct_cities_count)}
          />
        </div>
      </Section>

      <div className="grid gap-4 lg:grid-cols-2">
        <TimeseriesChart city={city || undefined} />
        <DistributionChart city={city || undefined} />
        <TopCitiesChart />
        <YoyTable />
        <SeasonalityChart city={city || undefined} />
        <PropertyTypeBreakdown city={city || undefined} />
        <SourceBreakdown />
      </div>
    </div>
  );
}
