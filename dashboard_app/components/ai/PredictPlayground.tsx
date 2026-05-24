"use client";

import { useState } from "react";
import { Brain, Loader2, GitCompare, MapPin, Search } from "lucide-react";
import { useMutation } from "@tanstack/react-query";
import { fetchApi } from "@/lib/api/client";
import { API_ENDPOINTS } from "@/lib/api/endpoints";
import { useModels } from "@/hooks/useProperty";
import { modelDisplayName } from "@/lib/model-utils";
import { searchPlaces, formatAddress } from "@/lib/geocoding";
import { Card } from "@/components/ui/card";
import { Section } from "@/components/ui/Section";
import { GradientText } from "@/components/ui/GradientText";
import { Pill } from "@/components/ui/Pill";
import { formatCurrency } from "@/lib/format";

interface FieldDef {
  key: string;
  label: string;
  type?: "number" | "text";
  step?: string;
  defaultValue?: string;
  hint?: string;
}

const FIELDS: FieldDef[] = [
  { key: "area_sqm", label: "Area (m²)", type: "number", defaultValue: "100" },
  { key: "rooms", label: "Rooms", type: "number", step: "0.5", defaultValue: "4" },
  { key: "floor", label: "Floor", type: "number", defaultValue: "3" },
  { key: "building_floors", label: "Building floors", type: "number", defaultValue: "8" },
  { key: "year_built", label: "Year built", type: "number", defaultValue: "2010" },
  { key: "property_age", label: "Property age (yr)", type: "number", defaultValue: "15" },
  { key: "year", label: "Transaction year", type: "number", defaultValue: "2024" },
  { key: "month", label: "Month (1–12)", type: "number", defaultValue: "6" },
  { key: "quarter", label: "Quarter (1–4)", type: "number", defaultValue: "2" },
  { key: "log_area_sqm", label: "log(area)", type: "number", step: "0.001", defaultValue: "4.605", hint: "= ln(area_sqm)" },
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

export function PredictPlayground() {
  const { data: models = [] } = useModels();
  const [values, setValues] = useState<Record<string, string>>(() =>
    Object.fromEntries(FIELDS.map((f) => [f.key, f.defaultValue ?? ""])),
  );
  const [selectedModel, setSelectedModel] = useState<string>("");
  const [compareMode, setCompareMode] = useState(false);

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
        setGeocodeError("Address not found");
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
      setGeocodeError("Geocoding error");
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
      fetchApi(
        `${API_ENDPOINTS.PREDICT}${selectedModel ? `?model=${encodeURIComponent(selectedModel)}` : ""}`,
        {
          method: "POST",
          body: JSON.stringify({ features: buildFeatures() }),
        },
      ),
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
    <Section
      title="Playground"
      subtitle="Tune features by hand, swap models, and stress-test the ensemble."
      eyebrow="Predict"
    >
      <Card className="space-y-5 p-5">
        <div>
          <div className="mb-2 flex items-center gap-2 text-xs font-medium text-[--fg-muted]">
            <MapPin className="h-3.5 w-3.5 text-[--accent-1]" />
            Property address
          </div>
          <div className="flex flex-col gap-2 sm:flex-row">
            <input
              type="text"
              value={address}
              onChange={(e) => setAddress(e.target.value)}
              onKeyDown={(e) => e.key === "Enter" && handleGeocode()}
              placeholder="e.g., Rothschild 22, Tel Aviv"
              className="flex-1 rounded-md border border-[--border] bg-[--bg] px-2.5 py-1.5 text-sm text-[--fg] placeholder:text-[--fg-dim] focus:border-[--accent-1]/50 focus:outline-none"
            />
            <button
              onClick={handleGeocode}
              disabled={geocoding || !address.trim()}
              className="flex items-center justify-center gap-2 rounded-md border border-[--border] bg-[--bg] px-3 py-1.5 text-sm text-[--fg] hover:border-[--border-strong] disabled:opacity-50"
            >
              {geocoding ? <Loader2 className="h-3.5 w-3.5 animate-spin" /> : <Search className="h-3.5 w-3.5" />}
              Search
            </button>
          </div>
          {resolved && (
            <div className="mt-2 flex flex-wrap items-center gap-2 text-xs">
              <Pill tone="up">
                <MapPin className="h-3 w-3" /> {resolved.label}
              </Pill>
              <span className="tabular text-[--fg-dim]">
                ({resolved.lat.toFixed(4)}, {resolved.lon.toFixed(4)})
              </span>
            </div>
          )}
          {geocodeError && (
            <div className="mt-2 text-xs text-[--down]">{geocodeError}</div>
          )}
        </div>

        <div className="grid gap-3 md:grid-cols-2 lg:grid-cols-5">
          {FIELDS.map((f) => (
            <label key={f.key} className="flex flex-col gap-1 text-xs">
              <span className="text-[--fg-muted]">{f.label}</span>
              <input
                type={f.type ?? "text"}
                step={f.step}
                value={values[f.key] ?? ""}
                onChange={(e) => setValues({ ...values, [f.key]: e.target.value })}
                className="tabular w-full rounded-md border border-[--border] bg-[--bg] px-2.5 py-1.5 text-sm text-[--fg] focus:border-[--accent-1]/50 focus:outline-none"
              />
              {f.hint && <span className="text-[10px] text-[--fg-dim]">{f.hint}</span>}
            </label>
          ))}
        </div>

        <div className="flex flex-wrap items-center gap-3">
          <label className="flex items-center gap-2 text-xs text-[--fg-muted]">
            <input
              type="checkbox"
              checked={compareMode}
              onChange={(e) => setCompareMode(e.target.checked)}
              className="h-3.5 w-3.5 accent-[--accent-1]"
            />
            Compare all models
          </label>
          {!compareMode && (
            <select
              value={selectedModel}
              onChange={(e) => setSelectedModel(e.target.value)}
              className="rounded-md border border-[--border] bg-[--bg] px-2.5 py-1.5 text-sm text-[--fg]"
            >
              <option value="">Champion (default)</option>
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
            className="flex items-center gap-2 rounded-md bg-[--accent-1] px-4 py-2 text-sm font-semibold text-[--bg] hover:opacity-90 disabled:opacity-60"
          >
            {single.isPending || compare.isPending ? (
              <Loader2 className="h-4 w-4 animate-spin" />
            ) : compareMode ? (
              <GitCompare className="h-4 w-4" />
            ) : (
              <Brain className="h-4 w-4" />
            )}
            {compareMode ? "Run all" : "Predict"}
          </button>
        </div>

        {!compareMode && single.data && (
          <div className="rounded-lg border border-[--accent-1]/30 bg-[--bg] p-4">
            <div className="text-xs uppercase tracking-wide text-[--fg-dim]">
              Predicted · {modelDisplayName(single.data.model)}
            </div>
            <div className="tabular mt-1 text-3xl font-semibold">
              <GradientText>{formatCurrency(single.data.predicted_price)}</GradientText>
            </div>
          </div>
        )}

        {compareMode && compare.data && (
          <div className="space-y-2">
            {compare.data.consensus_price != null && (
              <div className="rounded-lg border border-[--accent-2]/30 bg-[--bg] p-4">
                <div className="text-xs uppercase tracking-wide text-[--fg-dim]">
                  Consensus (median)
                </div>
                <div className="tabular mt-1 text-3xl font-semibold">
                  <GradientText>{formatCurrency(compare.data.consensus_price)}</GradientText>
                </div>
                <div className="tabular mt-1 text-xs text-[--fg-dim]">
                  spread {formatCurrency(compare.data.spread_price)} · stddev{" "}
                  {formatCurrency(compare.data.stddev_price)}
                </div>
              </div>
            )}
            <div className="grid gap-1.5 md:grid-cols-2">
              {compare.data.items.map((it) => (
                <div
                  key={it.model}
                  className="flex items-center justify-between rounded-md border border-[--border] bg-[--bg] px-3 py-2 text-xs"
                >
                  <span className="text-[--fg-muted]">{modelDisplayName(it.model)}</span>
                  {it.error ? (
                    <Pill tone="down">error</Pill>
                  ) : (
                    <span className="tabular font-medium text-[--fg]">
                      {formatCurrency(it.predicted_price)}
                    </span>
                  )}
                </div>
              ))}
            </div>
          </div>
        )}

        {(single.isError || compare.isError) && (
          <div className="rounded-md border border-[--down]/30 bg-[--down]/10 p-3 text-xs text-[--down]">
            Prediction error. Check that prediction_service is running and a champion model is set.
          </div>
        )}
      </Card>
    </Section>
  );
}
