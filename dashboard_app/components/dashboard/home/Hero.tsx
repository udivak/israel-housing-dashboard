"use client";

import Link from "next/link";
import { useStatsSummary } from "@/hooks/useStatsSummary";
import { GradientText } from "@/components/ui/GradientText";
import { Pill } from "@/components/ui/Pill";
import { useFiltersStore } from "@/lib/store/filters";
import { formatNumber, humanizeAgo } from "@/lib/format";

export function Hero() {
  const filters = useFiltersStore((s) => s.filters);
  const { data } = useStatsSummary(filters);
  const cities = data?.distinct_cities_count;
  const updated = data?.max_date ? humanizeAgo(data.max_date) : "live";

  return (
    <section className="relative overflow-hidden border-b border-[--border]">
      <div className="pointer-events-none absolute inset-0">
        <div className="absolute -left-32 top-0 h-96 w-96 rounded-full bg-[--accent-1]/10 blur-3xl" />
        <div className="absolute -right-32 top-40 h-96 w-96 rounded-full bg-[--accent-2]/10 blur-3xl" />
      </div>
      <div className="relative px-6 py-16 sm:py-24">
        <Pill tone="live">Live · updated {updated}</Pill>
        <h1 className="mt-6 max-w-4xl text-4xl font-semibold tracking-tight text-[--fg] sm:text-5xl md:text-6xl">
          Israel’s housing market,
          <br />
          <GradientText>
            across {formatNumber(cities) === "—" ? "248" : formatNumber(cities)} cities — modeled, mapped, priced.
          </GradientText>
        </h1>
        <p className="mt-6 max-w-2xl text-base text-[--fg-muted] sm:text-lg">
          Listings collected nightly, enriched with OSM context, indexed by H3 cells, and priced
          by seven ML models — served live through a FastAPI stack.
        </p>
        <div className="mt-8 flex flex-wrap items-center gap-3">
          <Link
            href="/map"
            className="rounded-md bg-[--accent-1] px-5 py-2.5 text-sm font-semibold text-[--bg] transition-opacity hover:opacity-90"
          >
            Open the map →
          </Link>
          <a
            href="#predict"
            className="rounded-md border border-[--border] bg-[--bg-elev] px-5 py-2.5 text-sm font-medium text-[--fg] transition-colors hover:border-[--border-strong]"
          >
            Try a prediction
          </a>
        </div>
      </div>
    </section>
  );
}
