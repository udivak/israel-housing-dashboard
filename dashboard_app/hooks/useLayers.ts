"use client";

import { useQuery } from "@tanstack/react-query";
import { fetchApi } from "@/lib/api/client";
import { API_ENDPOINTS } from "@/lib/api/endpoints";
import type { LayerConfig } from "@/lib/api/types";

export function useLayers() {
  return useQuery<LayerConfig[]>({
    queryKey: ["layers"],
    queryFn: () => fetchApi<LayerConfig[]>(API_ENDPOINTS.LAYERS),
    retry: 1,
    staleTime: 60_000,
  });
}
