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
import { useLocale } from "@/lib/i18n/LocaleProvider";
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
        <Icon className="h-4 w-4 text-[var(--accent-1)]" />
        <h3 className="text-sm font-semibold text-[var(--fg)]">{title}</h3>
      </div>
      {children}
    </Card>
  );
}

export function SettingsClient() {
  const apiUrl = getApiUrl();
  const { t, locale } = useLocale();

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
        title={t("settings.title")}
        subtitle={t("settings.subtitle")}
        eyebrow={t("settings.eyebrow")}
      >
        <div className="grid gap-4 lg:grid-cols-2">
          <SectionCard title={t("settings.health")} icon={Activity}>
            <div className="space-y-2 text-xs">
              <div className="flex items-center justify-between rounded-md border border-[var(--border)] bg-[var(--bg)] px-3 py-2">
                <div className="flex items-center gap-2 text-[var(--fg)]">
                  <Pill tone={ok ? "up" : "down"}>{ok ? t("settings.online") : t("settings.down")}</Pill>
                  dashboard_service
                </div>
                <span className="text-[var(--fg-dim)]">
                  {health.isLoading ? t("settings.checking") : health.data?.status ?? t("settings.statusDown")}
                </span>
              </div>
              <div className="flex items-center justify-between rounded-md border border-[var(--border)] bg-[var(--bg)] px-3 py-2">
                <span className="text-[var(--fg-muted)]">{t("settings.apiBaseUrl")}</span>
                <code className="text-[var(--fg)]">{apiUrl}</code>
              </div>
              <a
                href={`${apiUrl}/docs`}
                target="_blank"
                rel="noreferrer"
                className="flex items-center justify-between rounded-md border border-[var(--border)] bg-[var(--bg)] px-3 py-2 hover:border-[var(--border-strong)]"
              >
                <span className="text-[var(--fg-muted)]">{t("settings.apiDocs")}</span>
                <ExternalLink className="h-3.5 w-3.5 text-[var(--fg-dim)]" />
              </a>
            </div>
          </SectionCard>

          <SectionCard title={t("settings.models")} icon={Brain}>
            <div className="text-xs text-[var(--fg-muted)]">
              {t("settings.modelsAvailable", { count: models.length })}
            </div>
            <pre className="tabular mt-2 overflow-x-auto rounded-md border border-[var(--border)] bg-[var(--bg)] p-2 text-[11px] text-[var(--fg)]">
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

          <SectionCard title={t("settings.sources")} icon={Database}>
            {sources.length === 0 ? (
              <div className="text-xs text-[var(--fg-dim)]">{t("settings.noData")}</div>
            ) : (
              <div className="space-y-1 text-xs">
                {sources.map((s) => (
                  <div
                    key={s.source}
                    className="flex items-center justify-between rounded-md border border-[var(--border)] bg-[var(--bg)] px-3 py-2"
                  >
                    <span className="text-[var(--fg)]">{s.source}</span>
                    <div className="tabular flex items-center gap-3 text-[var(--fg-dim)]">
                      <span>{t("settings.transactionsCount", { count: formatNumber(s.count) })}</span>
                      <span>{formatDate(s.max_date ?? undefined, `${locale}-IL`)}</span>
                    </div>
                  </div>
                ))}
              </div>
            )}
          </SectionCard>

          <SectionCard title={t("settings.preferences")} icon={RefreshCw}>
            <div className="flex flex-col gap-2 text-xs">
              <div className="flex items-center justify-between rounded-md border border-[var(--border)] bg-[var(--bg)] px-3 py-2">
                <span className="text-[var(--fg-muted)]">{t("settings.activeFilters")}</span>
                <span className="tabular text-[var(--fg-dim)]">
                  {t("settings.fieldsCount", { count: filterCount })}
                </span>
              </div>
              <button
                onClick={resetFilters}
                disabled={filterCount === 0}
                className="flex items-center justify-center gap-2 rounded-md border border-[var(--border)] bg-[var(--bg)] px-3 py-2 text-[var(--fg-muted)] hover:border-[var(--border-strong)] disabled:opacity-40"
              >
                <Trash2 className="h-3.5 w-3.5" />
                {t("settings.resetFilters")}
              </button>
            </div>
          </SectionCard>
        </div>
      </Section>
    </div>
  );
}
