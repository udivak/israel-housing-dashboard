"use client";

import { useEffect, useRef } from "react";
import maplibregl from "maplibre-gl";
import "maplibre-gl/dist/maplibre-gl.css";
import { OSM_STYLE } from "@/lib/map-style";

export function MiniMap({ lng, lat }: { lng: number; lat: number }) {
  const ref = useRef<HTMLDivElement>(null);

  useEffect(() => {
    if (!ref.current) return;
    const m = new maplibregl.Map({
      container: ref.current,
      style: OSM_STYLE as unknown as maplibregl.StyleSpecification,
      center: [lng, lat],
      zoom: 15,
      interactive: false,
    });
    new maplibregl.Marker({ color: "#06b6d4" }).setLngLat([lng, lat]).addTo(m);
    return () => m.remove();
  }, [lng, lat]);

  return <div ref={ref} className="h-48 w-full overflow-hidden rounded-xl border border-white/10" />;
}
