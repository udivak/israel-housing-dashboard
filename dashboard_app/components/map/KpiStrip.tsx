"use client";

import { Building2, Coins, MapPin, TrendingUp } from "lucide-react";
import { useStatsSummary } from "@/hooks/useStatsSummary";
import { useFiltersStore } from "@/lib/store/filters";
import { KpiCard } from "@/components/ui/KpiCard";
import { useLocale } from "@/lib/i18n/LocaleProvider";
import { formatCurrency, formatNumber } from "@/lib/format";

export function KpiStrip() {
  const filters = useFiltersStore((s) => s.filters);
  const { data, isLoading } = useStatsSummary(filters);
  const { t } = useLocale();

  return (
    <div className="grid w-full grid-cols-2 gap-3 lg:grid-cols-4">
      <KpiCard
        label={t("kpi.transactions")}
        icon={Building2}
        value={isLoading ? "…" : formatNumber(data?.count)}
      />
      <KpiCard
        label={t("kpi.avgPrice")}
        icon={Coins}
        value={isLoading ? "…" : formatCurrency(data?.avg_price)}
      />
      <KpiCard
        label={t("kpi.avgPricePerSqm")}
        icon={TrendingUp}
        value={isLoading ? "…" : formatCurrency(data?.avg_price_per_sqm)}
      />
      <KpiCard
        label={t("kpi.citiesInData")}
        icon={MapPin}
        value={isLoading ? "…" : formatNumber(data?.distinct_cities_count)}
      />
    </div>
  );
}
