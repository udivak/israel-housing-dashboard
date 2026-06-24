"use client";

import { Section } from "@/components/ui/Section";
import { ModelGarden } from "./ModelGarden";
import { useLocale } from "@/lib/i18n/LocaleProvider";

export function ModelsList() {
  const { t } = useLocale();
  return (
    <Section
      title={t("models.title")}
      subtitle={t("models.subtitle")}
      eyebrow={t("models.eyebrow")}
    >
      <ModelGarden />
    </Section>
  );
}
