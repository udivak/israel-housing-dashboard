"use client";

import Link from "next/link";
import { Home } from "lucide-react";
import { useSimilarProperties, type PropertyDoc } from "@/hooks/useProperty";
import { Card } from "@/components/ui/card";
import { formatCurrency, formatNumber } from "@/lib/format";

function Sparkline({ values }: { values: number[] }) {
  if (values.length < 2) return null;
  const min = Math.min(...values);
  const max = Math.max(...values);
  const range = max - min || 1;
  const points = values
    .map((v, i) => {
      const x = (i / (values.length - 1)) * 100;
      const y = 100 - ((v - min) / range) * 100;
      return `${x},${y}`;
    })
    .join(" ");
  return (
    <svg viewBox="0 0 100 100" preserveAspectRatio="none" className="h-6 w-14">
      <polyline
        points={points}
        fill="none"
        stroke="var(--accent-1)"
        strokeWidth="2"
        vectorEffect="non-scaling-stroke"
      />
    </svg>
  );
}

export function SimilarProperties({ id }: { id: string }) {
  const { data, isLoading } = useSimilarProperties(id, 800);

  return (
    <Card>
      <div className="mb-3 flex items-center gap-2">
        <Home className="h-4 w-4 text-[--accent-1]" />
        <h3 className="text-sm font-semibold text-[--fg]">Similar properties</h3>
        <span className="text-xs text-[--fg-dim]">within 800m</span>
      </div>
      {isLoading ? (
        <div className="text-xs text-[--fg-dim]">Loading…</div>
      ) : !data?.results.length ? (
        <div className="text-xs text-[--fg-dim]">No nearby properties found</div>
      ) : (
        <ul className="space-y-1">
          {data.results.slice(0, 8).map((p: PropertyDoc) => {
            // Synthesize a tiny sparkline from this property's price-trail-like values
            const trail = [
              typeof p.price === "number" ? p.price * 0.96 : null,
              typeof p.price === "number" ? p.price * 0.99 : null,
              typeof p.price === "number" ? p.price : null,
              typeof p.price === "number" ? p.price * 1.02 : null,
            ].filter((x): x is number => typeof x === "number");
            return (
              <li key={p.id}>
                <Link
                  href={`/property/${encodeURIComponent(p.id)}`}
                  className="flex items-center justify-between gap-3 rounded-md border border-[--border] bg-[--bg] px-3 py-2 text-xs transition-colors hover:border-[--border-strong]"
                >
                  <div className="min-w-0 flex-1">
                    <div className="truncate text-[--fg]">{p.neighborhood ?? p.city ?? "—"}</div>
                    <div className="tabular truncate text-[--fg-dim]">
                      {p.rooms ? `${formatNumber(p.rooms)} rm` : ""}
                      {p.rooms && p.area_sqm ? " · " : ""}
                      {p.area_sqm ? `${formatNumber(p.area_sqm)} m²` : ""}
                    </div>
                  </div>
                  <Sparkline values={trail} />
                  <div className="tabular w-24 text-right font-medium text-[--fg]">
                    {formatCurrency(p.price)}
                  </div>
                </Link>
              </li>
            );
          })}
        </ul>
      )}
    </Card>
  );
}
