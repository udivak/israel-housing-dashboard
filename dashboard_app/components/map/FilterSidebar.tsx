"use client";

import { useFiltersStore } from "@/lib/store/filters";
import { Filter, X } from "lucide-react";

const PROPERTY_TYPES = [
  "דירה",
  "דירה בבית קומות",
  "קוטג'",
  "פנטהאוז",
  "דופלקס",
  "דירת גן",
];

function Field({ label, children }: { label: string; children: React.ReactNode }) {
  return (
    <label className="flex flex-col gap-1.5 text-xs">
      <span className="text-zinc-400">{label}</span>
      {children}
    </label>
  );
}

const inputCls =
  "w-full rounded-md border border-white/10 bg-zinc-950/60 px-2.5 py-1.5 text-sm text-white placeholder:text-zinc-500 focus:border-cyan-500/50 focus:outline-none";

export function FilterSidebar() {
  const filters = useFiltersStore((s) => s.filters);
  const setFilters = useFiltersStore((s) => s.setFilters);
  const reset = useFiltersStore((s) => s.resetFilters);

  return (
    <aside
      dir="rtl"
      className="flex h-full w-72 shrink-0 flex-col gap-4 overflow-y-auto rounded-xl border border-white/10 bg-zinc-900/60 p-4 backdrop-blur"
    >
      <div className="flex items-center justify-between">
        <div className="flex items-center gap-2 text-sm font-semibold text-white">
          <Filter className="h-4 w-4" />
          סינון
        </div>
        <button
          onClick={reset}
          className="flex items-center gap-1 rounded-md px-2 py-1 text-xs text-zinc-400 hover:bg-white/5 hover:text-white"
        >
          <X className="h-3 w-3" />
          איפוס
        </button>
      </div>

      <Field label="עיר">
        <input
          className={inputCls}
          value={filters.city ?? ""}
          placeholder="כל הערים"
          onChange={(e) => setFilters({ city: e.target.value || undefined })}
        />
      </Field>

      <Field label="שכונה">
        <input
          className={inputCls}
          value={filters.neighborhood ?? ""}
          placeholder="כל השכונות"
          onChange={(e) => setFilters({ neighborhood: e.target.value || undefined })}
        />
      </Field>

      <div className="grid grid-cols-2 gap-2">
        <Field label="מחיר מינ׳ (₪)">
          <input
            type="number"
            className={inputCls}
            value={filters.min_price ?? ""}
            onChange={(e) =>
              setFilters({ min_price: e.target.value ? Number(e.target.value) : undefined })
            }
          />
        </Field>
        <Field label="מחיר מקס׳ (₪)">
          <input
            type="number"
            className={inputCls}
            value={filters.max_price ?? ""}
            onChange={(e) =>
              setFilters({ max_price: e.target.value ? Number(e.target.value) : undefined })
            }
          />
        </Field>
      </div>

      <div className="grid grid-cols-2 gap-2">
        <Field label="חדרים מינ׳">
          <input
            type="number"
            step="0.5"
            className={inputCls}
            value={filters.min_rooms ?? ""}
            onChange={(e) =>
              setFilters({ min_rooms: e.target.value ? Number(e.target.value) : undefined })
            }
          />
        </Field>
        <Field label="חדרים מקס׳">
          <input
            type="number"
            step="0.5"
            className={inputCls}
            value={filters.max_rooms ?? ""}
            onChange={(e) =>
              setFilters({ max_rooms: e.target.value ? Number(e.target.value) : undefined })
            }
          />
        </Field>
      </div>

      <div className="grid grid-cols-2 gap-2">
        <Field label="שטח מינ׳ (m²)">
          <input
            type="number"
            className={inputCls}
            value={filters.min_area ?? ""}
            onChange={(e) =>
              setFilters({ min_area: e.target.value ? Number(e.target.value) : undefined })
            }
          />
        </Field>
        <Field label="שטח מקס׳ (m²)">
          <input
            type="number"
            className={inputCls}
            value={filters.max_area ?? ""}
            onChange={(e) =>
              setFilters({ max_area: e.target.value ? Number(e.target.value) : undefined })
            }
          />
        </Field>
      </div>

      <div className="grid grid-cols-2 gap-2">
        <Field label="מתאריך">
          <input
            type="date"
            className={inputCls}
            value={filters.from_date ?? ""}
            onChange={(e) => setFilters({ from_date: e.target.value || undefined })}
          />
        </Field>
        <Field label="עד תאריך">
          <input
            type="date"
            className={inputCls}
            value={filters.to_date ?? ""}
            onChange={(e) => setFilters({ to_date: e.target.value || undefined })}
          />
        </Field>
      </div>

      <Field label="סוג נכס">
        <select
          className={inputCls}
          value={filters.property_type ?? ""}
          onChange={(e) => setFilters({ property_type: e.target.value || undefined })}
        >
          <option value="">הכל</option>
          {PROPERTY_TYPES.map((t) => (
            <option key={t} value={t}>
              {t}
            </option>
          ))}
        </select>
      </Field>

      <Field label="מקור">
        <select
          className={inputCls}
          value={filters.source ?? ""}
          onChange={(e) => setFilters({ source: e.target.value || undefined })}
        >
          <option value="">הכל</option>
          <option value="nadlan_gov">nadlan_gov</option>
          <option value="odata_il_nadlan">odata_il_nadlan</option>
          <option value="tax_authority_nadlan">tax_authority_nadlan</option>
          <option value="madlan_for_sale">madlan_for_sale</option>
        </select>
      </Field>
    </aside>
  );
}
