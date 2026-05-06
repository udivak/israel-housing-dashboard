"use client";

import { useState } from "react";
import { TimeseriesChart } from "./TimeseriesChart";
import { TopCitiesChart } from "./TopCitiesChart";
import { DistributionChart } from "./DistributionChart";
import { YoyTable } from "./YoyTable";
import { SeasonalityChart } from "./SeasonalityChart";
import { SourceBreakdown, PropertyTypeBreakdown } from "./Breakdowns";

export function StatsClient() {
  const [city, setCity] = useState<string>("");

  return (
    <div dir="rtl" className="flex flex-col gap-4">
      <div className="flex items-center justify-between gap-3 rounded-xl border border-white/10 bg-zinc-900/60 p-4 backdrop-blur">
        <div>
          <h1 className="text-xl font-semibold text-white">סטטיסטיקות</h1>
          <p className="text-xs text-zinc-400">
            תובנות על שוק הנדל״ן הישראלי. סנן לפי עיר כדי לראות פילוח ספציפי.
          </p>
        </div>
        <input
          value={city}
          onChange={(e) => setCity(e.target.value)}
          placeholder="סנן לפי עיר…"
          className="w-56 rounded-md border border-white/10 bg-zinc-950/60 px-3 py-1.5 text-sm text-white placeholder:text-zinc-500 focus:border-cyan-500/50 focus:outline-none"
        />
      </div>

      <div className="grid gap-4 lg:grid-cols-2">
        <TimeseriesChart city={city || undefined} />
        <DistributionChart city={city || undefined} />
        <TopCitiesChart />
        <YoyTable />
        <SeasonalityChart city={city || undefined} />
        <PropertyTypeBreakdown city={city || undefined} />
        <SourceBreakdown />
      </div>
    </div>
  );
}
