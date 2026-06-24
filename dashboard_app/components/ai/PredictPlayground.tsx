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
import { useLocale } from "@/lib/i18n/LocaleProvider";
import type { Messages } from "@/lib/i18n/en";
import { formatCurrency } from "@/lib/format";

interface FieldDef {
  key: string;
  labelKey: keyof Messages;
  type?: "number" | "text";
  step?: string;
  defaultValue?: string;
  hintKey?: keyof Messages;
}

const FIELDS: FieldDef[] = [
  { key: "area_sqm", labelKey: "pg.field.area", type: "number", defaultValue: "100" },
  { key: "rooms", labelKey: "pg.field.rooms", type: "number", step: "0.5", defaultValue: "4" },
  { key: "floor", labelKey: "pg.field.floor", type: "number", defaultValue: "3" },
  { key: "building_floors", labelKey: "pg.field.buildingFloors", type: "number", defaultValue: "8" },
  { key: "year_built", labelKey: "pg.field.yearBuilt", type: "number", defaultValue: "2010" },
  { key: "property_age", labelKey: "pg.field.propertyAge", type: "number", defaultValue: "15" },
  { key: "year", labelKey: "pg.field.year", type: "number", defaultValue: "2024" },
  { key: "month", labelKey: "pg.field.month", type: "number", defaultValue: "6" },
  { key: "quarter", labelKey: "pg.field.quarter", type: "number", defaultValue: "2" },
  {
    key: "log_area_sqm",
    labelKey: "pg.field.logArea",
    type: "number",
    step: "0.001",
    defaultValue: "4.605",
    hintKey: "pg.field.logAreaHint",
  },
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
  const { t } = useLocale();
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
        setGeocodeError(t("pg.addressNotFound"));
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
      setGeocodeError(t("pg.geocodingError"));
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
    <Section title={t("pg.title")} subtitle={t("pg.subtitle")} eyebrow={t("pg.eyebrow")}>
      <Card className="space-y-5 p-5">
        <div>
          <div className="mb-2 flex items-center gap-2 text-xs font-medium text-[var(--fg-muted)]">
            <MapPin className="h-3.5 w-3.5 text-[var(--accent-1)]" />
            {t("pg.addressSection")}
          </div>
          <div className="flex flex-col gap-2 sm:flex-row">
            <input
              type="text"
              value={address}
              onChange={(e) => setAddress(e.target.value)}
              onKeyDown={(e) => e.key === "Enter" && handleGeocode()}
              placeholder={t("pg.addressPlaceholder")}
              className="flex-1 rounded-md border border-[var(--border)] bg-[var(--bg)] px-2.5 py-1.5 text-sm text-[var(--fg)] placeholder:text-[var(--fg-dim)] focus:border-[var(--accent-1)]/50 focus:outline-none"
            />
            <button
              onClick={handleGeocode}
              disabled={geocoding || !address.trim()}
              className="flex items-center justify-center gap-2 rounded-md border border-[var(--border)] bg-[var(--bg)] px-3 py-1.5 text-sm text-[var(--fg)] hover:border-[var(--border-strong)] disabled:opacity-50"
            >
              {geocoding ? <Loader2 className="h-3.5 w-3.5 animate-spin" /> : <Search className="h-3.5 w-3.5" />}
              {t("pg.search")}
            </button>
          </div>
          {resolved && (
            <div className="mt-2 flex flex-wrap items-center gap-2 text-xs">
              <Pill tone="up">
                <MapPin className="h-3 w-3" /> {resolved.label}
              </Pill>
              <span className="tabular text-[var(--fg-dim)]">
                ({resolved.lat.toFixed(4)}, {resolved.lon.toFixed(4)})
              </span>
            </div>
          )}
          {geocodeError && (
            <div className="mt-2 text-xs text-[var(--down)]">{geocodeError}</div>
          )}
        </div>

        <div className="grid gap-3 md:grid-cols-2 lg:grid-cols-5">
          {FIELDS.map((f) => (
            <label key={f.key} className="flex flex-col gap-1 text-xs">
              <span className="text-[var(--fg-muted)]">{t(f.labelKey)}</span>
              <input
                type={f.type ?? "text"}
                step={f.step}
                value={values[f.key] ?? ""}
                onChange={(e) => setValues({ ...values, [f.key]: e.target.value })}
                className="tabular w-full rounded-md border border-[var(--border)] bg-[var(--bg)] px-2.5 py-1.5 text-sm text-[var(--fg)] focus:border-[var(--accent-1)]/50 focus:outline-none"
              />
              {f.hintKey && <span className="text-[10px] text-[var(--fg-dim)]">{t(f.hintKey)}</span>}
            </label>
          ))}
        </div>

        <div className="flex flex-wrap items-center gap-3">
          <label className="flex items-center gap-2 text-xs text-[var(--fg-muted)]">
            <input
              type="checkbox"
              checked={compareMode}
              onChange={(e) => setCompareMode(e.target.checked)}
              className="h-3.5 w-3.5 accent-[var(--accent-1)]"
            />
            {t("pg.compareAll")}
          </label>
          {!compareMode && (
            <select
              value={selectedModel}
              onChange={(e) => setSelectedModel(e.target.value)}
              className="rounded-md border border-[var(--border)] bg-[var(--bg)] px-2.5 py-1.5 text-sm text-[var(--fg)]"
            >
              <option value="">{t("pg.champion")}</option>
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
            className="flex items-center gap-2 rounded-md bg-[var(--accent-1)] px-4 py-2 text-sm font-semibold text-[var(--bg)] hover:opacity-90 disabled:opacity-60"
          >
            {single.isPending || compare.isPending ? (
              <Loader2 className="h-4 w-4 animate-spin" />
            ) : compareMode ? (
              <GitCompare className="h-4 w-4" />
            ) : (
              <Brain className="h-4 w-4" />
            )}
            {compareMode ? t("pg.runAll") : t("pg.predict")}
          </button>
        </div>

        {!compareMode && single.data && (
          <div className="rounded-lg border border-[var(--accent-1)]/30 bg-[var(--bg)] p-4">
            <div className="text-xs uppercase tracking-wide text-[var(--fg-dim)]">
              {t("pg.predicted", { model: modelDisplayName(single.data.model) })}
            </div>
            <div className="tabular mt-1 text-3xl font-semibold">
              <GradientText>{formatCurrency(single.data.predicted_price)}</GradientText>
            </div>
          </div>
        )}

        {compareMode && compare.data && (
          <div className="space-y-2">
            {compare.data.consensus_price != null && (
              <div className="rounded-lg border border-[var(--accent-2)]/30 bg-[var(--bg)] p-4">
                <div className="text-xs uppercase tracking-wide text-[var(--fg-dim)]">
                  {t("pg.consensus")}
                </div>
                <div className="tabular mt-1 text-3xl font-semibold">
                  <GradientText>{formatCurrency(compare.data.consensus_price)}</GradientText>
                </div>
                <div className="tabular mt-1 text-xs text-[var(--fg-dim)]">
                  {t("pg.spreadStddev", {
                    spread: formatCurrency(compare.data.spread_price),
                    stddev: formatCurrency(compare.data.stddev_price),
                  })}
                </div>
              </div>
            )}
            <div className="grid gap-1.5 md:grid-cols-2">
              {compare.data.items.map((it) => (
                <div
                  key={it.model}
                  className="flex items-center justify-between rounded-md border border-[var(--border)] bg-[var(--bg)] px-3 py-2 text-xs"
                >
                  <span className="text-[var(--fg-muted)]">{modelDisplayName(it.model)}</span>
                  {it.error ? (
                    <Pill tone="down">{t("common.error")}</Pill>
                  ) : (
                    <span className="tabular font-medium text-[var(--fg)]">
                      {formatCurrency(it.predicted_price)}
                    </span>
                  )}
                </div>
              ))}
            </div>
          </div>
        )}

        {(single.isError || compare.isError) && (
          <div className="rounded-md border border-[var(--down)]/30 bg-[var(--down)]/10 p-3 text-xs text-[var(--down)]">
            {t("pg.predictionError")}
          </div>
        )}
      </Card>
    </Section>
  );
}
