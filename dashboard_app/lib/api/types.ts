export interface LayerConfig {
  id: string;
  name: string;
  type: "fill" | "line" | "circle" | "symbol";
  color: string;
  source: string;
  min_zoom?: number;
  max_zoom?: number;
  opacity: number;
}

export interface BBoxParams {
  min_lat: number;
  max_lat: number;
  min_lng: number;
  max_lng: number;
}

export interface MapFilters {
  city?: string;
  neighborhood?: string;
  min_price?: number;
  max_price?: number;
  min_rooms?: number;
  max_rooms?: number;
  min_area?: number;
  max_area?: number;
  from_date?: string;
  to_date?: string;
  property_type?: string;
  source?: string;
}

export interface ClusterCell {
  h3: string;
  lat: number;
  lng: number;
  count: number;
  median_price?: number | null;
  median_price_per_sqm?: number | null;
  min_price?: number | null;
  max_price?: number | null;
}

export interface ClusterResponse {
  type: "clusters";
  resolution: number;
  cells: ClusterCell[];
}

export interface PointFeature {
  id: string;
  lat: number;
  lng: number;
  price?: number | null;
  price_per_sqm?: number | null;
  rooms?: number | null;
  area_sqm?: number | null;
  city?: string | null;
  neighborhood?: string | null;
  street?: string | null;
  transaction_date?: string | null;
  coord_source?: string | null;
}

export interface PointsResponse {
  type: "points";
  truncated: boolean;
  features: PointFeature[];
}

export type MapDataResponse = ClusterResponse | PointsResponse;

export interface StatsSummary {
  count: number;
  avg_price?: number | null;
  avg_price_per_sqm?: number | null;
  min_date?: string | null;
  max_date?: string | null;
  distinct_cities_count?: number;
}

export interface AutocompleteSuggestion {
  type: "city" | "neighborhood" | "street";
  value: string;
  count: number;
}

export interface ModelInfo {
  id: string;
  owner: string;
  name: string;
  metrics?: Record<string, unknown> | null;
  metadata?: Record<string, unknown> | null;
  n_features?: number | null;
}

export interface PropertySearchResult {
  page: number;
  size: number;
  total: number;
  results: Array<Record<string, unknown> & { id: string }>;
}

export interface GeoJSONGeometry {
  type: string;
  coordinates: number[] | number[][] | number[][][];
}

export interface GeoJSONFeature {
  type: "Feature";
  geometry: GeoJSONGeometry | null;
  properties?: Record<string, unknown>;
  id?: string | number;
}

export interface FeatureCollection {
  type: "FeatureCollection";
  features: GeoJSONFeature[];
}
