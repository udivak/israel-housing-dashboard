"use client";

import { useMemo, useState } from "react";
import { Brain, Loader2, GitCompare } from "lucide-react";
import { useMutation } from "@tanstack/react-query";
import { fetchApi } from "@/lib/api/client";
import { API_ENDPOINTS } from "@/lib/api/endpoints";
import { useModels } from "@/hooks/useProperty";
import type { PropertyDoc } from "@/hooks/useProperty";

interface PredictResponse {
  predicted_log_price: number;
  predicted_price: number;
  model: string;
}

interface CompareItem {
  model: string;
  predicted_log_price?: number | null;
  predicted_price?: number | null;
  error?: string | null;
}

interface CompareResponse {
  items: CompareItem[];
  consensus_price?: number | null;
  spread_price?: number | null;
  stddev_price?: number | null;
}

const NON_FEATURE_KEYS = new Set([
  "id",
  "_id",
  "geometry",
  "price",
  "price_per_sqm",
  "log_price",
  "log_price_per_sqm",
  "log_real_price",
  "real_price",
  "real_price_per_sqm",
  "real_price_factor",
  "annual_change",
  "mom_change",
  "price_index",
  "source_name",
  "transaction_date",
  "city",
  "neighborhood",
  "street",
  "project_name",
  "h3_r5",
  "h3_r7",
  "h3_r8",
]);

function buildFeatureDict(p: PropertyDoc): Record<string, unknown> {
  const out: Record<string, unknown> = {};
  for (const [k, v] of Object.entries(p)) {
    if (NON_FEATURE_KEYS.has(k)) continue;
    if (v === null || v === undefined) continue;
    out[k] = v;
  }
  return out;
}

function fmtCurrency(n: number | null | undefined): string {
  if (n == null || !Number.isFinite(n)) return "—";
  return `₪${n.toLocaleString("he-IL", { maximumFractionDigits: 0 })}`;
}

export function PredictionPanel({ property }: { property: PropertyDoc }) {
  const { data: models = [] } = useModels();
  const [selectedModel, setSelectedModel] = useState<string>("");
  const [compareMode, setCompareMode] = useState(false);

  const features = useMemo(() => buildFeatureDict(property), [property]);

  const single = useMutation<PredictResponse>({
    mutationFn: () =>
      fetchApi(`${API_ENDPOINTS.PREDICT}${selectedModel ? `?model=${encodeURIComponent(selectedModel)}` : ""}`, {
        method: "POST",
        body: JSON.stringify({ features }),
      }),
  });

  const compare = useMutation<CompareResponse>({
    mutationFn: () =>
      fetchApi(API_ENDPOINTS.PREDICT_COMPARE, {
        method: "POST",
        body: JSON.stringify({ features }),
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
        <h3 className="text-sm font-semibold text-white">ניבוי מחיר</h3>
      </div>

      <div className="mb-3 flex flex-col gap-2">
        <div className="flex items-center gap-2">
          <label className="flex items-center gap-2 text-xs text-zinc-400">
            <input
              type="checkbox"
              checked={compareMode}
              onChange={(e) => setCompareMode(e.target.checked)}
              className="h-3.5 w-3.5 accent-cyan-500"
            />
            השוואת מודלים
          </label>
        </div>

        {!compareMode && (
          <select
            value={selectedModel}
            onChange={(e) => setSelectedModel(e.target.value)}
            className="rounded-md border border-white/10 bg-zinc-950/60 px-2.5 py-1.5 text-sm text-white"
          >
            <option value="">Champion (ברירת מחדל)</option>
            {models.map((m) => (
              <option key={m.id} value={m.id}>
                {m.id}
              </option>
            ))}
          </select>
        )}

        <button
          onClick={onRun}
          disabled={single.isPending || compare.isPending}
          className="flex items-center justify-center gap-2 rounded-md bg-gradient-to-r from-cyan-500 to-violet-600 px-3 py-2 text-sm font-medium text-white hover:opacity-90 disabled:opacity-50"
        >
          {(single.isPending || compare.isPending) ? (
            <Loader2 className="h-4 w-4 animate-spin" />
          ) : compareMode ? (
            <GitCompare className="h-4 w-4" />
          ) : (
            <Brain className="h-4 w-4" />
          )}
          {compareMode ? "הרץ את כל המודלים" : "הערך"}
        </button>
      </div>

      {!compareMode && single.data && (
        <div className="rounded-md border border-cyan-500/30 bg-cyan-500/10 p-3">
          <div className="text-xs text-zinc-400">תחזית · {single.data.model}</div>
          <div className="mt-1 text-2xl font-semibold text-white">{fmtCurrency(single.data.predicted_price)}</div>
          {property.price != null && (
            <div className="mt-1 text-xs text-zinc-400">
              לעומת מחיר עסקה: {fmtCurrency(property.price)} (
              <span className={single.data.predicted_price > property.price ? "text-emerald-400" : "text-rose-400"}>
                {(((single.data.predicted_price - property.price) / property.price) * 100).toFixed(1)}%
              </span>
              )
            </div>
          )}
        </div>
      )}

      {compareMode && compare.data && (
        <div className="space-y-2">
          {compare.data.consensus_price != null && (
            <div className="rounded-md border border-violet-500/30 bg-violet-500/10 p-3">
              <div className="text-xs text-zinc-400">קונצנזוס (חציון)</div>
              <div className="text-2xl font-semibold text-white">{fmtCurrency(compare.data.consensus_price)}</div>
              <div className="text-xs text-zinc-500">
                spread: {fmtCurrency(compare.data.spread_price)} · stddev: {fmtCurrency(compare.data.stddev_price)}
              </div>
            </div>
          )}
          <div className="space-y-1">
            {compare.data.items.map((it) => (
              <div
                key={it.model}
                className="flex items-center justify-between rounded-md border border-white/10 bg-zinc-950/40 px-3 py-2 text-xs"
              >
                <span className="text-zinc-300">{it.model}</span>
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
        <div className="mt-2 rounded-md border border-rose-500/30 bg-rose-500/10 p-2 text-xs text-rose-300">
          שגיאה בניבוי. ודא שה-prediction service רץ ושיש champion model.
        </div>
      )}
    </div>
  );
}
