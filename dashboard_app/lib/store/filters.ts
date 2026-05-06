import { create } from "zustand";
import { persist } from "zustand/middleware";
import type { MapFilters } from "@/lib/api/types";

export interface Viewport {
  longitude: number;
  latitude: number;
  zoom: number;
}

interface FiltersState {
  filters: MapFilters;
  viewport: Viewport;
  setFilters: (patch: Partial<MapFilters>) => void;
  resetFilters: () => void;
  setViewport: (vp: Viewport) => void;
}

export const DEFAULT_VIEWPORT: Viewport = {
  longitude: 34.7818,
  latitude: 32.0853,
  zoom: 8,
};

export const useFiltersStore = create<FiltersState>()(
  persist(
    (set) => ({
      filters: {},
      viewport: DEFAULT_VIEWPORT,
      setFilters: (patch) =>
        set((s) => ({
          filters: Object.fromEntries(
            Object.entries({ ...s.filters, ...patch }).filter(
              ([, v]) => v !== undefined && v !== null && v !== ""
            )
          ) as MapFilters,
        })),
      resetFilters: () => set({ filters: {} }),
      setViewport: (viewport) => set({ viewport }),
    }),
    { name: "ihd-filters" }
  )
);
