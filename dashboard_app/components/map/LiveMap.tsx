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
    if (!containerRef.current) return;
    const m = new maplibregl.Map({
      container: containerRef.current,
      style: OSM_STYLE as unknown as maplibregl.StyleSpecification,
      center: [DEFAULT_VIEWPORT.longitude, DEFAULT_VIEWPORT.latitude],
      zoom: DEFAULT_VIEWPORT.zoom,
    });
    m.addControl(new maplibregl.NavigationControl(), "top-right");
    mapRef.current = m;

    const update = () => {
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
      update();
      setMap(m);
    });
    m.on("moveend", update);
    m.on("zoomend", update);

    return () => {
      mapRef.current = null;
      setMap(null);
      m.remove();
    };
  }, [setViewport]);

  const handleSearchSelect = useCallback((lon: number, lat: number, z = 14) => {
    mapRef.current?.flyTo({ center: [lon, lat], zoom: z, duration: 1200 });
  }, []);

  return (
    <div className="relative h-full w-full overflow-hidden rounded-xl border border-white/10">
      <div ref={containerRef} className="absolute inset-0" />
      <div className="absolute right-3 top-3 z-10">
        <SearchBar onSelect={handleSearchSelect} />
      </div>
      <DeckOverlay map={map} data={data} onPointClick={setSelected} />
      <PropertyPanel point={selected} onClose={() => setSelected(null)} />
      {data?.type === "points" && data.truncated && (
        <div className="absolute bottom-3 right-3 z-10 rounded-md bg-amber-500/90 px-2 py-1 text-xs text-zinc-900">
          מוצגות עד 2,000 תוצאות — הגדל זום או הוסף סינון
        </div>
      )}
    </div>
  );
}
