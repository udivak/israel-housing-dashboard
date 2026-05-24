"use client";

import { useFiltersStore } from "@/lib/store/filters";
import { Filter, X } from "lucide-react";
import { Pill } from "@/components/ui/Pill";
import type { MapFilters } from "@/lib/api/types";

const PROPERTY_TYPES = [
  { value: "דירה", label: "Apartment" },
  { value: "דירה בבית קומות", label: "Apartment in tower" },
  { value: "קוטג'", label: "Cottage" },
  { value: "פנטהאוז", label: "Penthouse" },
  { value: "דופלקס", label: "Duplex" },
  { value: "דירת גן", label: "Garden apartment" },
];

function Group({ label, children }: { label: string; children: React.ReactNode }) {
  return (
    <div className="flex flex-col gap-2 border-t border-[--border] pt-4 first:border-t-0 first:pt-0">
      <div className="text-[11px] font-semibold uppercase tracking-wide text-[--fg-dim]">
        {label}
      </div>
      {children}
    </div>
  );
}

function Field({ label, children }: { label: string; children: React.ReactNode }) {
  return (
    <label className="flex flex-col gap-1 text-xs">
      <span className="text-[--fg-muted]">{label}</span>
      {children}
    </label>
  );
}

const inputCls =
  "w-full rounded-md border border-[--border] bg-[--bg] px-2.5 py-1.5 text-sm text-[--fg] placeholder:text-[--fg-dim] focus:border-[--accent-1]/50 focus:outline-none";

const ACTIVE_LABELS: Partial<Record<keyof MapFilters, (v: unknown) => string>> = {
  city: (v) => `City: ${v}`,
  neighborhood: (v) => `Neighborhood: ${v}`,
  min_price: (v) => `≥ ₪${Number(v).toLocaleString()}`,
  max_price: (v) => `≤ ₪${Number(v).toLocaleString()}`,
  min_rooms: (v) => `≥ ${v} rooms`,
  max_rooms: (v) => `≤ ${v} rooms`,
  min_area: (v) => `≥ ${v}m²`,
  max_area: (v) => `≤ ${v}m²`,
  from_date: (v) => `From ${v}`,
  to_date: (v) => `To ${v}`,
  property_type: (v) => `Type: ${v}`,
  source: (v) => `Source: ${v}`,
};

export function FilterSidebar() {
  const filters = useFiltersStore((s) => s.filters);
  const setFilters = useFiltersStore((s) => s.setFilters);
  const reset = useFiltersStore((s) => s.resetFilters);

  const active = (Object.entries(filters) as [keyof MapFilters, unknown][])
    .filter(([, v]) => v !== undefined && v !== null && v !== "");

  return (
    <aside className="flex h-full w-72 shrink-0 flex-col gap-5 overflow-y-auto rounded-xl border border-[--border] bg-[--bg-elev] p-4">
      <div className="flex items-center justify-between">
        <div className="flex items-center gap-2 text-sm font-semibold text-[--fg]">
          <Filter className="h-4 w-4 text-[--accent-1]" />
          Filters
        </div>
        <button
          onClick={reset}
          disabled={!active.length}
          className="flex items-center gap-1 rounded-md px-2 py-1 text-xs text-[--fg-muted] hover:bg-[--bg-elev-2] hover:text-[--fg] disabled:opacity-40"
        >
          <X className="h-3 w-3" />
          Reset
        </button>
      </div>

      {active.length > 0 && (
        <div className="flex flex-wrap gap-1.5">
          {active.map(([k, v]) => (
            <Pill key={k as string} tone="accent" className="gap-1">
              {(ACTIVE_LABELS[k] ?? ((x) => `${k}: ${x}`))(v)}
              <button
                type="button"
                onClick={() => setFilters({ [k]: undefined } as Partial<MapFilters>)}
                className="rounded-full p-0.5 hover:bg-[--accent-1]/20"
                aria-label={`Clear ${k}`}
              >
                <X className="h-2.5 w-2.5" />
              </button>
            </Pill>
          ))}
        </div>
      )}

      <Group label="Location">
        <Field label="City">
          <input
            className={inputCls}
            value={filters.city ?? ""}
            placeholder="All cities"
            onChange={(e) => setFilters({ city: e.target.value || undefined })}
          />
        </Field>
        <Field label="Neighborhood">
          <input
            className={inputCls}
            value={filters.neighborhood ?? ""}
            placeholder="All neighborhoods"
            onChange={(e) => setFilters({ neighborhood: e.target.value || undefined })}
          />
        </Field>
      </Group>

      <Group label="Price (₪)">
        <div className="grid grid-cols-2 gap-2">
          <Field label="Min">
            <input
              type="number"
              className={`tabular ${inputCls}`}
              value={filters.min_price ?? ""}
              onChange={(e) =>
                setFilters({ min_price: e.target.value ? Number(e.target.value) : undefined })
              }
            />
          </Field>
          <Field label="Max">
            <input
              type="number"
              className={`tabular ${inputCls}`}
              value={filters.max_price ?? ""}
              onChange={(e) =>
                setFilters({ max_price: e.target.value ? Number(e.target.value) : undefined })
              }
            />
          </Field>
        </div>
      </Group>

      <Group label="Size">
        <div className="grid grid-cols-2 gap-2">
          <Field label="Min rooms">
            <input
              type="number"
              step="0.5"
              className={`tabular ${inputCls}`}
              value={filters.min_rooms ?? ""}
              onChange={(e) =>
                setFilters({ min_rooms: e.target.value ? Number(e.target.value) : undefined })
              }
            />
          </Field>
          <Field label="Max rooms">
            <input
              type="number"
              step="0.5"
              className={`tabular ${inputCls}`}
              value={filters.max_rooms ?? ""}
              onChange={(e) =>
                setFilters({ max_rooms: e.target.value ? Number(e.target.value) : undefined })
              }
            />
          </Field>
          <Field label="Min m²">
            <input
              type="number"
              className={`tabular ${inputCls}`}
              value={filters.min_area ?? ""}
              onChange={(e) =>
                setFilters({ min_area: e.target.value ? Number(e.target.value) : undefined })
              }
            />
          </Field>
          <Field label="Max m²">
            <input
              type="number"
              className={`tabular ${inputCls}`}
              value={filters.max_area ?? ""}
              onChange={(e) =>
                setFilters({ max_area: e.target.value ? Number(e.target.value) : undefined })
              }
            />
          </Field>
        </div>
      </Group>

      <Group label="Date">
        <div className="grid grid-cols-2 gap-2">
          <Field label="From">
            <input
              type="date"
              className={inputCls}
              value={filters.from_date ?? ""}
              onChange={(e) => setFilters({ from_date: e.target.value || undefined })}
            />
          </Field>
          <Field label="To">
            <input
              type="date"
              className={inputCls}
              value={filters.to_date ?? ""}
              onChange={(e) => setFilters({ to_date: e.target.value || undefined })}
            />
          </Field>
        </div>
      </Group>

      <Group label="Type & source">
        <Field label="Property type">
          <select
            className={inputCls}
            value={filters.property_type ?? ""}
            onChange={(e) => setFilters({ property_type: e.target.value || undefined })}
          >
            <option value="">All</option>
            {PROPERTY_TYPES.map((t) => (
              <option key={t.value} value={t.value}>
                {t.label}
              </option>
            ))}
          </select>
        </Field>
        <Field label="Source">
          <select
            className={inputCls}
            value={filters.source ?? ""}
            onChange={(e) => setFilters({ source: e.target.value || undefined })}
          >
            <option value="">All</option>
            <option value="nadlan_gov">nadlan_gov</option>
            <option value="odata_il_nadlan">odata_il_nadlan</option>
            <option value="tax_authority_nadlan">tax_authority_nadlan</option>
            <option value="madlan_for_sale">madlan_for_sale</option>
          </select>
        </Field>
      </Group>
    </aside>
  );
}
