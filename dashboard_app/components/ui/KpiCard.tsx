import * as React from "react";
import { cn } from "@/lib/utils";

export type KpiTone = "up" | "down" | "neutral";

interface KpiCardProps {
  label: string;
  value: React.ReactNode;
  delta?: string;
  deltaTone?: KpiTone;
  hint?: string;
  icon?: React.ComponentType<{ className?: string }>;
  sparkline?: React.ReactNode;
  className?: string;
}

export function KpiCard({
  label,
  value,
  delta,
  deltaTone = "neutral",
  hint,
  icon: Icon,
  sparkline,
  className,
}: KpiCardProps) {
  const deltaColor =
    deltaTone === "up"
      ? "text-[--up]"
      : deltaTone === "down"
        ? "text-[--down]"
        : "text-[--fg-muted]";

  return (
    <div
      className={cn(
        "group rounded-xl border border-[--border] bg-gradient-to-b from-[--bg-elev] to-[--bg-elev-2] p-4 transition-colors hover:border-[--border-strong]",
        className,
      )}
    >
      <div className="flex items-start justify-between gap-3">
        <div className="min-w-0 flex-1">
          <div className="flex items-center gap-2 text-xs uppercase tracking-wide text-[--fg-dim]">
            {Icon && <Icon className="h-3.5 w-3.5" />}
            <span className="truncate">{label}</span>
          </div>
          <div className="tabular mt-2 text-2xl font-semibold tracking-tight text-[--fg]">
            {value}
          </div>
          {(delta || hint) && (
            <div className="mt-1 flex items-center gap-2 text-xs">
              {delta && <span className={cn("tabular font-medium", deltaColor)}>{delta}</span>}
              {hint && <span className="text-[--fg-dim]">{hint}</span>}
            </div>
          )}
        </div>
        {sparkline && (
          <div className="h-10 w-20 shrink-0 opacity-80">{sparkline}</div>
        )}
      </div>
    </div>
  );
}
