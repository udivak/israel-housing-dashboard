import { useQuery } from "@tanstack/react-query";
import { fetchApi } from "@/lib/api/client";
import { API_ENDPOINTS, buildQuery } from "@/lib/api/endpoints";
import type { AutocompleteSuggestion } from "@/lib/api/types";

interface AutocompleteResponse {
  suggestions: AutocompleteSuggestion[];
}

export function useAutocomplete(q: string, enabled = true) {
  return useQuery<AutocompleteResponse>({
    queryKey: ["autocomplete", q],
    enabled: enabled && q.trim().length >= 2,
    queryFn: () =>
      fetchApi<AutocompleteResponse>(`${API_ENDPOINTS.PROPERTIES_AUTOCOMPLETE}${buildQuery({ q })}`),
    staleTime: 5 * 60_000,
  });
}
