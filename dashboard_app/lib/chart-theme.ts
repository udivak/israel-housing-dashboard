/**
 * Centralised Recharts theme so every chart shares axis/grid/tooltip styling.
 * Values mirror the CSS tokens in globals.css.
 */
export const CHART_COLORS = {
  axis: "#475569",
  axisLabel: "#94a3b8",
  grid: "#1e293b",
  tooltipBg: "#0f172a",
  tooltipBorder: "#334155",
  fg: "#e2e8f0",
  accent1: "#38bdf8",
  accent2: "#a78bfa",
  up: "#22d3ee",
  down: "#f472b6",
} as const;

export const CHART_SERIES = [
  "#38bdf8",
  "#a78bfa",
  "#22d3ee",
  "#f472b6",
  "#fbbf24",
  "#34d399",
  "#fb923c",
  "#60a5fa",
] as const;

export const tooltipStyle = {
  backgroundColor: CHART_COLORS.tooltipBg,
  border: `1px solid ${CHART_COLORS.tooltipBorder}`,
  borderRadius: 8,
  color: CHART_COLORS.fg,
  fontSize: 12,
};

// Recharts colors each tooltip item inline (defaults to #000 for pie slices),
// overriding contentStyle.color — so force the item text light too.
export const tooltipItemStyle = { color: CHART_COLORS.fg };

export const axisProps = {
  stroke: CHART_COLORS.axis,
  tick: { fill: CHART_COLORS.axisLabel, fontSize: 11 },
};

export const gridProps = {
  stroke: CHART_COLORS.grid,
  strokeDasharray: "3 3",
};
