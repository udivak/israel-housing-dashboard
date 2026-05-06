"use client";

import { Brain, Check } from "lucide-react";
import { useModels } from "@/hooks/useProperty";
import { modelDisplayName } from "@/lib/model-utils";

export function ModelsList() {
  const { data: models = [], isLoading } = useModels();

  return (
    <div dir="rtl" className="rounded-xl border border-white/10 bg-zinc-900/60 p-4 backdrop-blur">
      <div className="mb-3 flex items-center gap-2">
        <Brain className="h-4 w-4 text-cyan-400" />
        <h3 className="text-sm font-semibold text-white">מודלים מאומנים</h3>
        <span className="text-xs text-zinc-500">{models.length} זמינים</span>
      </div>
      {isLoading ? (
        <div className="text-xs text-zinc-500">טוען…</div>
      ) : (
        <div className="space-y-2">
          {models.map((m) => {
            const metrics = (m.metrics ?? {}) as Record<string, unknown>;
            const mape = typeof metrics.mape === "number" ? metrics.mape : null;
            const r2 = typeof metrics.r2 === "number" ? metrics.r2 : null;
            return (
              <div
                key={m.id}
                className="flex items-center justify-between gap-3 rounded-md border border-white/10 bg-zinc-950/40 px-3 py-2 text-xs"
              >
                <div className="min-w-0 flex-1">
                  <div className="font-medium text-white">{modelDisplayName(m.id)}</div>
                  <div className="text-[11px] text-zinc-500">
                    {m.n_features != null && <span>{m.n_features} features</span>}
                    {mape != null && <span> · MAPE {(mape * 100).toFixed(2)}%</span>}
                    {r2 != null && <span> · R² {r2.toFixed(3)}</span>}
                  </div>
                </div>
                <Check className="h-4 w-4 text-emerald-400" />
              </div>
            );
          })}
        </div>
      )}
    </div>
  );
}
