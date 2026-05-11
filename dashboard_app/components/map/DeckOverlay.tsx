"use client";

import { useEffect } from "react";
import maplibregl from "maplibre-gl";
import type { MapDataResponse, PointFeature } from "@/lib/api/types";

interface DeckOverlayProps {
  map: maplibregl.Map | null;
  data: MapDataResponse | undefined;
  onPointClick?: (p: PointFeature) => void;
}

const SOURCE_ID = "ihd-points";
const LAYER_ID = "ihd-points-layer";

function toGeoJSON(data: MapDataResponse | undefined) {
  const features: GeoJSON.Feature[] = [];
  if (!data) return { type: "FeatureCollection", features } as const;

  if (data.type === "clusters") {
    for (const c of data.cells) {
      features.push({
        type: "Feature",
        geometry: { type: "Point", coordinates: [c.lng, c.lat] },
        properties: {
          kind: "cluster",
          h3: c.h3,
          count: c.count,
          ppsm: c.median_price_per_sqm ?? 0,
          price: c.median_price ?? 0,
        },
      });
    }
  } else {
    for (const p of data.features) {
      features.push({
        type: "Feature",
        geometry: { type: "Point", coordinates: [p.lng, p.lat] },
        properties: {
          kind: "point",
          id: p.id,
          ppsm: p.price_per_sqm ?? 0,
          price: p.price ?? 0,
          rooms: p.rooms ?? null,
          area_sqm: p.area_sqm ?? null,
          city: p.city ?? "",
          neighborhood: p.neighborhood ?? "",
          transaction_date: p.transaction_date ?? "",
          coord_source: p.coord_source ?? "unknown",
        },
      });
    }
  }
  return { type: "FeatureCollection", features } as const;
}

export function DeckOverlay({ map, data, onPointClick }: DeckOverlayProps) {
  // Add source + layer once on the map
  useEffect(() => {
    if (!map) return;
    const ensureLayer = () => {
      if (!map.getSource(SOURCE_ID)) {
        map.addSource(SOURCE_ID, {
          type: "geojson",
          data: { type: "FeatureCollection", features: [] },
        });
      }
      if (!map.getLayer(LAYER_ID)) {
        map.addLayer({
          id: LAYER_ID,
          type: "circle",
          source: SOURCE_ID,
          paint: {
            // Cluster radius scales with count; point radius reflects coord accuracy.
            "circle-radius": [
              "case",
              ["==", ["get", "kind"], "cluster"],
              ["max", 8, ["min", 40, ["sqrt", ["get", "count"]]]],
              ["==", ["get", "coord_source"], "address"], 6,
              ["==", ["get", "coord_source"], "parcel_centroid"], 4,
              3,
            ],
            // Color scales with price/m² along a red->blue gradient
            "circle-color": [
              "interpolate",
              ["linear"],
              ["get", "ppsm"],
              5000, "#33a3d4",
              15000, "#8ddccd",
              25000, "#fde0a3",
              40000, "#f08c69",
              80000, "#b22834",
            ],
            "circle-opacity": [
              "case",
              ["==", ["get", "kind"], "cluster"], 0.8,
              ["==", ["get", "coord_source"], "address"], 0.9,
              ["==", ["get", "coord_source"], "parcel_centroid"], 0.55,
              0.35,
            ],
            "circle-stroke-color": "#ffffff",
            "circle-stroke-width": 1,
            "circle-stroke-opacity": 0.4,
          },
        });
      }
    };
    if (map.isStyleLoaded()) ensureLayer();
    else map.once("load", ensureLayer);

    const onClick = (e: maplibregl.MapMouseEvent & { features?: maplibregl.MapGeoJSONFeature[] }) => {
      const f = e.features?.[0];
      if (!f) return;
      const props = f.properties as Record<string, unknown>;
      if (props.kind === "point" && onPointClick) {
        const coords = (f.geometry as GeoJSON.Point).coordinates;
        onPointClick({
          id: String(props.id),
          lng: coords[0],
          lat: coords[1],
          price: typeof props.price === "number" ? props.price : null,
          price_per_sqm: typeof props.ppsm === "number" ? props.ppsm : null,
          rooms: typeof props.rooms === "number" ? props.rooms : null,
          area_sqm: typeof props.area_sqm === "number" ? props.area_sqm : null,
          city: String(props.city || "") || null,
          neighborhood: String(props.neighborhood || "") || null,
          transaction_date: String(props.transaction_date || "") || null,
          coord_source: typeof props.coord_source === "string" ? props.coord_source : null,
        });
      } else if (props.kind === "cluster") {
        // Zoom in on cluster click
        const coords = (f.geometry as GeoJSON.Point).coordinates;
        map.flyTo({ center: [coords[0], coords[1]], zoom: Math.min(15, map.getZoom() + 2) });
      }
    };
    const onEnter = () => { map.getCanvas().style.cursor = "pointer"; };
    const onLeave = () => { map.getCanvas().style.cursor = ""; };

    map.on("click", LAYER_ID, onClick);
    map.on("mouseenter", LAYER_ID, onEnter);
    map.on("mouseleave", LAYER_ID, onLeave);

    return () => {
      map.off("click", LAYER_ID, onClick);
      map.off("mouseenter", LAYER_ID, onEnter);
      map.off("mouseleave", LAYER_ID, onLeave);
      try {
        if (map.getLayer(LAYER_ID)) map.removeLayer(LAYER_ID);
        if (map.getSource(SOURCE_ID)) map.removeSource(SOURCE_ID);
      } catch {
        // map may already be torn down
      }
    };
  }, [map, onPointClick]);

  // Update source data when API data changes
  useEffect(() => {
    if (!map) return;
    const source = map.getSource(SOURCE_ID) as maplibregl.GeoJSONSource | undefined;
    if (!source) return;
    source.setData(toGeoJSON(data) as GeoJSON.FeatureCollection);
  }, [map, data]);

  return null;
}
