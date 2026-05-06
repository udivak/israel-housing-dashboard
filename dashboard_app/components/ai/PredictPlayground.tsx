"use client";

import { useState } from "react";
import { Brain, Loader2, GitCompare, MapPin, Search } from "lucide-react";
import { useMutation } from "@tanstack/react-query";
import { fetchApi } from "@/lib/api/client";
import { API_ENDPOINTS } from "@/lib/api/endpoints";
import { useModels } from "@/hooks/useProperty";
import { modelDisplayName } from "@/lib/model-utils";
import { searchPlaces, formatAddress } from "@/lib/geocoding";

interface FieldDef {
  key: string;
  label: string;
  type?: "number" | "text";
  step?: string;
  defaultValue?: string;
  hint?: string;
}

const FIELDS: FieldDef[] = [
  { key: "area_sqm", label: "שטח (m²)", type: "number", defaultValue: "100" },
  { key: "rooms", label: "חדרים", type: "number", step: "0.5", defaultValue: "4" },
  { key: "floor", label: "קומה", type: "number", defaultValue: "3" },
  { key: "building_floors", label: "קומות בבניין", type: "number", defaultValue: "8" },
  { key: "year_built", label: "שנת בנייה", type: "number", defaultValue: "2010" },
  { key: "property_age", label: "גיל נכס (שנים)", type: "number", defaultValue: "15" },
  { key: "year", label: "שנת עסקה", type: "number", defaultValue: "2024" },
  { key: "month", label: "חודש (1-12)", type: "number", defaultValue: "6" },
  { key: "quarter", label: "רבעון (1-4)", type: "number", defaultValue: "2" },
  { key: "log_area_sqm", label: "log(שטח)", type: "number", step: "0.001", defaultValue: "4.605", hint: "= ln(area_sqm)" },
];

interface PredictResponse {
  predicted_log_price: number;
  predicted_price: number;
  model: string;
}

interface CompareItem {
  model: string;
  predicted_price?: number | null;
  error?: string | null;
}

interface CompareResponse {
  items: CompareItem[];
  consensus_price?: number | null;
  spread_price?: number | null;
  stddev_price?: number | null;
}

function fmtCurrency(n: number | null | undefined): string {
  if (n == null || !Number.isFinite(n)) return "—";
  return `₪${n.toLocaleString("he-IL", { maximumFractionDigits: 0 })}`;
}

export function PredictPlayground() {
  const { data: models = [] } = useModels();
  const [values, setValues] = useState<Record<string, string>>(() =>
    Object.fromEntries(FIELDS.map((f) => [f.key, f.defaultValue ?? ""]))
  );
  const [selectedModel, setSelectedModel] = useState<string>("");
  const [compareMode, setCompareMode] = useState(false);

  // Address / location state — geocoded to lat/lng + city/street.
  const [address, setAddress] = useState("");
  const [resolved, setResolved] = useState<{
    lat: number;
    lon: number;
    label: string;
    city?: string;
    street?: string;
  } | null>(null);
  const [geocoding, setGeocoding] = useState(false);
  const [geocodeError, setGeocodeError] = useState<string | null>(null);

  const handleGeocode = async () => {
    if (!address.trim()) return;
    setGeocoding(true);
    setGeocodeError(null);
    try {
      const features = await searchPlaces(address, { limit: 1 });
      const f = features[0];
      if (!f) {
        setGeocodeError("לא נמצאה כתובת");
        setResolved(null);
      } else {
        const [lon, lat] = f.geometry.coordinates;
        const props = f.properties as Record<string, string | undefined>;
        setResolved({
          lat,
          lon,
          label: formatAddress(f),
          city: props.city ?? props.district ?? props.county,
          street: props.street,
        });
      }
    } catch {
      setGeocodeError("שגיאה ב-geocoding");
    } finally {
      setGeocoding(false);
    }
  };

  const buildFeatures = () => {
    const out: Record<string, number | string> = {};
    for (const f of FIELDS) {
      const v = values[f.key];
      if (v === "" || v == null) continue;
      const n = Number(v);
      if (Number.isFinite(n)) out[f.key] = n;
    }
    if (resolved) {
      out.lat = resolved.lat;
      out.lon = resolved.lon;
      if (resolved.city) out.city = resolved.city;
      if (resolved.street) out.street = resolved.street;
    }
    return out;
  };

  const single = useMutation<PredictResponse>({
    mutationFn: () =>
      fetchApi(`${API_ENDPOINTS.PREDICT}${selectedModel ? `?model=${encodeURIComponent(selectedModel)}` : ""}`, {
        method: "POST",
        body: JSON.stringify({ features: buildFeatures() }),
      }),
  });

  const compare = useMutation<CompareResponse>({
    mutationFn: () =>
      fetchApi(API_ENDPOINTS.PREDICT_COMPARE, {
        method: "POST",
        body: JSON.stringify({ features: buildFeatures() }),
      }),
  });

  const onRun = () => {
    if (compareMode) compare.mutate();
    else single.mutate();
  };

  return (
    <div dir="rtl" className="rounded-xl border border-white/10 bg-zinc-900/60 p-4 backdrop-blur">
      <div className="mb-3 flex items-center gap-2">
        <Brain className="h-4 w-4 text-cyan-400" />
        <h3 className="text-sm font-semibold text-white">מגרש משחקים — ניבוי מחיר</h3>
      </div>
      <p className="mb-4 text-xs text-zinc-500">
        מלא את הפיצ'רים ולחץ על הכפתור. שדות חסרים יוחלפו ב-null. הוסף כתובת לתוצאה מדויקת יותר.
      </p>

      <div className="mb-4 rounded-md border border-white/10 bg-zinc-950/40 p-3">
        <div className="mb-2 flex items-center gap-2 text-xs font-medium text-zinc-300">
          <MapPin className="h-3.5 w-3.5 text-cyan-400" />
          כתובת הנכס
        </div>
        <div className="flex flex-col gap-2 sm:flex-row">
          <input
            type="text"
            value={address}
            onChange={(e) => setAddress(e.target.value)}
            onKeyDown={(e) => e.key === "Enter" && handleGeocode()}
            placeholder="לדוגמה: רוטשילד 22 תל אביב"
            className="flex-1 rounded-md border border-white/10 bg-zinc-950/60 px-2.5 py-1.5 text-sm text-white placeholder:text-zinc-500 focus:border-cyan-500/50 focus:outline-none"
          />
          <button
            onClick={handleGeocode}
            disabled={geocoding || !address.trim()}
            className="flex items-center justify-center gap-2 rounded-md border border-white/10 bg-zinc-950/60 px-3 py-1.5 text-sm text-white hover:bg-white/5 disabled:opacity-50"
          >
            {geocoding ? <Loader2 className="h-3.5 w-3.5 animate-spin" /> : <Search className="h-3.5 w-3.5" />}
            חפש
          </button>
        </div>
        {resolved && (
          <div className="mt-2 flex items-center gap-2 rounded-md border border-emerald-500/30 bg-emerald-500/10 px-2.5 py-1.5 text-xs">
            <MapPin className="h-3 w-3 text-emerald-400" />
            <span className="text-zinc-200">{resolved.label}</span>
            <span className="text-zinc-500">
              ({resolved.lat.toFixed(4)}, {resolved.lon.toFixed(4)})
            </span>
          </div>
        )}
        {geocodeError && (
          <div className="mt-2 text-xs text-rose-300">{geocodeError}</div>
        )}
      </div>

      <div className="grid gap-3 md:grid-cols-2 lg:grid-cols-5">
        {FIELDS.map((f) => (
          <label key={f.key} className="flex flex-col gap-1 text-xs">
            <span className="text-zinc-400">{f.label}</span>
            <input
              type={f.type ?? "text"}
              step={f.step}
              value={values[f.key] ?? ""}
              onChange={(e) => setValues({ ...values, [f.key]: e.target.value })}
              className="w-full rounded-md border border-white/10 bg-zinc-950/60 px-2.5 py-1.5 text-sm text-white focus:border-cyan-500/50 focus:outline-none"
            />
            {f.hint && <span className="text-[10px] text-zinc-600">{f.hint}</span>}
          </label>
        ))}
      </div>

      <div className="mt-4 flex flex-wrap items-center gap-3">
        <label className="flex items-center gap-2 text-xs text-zinc-400">
          <input
            type="checkbox"
            checked={compareMode}
            onChange={(e) => setCompareMode(e.target.checked)}
            className="h-3.5 w-3.5 accent-cyan-500"
          />
          השוואת כל המודלים
        </label>
        {!compareMode && (
          <select
            value={selectedModel}
            onChange={(e) => setSelectedModel(e.target.value)}
            className="rounded-md border border-white/10 bg-zinc-950/60 px-2.5 py-1.5 text-sm text-white"
          >
            <option value="">Champion (ברירת מחדל)</option>
            {models.map((m) => (
              <option key={m.id} value={m.id}>
                {modelDisplayName(m.id)}
              </option>
            ))}
          </select>
        )}
        <button
          onClick={onRun}
          disabled={single.isPending || compare.isPending}
          className="flex items-center gap-2 rounded-md bg-gradient-to-r from-cyan-500 to-violet-600 px-4 py-2 text-sm font-medium text-white hover:opacity-90 disabled:opacity-50"
        >
          {(single.isPending || compare.isPending) ? (
            <Loader2 className="h-4 w-4 animate-spin" />
          ) : compareMode ? (
            <GitCompare className="h-4 w-4" />
          ) : (
            <Brain className="h-4 w-4" />
          )}
          {compareMode ? "הרץ הכל" : "הערך"}
        </button>
      </div>

      {!compareMode && single.data && (
        <div className="mt-4 rounded-md border border-cyan-500/30 bg-cyan-500/10 p-4">
          <div className="text-xs text-zinc-400">תחזית · {modelDisplayName(single.data.model)}</div>
          <div className="mt-1 text-3xl font-semibold text-white">
            {fmtCurrency(single.data.predicted_price)}
          </div>
        </div>
      )}

      {compareMode && compare.data && (
        <div className="mt-4 space-y-2">
          {compare.data.consensus_price != null && (
            <div className="rounded-md border border-violet-500/30 bg-violet-500/10 p-4">
              <div className="text-xs text-zinc-400">קונצנזוס (חציון)</div>
              <div className="text-3xl font-semibold text-white">{fmtCurrency(compare.data.consensus_price)}</div>
              <div className="mt-1 text-xs text-zinc-500">
                spread: {fmtCurrency(compare.data.spread_price)} · stddev: {fmtCurrency(compare.data.stddev_price)}
              </div>
            </div>
          )}
          <div className="grid gap-1.5 md:grid-cols-2">
            {compare.data.items.map((it) => (
              <div
                key={it.model}
                className="flex items-center justify-between rounded-md border border-white/10 bg-zinc-950/40 px-3 py-2 text-xs"
              >
                <span className="text-zinc-300">{modelDisplayName(it.model)}</span>
                {it.error ? (
                  <span className="text-rose-400">שגיאה</span>
                ) : (
                  <span className="font-medium text-white">{fmtCurrency(it.predicted_price)}</span>
                )}
              </div>
            ))}
          </div>
        </div>
      )}

      {(single.isError || compare.isError) && (
        <div className="mt-4 rounded-md border border-rose-500/30 bg-rose-500/10 p-3 text-xs text-rose-300">
          שגיאה. בדוק שה-prediction service רץ ושיש מודל champion.
        </div>
      )}
    </div>
  );
}
