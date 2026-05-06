"use client";

import { useQuery } from "@tanstack/react-query";
import { Activity, Brain, Database, RefreshCw, Trash2, ExternalLink } from "lucide-react";
import { fetchApi, getApiUrl } from "@/lib/api/client";
import { API_ENDPOINTS } from "@/lib/api/endpoints";
import { useFiltersStore } from "@/lib/store/filters";
import { useSourceBreakdown } from "@/hooks/useStats";
import { useModels } from "@/hooks/useProperty";
import { modelDisplayName } from "@/lib/model-utils";

interface HealthResp {
  status: string;
  service?: string;
}

function StatusDot({ ok }: { ok: boolean }) {
  return (
    <span
      className={`inline-block h-2.5 w-2.5 rounded-full ${ok ? "bg-emerald-400" : "bg-rose-400"}`}
    />
  );
}

function Section({ title, icon: Icon, children }: { title: string; icon: React.ComponentType<{ className?: string }>; children: React.ReactNode }) {
  return (
    <div className="rounded-xl border border-white/10 bg-zinc-900/60 p-4 backdrop-blur">
      <div className="mb-3 flex items-center gap-2">
        <Icon className="h-4 w-4 text-cyan-400" />
        <h3 className="text-sm font-semibold text-white">{title}</h3>
      </div>
      {children}
    </div>
  );
}

export function SettingsClient() {
  const apiUrl = getApiUrl();

  const health = useQuery<HealthResp>({
    queryKey: ["dashboard-health"],
    queryFn: () => fetchApi(API_ENDPOINTS.HEALTH),
    refetchInterval: 30_000,
  });

  const { data: sources = [] } = useSourceBreakdown();
  const { data: models = [] } = useModels();

  const filters = useFiltersStore((s) => s.filters);
  const resetFilters = useFiltersStore((s) => s.resetFilters);
  const filterCount = Object.values(filters).filter((v) => v !== undefined && v !== "").length;

  return (
    <div dir="rtl" className="flex flex-col gap-4">
      <div>
        <h1 className="text-2xl font-semibold text-white">הגדרות</h1>
        <p className="text-sm text-zinc-400">סטטוס מערכת, מודלים, מקורות נתונים.</p>
      </div>

      <Section title="בריאות מערכת" icon={Activity}>
        <div className="space-y-2 text-xs">
          <div className="flex items-center justify-between rounded-md border border-white/10 bg-zinc-950/40 px-3 py-2">
            <div className="flex items-center gap-2">
              <StatusDot ok={health.data?.status === "ok"} />
              <span className="text-white">dashboard_service</span>
            </div>
            <span className="text-zinc-500">{health.isLoading ? "בודק…" : health.data?.status ?? "DOWN"}</span>
          </div>
          <div className="rounded-md border border-white/10 bg-zinc-950/40 px-3 py-2 text-zinc-500">
            <div className="flex items-center justify-between">
              <span>API Base URL</span>
              <code className="text-zinc-300">{apiUrl}</code>
            </div>
          </div>
          <a
            href={`${apiUrl}/docs`}
            target="_blank"
            rel="noreferrer"
            className="flex items-center justify-between rounded-md border border-white/10 bg-zinc-950/40 px-3 py-2 hover:bg-white/5"
          >
            <span className="text-zinc-300">Swagger / API Docs</span>
            <ExternalLink className="h-3.5 w-3.5 text-zinc-500" />
          </a>
        </div>
      </Section>

      <Section title="מודלים" icon={Brain}>
        <div className="text-xs text-zinc-400">
          {models.length} מודלים מאומנים זמינים. החלפת champion דורשת:
        </div>
        <pre className="mt-2 overflow-x-auto rounded-md border border-white/10 bg-zinc-950/60 p-2 text-[11px] text-zinc-300">
{`make champion MODEL=moses/stacked_v2
# או דרך .env: CHAMPION_MODEL=moses/stacked_v2`}
        </pre>
        <div className="mt-3 flex flex-wrap gap-1.5">
          {models.map((m) => (
            <span
              key={m.id}
              className="rounded-md border border-white/10 bg-zinc-950/40 px-2 py-1 text-[11px] text-zinc-300"
            >
              {modelDisplayName(m.id)}
            </span>
          ))}
        </div>
      </Section>

      <Section title="מקורות נתונים — Freshness" icon={Database}>
        {sources.length === 0 ? (
          <div className="text-xs text-zinc-500">אין נתונים עדיין</div>
        ) : (
          <div className="space-y-1 text-xs">
            {sources.map((s) => (
              <div
                key={s.source}
                className="flex items-center justify-between rounded-md border border-white/10 bg-zinc-950/40 px-3 py-2"
              >
                <span className="text-white">{s.source}</span>
                <div className="flex items-center gap-3 text-zinc-500">
                  <span>{s.count.toLocaleString("he-IL")} עסקאות</span>
                  <span>
                    {s.max_date
                      ? new Date(s.max_date).toLocaleDateString("he-IL")
                      : "—"}
                  </span>
                </div>
              </div>
            ))}
          </div>
        )}
      </Section>

      <Section title="העדפות" icon={RefreshCw}>
        <div className="flex flex-col gap-2 text-xs">
          <div className="flex items-center justify-between rounded-md border border-white/10 bg-zinc-950/40 px-3 py-2">
            <span className="text-zinc-300">סינון פעיל</span>
            <span className="text-zinc-500">{filterCount} שדות</span>
          </div>
          <button
            onClick={resetFilters}
            disabled={filterCount === 0}
            className="flex items-center justify-center gap-2 rounded-md border border-white/10 bg-zinc-950/40 px-3 py-2 text-zinc-300 hover:bg-white/5 disabled:opacity-40"
          >
            <Trash2 className="h-3.5 w-3.5" />
            איפוס סינון
          </button>
        </div>
      </Section>
    </div>
  );
}
