"use client";

import dynamic from "next/dynamic";
import { FilterSidebar } from "./FilterSidebar";
import { KpiStrip } from "./KpiStrip";

const LiveMap = dynamic(() => import("./LiveMap").then((m) => m.LiveMap), {
  ssr: false,
  loading: () => (
    <div className="flex h-full w-full items-center justify-center rounded-xl border border-white/10 bg-zinc-900/40">
      <div className="text-sm text-zinc-400">טוען מפה…</div>
    </div>
  ),
});

export function MapPageClient() {
  return (
    <div className="flex h-[calc(100vh-9rem)] flex-col gap-3" dir="rtl">
      <KpiStrip />
      <div className="flex min-h-0 flex-1 gap-3">
        <FilterSidebar />
        <div className="min-w-0 flex-1">
          <LiveMap />
        </div>
      </div>
    </div>
  );
}
