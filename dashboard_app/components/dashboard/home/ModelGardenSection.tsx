"use client";

import { Section } from "@/components/ui/Section";
import { ModelGarden } from "@/components/ai/ModelGarden";

export function ModelGardenSection() {
  return (
    <Section
      title="Seven models, one prediction"
      subtitle="Each apartment is priced by an ensemble. The champion drives default predictions; the others let you challenge it."
      rightLink={{ href: "/ai", label: "Compare all" }}
      className="border-b border-[var(--border)] px-6 py-12"
    >
      <ModelGarden />
    </Section>
  );
}
