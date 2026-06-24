"use client";

import { Building2, Coins, TrendingUp, Brain } from "lucide-react";
import { useStatsSummary } from "@/hooks/useStatsSummary";
import { useModels } from "@/hooks/useProperty";
import { KpiCard } from "@/components/ui/KpiCard";
import { useFiltersStore } from "@/lib/store/filters";
import { useLocale } from "@/lib/i18n/LocaleProvider";
import { formatCurrency, formatNumber } from "@/lib/format";
import { modelDisplayName } from "@/lib/model-utils";

function pickBestModel(models: Array<{ id: string; metrics?: Record<string, unknown> | null }>) {
  let best: { id: string; r2: number } | null = null;
  for (const m of models) {
    const r2 = typeof m.metrics?.r2 === "number" ? (m.metrics.r2 as number) : null;
    if (r2 == null) continue;
    if (!best || r2 > best.r2) best = { id: m.id, r2 };
  }
  return best;
}

export function HomeKpiStrip() {
  const filters = useFiltersStore((s) => s.filters);
  const { data: stats, isLoading } = useStatsSummary(filters);
  const { data: models = [] } = useModels();
  const { t } = useLocale();
  const best = pickBestModel(models);

  return (
    <section className="border-b border-[var(--border)] bg-[var(--bg)]">
      <div className="grid grid-cols-2 gap-3 px-6 py-12 sm:gap-4 lg:grid-cols-4">
        <KpiCard
          label={t("home.kpi.listings")}
          icon={Building2}
          value={isLoading ? "…" : formatNumber(stats?.count)}
          hint={t("home.kpi.listingsHint")}
        />
        <KpiCard
          label={t("kpi.avgPrice")}
          icon={Coins}
          value={isLoading ? "…" : formatCurrency(stats?.avg_price)}
          hint={t("home.kpi.avgPriceHint")}
        />
        <KpiCard
          label={t("kpi.avgPricePerSqm")}
          icon={TrendingUp}
          value={isLoading ? "…" : formatCurrency(stats?.avg_price_per_sqm)}
          hint={
            stats?.distinct_cities_count
              ? t("home.kpi.citiesHint", { count: formatNumber(stats.distinct_cities_count) })
              : undefined
          }
        />
        <KpiCard
          label={t("home.kpi.bestModel")}
          icon={Brain}
          value={best ? best.r2.toFixed(3) : "—"}
          hint={best ? modelDisplayName(best.id) : t("home.kpi.noModel")}
        />
      </div>
    </section>
  );
}
