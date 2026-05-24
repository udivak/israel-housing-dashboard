"use client";

import { Section } from "@/components/ui/Section";
import { ModelGarden } from "./ModelGarden";

export function ModelsList() {
  return (
    <Section
      title="Trained models"
      subtitle="Live from the registry. The champion drives default predictions."
      eyebrow="Garden"
    >
      <ModelGarden />
    </Section>
  );
}
