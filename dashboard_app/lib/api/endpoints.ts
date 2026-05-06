import type { MapFilters } from "./types";

export const API_ENDPOINTS = {
  HEALTH: "/health",
  LAYERS: "/api/v1/layers",
  MAP_FEATURES: "/api/v1/map/features",
  MAP_DATA: "/api/v1/map/data",
  PROPERTIES_SEARCH: "/api/v1/properties/search",
  PROPERTIES_AUTOCOMPLETE: "/api/v1/properties/autocomplete",
  PROPERTY_DETAIL: (id: string) => `/api/v1/properties/${encodeURIComponent(id)}`,
  PROPERTY_SIMILAR: (id: string) => `/api/v1/properties/${encodeURIComponent(id)}/similar`,
  STATS_SUMMARY: "/api/v1/stats/summary",
  STATS_TIMESERIES: "/api/v1/stats/timeseries",
  STATS_BY_REGION: "/api/v1/stats/by-region",
  STATS_DISTRIBUTION: "/api/v1/stats/distribution",
  STATS_YOY: "/api/v1/stats/yoy-by-city",
  STATS_SOURCE: "/api/v1/stats/source-breakdown",
  STATS_PROPERTY_TYPE: "/api/v1/stats/property-type-breakdown",
  STATS_SEASONALITY: "/api/v1/stats/seasonality",
  PREDICT: "/api/v1/predict",
  PREDICT_COMPARE: "/api/v1/predict/compare",
  PREDICT_MODELS: "/api/v1/predict/models",
} as const;

export function buildQuery(params: Record<string, unknown>): string {
  const sp = new URLSearchParams();
  for (const [k, v] of Object.entries(params)) {
    if (v === undefined || v === null || v === "") continue;
    sp.set(k, String(v));
  }
  const s = sp.toString();
  return s ? `?${s}` : "";
}

export function filtersToQuery(f: MapFilters): Record<string, string | number> {
  const out: Record<string, string | number> = {};
  for (const [k, v] of Object.entries(f)) {
    if (v === undefined || v === null || v === "") continue;
    out[k] = v as string | number;
  }
  return out;
}
