"use client";

import { Database, Map, Brain, Network } from "lucide-react";
import { Section } from "@/components/ui/Section";
import { useLocale } from "@/lib/i18n/LocaleProvider";
import type { Messages } from "@/lib/i18n/en";

const STEPS: {
  n: string;
  titleKey: keyof Messages;
  bodyKey: keyof Messages;
  icon: React.ComponentType<{ className?: string }>;
}[] = [
  { n: "01", titleKey: "how.step1.title", bodyKey: "how.step1.body", icon: Database },
  { n: "02", titleKey: "how.step2.title", bodyKey: "how.step2.body", icon: Map },
  { n: "03", titleKey: "how.step3.title", bodyKey: "how.step3.body", icon: Brain },
  { n: "04", titleKey: "how.step4.title", bodyKey: "how.step4.body", icon: Network },
];

export function HowItWorks() {
  const { t } = useLocale();
  return (
    <Section
      title={t("how.title")}
      subtitle={t("how.subtitle")}
      eyebrow={t("how.eyebrow")}
      className="px-6 py-14"
    >
      <div className="grid gap-3 sm:grid-cols-2 lg:grid-cols-4">
        {STEPS.map((s) => {
          const Icon = s.icon;
          return (
            <div
              key={s.n}
              className="rounded-xl border border-[var(--border)] bg-[var(--bg-elev)] p-4 transition-colors hover:border-[var(--border-strong)]"
            >
              <div className="flex items-center justify-between text-xs uppercase tracking-wide text-[var(--fg-dim)]">
                <span className="tabular">{s.n}</span>
                <Icon className="h-4 w-4 text-[var(--accent-1)]" />
              </div>
              <div className="mt-3 text-sm font-semibold text-[var(--fg)]">{t(s.titleKey)}</div>
              <p className="mt-1.5 text-xs leading-relaxed text-[var(--fg-muted)]">{t(s.bodyKey)}</p>
            </div>
          );
        })}
      </div>
    </Section>
  );
}
