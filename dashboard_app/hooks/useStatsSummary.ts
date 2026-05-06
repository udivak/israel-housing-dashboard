import { useQuery } from "@tanstack/react-query";
import { fetchApi } from "@/lib/api/client";
import { API_ENDPOINTS, buildQuery, filtersToQuery } from "@/lib/api/endpoints";
import type { MapFilters, StatsSummary } from "@/lib/api/types";

export function useStatsSummary(filters: MapFilters) {
  return useQuery<StatsSummary>({
    queryKey: ["stats-summary", filters],
    queryFn: () =>
      fetchApi<StatsSummary>(`${API_ENDPOINTS.STATS_SUMMARY}${buildQuery(filtersToQuery(filters))}`),
    staleTime: 60_000,
  });
}
