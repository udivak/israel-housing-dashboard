"use client";

import { useQuery } from "@tanstack/react-query";
import { fetchApi } from "@/lib/api/client";
import { API_ENDPOINTS } from "@/lib/api/endpoints";

interface HealthResponse {
  status: string;
  service: string;
}

export function useHealth() {
  return useQuery<HealthResponse>({
    queryKey: ["health"],
    queryFn: () => fetchApi<HealthResponse>(API_ENDPOINTS.HEALTH),
    retry: 1,
    staleTime: 30_000,
  });
}
