"use client";

import { useEffect, useRef } from "react";
import maplibregl from "maplibre-gl";
import "maplibre-gl/dist/maplibre-gl.css";
import { OSM_STYLE } from "@/lib/map-style";

interface MiniMapProps {
  lng: number;
  lat: number;
  zoom?: number;
  className?: string;
  showMarker?: boolean;
}

export function MiniMap({
  lng,
  lat,
  zoom = 15,
  className = "h-48 w-full overflow-hidden rounded-xl border border-[var(--border)]",
  showMarker = true,
}: MiniMapProps) {
  const ref = useRef<HTMLDivElement>(null);

  useEffect(() => {
    if (!ref.current) return;
    const m = new maplibregl.Map({
      container: ref.current,
      style: OSM_STYLE as unknown as maplibregl.StyleSpecification,
      center: [lng, lat],
      zoom,
      interactive: false,
      attributionControl: false,
    });
    if (showMarker) {
      new maplibregl.Marker({ color: "#38bdf8" }).setLngLat([lng, lat]).addTo(m);
    }
    return () => m.remove();
  }, [lng, lat, zoom, showMarker]);

  return <div ref={ref} className={className} />;
}
