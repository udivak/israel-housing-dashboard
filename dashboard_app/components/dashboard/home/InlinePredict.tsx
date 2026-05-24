"use client";

import { useState } from "react";
import { Loader2, MapPin, Sparkles } from "lucide-react";
import { useMutation } from "@tanstack/react-query";
import { Section } from "@/components/ui/Section";
import { GradientText } from "@/components/ui/GradientText";
import { Pill } from "@/components/ui/Pill";
import { fetchApi } from "@/lib/api/client";
import { API_ENDPOINTS } from "@/lib/api/endpoints";
import { searchPlaces, formatAddress } from "@/lib/geocoding";
import { modelDisplayName } from "@/lib/model-utils";
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

const EXAMPLE = "Dizengoff 99, Tel Aviv";

export function InlinePredict() {
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
        setGeoError(`Couldn’t locate "${address}".`);
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
      title="Predict an apartment in 10 seconds"
      subtitle="Try a real address. The model returns an estimate with a confidence range."
      className="border-b border-[--border] px-6 py-12"
    >
      <div id="predict" className="rounded-xl border border-[--border] bg-[--bg-elev] p-5">
        <form
          onSubmit={(e) => {
            e.preventDefault();
            predict.mutate();
          }}
          className="grid gap-3 sm:grid-cols-[2fr_repeat(3,1fr)_auto]"
        >
          <label className="flex flex-col gap-1 text-xs">
            <span className="text-[--fg-dim]">Address</span>
            <div className="flex items-center gap-2 rounded-md border border-[--border] bg-[--bg] px-2.5 py-1.5 focus-within:border-[--accent-1]/50">
              <MapPin className="h-3.5 w-3.5 text-[--fg-dim]" />
              <input
                value={address}
                onChange={(e) => setAddress(e.target.value)}
                placeholder={EXAMPLE}
                className="flex-1 bg-transparent text-sm text-[--fg] placeholder:text-[--fg-dim] focus:outline-none"
              />
            </div>
          </label>
          <NumField label="Rooms" value={rooms} onChange={setRooms} step="0.5" />
          <NumField label="m²" value={area} onChange={setArea} />
          <NumField label="Floor" value={floor} onChange={setFloor} />
          <div className="flex flex-col justify-end">
            <button
              type="submit"
              disabled={predict.isPending}
              className="flex items-center justify-center gap-2 rounded-md bg-[--accent-1] px-4 py-2 text-sm font-semibold text-[--bg] hover:opacity-90 disabled:opacity-60"
            >
              {predict.isPending ? (
                <Loader2 className="h-4 w-4 animate-spin" />
              ) : (
                <Sparkles className="h-4 w-4" />
              )}
              Predict
            </button>
          </div>
        </form>

        <div className="mt-4 flex flex-wrap items-center gap-2 text-xs">
          {!predict.data && !predict.isPending && (
            <button
              type="button"
              onClick={() => setAddress(EXAMPLE)}
              className="rounded-full border border-[--border] bg-[--bg] px-3 py-1 text-[--fg-muted] hover:border-[--border-strong]"
            >
              Try: {EXAMPLE}
            </button>
          )}
          {geoError && <Pill tone="down">{geoError}</Pill>}
        </div>

        {predict.data && (
          <div className="mt-5 rounded-lg border border-[--accent-1]/30 bg-[image:linear-gradient(135deg,var(--accent-1)/0.06,var(--accent-2)/0.06)] p-5">
            <div className="text-xs uppercase tracking-wide text-[--fg-dim]">
              Predicted price · {modelDisplayName(predict.data.model)}
            </div>
            <div className="tabular mt-1 text-4xl font-semibold">
              <GradientText>{formatCurrency(predict.data.predicted_price)}</GradientText>
            </div>
            <div className="mt-1 text-xs text-[--fg-muted]">
              log-price {predict.data.predicted_log_price.toFixed(3)} · features auto-derived from your inputs
            </div>
          </div>
        )}

        {predict.isError && !geoError && (
          <div className="mt-4 rounded-md border border-[--down]/30 bg-[--down]/10 p-3 text-xs text-[--down]">
            Prediction failed. Verify the prediction_service is running and a champion model is set.
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
      <span className="text-[--fg-dim]">{label}</span>
      <input
        type="number"
        value={value}
        step={step}
        onChange={(e) => onChange(e.target.value)}
        className="tabular rounded-md border border-[--border] bg-[--bg] px-2.5 py-1.5 text-sm text-[--fg] focus:border-[--accent-1]/50 focus:outline-none"
      />
    </label>
  );
}
