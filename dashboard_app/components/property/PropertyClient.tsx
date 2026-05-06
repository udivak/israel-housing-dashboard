"use client";

import dynamic from "next/dynamic";
import { ArrowRight, MapPin, Calendar, Home, Building, Ruler } from "lucide-react";
import Link from "next/link";
import { useProperty } from "@/hooks/useProperty";
import { PredictionPanel } from "./PredictionPanel";
import { SimilarProperties } from "./SimilarProperties";

const MiniMap = dynamic(() => import("./MiniMap").then((m) => m.MiniMap), { ssr: false });

function fmt(n: number | null | undefined): string {
  if (n == null || !Number.isFinite(n)) return "—";
  return n.toLocaleString("en-US", { maximumFractionDigits: 0 });
}

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
    <div className="flex items-center gap-2 rounded-md border border-white/10 bg-zinc-950/40 px-3 py-2">
      <Icon className="h-4 w-4 text-cyan-400" />
      <div className="min-w-0">
        <div className="text-[11px] text-zinc-400">{label}</div>
        <div className="truncate text-sm font-medium text-white">{value}</div>
      </div>
    </div>
  );
}

export function PropertyClient({ id }: { id: string }) {
  const { data: property, isLoading, isError } = useProperty(id);

  if (isLoading) {
    return <div className="text-sm text-zinc-400">Loading…</div>;
  }
  if (isError || !property) {
    return (
      <div className="rounded-xl border border-rose-500/30 bg-rose-500/10 p-4 text-sm text-rose-300">
        Property not found: {id}
      </div>
    );
  }

  const lng = property.geometry?.coordinates?.[0];
  const lat = property.geometry?.coordinates?.[1];
  const date = property.transaction_date
    ? new Date(property.transaction_date).toLocaleDateString("en-US")
    : "—";

  return (
    <div  className="flex flex-col gap-4">
      <Link
        href="/map"
        className="inline-flex items-center gap-1 text-xs text-zinc-400 hover:text-white"
      >
        <ArrowRight className="h-3 w-3 rotate-180" />
        Back to map
      </Link>

      <div className="rounded-xl border border-white/10 bg-zinc-900/60 p-5 backdrop-blur">
        <div className="mb-2 flex items-start justify-between">
          <div>
            <div className="flex items-center gap-2 text-sm text-zinc-400">
              <MapPin className="h-3.5 w-3.5" />
              {[property.city, property.neighborhood, property.street].filter(Boolean).join(" · ") || "—"}
            </div>
            <h1 className="mt-1 text-2xl font-semibold text-white">{property.deal_nature ?? "Property"}</h1>
          </div>
          <div className="text-left">
            <div className="text-3xl font-bold text-white">₪{fmt(property.price)}</div>
            <div className="text-sm text-zinc-400">₪{fmt(property.price_per_sqm)}/m²</div>
          </div>
        </div>

        <div className="mt-4 grid grid-cols-2 gap-2 md:grid-cols-4">
          <Stat icon={Ruler} label="Area" value={`${fmt(property.area_sqm)} m²`} />
          <Stat icon={Home} label="Rooms" value={fmt(property.rooms)} />
          <Stat icon={Building} label="Floor" value={`${fmt(property.floor)}/${fmt(property.building_floors)}`} />
          <Stat icon={Calendar} label="Date" value={date} />
        </div>

        <div className="mt-2 grid grid-cols-2 gap-2 md:grid-cols-3">
          <Stat icon={Calendar} label="Year Built" value={fmt(property.year_built)} />
          {property.source_name && (
            <Stat icon={Home} label="Source" value={String(property.source_name)} />
          )}
        </div>
      </div>

      <div className="grid gap-4 lg:grid-cols-3">
        <div className="lg:col-span-2 space-y-4">
          {lng != null && lat != null && <MiniMap lng={lng} lat={lat} />}
          <SimilarProperties id={id} />
        </div>
        <div>
          <PredictionPanel property={property} />
        </div>
      </div>
    </div>
  );
}
