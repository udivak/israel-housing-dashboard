export function formatNumber(
  value: number | null | undefined,
  opts: Intl.NumberFormatOptions = {},
  locale = "en-IL",
): string {
  if (value == null || !Number.isFinite(value)) return "—";
  return value.toLocaleString(locale, { maximumFractionDigits: 0, ...opts });
}

export function formatCurrency(
  value: number | null | undefined,
  locale = "en-IL",
): string {
  if (value == null || !Number.isFinite(value)) return "—";
  return `₪${value.toLocaleString(locale, { maximumFractionDigits: 0 })}`;
}

export function formatCompact(
  value: number | null | undefined,
  locale = "en-IL",
): string {
  if (value == null || !Number.isFinite(value)) return "—";
  return value.toLocaleString(locale, {
    notation: "compact",
    maximumFractionDigits: 1,
  });
}

export function formatDate(
  value: string | Date | null | undefined,
  locale = "en-IL",
): string {
  if (!value) return "—";
  const d = value instanceof Date ? value : new Date(value);
  if (Number.isNaN(d.getTime())) return "—";
  return d.toLocaleDateString(locale, { day: "2-digit", month: "short", year: "numeric" });
}

export function humanizeAgo(
  value: string | Date | null | undefined,
): string {
  if (!value) return "—";
  const d = value instanceof Date ? value : new Date(value);
  if (Number.isNaN(d.getTime())) return "—";
  const diffMs = Date.now() - d.getTime();
  const min = Math.round(diffMs / 60000);
  if (min < 1) return "just now";
  if (min < 60) return `${min}m ago`;
  const hr = Math.round(min / 60);
  if (hr < 24) return `${hr}h ago`;
  const day = Math.round(hr / 24);
  return `${day}d ago`;
}
