"use client";

import { useMemo, useState } from "react";
import { Brain, Loader2, GitCompare, ChevronDown, ChevronUp } from "lucide-react";
import { useMutation } from "@tanstack/react-query";
import { fetchApi } from "@/lib/api/client";
import { API_ENDPOINTS } from "@/lib/api/endpoints";
import { useModels } from "@/hooks/useProperty";
import type { PropertyDoc } from "@/hooks/useProperty";
import { modelDisplayName } from "@/lib/model-utils";
import { Card } from "@/components/ui/card";
import { GradientText } from "@/components/ui/GradientText";
import { Pill } from "@/components/ui/Pill";
import { formatCurrency } from "@/lib/format";

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

export function PredictionPanel({ property }: { property: PropertyDoc }) {
  const { data: models = [] } = useModels();
  const [selectedModel, setSelectedModel] = useState<string>("");
  const [showAll, setShowAll] = useState(false);

  const features = useMemo(() => buildFeatureDict(property), [property]);

  const single = useMutation<PredictResponse>({
    mutationFn: () =>
      fetchApi(
        `${API_ENDPOINTS.PREDICT}${selectedModel ? `?model=${encodeURIComponent(selectedModel)}` : ""}`,
        {
          method: "POST",
          body: JSON.stringify({ features }),
        },
      ),
  });

  const compare = useMutation<CompareResponse>({
    mutationFn: () =>
      fetchApi(API_ENDPOINTS.PREDICT_COMPARE, {
        method: "POST",
        body: JSON.stringify({ features }),
      }),
  });

  const onPredict = () => single.mutate();
  const onCompare = () => {
    setShowAll(true);
    compare.mutate();
  };

  const predicted = single.data?.predicted_price;
  const listed = property.price ?? null;
  const delta =
    predicted != null && listed != null && listed > 0
      ? ((predicted - listed) / listed) * 100
      : null;

  // confidence band proxy: spread from compare, if available
  const spread = compare.data?.spread_price;
  const confidencePct =
    predicted != null && spread != null && predicted > 0
      ? Math.max(0, Math.min(100, 100 - (spread / predicted) * 100))
      : null;

  return (
    <Card className="space-y-4">
      <div className="flex items-center gap-2">
        <Brain className="h-4 w-4 text-[var(--accent-1)]" />
        <h3 className="text-sm font-semibold text-[var(--fg)]">Price prediction</h3>
      </div>

      <div className="flex flex-col gap-2">
        <select
          value={selectedModel}
          onChange={(e) => setSelectedModel(e.target.value)}
          className="rounded-md border border-[var(--border)] bg-[var(--bg)] px-2.5 py-1.5 text-sm text-[var(--fg)]"
        >
          <option value="">Champion (default)</option>
          {models.map((m) => (
            <option key={m.id} value={m.id}>
              {modelDisplayName(m.id)}
            </option>
          ))}
        </select>
        <button
          onClick={onPredict}
          disabled={single.isPending}
          className="flex items-center justify-center gap-2 rounded-md bg-[var(--accent-1)] px-3 py-2 text-sm font-semibold text-[var(--bg)] hover:opacity-90 disabled:opacity-60"
        >
          {single.isPending ? (
            <Loader2 className="h-4 w-4 animate-spin" />
          ) : (
            <Brain className="h-4 w-4" />
          )}
          Predict
        </button>
      </div>

      {single.data && (
        <div className="rounded-lg border border-[var(--border)] bg-[var(--bg)] p-4">
          <div className="grid grid-cols-2 gap-3 text-sm">
            <div>
              <div className="text-xs uppercase tracking-wide text-[var(--fg-dim)]">Predicted</div>
              <div className="tabular mt-1 text-xl font-semibold">
                <GradientText>{formatCurrency(predicted)}</GradientText>
              </div>
            </div>
            <div>
              <div className="text-xs uppercase tracking-wide text-[var(--fg-dim)]">Listed</div>
              <div className="tabular mt-1 text-xl font-semibold text-[var(--fg)]">
                {formatCurrency(listed)}
              </div>
            </div>
          </div>
          {delta != null && (
            <div className="mt-2 text-xs">
              <Pill tone={delta >= 0 ? "up" : "down"}>
                {delta >= 0 ? "+" : ""}
                {delta.toFixed(1)}% vs listed
              </Pill>
            </div>
          )}
          {confidencePct != null && (
            <div className="mt-3">
              <div className="mb-1 flex items-center justify-between text-[11px] text-[var(--fg-dim)]">
                <span>Model confidence (spread)</span>
                <span className="tabular">{confidencePct.toFixed(0)}%</span>
              </div>
              <div className="h-1.5 overflow-hidden rounded-full bg-[var(--bg-elev-2)]">
                <div
                  className="h-full bg-[image:linear-gradient(90deg,var(--accent-1),var(--accent-2))]"
                  style={{ width: `${confidencePct}%` }}
                />
              </div>
            </div>
          )}
          <div className="mt-3 text-[11px] text-[var(--fg-dim)]">
            Model: {modelDisplayName(single.data.model)}
          </div>
        </div>
      )}

      <div className="border-t border-[var(--border)] pt-3">
        <button
          onClick={() => (showAll ? setShowAll(false) : onCompare())}
          disabled={compare.isPending}
          className="flex w-full items-center justify-between rounded-md border border-[var(--border)] bg-[var(--bg)] px-3 py-2 text-xs text-[var(--fg-muted)] hover:border-[var(--border-strong)] disabled:opacity-60"
        >
          <span className="flex items-center gap-2">
            <GitCompare className="h-3.5 w-3.5" />
            Compare all models
          </span>
          {compare.isPending ? (
            <Loader2 className="h-3.5 w-3.5 animate-spin" />
          ) : showAll ? (
            <ChevronUp className="h-3.5 w-3.5" />
          ) : (
            <ChevronDown className="h-3.5 w-3.5" />
          )}
        </button>

        {showAll && compare.data && (
          <div className="mt-3 space-y-2">
            {compare.data.consensus_price != null && (
              <div className="rounded-md border border-[var(--accent-2)]/30 bg-[var(--bg)] p-3">
                <div className="text-[11px] uppercase tracking-wide text-[var(--fg-dim)]">
                  Consensus (median)
                </div>
                <div className="tabular text-lg font-semibold text-[var(--fg)]">
                  {formatCurrency(compare.data.consensus_price)}
                </div>
                <div className="tabular mt-0.5 text-[11px] text-[var(--fg-dim)]">
                  spread {formatCurrency(compare.data.spread_price)} · stddev{" "}
                  {formatCurrency(compare.data.stddev_price)}
                </div>
              </div>
            )}
            <div className="space-y-1">
              {compare.data.items.map((it) => (
                <div
                  key={it.model}
                  className="flex items-center justify-between rounded-md border border-[var(--border)] bg-[var(--bg)] px-3 py-1.5 text-xs"
                >
                  <span className="text-[var(--fg-muted)]">{modelDisplayName(it.model)}</span>
                  {it.error ? (
                    <Pill tone="down">error</Pill>
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
      </div>

      {(single.isError || compare.isError) && (
        <div className="rounded-md border border-[var(--down)]/30 bg-[var(--down)]/10 p-2 text-xs text-[var(--down)]">
          Prediction error. Verify prediction_service is running and a champion model is set.
        </div>
      )}
    </Card>
  );
}
