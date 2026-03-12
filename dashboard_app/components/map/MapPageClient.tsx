"use client";

import dynamic from "next/dynamic";

const MapWithSearch = dynamic(
  () => import("./MapWithSearch").then((m) => m.MapWithSearch),
  { ssr: false }
);

export function MapPageClient() {
  return (
    <div className="space-y-4">
      <div>
        <h1 className="text-2xl font-semibold text-white">Map</h1>
        <p className="text-sm text-zinc-400">
          Search for streets, cities, and addresses. Powered by OpenStreetMap.
        </p>
      </div>
      <MapWithSearch />
    </div>
  );
}
