"use client";

import { useState } from "react";
import { Loader2, MapPin, Sparkles } from "lucide-react";
import { useMutation } from "@tanstack/react-query";
import { Section } from "@/components/ui/Section";
import { GradientText } from "@/components/ui/GradientText";
import { Pill } from "@/components/ui/Pill";
import { fetchApi } from "@/lib/api/client";
import { API_ENDPOINTS } from "@/lib/api/endpoints";
import { searchPlaces } from "@/lib/geocoding";
import { modelDisplayName } from "@/lib/model-utils";
import { useLocale } from "@/lib/i18n/LocaleProvider";
import { formatCurrency } from "@/lib/format";

interface PredictResponse {
  predicted_log_price: number;
  predicted_price: number;
  model: string;
}

const DEFAULTS = {
  area_sqm: "100",
  rooms: "4",
  floor: "3",
};

export function InlinePredict() {
  const { t } = useLocale();
  const example = t("home.predict.example");
  const [address, setAddress] = useState("");
  const [rooms, setRooms] = useState(DEFAULTS.rooms);
  const [area, setArea] = useState(DEFAULTS.area_sqm);
  const [floor, setFloor] = useState(DEFAULTS.floor);
  const [geoError, setGeoError] = useState<string | null>(null);

  const predict = useMutation<PredictResponse, Error, void>({
    mutationFn: async () => {
      setGeoError(null);
      const places = address.trim() ? await searchPlaces(address, { limit: 1 }) : [];
      const place = places[0];
      if (address.trim() && !place) {
        setGeoError(t("home.predict.geoFail", { address }));
        throw new Error("geocode failed");
      }
      const features: Record<string, number | string> = {
        area_sqm: Number(area),
        rooms: Number(rooms),
        floor: Number(floor),
        log_area_sqm: Math.log(Number(area) || 1),
        year: new Date().getFullYear(),
        month: new Date().getMonth() + 1,
        quarter: Math.floor(new Date().getMonth() / 3) + 1,
      };
      if (place) {
        const [lon, lat] = place.geometry.coordinates;
        const props = place.properties as Record<string, string | undefined>;
        features.lat = lat;
        features.lon = lon;
        if (props.city) features.city = props.city;
        if (props.street) features.street = props.street;
      }
      return fetchApi<PredictResponse>(API_ENDPOINTS.PREDICT, {
        method: "POST",
        body: JSON.stringify({ features }),
      });
    },
  });

  return (
    <Section
      title={t("home.predict.title")}
      subtitle={t("home.predict.subtitle")}
      className="border-b border-[var(--border)] px-6 py-12"
    >
      <div id="predict" className="rounded-xl border border-[var(--border)] bg-[var(--bg-elev)] p-5">
        <form
          onSubmit={(e) => {
            e.preventDefault();
            predict.mutate();
          }}
          className="grid gap-3 sm:grid-cols-[2fr_repeat(3,1fr)_auto]"
        >
          <label className="flex flex-col gap-1 text-xs">
            <span className="text-[var(--fg-dim)]">{t("home.predict.address")}</span>
            <div className="flex items-center gap-2 rounded-md border border-[var(--border)] bg-[var(--bg)] px-2.5 py-1.5 focus-within:border-[var(--accent-1)]/50">
              <MapPin className="h-3.5 w-3.5 text-[var(--fg-dim)]" />
              <input
                value={address}
                onChange={(e) => setAddress(e.target.value)}
                placeholder={example}
                className="flex-1 bg-transparent text-sm text-[var(--fg)] placeholder:text-[var(--fg-dim)] focus:outline-none"
              />
            </div>
          </label>
          <NumField label={t("property.rooms")} value={rooms} onChange={setRooms} step="0.5" />
          <NumField label={t("unit.sqm")} value={area} onChange={setArea} />
          <NumField label={t("pg.field.floor")} value={floor} onChange={setFloor} />
          <div className="flex flex-col justify-end">
            <button
              type="submit"
              disabled={predict.isPending}
              className="flex items-center justify-center gap-2 rounded-md bg-[var(--accent-1)] px-4 py-2 text-sm font-semibold text-[var(--bg)] hover:opacity-90 disabled:opacity-60"
            >
              {predict.isPending ? (
                <Loader2 className="h-4 w-4 animate-spin" />
              ) : (
                <Sparkles className="h-4 w-4" />
              )}
              {t("home.predict.cta")}
            </button>
          </div>
        </form>

        <div className="mt-4 flex flex-wrap items-center gap-2 text-xs">
          {!predict.data && !predict.isPending && (
            <button
              type="button"
              onClick={() => setAddress(example)}
              className="rounded-full border border-[var(--border)] bg-[var(--bg)] px-3 py-1 text-[var(--fg-muted)] hover:border-[var(--border-strong)]"
            >
              {t("home.predict.try", { example })}
            </button>
          )}
          {geoError && <Pill tone="down">{geoError}</Pill>}
        </div>

        {predict.data && (
          <div className="mt-5 rounded-lg border border-[var(--accent-1)]/30 bg-[var(--bg-elev)] p-5">
            <div className="text-xs uppercase tracking-wide text-[var(--fg-dim)]">
              {t("home.predict.resultLabel", { model: modelDisplayName(predict.data.model) })}
            </div>
            <div className="tabular mt-1 text-4xl font-semibold">
              <GradientText>{formatCurrency(predict.data.predicted_price)}</GradientText>
            </div>
            <div className="mt-1 text-xs text-[var(--fg-muted)]">
              {t("home.predict.resultHint", {
                value: predict.data.predicted_log_price.toFixed(3),
              })}
            </div>
          </div>
        )}

        {predict.isError && !geoError && (
          <div className="mt-4 rounded-md border border-[var(--down)]/30 bg-[var(--down)]/10 p-3 text-xs text-[var(--down)]">
            {t("home.predict.error")}
          </div>
        )}
      </div>
    </Section>
  );
}

function NumField({
  label,
  value,
  onChange,
  step,
}: {
  label: string;
  value: string;
  onChange: (v: string) => void;
  step?: string;
}) {
  return (
    <label className="flex flex-col gap-1 text-xs">
      <span className="text-[var(--fg-dim)]">{label}</span>
      <input
        type="number"
        value={value}
        step={step}
        onChange={(e) => onChange(e.target.value)}
        className="tabular rounded-md border border-[var(--border)] bg-[var(--bg)] px-2.5 py-1.5 text-sm text-[var(--fg)] focus:border-[var(--accent-1)]/50 focus:outline-none"
      />
    </label>
  );
}
