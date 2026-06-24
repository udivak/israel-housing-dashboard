"use client";

import { Section } from "@/components/ui/Section";
import { ModelGarden } from "@/components/ai/ModelGarden";
import { useLocale } from "@/lib/i18n/LocaleProvider";

export function ModelGardenSection() {
  const { t } = useLocale();
  return (
    <Section
      title={t("home.garden.title")}
      subtitle={t("home.garden.subtitle")}
      rightLink={{ href: "/ai", label: t("home.garden.compareAll") }}
      className="border-b border-[var(--border)] px-6 py-12"
    >
      <ModelGarden />
    </Section>
  );
}
