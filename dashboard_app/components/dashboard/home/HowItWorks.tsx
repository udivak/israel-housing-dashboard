"use client";

import { Database, Map, Brain, Network } from "lucide-react";
import { Section } from "@/components/ui/Section";

const STEPS = [
  {
    n: "01",
    title: "Collect",
    body: "Nightly Playwright crawls of nadlan.gov.il and partner sources feed a Mongo store.",
    icon: Database,
  },
  {
    n: "02",
    title: "Enrich",
    body: "Each transaction joins OSM context, indexes into H3 r5/r7/r8 cells, and gets price-index adjustments.",
    icon: Map,
  },
  {
    n: "03",
    title: "Model",
    body: "Seven scikit-learn / boosting regressors are trained on the enriched feature table — a champion is elected.",
    icon: Brain,
  },
  {
    n: "04",
    title: "Serve",
    body: "FastAPI + Next.js + MapLibre stream predictions, KPIs, and tiles live.",
    icon: Network,
  },
];

export function HowItWorks() {
  return (
    <Section
      title="Under the hood"
      subtitle="Four services, one pipeline. Built to be reproducible end-to-end."
      eyebrow="How it works"
      className="px-6 py-14"
    >
      <div className="grid gap-3 sm:grid-cols-2 lg:grid-cols-4">
        {STEPS.map((s) => {
          const Icon = s.icon;
          return (
            <div
              key={s.n}
              className="rounded-xl border border-[--border] bg-[--bg-elev] p-4 transition-colors hover:border-[--border-strong]"
            >
              <div className="flex items-center justify-between text-xs uppercase tracking-wide text-[--fg-dim]">
                <span className="tabular">{s.n}</span>
                <Icon className="h-4 w-4 text-[--accent-1]" />
              </div>
              <div className="mt-3 text-sm font-semibold text-[--fg]">{s.title}</div>
              {/* i18n:tbd — long-form descriptive copy stays English in v1 */}
              <p className="mt-1.5 text-xs leading-relaxed text-[--fg-muted]">{s.body}</p>
            </div>
          );
        })}
      </div>
    </Section>
  );
}
