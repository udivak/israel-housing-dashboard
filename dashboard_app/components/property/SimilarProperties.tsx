"use client";

import Link from "next/link";
import { Home } from "lucide-react";
import { useSimilarProperties, type PropertyDoc } from "@/hooks/useProperty";

function fmtPrice(n: number | null | undefined): string {
  if (n == null) return "—";
  return `₪${n.toLocaleString("en-US", { maximumFractionDigits: 0 })}`;
}

export function SimilarProperties({ id }: { id: string }) {
  const { data, isLoading } = useSimilarProperties(id, 800);

  return (
    <div  className="rounded-xl border border-white/10 bg-zinc-900/60 p-4 backdrop-blur">
      <div className="mb-3 flex items-center gap-2">
        <Home className="h-4 w-4 text-cyan-400" />
        <h3 className="text-sm font-semibold text-white">Similar Properties</h3>
        <span className="text-xs text-zinc-500">within 800m</span>
      </div>
      {isLoading ? (
        <div className="text-xs text-zinc-500">Loading…</div>
      ) : !data?.results.length ? (
        <div className="text-xs text-zinc-500">No nearby properties found</div>
      ) : (
        <ul className="space-y-1">
          {data.results.slice(0, 8).map((p: PropertyDoc) => (
            <li key={p.id}>
              <Link
                href={`/property/${encodeURIComponent(p.id)}`}
                className="flex items-center justify-between rounded-md border border-white/10 bg-zinc-950/40 px-3 py-2 text-xs hover:bg-white/5"
              >
                <div className="min-w-0">
                  <div className="truncate text-white">{p.neighborhood ?? p.city ?? "—"}</div>
                  <div className="truncate text-zinc-500">
                    {p.rooms ? `${p.rooms} rm` : ""} · {p.area_sqm ? `${p.area_sqm} m²` : ""}
                  </div>
                </div>
                <div className="font-medium text-white">{fmtPrice(p.price)}</div>
              </Link>
            </li>
          ))}
        </ul>
      )}
    </div>
  );
}
