import { Hero } from "@/components/dashboard/home/Hero";
import { HomeKpiStrip } from "@/components/dashboard/home/HomeKpiStrip";
import { MapPreview } from "@/components/dashboard/home/MapPreview";
import { ModelGardenSection } from "@/components/dashboard/home/ModelGardenSection";
import { InlinePredict } from "@/components/dashboard/home/InlinePredict";
import { HowItWorks } from "@/components/dashboard/home/HowItWorks";

export default function DashboardPage() {
  return (
    <div>
      <Hero />
      <HomeKpiStrip />
      <MapPreview />
      <ModelGardenSection />
      <InlinePredict />
      <HowItWorks />
    </div>
  );
}
