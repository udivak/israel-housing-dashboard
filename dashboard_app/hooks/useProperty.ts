import { useQuery } from "@tanstack/react-query";
import { fetchApi } from "@/lib/api/client";
import { API_ENDPOINTS, buildQuery } from "@/lib/api/endpoints";
import type { ModelInfo } from "@/lib/api/types";

export interface PropertyDoc {
  id: string;
  geometry?: { type: string; coordinates: [number, number] } | null;
  price?: number | null;
  price_per_sqm?: number | null;
  rooms?: number | null;
  area_sqm?: number | null;
  floor?: number | null;
  building_floors?: number | null;
  year_built?: number | null;
  city?: string | null;
  neighborhood?: string | null;
  street?: string | null;
  deal_nature?: string | null;
  transaction_date?: string | null;
  source_name?: string | null;
  [key: string]: unknown;
}

export function useProperty(id: string) {
  return useQuery<PropertyDoc>({
    queryKey: ["property", id],
    enabled: !!id,
    queryFn: () => fetchApi(API_ENDPOINTS.PROPERTY_DETAIL(id)),
    staleTime: 5 * 60_000,
  });
}

interface SimilarResponse {
  results: PropertyDoc[];
}

export function useSimilarProperties(id: string, radius = 500) {
  return useQuery<SimilarResponse>({
    queryKey: ["property-similar", id, radius],
    enabled: !!id,
    queryFn: () => fetchApi(`${API_ENDPOINTS.PROPERTY_SIMILAR(id)}${buildQuery({ radius })}`),
    staleTime: 5 * 60_000,
  });
}

export function useModels() {
  return useQuery<ModelInfo[]>({
    queryKey: ["predict-models"],
    queryFn: () => fetchApi(API_ENDPOINTS.PREDICT_MODELS),
    staleTime: 5 * 60_000,
  });
}
