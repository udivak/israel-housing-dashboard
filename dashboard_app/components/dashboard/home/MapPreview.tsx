"use client";

import dynamic from "next/dynamic";
import Link from "next/link";
import { Flame, Sparkles, Target } from "lucide-react";
import { Section } from "@/components/ui/Section";
import { KpiCard } from "@/components/ui/KpiCard";
import { useByRegion, useYoyByCity } from "@/hooks/useStats";
import { formatCurrency } from "@/lib/format";

const MiniMap = dynamic(
  () => import("@/components/property/MiniMap").then((m) => m.MiniMap),
  {
    ssr: false,
    loading: () => (
      <div className="flex h-full w-full items-center justify-center text-xs text-[--fg-dim]">
        Loading preview…
      </div>
    ),
  },
);

export function MapPreview() {
  const { data: topCities = [] } = useByRegion("city", "avg_price_per_sqm", 25);
  const { data: yoy = [] } = useYoyByCity(40);

  const hottest = topCities[0];

  // best value: lowest ₪/m² among cities with enough volume
  const bestValue = [...topCities]
    .filter((r) => r.count >= 50)
    .sort((a, b) => a.avg_price_per_sqm - b.avg_price_per_sqm)[0];

  const trending = [...yoy]
    .filter((r) => Number.isFinite(r.yoy_pct))
    .sort((a, b) => b.yoy_pct - a.yoy_pct)[0];

  // Tel Aviv center as the preview anchor.
  return (
    <Section
      title="Live map preview"
      subtitle="Cyan-to-violet heat across H3 cells. Click to dive in."
      rightLink={{ href: "/map", label: "Open the map" }}
      className="border-b border-[--border] px-6 py-12"
    >
      <div className="grid gap-4 lg:grid-cols-[1.5fr_1fr]">
        <Link
          href="/map"
          className="group relative h-[280px] overflow-hidden rounded-xl border border-[--border] bg-[--bg-elev]"
        >
          <MiniMap
            lng={34.7818}
            lat={32.0853}
            zoom={11}
            showMarker={false}
            className="h-full w-full"
          />
          <div className="pointer-events-none absolute inset-0 bg-gradient-to-tr from-[--bg]/40 via-transparent to-[--accent-2]/15" />
          <div className="absolute bottom-3 left-3 right-3 flex items-center justify-between rounded-md border border-[--border] bg-[--bg]/70 px-3 py-2 text-xs text-[--fg-muted] backdrop-blur">
            <span>Tel Aviv–Yafo</span>
            <span className="font-medium text-[--accent-1] transition-transform group-hover:translate-x-1 rtl-flip">
              Explore →
            </span>
          </div>
        </Link>

        <div className="grid gap-3">
          <KpiCard
            label="Hottest market"
            icon={Flame}
            value={hottest?.region ?? "—"}
            hint={hottest ? `${formatCurrency(hottest.avg_price_per_sqm)} /m²` : undefined}
          />
          <KpiCard
            label="Best value"
            icon={Target}
            value={bestValue?.region ?? "—"}
            hint={bestValue ? `${formatCurrency(bestValue.avg_price_per_sqm)} /m²` : undefined}
          />
          <KpiCard
            label="Trending up"
            icon={Sparkles}
            value={trending?.city ?? "—"}
            delta={trending ? `${trending.yoy_pct >= 0 ? "+" : ""}${trending.yoy_pct.toFixed(1)}%` : undefined}
            deltaTone={trending && trending.yoy_pct >= 0 ? "up" : "down"}
            hint="YoY"
          />
        </div>
      </div>
    </Section>
  );
}
