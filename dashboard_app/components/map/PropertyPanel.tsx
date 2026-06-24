"use client";

import { X } from "lucide-react";
import type { PointFeature } from "@/lib/api/types";
import { Card } from "@/components/ui/card";
import { GradientText } from "@/components/ui/GradientText";
import { useLocale } from "@/lib/i18n/LocaleProvider";
import { formatCurrency, formatDate, formatNumber } from "@/lib/format";

interface PropertyPanelProps {
  point: PointFeature | null;
  onClose: () => void;
}

function Row({ label, value }: { label: string; value: React.ReactNode }) {
  return (
    <div className="flex items-center justify-between py-1 text-sm">
      <span className="text-[var(--fg-muted)]">{label}</span>
      <span className="tabular font-medium text-[var(--fg)]">{value}</span>
    </div>
  );
}

export function PropertyPanel({ point, onClose }: PropertyPanelProps) {
  const { t, locale } = useLocale();
  if (!point) return null;

  return (
    <Card className="absolute bottom-4 start-4 z-20 w-80 border-[var(--border-strong)] shadow-[0_20px_50px_-10px_rgba(0,0,0,0.7)] ring-1 ring-black/30">
      <div className="mb-2 flex items-start justify-between gap-2">
        <div className="min-w-0 flex-1">
          <div className="text-xs text-[var(--fg-dim)]">
            {[point.city, point.neighborhood].filter(Boolean).join(" · ") || "—"}
          </div>
          <div className="truncate text-sm font-semibold text-[var(--fg)]">
            {point.street || t("property.fallbackName")}
          </div>
        </div>
        <button
          onClick={onClose}
          className="rounded-md p-1 text-[var(--fg-muted)] hover:bg-[var(--bg-elev-2)] hover:text-[var(--fg)]"
          aria-label={t("common.close")}
        >
          <X className="h-4 w-4" />
        </button>
      </div>

      <div className="rounded-md border border-[var(--border)] bg-[var(--bg)] p-3">
        <div className="text-xs uppercase tracking-wide text-[var(--fg-dim)]">
          {t("property.listedPrice")}
        </div>
        <div className="tabular mt-1 text-2xl font-semibold">
          <GradientText>{formatCurrency(point.price)}</GradientText>
        </div>
      </div>

      <div className="mt-3 space-y-0.5 border-t border-[var(--border)] pt-2">
        <Row label={t("property.pricePerSqm")} value={formatCurrency(point.price_per_sqm)} />
        <Row label={t("property.rooms")} value={formatNumber(point.rooms)} />
        <Row
          label={t("property.area")}
          value={`${formatNumber(point.area_sqm)} ${t("unit.sqm")}`}
        />
        <Row label={t("property.date")} value={formatDate(point.transaction_date, `${locale}-IL`)} />
      </div>

      <a
        href={`/property/${encodeURIComponent(point.id)}`}
        className="mt-3 block w-full rounded-md bg-[var(--accent-1)] py-2 text-center text-sm font-semibold text-[var(--bg)] hover:opacity-90"
      >
        {t("property.openProperty")}
      </a>
    </Card>
  );
}
