import * as React from "react";
import { cn } from "@/lib/utils";

export type PillTone = "default" | "accent" | "muted" | "up" | "down" | "live";

interface PillProps extends React.HTMLAttributes<HTMLSpanElement> {
  tone?: PillTone;
}

const TONE: Record<PillTone, string> = {
  default: "border-[var(--border)] bg-[var(--bg-elev-2)] text-[var(--fg-muted)]",
  accent: "border-[var(--accent-1)]/30 bg-[var(--accent-1)]/10 text-[var(--accent-1)]",
  muted: "border-[var(--border)] bg-[var(--bg-elev)] text-[var(--fg-dim)]",
  up: "border-[var(--up)]/30 bg-[var(--up)]/10 text-[var(--up)]",
  down: "border-[var(--down)]/30 bg-[var(--down)]/10 text-[var(--down)]",
  live: "border-emerald-500/30 bg-emerald-500/10 text-emerald-300",
};

export function Pill({ tone = "default", className, children, ...props }: PillProps) {
  return (
    <span
      className={cn(
        "inline-flex items-center gap-1.5 rounded-full border px-2.5 py-0.5 text-xs font-medium",
        TONE[tone],
        className,
      )}
      {...props}
    >
      {tone === "live" && (
        <span className="relative inline-flex h-1.5 w-1.5">
          <span className="absolute inline-flex h-full w-full animate-ping rounded-full bg-emerald-400 opacity-75" />
          <span className="relative inline-flex h-1.5 w-1.5 rounded-full bg-emerald-400" />
        </span>
      )}
      {children}
    </span>
  );
}
