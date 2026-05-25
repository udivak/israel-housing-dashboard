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
import { formatCurrency, formatNumber } from "@/lib/format";

export function StatsClient() {
  const [city, setCity] = useState<string>("");
  const { data: summary, isLoading } = useStatsSummary(city ? { city } : {});

  return (
    <div className="px-6 py-10 space-y-10">
      <Section
        title="Stats overview"
        subtitle={
          city
            ? `Filtered to ${city}. Clear the field to see the country-wide view.`
            : "Country-wide rollups. Filter by city to focus."
        }
        eyebrow="Statistics"
      >
        <div className="mb-6 flex flex-wrap items-center gap-3">
          <input
            value={city}
            onChange={(e) => setCity(e.target.value)}
            placeholder="Filter by city…"
            className="w-64 rounded-md border border-[var(--border)] bg-[var(--bg-elev)] px-3 py-1.5 text-sm text-[var(--fg)] placeholder:text-[var(--fg-dim)] focus:border-[var(--accent-1)]/50 focus:outline-none"
          />
        </div>
        <div className="grid grid-cols-2 gap-3 sm:gap-4 lg:grid-cols-4">
          <KpiCard
            label="Transactions"
            icon={Building2}
            value={isLoading ? "…" : formatNumber(summary?.count)}
            hint={city || "all cities"}
          />
          <KpiCard
            label="Avg price"
            icon={Coins}
            value={isLoading ? "…" : formatCurrency(summary?.avg_price)}
          />
          <KpiCard
            label="Avg ₪/m²"
            icon={TrendingUp}
            value={isLoading ? "…" : formatCurrency(summary?.avg_price_per_sqm)}
          />
          <KpiCard
            label="Cities in scope"
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
