import { useQuery } from "@tanstack/react-query";
import { fetchApi } from "@/lib/api/client";
import { API_ENDPOINTS, buildQuery, filtersToQuery } from "@/lib/api/endpoints";
import type { BBoxParams, MapDataResponse, MapFilters } from "@/lib/api/types";

interface UseMapDataArgs {
  bbox: BBoxParams | null;
  zoom: number;
  filters: MapFilters;
  enabled?: boolean;
}

export function useMapData({ bbox, zoom, filters, enabled = true }: UseMapDataArgs) {
  return useQuery<MapDataResponse>({
    queryKey: ["map-data", bbox, zoom, filters],
    enabled: !!bbox && enabled,
    queryFn: async () => {
      if (!bbox) throw new Error("bbox required");
      const params = {
        ...bbox,
        zoom,
        ...filtersToQuery(filters),
      };
      return fetchApi<MapDataResponse>(`${API_ENDPOINTS.MAP_DATA}${buildQuery(params)}`);
    },
    staleTime: 30_000,
  });
}
