"use client";

import { useRef, useCallback } from "react";
import { MapView } from "./MapView";
import { SearchBar } from "./SearchBar";
import maplibregl from "maplibre-gl";

export function MapWithSearch() {
  const mapRef = useRef<maplibregl.Map | null>(null);

  const handleMapReady = useCallback((map: maplibregl.Map) => {
    mapRef.current = map;
  }, []);

  const handleSearchSelect = useCallback((lon: number, lat: number, zoom = 15) => {
    mapRef.current?.flyTo({ center: [lon, lat], zoom, duration: 1500 });
  }, []);

  return (
    <div className="relative h-[calc(100vh-8rem)] w-full">
      <div className="absolute left-4 top-4 z-10">
        <SearchBar onSelect={handleSearchSelect} />
      </div>
      <MapView onMapReady={handleMapReady} className="h-full w-full" />
    </div>
  );
}
