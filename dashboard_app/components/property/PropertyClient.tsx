"use client";

import dynamic from "next/dynamic";
import { ArrowRight, MapPin, Calendar, Home, Building, Ruler } from "lucide-react";
import Link from "next/link";
import { useProperty } from "@/hooks/useProperty";
import { PredictionPanel } from "./PredictionPanel";
import { SimilarProperties } from "./SimilarProperties";
import { Card } from "@/components/ui/card";
import { GradientText } from "@/components/ui/GradientText";
import { Pill } from "@/components/ui/Pill";
import { useLocale } from "@/lib/i18n/LocaleProvider";
import { formatCurrency, formatDate, formatNumber } from "@/lib/format";

const MiniMap = dynamic(() => import("./MiniMap").then((m) => m.MiniMap), { ssr: false });

function Stat({
  icon: Icon,
  label,
  value,
}: {
  icon: React.ComponentType<{ className?: string }>;
  label: string;
  value: string;
}) {
  return (
    <div className="flex items-center gap-2 rounded-md border border-[var(--border)] bg-[var(--bg)] px-3 py-2">
      <Icon className="h-4 w-4 text-[var(--accent-1)]" />
      <div className="min-w-0">
        <div className="text-[11px] uppercase tracking-wide text-[var(--fg-dim)]">{label}</div>
        <div className="tabular truncate text-sm font-medium text-[var(--fg)]">{value}</div>
      </div>
    </div>
  );
}

export function PropertyClient({ id }: { id: string }) {
  const { data: property, isLoading, isError } = useProperty(id);
  const { t, locale } = useLocale();

  if (isLoading) {
    return <div className="px-6 py-10 text-sm text-[var(--fg-muted)]">{t("common.loading")}</div>;
  }
  if (isError || !property) {
    return (
      <div className="px-6 py-10">
        <Card className="border-[var(--down)]/30 bg-[var(--down)]/10 text-sm text-[var(--down)]">
          {t("property.notFound", { id })}
        </Card>
      </div>
    );
  }

  const lng = property.geometry?.coordinates?.[0];
  const lat = property.geometry?.coordinates?.[1];

  return (
    <div className="space-y-5 px-6 py-8">
      <Link
        href="/map"
        className="inline-flex items-center gap-1 text-xs text-[var(--fg-muted)] hover:text-[var(--fg)]"
      >
        <ArrowRight className="h-3 w-3 rotate-180 rtl-flip" />
        {t("property.backToMap")}
      </Link>

      <Card className="p-6">
        <div className="flex flex-col gap-4 sm:flex-row sm:items-start sm:justify-between">
          <div className="min-w-0">
            <div className="flex items-center gap-2 text-sm text-[var(--fg-muted)]">
              <MapPin className="h-3.5 w-3.5" />
              {[property.city, property.neighborhood, property.street].filter(Boolean).join(" · ") || "—"}
            </div>
            <h1 className="mt-2 text-3xl font-semibold tracking-tight text-[var(--fg)]">
              {property.deal_nature ?? t("property.fallbackName")}
            </h1>
            {property.source_name && (
              <div className="mt-2">
                <Pill tone="muted">{String(property.source_name)}</Pill>
              </div>
            )}
          </div>
          <div className="rounded-lg border border-[var(--accent-1)]/30 bg-[var(--bg)] p-4 text-end">
            <div className="text-xs uppercase tracking-wide text-[var(--fg-dim)]">{t("property.listedPrice")}</div>
            <div className="tabular mt-1 text-3xl font-semibold">
              <GradientText>{formatCurrency(property.price)}</GradientText>
            </div>
            <div className="tabular mt-1 text-xs text-[var(--fg-muted)]">
              {t("home.map.perSqm", { value: formatCurrency(property.price_per_sqm) })}
            </div>
          </div>
        </div>

        <div className="mt-5 grid grid-cols-2 gap-2 md:grid-cols-4">
          <Stat icon={Ruler} label={t("property.area")} value={`${formatNumber(property.area_sqm)} ${t("unit.sqm")}`} />
          <Stat icon={Home} label={t("property.rooms")} value={formatNumber(property.rooms)} />
          <Stat
            icon={Building}
            label={t("pg.field.floor")}
            value={`${formatNumber(property.floor)} / ${formatNumber(property.building_floors)}`}
          />
          <Stat icon={Calendar} label={t("property.date")} value={formatDate(property.transaction_date, `${locale}-IL`)} />
        </div>
      </Card>

      <div className="grid gap-4 lg:grid-cols-3">
        <div className="space-y-4 lg:col-span-2">
          {lng != null && lat != null && (
            <MiniMap
              lng={lng}
              lat={lat}
              className="h-64 w-full overflow-hidden rounded-xl border border-[var(--border)]"
            />
          )}
          <SimilarProperties id={id} />
        </div>
        <div>
          <PredictionPanel property={property} />
        </div>
      </div>
    </div>
  );
}
