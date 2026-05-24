"use client";

import { X } from "lucide-react";
import type { PointFeature } from "@/lib/api/types";
import { Card } from "@/components/ui/card";
import { GradientText } from "@/components/ui/GradientText";
import { formatCurrency, formatDate, formatNumber } from "@/lib/format";

interface PropertyPanelProps {
  point: PointFeature | null;
  onClose: () => void;
}

function Row({ label, value }: { label: string; value: React.ReactNode }) {
  return (
    <div className="flex items-center justify-between py-1 text-sm">
      <span className="text-[--fg-muted]">{label}</span>
      <span className="tabular font-medium text-[--fg]">{value}</span>
    </div>
  );
}

export function PropertyPanel({ point, onClose }: PropertyPanelProps) {
  if (!point) return null;

  return (
    <Card className="absolute bottom-4 left-4 z-20 w-80 shadow-2xl">
      <div className="mb-2 flex items-start justify-between gap-2">
        <div className="min-w-0 flex-1">
          <div className="text-xs text-[--fg-dim]">
            {[point.city, point.neighborhood].filter(Boolean).join(" · ") || "—"}
          </div>
          <div className="truncate text-sm font-semibold text-[--fg]">
            {point.street || "Property"}
          </div>
        </div>
        <button
          onClick={onClose}
          className="rounded-md p-1 text-[--fg-muted] hover:bg-[--bg-elev-2] hover:text-[--fg]"
          aria-label="Close"
        >
          <X className="h-4 w-4" />
        </button>
      </div>

      <div className="rounded-md border border-[--border] bg-[--bg] p-3">
        <div className="text-xs uppercase tracking-wide text-[--fg-dim]">Listed price</div>
        <div className="tabular mt-1 text-2xl font-semibold">
          <GradientText>{formatCurrency(point.price)}</GradientText>
        </div>
      </div>

      <div className="mt-3 space-y-0.5 border-t border-[--border] pt-2">
        <Row label="₪/m²" value={formatCurrency(point.price_per_sqm)} />
        <Row label="Rooms" value={formatNumber(point.rooms)} />
        <Row label="Area" value={`${formatNumber(point.area_sqm)} m²`} />
        <Row label="Date" value={formatDate(point.transaction_date)} />
      </div>

      <a
        href={`/property/${encodeURIComponent(point.id)}`}
        className="mt-3 block w-full rounded-md bg-[--accent-1] py-2 text-center text-sm font-semibold text-[--bg] hover:opacity-90"
      >
        Open property
      </a>
    </Card>
  );
}
