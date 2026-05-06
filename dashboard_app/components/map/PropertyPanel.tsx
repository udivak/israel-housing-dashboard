"use client";

import { X } from "lucide-react";
import type { PointFeature } from "@/lib/api/types";

interface PropertyPanelProps {
  point: PointFeature | null;
  onClose: () => void;
}

function fmt(n: number | null | undefined): string {
  if (n == null || !Number.isFinite(n)) return "—";
  return n.toLocaleString("en-US", { maximumFractionDigits: 0 });
}

function Row({ label, value }: { label: string; value: string }) {
  return (
    <div className="flex items-center justify-between py-1 text-sm">
      <span className="text-zinc-400">{label}</span>
      <span className="font-medium text-white">{value}</span>
    </div>
  );
}

export function PropertyPanel({ point, onClose }: PropertyPanelProps) {
  if (!point) return null;
  const date = point.transaction_date
    ? new Date(point.transaction_date).toLocaleDateString("en-GB")
    : "—";

  return (
    <div className="absolute left-4 bottom-4 z-20 w-80 rounded-xl border border-white/10 bg-zinc-900/95 p-4 shadow-2xl backdrop-blur">
      <div className="mb-2 flex items-start justify-between">
        <div className="min-w-0 flex-1">
          <div className="text-xs text-zinc-500">
            {[point.city, point.neighborhood].filter(Boolean).join(" · ") || "—"}
          </div>
          <div className="truncate font-semibold text-white">
            {point.street || "Property"}
          </div>
        </div>
        <button onClick={onClose} className="rounded-md p-1 text-zinc-400 hover:bg-white/5">
          <X className="h-4 w-4" />
        </button>
      </div>
      <div className="space-y-0.5 border-t border-white/10 pt-2">
        <Row label="Price" value={`₪${fmt(point.price)}`} />
        <Row label="₪/m²" value={`₪${fmt(point.price_per_sqm)}`} />
        <Row label="Rooms" value={fmt(point.rooms)} />
        <Row label="Area" value={`${fmt(point.area_sqm)} m²`} />
        <Row label="Date" value={date} />
      </div>
      <a
        href={`/property/${encodeURIComponent(point.id)}`}
        className="mt-3 block w-full rounded-lg bg-gradient-to-r from-cyan-500 to-violet-600 py-2 text-center text-sm font-medium text-white hover:opacity-90"
      >
        Open Property
      </a>
    </div>
  );
}
