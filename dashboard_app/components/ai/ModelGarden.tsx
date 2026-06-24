"use client";

import { Brain } from "lucide-react";
import { useModels } from "@/hooks/useProperty";
import { Pill } from "@/components/ui/Pill";
import { modelDisplayName } from "@/lib/model-utils";
import { useLocale } from "@/lib/i18n/LocaleProvider";
import { cn } from "@/lib/utils";

interface ModelGardenProps {
  /** When true, only render a 4-up grid even if more models exist. */
  compact?: boolean;
}

function readMetric(m: Record<string, unknown> | null | undefined, key: string): number | null {
  if (!m) return null;
  const v = m[key];
  return typeof v === "number" && Number.isFinite(v) ? v : null;
}

export function ModelGarden({ compact = false }: ModelGardenProps) {
  const { data: models = [], isLoading } = useModels();
  const { t } = useLocale();

  if (isLoading) {
    return (
      <div className="grid gap-3 sm:grid-cols-2 lg:grid-cols-4">
        {Array.from({ length: 8 }).map((_, i) => (
          <div
            key={i}
            className="h-24 animate-pulse rounded-xl border border-[var(--border)] bg-[var(--bg-elev)]"
          />
        ))}
      </div>
    );
  }

  if (!models.length) {
    return (
      <div className="rounded-xl border border-[var(--border)] bg-[var(--bg-elev)] p-6 text-sm text-[var(--fg-muted)]">
        {t("models.empty")}
      </div>
    );
  }

  const ranked = [...models].sort((a, b) => {
    const ar = readMetric(a.metrics, "r2") ?? -Infinity;
    const br = readMetric(b.metrics, "r2") ?? -Infinity;
    return br - ar;
  });
  const list = compact ? ranked.slice(0, 4) : ranked;
  const champion = ranked[0];

  return (
    <div className="grid gap-3 sm:grid-cols-2 lg:grid-cols-4">
      {list.map((m) => {
        const isBest = m.id === champion?.id;
        const r2 = readMetric(m.metrics, "r2");
        const mae = readMetric(m.metrics, "mae");
        const mape = readMetric(m.metrics, "mape");

        return (
          <div
            key={m.id}
            className={cn(
              "rounded-xl border border-[var(--border)] bg-[var(--bg-elev)] p-4 transition-colors hover:border-[var(--border-strong)]",
              !isBest && "opacity-70 hover:opacity-100",
            )}
          >
            <div className="flex items-center justify-between gap-2">
              <div className="flex items-center gap-2 text-xs uppercase tracking-wide text-[var(--fg-dim)]">
                <Brain className="h-3.5 w-3.5" />
                {t("models.modelTag")}
              </div>
              {isBest && <Pill tone="accent">{t("models.best")}</Pill>}
            </div>
            <div className="mt-2 truncate text-sm font-semibold text-[var(--fg)]">
              {modelDisplayName(m.id)}
            </div>
            <div className="tabular mt-3 grid grid-cols-2 gap-2 text-xs">
              <div>
                <div className="text-[var(--fg-dim)]">{t("metric.r2")}</div>
                <div className="font-medium text-[var(--fg)]">{r2 != null ? r2.toFixed(3) : "—"}</div>
              </div>
              <div>
                <div className="text-[var(--fg-dim)]">{mae != null ? t("metric.mae") : t("metric.mape")}</div>
                <div className="font-medium text-[var(--fg)]">
                  {mae != null
                    ? mae.toLocaleString("en-US", { maximumFractionDigits: 0 })
                    : mape != null
                      ? `${(mape * 100).toFixed(2)}%`
                      : "—"}
                </div>
              </div>
            </div>
          </div>
        );
      })}
    </div>
  );
}
