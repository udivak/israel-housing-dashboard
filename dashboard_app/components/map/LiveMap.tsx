"use client";

import { useCallback, useEffect, useRef, useState } from "react";
import maplibregl from "maplibre-gl";
import "maplibre-gl/dist/maplibre-gl.css";
import { DeckOverlay } from "./DeckOverlay";
import { PropertyPanel } from "./PropertyPanel";
import { SearchBar } from "./SearchBar";
import { useDebounce } from "@/hooks/useDebounce";
import { useMapData } from "@/hooks/useMapData";
import { useFiltersStore, DEFAULT_VIEWPORT } from "@/lib/store/filters";
import { OSM_STYLE } from "@/lib/map-style";
import type { BBoxParams, PointFeature } from "@/lib/api/types";

export function LiveMap() {
  const containerRef = useRef<HTMLDivElement>(null);
  const mapRef = useRef<maplibregl.Map | null>(null);
  const [map, setMap] = useState<maplibregl.Map | null>(null);
  const [bbox, setBBox] = useState<BBoxParams | null>(null);
  const [zoom, setZoom] = useState<number>(DEFAULT_VIEWPORT.zoom);
  const [selected, setSelected] = useState<PointFeature | null>(null);
  const [error, setError] = useState<string | null>(null);

  const setViewport = useFiltersStore((s) => s.setViewport);
  const filters = useFiltersStore((s) => s.filters);

  const debouncedBBox = useDebounce(bbox, 300);
  const debouncedZoom = useDebounce(zoom, 300);

  const { data } = useMapData({
    bbox: debouncedBBox,
    zoom: Math.round(debouncedZoom),
    filters,
  });

  useEffect(() => {
    const container = containerRef.current;
    if (!container) return;

    let m: maplibregl.Map | null = null;
    try {
      m = new maplibregl.Map({
        container,
        style: OSM_STYLE as unknown as maplibregl.StyleSpecification,
        center: [DEFAULT_VIEWPORT.longitude, DEFAULT_VIEWPORT.latitude],
        zoom: DEFAULT_VIEWPORT.zoom,
        attributionControl: false,
      });
    } catch (e) {
      setError(`MapLibre failed to init: ${(e as Error).message}`);
      return;
    }

    m.addControl(new maplibregl.NavigationControl(), "top-right");
    m.addControl(new maplibregl.AttributionControl({ compact: true }), "bottom-left");
    mapRef.current = m;

    const update = () => {
      if (!m) return;
      const b = m.getBounds();
      setBBox({
        min_lat: b.getSouth(),
        max_lat: b.getNorth(),
        min_lng: b.getWest(),
        max_lng: b.getEast(),
      });
      setZoom(m.getZoom());
      setViewport({
        longitude: m.getCenter().lng,
        latitude: m.getCenter().lat,
        zoom: m.getZoom(),
      });
    };

    m.on("load", () => {
      m?.resize();
      update();
      setMap(m);
      // Debug: expose map instance for browser console inspection
      if (typeof window !== "undefined") {
        (window as unknown as { __map: maplibregl.Map | null }).__map = m;
      }
    });
    m.on("moveend", update);
    m.on("zoomend", update);
    m.on("error", (e) => {
      console.error("[MapLibre]", e);
    });

    // Force resize after a tick, in case the container was 0-sized at init.
    const t1 = window.setTimeout(() => m?.resize(), 100);
    const t2 = window.setTimeout(() => m?.resize(), 600);

    // Track container size changes (window resize, sidebar toggles, etc.).
    const ro = new ResizeObserver(() => m?.resize());
    ro.observe(container);

    return () => {
      window.clearTimeout(t1);
      window.clearTimeout(t2);
      ro.disconnect();
      mapRef.current = null;
      setMap(null);
      m?.remove();
    };
  }, [setViewport]);

  const handleSearchSelect = useCallback((lon: number, lat: number, z = 14) => {
    mapRef.current?.flyTo({ center: [lon, lat], zoom: z, duration: 1200 });
  }, []);

  return (
    <div className="relative h-full min-h-[500px] w-full overflow-hidden rounded-xl border border-white/10">
      <div ref={containerRef} className="h-full w-full" style={{ background: "#1a1a1a" }} />
      <div className="absolute right-3 top-3 z-10">
        <SearchBar onSelect={handleSearchSelect} />
      </div>
      <DeckOverlay map={map} data={data} onPointClick={setSelected} />
      <PropertyPanel point={selected} onClose={() => setSelected(null)} />
      {error && (
        <div className="absolute inset-x-3 top-3 z-20 rounded-md border border-rose-500/40 bg-rose-500/10 p-3 text-xs text-rose-200">
          Map error: {error}
        </div>
      )}
      {data?.type === "points" && data.truncated && (
        <div className="absolute bottom-3 right-3 z-10 rounded-md bg-amber-500/90 px-2 py-1 text-xs text-zinc-900">
          Showing up to 2,000 results — zoom in or add filters
        </div>
      )}
    </div>
  );
}
