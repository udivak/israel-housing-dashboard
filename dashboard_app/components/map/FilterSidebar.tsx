"use client";

import { useFiltersStore } from "@/lib/store/filters";
import { Filter, X } from "lucide-react";
import { Pill } from "@/components/ui/Pill";
import { useLocale } from "@/lib/i18n/LocaleProvider";
import type { Messages } from "@/lib/i18n/en";
import type { MapFilters } from "@/lib/api/types";

// value = Hebrew DB value (sent to API); key resolves to the localized label.
const PROPERTY_TYPES: { value: string; key: keyof Messages }[] = [
  { value: "דירה", key: "ptype.apartment" },
  { value: "דירה בבית קומות", key: "ptype.apartmentTower" },
  { value: "קוטג'", key: "ptype.cottage" },
  { value: "פנטהאוז", key: "ptype.penthouse" },
  { value: "דופלקס", key: "ptype.duplex" },
  { value: "דירת גן", key: "ptype.gardenApartment" },
];

const ACTIVE_LABEL_KEYS: Partial<Record<keyof MapFilters, keyof Messages>> = {
  city: "filters.active.city",
  neighborhood: "filters.active.neighborhood",
  min_price: "filters.active.minPrice",
  max_price: "filters.active.maxPrice",
  min_rooms: "filters.active.minRooms",
  max_rooms: "filters.active.maxRooms",
  min_area: "filters.active.minArea",
  max_area: "filters.active.maxArea",
  from_date: "filters.active.fromDate",
  to_date: "filters.active.toDate",
  property_type: "filters.active.propertyType",
  source: "filters.active.source",
};

function Group({ label, children }: { label: string; children: React.ReactNode }) {
  return (
    <div className="flex flex-col gap-2 border-t border-[var(--border)] pt-4 first:border-t-0 first:pt-0">
      <div className="text-[11px] font-semibold uppercase tracking-wide text-[var(--fg-dim)]">
        {label}
      </div>
      {children}
    </div>
  );
}

function Field({ label, children }: { label: string; children: React.ReactNode }) {
  return (
    <label className="flex flex-col gap-1 text-xs">
      <span className="text-[var(--fg-muted)]">{label}</span>
      {children}
    </label>
  );
}

const inputCls =
  "w-full rounded-md border border-[var(--border)] bg-[var(--bg)] px-2.5 py-1.5 text-sm text-[var(--fg)] placeholder:text-[var(--fg-dim)] focus:border-[var(--accent-1)]/50 focus:outline-none";

export function FilterSidebar() {
  const filters = useFiltersStore((s) => s.filters);
  const setFilters = useFiltersStore((s) => s.setFilters);
  const reset = useFiltersStore((s) => s.resetFilters);
  const { t } = useLocale();

  const active = (Object.entries(filters) as [keyof MapFilters, unknown][])
    .filter(([, v]) => v !== undefined && v !== null && v !== "");

  return (
    <aside className="flex h-full w-72 shrink-0 flex-col gap-5 overflow-y-auto rounded-xl border border-[var(--border)] bg-[var(--bg-elev)] p-4">
      <div className="flex items-center justify-between">
        <div className="flex items-center gap-2 text-sm font-semibold text-[var(--fg)]">
          <Filter className="h-4 w-4 text-[var(--accent-1)]" />
          {t("filters.title")}
        </div>
        <button
          onClick={reset}
          disabled={!active.length}
          className="flex items-center gap-1 rounded-md px-2 py-1 text-xs text-[var(--fg-muted)] hover:bg-[var(--bg-elev-2)] hover:text-[var(--fg)] disabled:opacity-40"
        >
          <X className="h-3 w-3" />
          {t("filters.reset")}
        </button>
      </div>

      {active.length > 0 && (
        <div className="flex flex-wrap gap-1.5">
          {active.map(([k, v]) => {
            const mk = ACTIVE_LABEL_KEYS[k];
            const value =
              k === "min_price" || k === "max_price" ? Number(v).toLocaleString() : String(v);
            return (
              <Pill key={k as string} tone="accent" className="gap-1">
                {mk ? t(mk, { value }) : `${k}: ${String(v)}`}
                <button
                  type="button"
                  onClick={() => setFilters({ [k]: undefined } as Partial<MapFilters>)}
                  className="rounded-full p-0.5 hover:bg-[var(--accent-1)]/20"
                  aria-label={t("filters.clear", { field: String(k) })}
                >
                  <X className="h-2.5 w-2.5" />
                </button>
              </Pill>
            );
          })}
        </div>
      )}

      <Group label={t("filters.group.location")}>
        <Field label={t("filters.city")}>
          <input
            className={inputCls}
            value={filters.city ?? ""}
            placeholder={t("filters.allCities")}
            onChange={(e) => setFilters({ city: e.target.value || undefined })}
          />
        </Field>
        <Field label={t("filters.neighborhood")}>
          <input
            className={inputCls}
            value={filters.neighborhood ?? ""}
            placeholder={t("filters.allNeighborhoods")}
            onChange={(e) => setFilters({ neighborhood: e.target.value || undefined })}
          />
        </Field>
      </Group>

      <Group label={t("filters.group.price")}>
        <div className="grid grid-cols-2 gap-2">
          <Field label={t("filters.min")}>
            <input
              type="number"
              className={`tabular ${inputCls}`}
              value={filters.min_price ?? ""}
              onChange={(e) =>
                setFilters({ min_price: e.target.value ? Number(e.target.value) : undefined })
              }
            />
          </Field>
          <Field label={t("filters.max")}>
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

      <Group label={t("filters.group.size")}>
        <div className="grid grid-cols-2 gap-2">
          <Field label={t("filters.minRooms")}>
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
          <Field label={t("filters.maxRooms")}>
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
          <Field label={t("filters.minArea")}>
            <input
              type="number"
              className={`tabular ${inputCls}`}
              value={filters.min_area ?? ""}
              onChange={(e) =>
                setFilters({ min_area: e.target.value ? Number(e.target.value) : undefined })
              }
            />
          </Field>
          <Field label={t("filters.maxArea")}>
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

      <Group label={t("filters.group.date")}>
        <div className="grid grid-cols-2 gap-2">
          <Field label={t("filters.from")}>
            <input
              type="date"
              className={inputCls}
              value={filters.from_date ?? ""}
              onChange={(e) => setFilters({ from_date: e.target.value || undefined })}
            />
          </Field>
          <Field label={t("filters.to")}>
            <input
              type="date"
              className={inputCls}
              value={filters.to_date ?? ""}
              onChange={(e) => setFilters({ to_date: e.target.value || undefined })}
            />
          </Field>
        </div>
      </Group>

      <Group label={t("filters.group.typeSource")}>
        <Field label={t("filters.propertyType")}>
          <select
            className={inputCls}
            value={filters.property_type ?? ""}
            onChange={(e) => setFilters({ property_type: e.target.value || undefined })}
          >
            <option value="">{t("filters.all")}</option>
            {PROPERTY_TYPES.map((pt) => (
              <option key={pt.value} value={pt.value}>
                {t(pt.key)}
              </option>
            ))}
          </select>
        </Field>
        <Field label={t("filters.source")}>
          <select
            className={inputCls}
            value={filters.source ?? ""}
            onChange={(e) => setFilters({ source: e.target.value || undefined })}
          >
            <option value="">{t("filters.all")}</option>
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
