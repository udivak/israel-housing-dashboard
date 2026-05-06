"use client";

interface ChartCardProps {
  title: string;
  subtitle?: string;
  children: React.ReactNode;
  className?: string;
}

export function ChartCard({ title, subtitle, children, className = "" }: ChartCardProps) {
  return (
    <div
      className={`flex flex-col gap-3 rounded-xl border border-white/10 bg-zinc-900/60 p-4 backdrop-blur ${className}`}
    >
      <div>
        <h3 className="text-sm font-semibold text-white">{title}</h3>
        {subtitle && <p className="text-xs text-zinc-400">{subtitle}</p>}
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
