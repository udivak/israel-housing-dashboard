"use client";

import { useEffect, useRef, useCallback } from "react";
import maplibregl from "maplibre-gl";
import "maplibre-gl/dist/maplibre-gl.css";
import { DEFAULT_CENTER, DEFAULT_ZOOM, OSM_STYLE } from "@/lib/map-style";

interface MapViewProps {
  center?: [number, number];
  zoom?: number;
  onMapReady?: (map: maplibregl.Map) => void;
  className?: string;
}

export function MapView({
  center = DEFAULT_CENTER,
  zoom = DEFAULT_ZOOM,
  onMapReady,
  className = "",
}: MapViewProps) {
  const mapContainer = useRef<HTMLDivElement>(null);
  const map = useRef<maplibregl.Map | null>(null);

  const flyTo = useCallback((lng: number, lat: number, zoomLevel = 14) => {
    map.current?.flyTo({ center: [lng, lat], zoom: zoomLevel, duration: 1500 });
  }, []);

  useEffect(() => {
    if (!mapContainer.current) return;

    map.current = new maplibregl.Map({
      container: mapContainer.current,
      style: OSM_STYLE as unknown as maplibregl.StyleSpecification,
      center,
      zoom,
    });

    map.current.addControl(new maplibregl.NavigationControl(), "top-right");

    onMapReady?.(map.current);

    return () => {
      map.current?.remove();
      map.current = null;
    };
  }, []);

  useEffect(() => {
    if (map.current) {
      map.current.flyTo({ center, zoom, duration: 500 });
    }
  }, [center, zoom]);

  return (
    <div
      ref={mapContainer}
      className={`w-full h-full rounded-xl overflow-hidden ${className}`}
    />
  );
}
