"use client";

import * as React from "react";
import { cn } from "@/lib/utils";

interface ChartCardProps {
  title: string;
  subtitle?: string;
  right?: React.ReactNode;
  children: React.ReactNode;
  className?: string;
}

export function ChartCard({ title, subtitle, right, children, className }: ChartCardProps) {
  return (
    <div
      className={cn(
        "flex flex-col gap-3 rounded-xl border border-[--border] bg-[--bg-elev] p-4 transition-colors hover:border-[--border-strong]",
        className,
      )}
    >
      <div className="flex items-start justify-between gap-3">
        <div className="min-w-0">
          <h3 className="text-sm font-semibold tracking-tight text-[--fg]">{title}</h3>
          {subtitle && <p className="mt-0.5 text-xs text-[--fg-muted]">{subtitle}</p>}
        </div>
        {right && <div className="shrink-0 text-xs text-[--fg-muted]">{right}</div>}
      </div>
      <div className="min-h-0 flex-1">{children}</div>
    </div>
  );
}

export function fmtNum(n: number | null | undefined, opts?: Intl.NumberFormatOptions): string {
  if (n == null || !Number.isFinite(n)) return "—";
  return n.toLocaleString("en-US", { maximumFractionDigits: 0, ...opts });
}

export function fmtCurrency(n: number | null | undefined): string {
  if (n == null || !Number.isFinite(n)) return "—";
  return `₪${n.toLocaleString("en-US", { maximumFractionDigits: 0 })}`;
}
