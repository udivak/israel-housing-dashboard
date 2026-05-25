"use client";

import { Building2, Coins, MapPin, TrendingUp } from "lucide-react";
import { useStatsSummary } from "@/hooks/useStatsSummary";
import { useFiltersStore } from "@/lib/store/filters";
import { KpiCard } from "@/components/ui/KpiCard";
import { formatCurrency, formatNumber } from "@/lib/format";

export function KpiStrip() {
  const filters = useFiltersStore((s) => s.filters);
  const { data, isLoading } = useStatsSummary(filters);

  return (
    <div className="grid w-full grid-cols-2 gap-3 lg:grid-cols-4">
      <KpiCard
        label="Transactions"
        icon={Building2}
        value={isLoading ? "…" : formatNumber(data?.count)}
      />
      <KpiCard
        label="Avg price"
        icon={Coins}
        value={isLoading ? "…" : formatCurrency(data?.avg_price)}
      />
      <KpiCard
        label="Avg ₪/m²"
        icon={TrendingUp}
        value={isLoading ? "…" : formatCurrency(data?.avg_price_per_sqm)}
      />
      <KpiCard
        label="Cities in data"
        icon={MapPin}
        value={isLoading ? "…" : formatNumber(data?.distinct_cities_count)}
      />
    </div>
  );
}
