import { useQuery } from "@tanstack/react-query";
import { fetchApi } from "@/lib/api/client";
import { API_ENDPOINTS, buildQuery } from "@/lib/api/endpoints";

export interface TimeseriesPoint {
  bucket: string;
  avg_price: number;
  avg_price_per_sqm: number;
  count: number;
}

export interface RegionRow {
  region: string;
  avg_price: number;
  avg_price_per_sqm: number;
  count: number;
}

export interface DistributionBin {
  min: number;
  max: number;
  count: number;
}

export interface YoyRow {
  city: string;
  current_year: number;
  current_avg: number;
  current_count: number;
  previous_year: number;
  previous_avg: number;
  yoy_pct: number;
}

export interface SourceRow {
  source: string;
  count: number;
  max_date?: string | null;
}

export interface PropertyTypeRow {
  type: string;
  count: number;
  avg_price: number;
}

export interface SeasonalityRow {
  month: number;
  count: number;
  avg_price: number;
}

export function useTimeseries(granularity: "month" | "quarter" | "year", city?: string) {
  return useQuery<TimeseriesPoint[]>({
    queryKey: ["stats-timeseries", granularity, city],
    queryFn: () =>
      fetchApi(`${API_ENDPOINTS.STATS_TIMESERIES}${buildQuery({ granularity, city })}`),
    staleTime: 5 * 60_000,
  });
}

export function useByRegion(level: "city" | "neighborhood", metric = "avg_price_per_sqm", limit = 20) {
  return useQuery<RegionRow[]>({
    queryKey: ["stats-by-region", level, metric, limit],
    queryFn: () =>
      fetchApi(`${API_ENDPOINTS.STATS_BY_REGION}${buildQuery({ level, metric, limit })}`),
    staleTime: 5 * 60_000,
  });
}

export function useDistribution(field: "price" | "price_per_sqm" | "rooms" | "area_sqm" | "year_built", bins = 30, city?: string) {
  return useQuery<DistributionBin[]>({
    queryKey: ["stats-distribution", field, bins, city],
    queryFn: () =>
      fetchApi(`${API_ENDPOINTS.STATS_DISTRIBUTION}${buildQuery({ field, bins, city })}`),
    staleTime: 5 * 60_000,
  });
}

export function useYoyByCity(top = 20) {
  return useQuery<YoyRow[]>({
    queryKey: ["stats-yoy", top],
    queryFn: () => fetchApi(`${API_ENDPOINTS.STATS_YOY}${buildQuery({ top })}`),
    staleTime: 5 * 60_000,
  });
}

export function useSourceBreakdown() {
  return useQuery<SourceRow[]>({
    queryKey: ["stats-source"],
    queryFn: () => fetchApi(API_ENDPOINTS.STATS_SOURCE),
    staleTime: 5 * 60_000,
  });
}

export function usePropertyTypeBreakdown(city?: string) {
  return useQuery<PropertyTypeRow[]>({
    queryKey: ["stats-property-type", city],
    queryFn: () =>
      fetchApi(`${API_ENDPOINTS.STATS_PROPERTY_TYPE}${buildQuery({ city })}`),
    staleTime: 5 * 60_000,
  });
}

export function useSeasonality(city?: string) {
  return useQuery<SeasonalityRow[]>({
    queryKey: ["stats-seasonality", city],
    queryFn: () =>
      fetchApi(`${API_ENDPOINTS.STATS_SEASONALITY}${buildQuery({ city })}`),
    staleTime: 5 * 60_000,
  });
}
