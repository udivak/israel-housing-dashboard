"use client";

import { useEffect, useMemo, useRef } from "react";
import maplibregl from "maplibre-gl";
import { MapboxOverlay } from "@deck.gl/mapbox";
import { H3HexagonLayer } from "@deck.gl/geo-layers";
import { ScatterplotLayer } from "@deck.gl/layers";
import type { ClusterCell, MapDataResponse, PointFeature } from "@/lib/api/types";

interface DeckOverlayProps {
  map: maplibregl.Map | null;
  data: MapDataResponse | undefined;
  onPointClick?: (p: PointFeature) => void;
}

const RAMP: [number, number, number][] = [
  [33, 102, 172],
  [103, 169, 207],
  [209, 229, 240],
  [253, 219, 199],
  [239, 138, 98],
  [178, 24, 43],
];

function colorFor(value: number, vmin: number, vmax: number): [number, number, number, number] {
  if (!Number.isFinite(value) || vmax <= vmin) return [200, 200, 200, 200];
  const t = Math.max(0, Math.min(1, (value - vmin) / (vmax - vmin)));
  const idx = Math.min(RAMP.length - 1, Math.floor(t * RAMP.length));
  const [r, g, b] = RAMP[idx];
  return [r, g, b, 200];
}

export function DeckOverlay({ map, data, onPointClick }: DeckOverlayProps) {
  const overlayRef = useRef<MapboxOverlay | null>(null);

  const layers = useMemo(() => {
    if (!data) return [];

    if (data.type === "clusters") {
      const cells = data.cells.filter((c) => c.median_price_per_sqm != null);
      const values = cells.map((c) => c.median_price_per_sqm as number).sort((a, b) => a - b);
      const vmin = values[Math.floor(values.length * 0.05)] ?? 0;
      const vmax = values[Math.floor(values.length * 0.95)] ?? 1;
      return [
        new H3HexagonLayer<ClusterCell>({
          id: "h3-clusters",
          data: data.cells,
          pickable: true,
          extruded: false,
          filled: true,
          stroked: true,
          lineWidthMinPixels: 1,
          getHexagon: (d) => d.h3,
          getFillColor: (d) => colorFor(d.median_price_per_sqm ?? 0, vmin, vmax),
          getLineColor: [255, 255, 255, 60],
          opacity: 0.75,
          updateTriggers: { getFillColor: [vmin, vmax] },
        }),
      ];
    }

    const prices = data.features
      .map((f) => f.price_per_sqm)
      .filter((v): v is number => v != null)
      .sort((a, b) => a - b);
    const vmin = prices[Math.floor(prices.length * 0.05)] ?? 0;
    const vmax = prices[Math.floor(prices.length * 0.95)] ?? 1;
    return [
      new ScatterplotLayer<PointFeature>({
        id: "points",
        data: data.features,
        pickable: true,
        radiusUnits: "pixels",
        getRadius: 5,
        radiusMinPixels: 3,
        radiusMaxPixels: 8,
        getPosition: (d) => [d.lng, d.lat],
        getFillColor: (d) => colorFor(d.price_per_sqm ?? 0, vmin, vmax),
        getLineColor: [255, 255, 255, 200],
        lineWidthMinPixels: 1,
        stroked: true,
        onClick: (info) => info.object && onPointClick?.(info.object as PointFeature),
        updateTriggers: { getFillColor: [vmin, vmax] },
      }),
    ];
  }, [data, onPointClick]);

  useEffect(() => {
    if (!map) return;
    const overlay = new MapboxOverlay({ layers });
    overlayRef.current = overlay;
    map.addControl(overlay as unknown as maplibregl.IControl);
    return () => {
      try {
        map.removeControl(overlay as unknown as maplibregl.IControl);
      } catch {
        // map may already be torn down
      }
      overlayRef.current = null;
    };
  }, [map]);

  useEffect(() => {
    overlayRef.current?.setProps({ layers });
  }, [layers]);

  return null;
}
