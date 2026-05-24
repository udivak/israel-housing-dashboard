"use client";

import dynamic from "next/dynamic";
import { FilterSidebar } from "./FilterSidebar";
import { KpiStrip } from "./KpiStrip";

const LiveMap = dynamic(() => import("./LiveMap").then((m) => m.LiveMap), {
  ssr: false,
  loading: () => (
    <div className="flex h-full w-full items-center justify-center rounded-xl border border-[--border] bg-[--bg-elev]">
      <div className="text-sm text-[--fg-muted]">Loading map…</div>
    </div>
  ),
});

export function MapPageClient() {
  return (
    <div className="flex h-[calc(100vh-7rem)] flex-col gap-4 px-6 py-6">
      <KpiStrip />
      <div className="flex min-h-0 flex-1 gap-4">
        <FilterSidebar />
        <div className="min-w-0 flex-1">
          <LiveMap />
        </div>
      </div>
    </div>
  );
}
