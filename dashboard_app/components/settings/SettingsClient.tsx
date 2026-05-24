"use client";

import { useQuery } from "@tanstack/react-query";
import { Activity, Brain, Database, RefreshCw, Trash2, ExternalLink } from "lucide-react";
import { fetchApi, getApiUrl } from "@/lib/api/client";
import { API_ENDPOINTS } from "@/lib/api/endpoints";
import { useFiltersStore } from "@/lib/store/filters";
import { useSourceBreakdown } from "@/hooks/useStats";
import { useModels } from "@/hooks/useProperty";
import { modelDisplayName } from "@/lib/model-utils";
import { Card } from "@/components/ui/card";
import { Pill } from "@/components/ui/Pill";
import { Section } from "@/components/ui/Section";
import { formatDate, formatNumber } from "@/lib/format";

interface HealthResp {
  status: string;
  service?: string;
}

function SectionCard({
  title,
  icon: Icon,
  children,
}: {
  title: string;
  icon: React.ComponentType<{ className?: string }>;
  children: React.ReactNode;
}) {
  return (
    <Card>
      <div className="mb-3 flex items-center gap-2">
        <Icon className="h-4 w-4 text-[--accent-1]" />
        <h3 className="text-sm font-semibold text-[--fg]">{title}</h3>
      </div>
      {children}
    </Card>
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

  const ok = health.data?.status === "ok";

  return (
    <div className="space-y-10 px-6 py-10">
      <Section
        title="Settings"
        subtitle="System status, models, and data sources."
        eyebrow="Configuration"
      >
        <div className="grid gap-4 lg:grid-cols-2">
          <SectionCard title="System health" icon={Activity}>
            <div className="space-y-2 text-xs">
              <div className="flex items-center justify-between rounded-md border border-[--border] bg-[--bg] px-3 py-2">
                <div className="flex items-center gap-2 text-[--fg]">
                  <Pill tone={ok ? "up" : "down"}>{ok ? "online" : "down"}</Pill>
                  dashboard_service
                </div>
                <span className="text-[--fg-dim]">
                  {health.isLoading ? "checking…" : health.data?.status ?? "DOWN"}
                </span>
              </div>
              <div className="flex items-center justify-between rounded-md border border-[--border] bg-[--bg] px-3 py-2">
                <span className="text-[--fg-muted]">API base URL</span>
                <code className="text-[--fg]">{apiUrl}</code>
              </div>
              <a
                href={`${apiUrl}/docs`}
                target="_blank"
                rel="noreferrer"
                className="flex items-center justify-between rounded-md border border-[--border] bg-[--bg] px-3 py-2 hover:border-[--border-strong]"
              >
                <span className="text-[--fg-muted]">Swagger / API docs</span>
                <ExternalLink className="h-3.5 w-3.5 text-[--fg-dim]" />
              </a>
            </div>
          </SectionCard>

          <SectionCard title="Models" icon={Brain}>
            <div className="text-xs text-[--fg-muted]">
              {models.length} trained models available. Switching the champion requires:
            </div>
            <pre className="tabular mt-2 overflow-x-auto rounded-md border border-[--border] bg-[--bg] p-2 text-[11px] text-[--fg]">
{`make champion MODEL=moses/stacked_v2
# or via .env: CHAMPION_MODEL=moses/stacked_v2`}
            </pre>
            <div className="mt-3 flex flex-wrap gap-1.5">
              {models.map((m) => (
                <Pill key={m.id} tone="muted">
                  {modelDisplayName(m.id)}
                </Pill>
              ))}
            </div>
          </SectionCard>

          <SectionCard title="Data sources · freshness" icon={Database}>
            {sources.length === 0 ? (
              <div className="text-xs text-[--fg-dim]">No data yet</div>
            ) : (
              <div className="space-y-1 text-xs">
                {sources.map((s) => (
                  <div
                    key={s.source}
                    className="flex items-center justify-between rounded-md border border-[--border] bg-[--bg] px-3 py-2"
                  >
                    <span className="text-[--fg]">{s.source}</span>
                    <div className="tabular flex items-center gap-3 text-[--fg-dim]">
                      <span>{formatNumber(s.count)} transactions</span>
                      <span>{formatDate(s.max_date ?? undefined)}</span>
                    </div>
                  </div>
                ))}
              </div>
            )}
          </SectionCard>

          <SectionCard title="Preferences" icon={RefreshCw}>
            <div className="flex flex-col gap-2 text-xs">
              <div className="flex items-center justify-between rounded-md border border-[--border] bg-[--bg] px-3 py-2">
                <span className="text-[--fg-muted]">Active filters</span>
                <span className="tabular text-[--fg-dim]">{filterCount} fields</span>
              </div>
              <button
                onClick={resetFilters}
                disabled={filterCount === 0}
                className="flex items-center justify-center gap-2 rounded-md border border-[--border] bg-[--bg] px-3 py-2 text-[--fg-muted] hover:border-[--border-strong] disabled:opacity-40"
              >
                <Trash2 className="h-3.5 w-3.5" />
                Reset filters
              </button>
            </div>
          </SectionCard>
        </div>
      </Section>
    </div>
  );
}
