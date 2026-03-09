import { WelcomeHero } from "@/components/dashboard/WelcomeHero";
import { StatsCards } from "@/components/dashboard/StatsCards";
import { AIPlaceholder } from "@/components/dashboard/AIPlaceholder";

export default function DashboardPage() {
  return (
    <div className="space-y-8">
      <WelcomeHero />
      <StatsCards />
      <AIPlaceholder />
    </div>
  );
}
