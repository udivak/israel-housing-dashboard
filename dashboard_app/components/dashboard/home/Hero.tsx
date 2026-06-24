"use client";

import Link from "next/link";
import { useStatsSummary } from "@/hooks/useStatsSummary";
import { GradientText } from "@/components/ui/GradientText";
import { Pill } from "@/components/ui/Pill";
import { useFiltersStore } from "@/lib/store/filters";
import { useLocale } from "@/lib/i18n/LocaleProvider";
import { formatNumber } from "@/lib/format";

export function Hero() {
  const filters = useFiltersStore((s) => s.filters);
  const { data } = useStatsSummary(filters);
  const { t } = useLocale();
  const cities = data?.distinct_cities_count;
  const cityCount = formatNumber(cities) === "—" ? "248" : formatNumber(cities);

  return (
    <section className="relative overflow-hidden border-b border-[var(--border)]">
      <div className="pointer-events-none absolute inset-0">
        <div className="absolute -start-32 top-0 h-96 w-96 rounded-full bg-[var(--accent-1)]/10 blur-3xl" />
        <div className="absolute -end-32 top-40 h-96 w-96 rounded-full bg-[var(--accent-2)]/10 blur-3xl" />
      </div>
      <div className="relative px-6 py-16 sm:py-24">
        <Pill tone="live">{t("hero.live")}</Pill>
        <h1 className="mt-6 max-w-4xl text-4xl font-semibold tracking-tight text-[var(--fg)] sm:text-5xl md:text-6xl">
          {t("hero.titleLead")}
          <br />
          <GradientText>{t("hero.titleGradient", { count: cityCount })}</GradientText>
        </h1>
        <p className="mt-6 max-w-2xl text-base text-[var(--fg-muted)] sm:text-lg">
          {t("hero.subtitle")}
        </p>
        <div className="mt-8 flex flex-wrap items-center gap-3">
          <Link
            href="/map"
            className="rounded-md bg-[var(--accent-1)] px-5 py-2.5 text-sm font-semibold text-[var(--bg)] transition-opacity hover:opacity-90"
          >
            {t("hero.openMap")}
          </Link>
          <a
            href="#predict"
            className="rounded-md border border-[var(--border)] bg-[var(--bg-elev)] px-5 py-2.5 text-sm font-medium text-[var(--fg)] transition-colors hover:border-[var(--border-strong)]"
          >
            {t("hero.tryPrediction")}
          </a>
        </div>
      </div>
    </section>
  );
}
