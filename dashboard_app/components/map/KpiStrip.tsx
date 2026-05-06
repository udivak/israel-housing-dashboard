"use client";

import { useStatsSummary } from "@/hooks/useStatsSummary";
import { useFiltersStore } from "@/lib/store/filters";
import { Building2, MapPin, TrendingUp, Coins } from "lucide-react";

function fmt(n: number | null | undefined, opts?: Intl.NumberFormatOptions): string {
  if (n == null || !Number.isFinite(n)) return "—";
  return n.toLocaleString("he-IL", { maximumFractionDigits: 0, ...opts });
}

function Card({
  icon: Icon,
  label,
  value,
  sub,
}: {
  icon: React.ComponentType<{ className?: string }>;
  label: string;
  value: string;
  sub?: string;
}) {
  return (
    <div className="flex flex-1 items-center gap-3 rounded-xl border border-white/10 bg-zinc-900/70 px-4 py-3 backdrop-blur">
      <div className="flex h-9 w-9 items-center justify-center rounded-lg bg-gradient-to-br from-cyan-500/20 to-violet-600/20">
        <Icon className="h-4 w-4 text-cyan-300" />
      </div>
      <div className="min-w-0">
        <div className="text-xs text-zinc-400">{label}</div>
        <div className="truncate text-base font-semibold text-white">{value}</div>
        {sub && <div className="text-[11px] text-zinc-500">{sub}</div>}
      </div>
    </div>
  );
}

export function KpiStrip() {
  const filters = useFiltersStore((s) => s.filters);
  const { data, isLoading } = useStatsSummary(filters);

  const total = isLoading ? "..." : fmt(data?.count ?? 0);
  const avgPrice = isLoading ? "..." : `₪${fmt(data?.avg_price)}`;
  const avgPpsm = isLoading ? "..." : `₪${fmt(data?.avg_price_per_sqm)}/m²`;
  const cities = isLoading ? "..." : fmt(data?.distinct_cities_count);

  return (
    <div className="flex w-full gap-3">
      <Card icon={Building2} label="עסקאות" value={total} />
      <Card icon={Coins} label="מחיר ממוצע" value={avgPrice} />
      <Card icon={TrendingUp} label="מחיר ממוצע למ״ר" value={avgPpsm} />
      <Card icon={MapPin} label="ערים בנתונים" value={cities} />
    </div>
  );
}
