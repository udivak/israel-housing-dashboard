"use client";

import { useLayers } from "@/hooks/useLayers";
import { useHealth } from "@/hooks/useHealth";
import { Card, CardContent, CardHeader } from "@/components/ui/card";
import { Skeleton } from "@/components/ui/skeleton";
import { Layers, MapPin, CheckCircle } from "lucide-react";

export function StatsCards() {
  const { data: layers, isLoading: layersLoading, isError: layersError } = useLayers();
  const { data: health, isError: healthError } = useHealth();

  const isApiAvailable = !healthError && health?.status === "ok";
  const layerCount = layers?.length ?? 0;

  const cards = [
    {
      title: "Map Layers",
      value: layersLoading ? "—" : layersError ? "—" : layerCount,
      subtitle: layersError ? "Service unavailable" : "Available layers",
      icon: Layers,
      color: "text-cyan-400",
      borderColor: "border-cyan-500/30",
    },
    {
      title: "Properties",
      value: layers?.find((l) => l.id === "properties") ? "Ready" : "—",
      subtitle: "Property data layer",
      icon: MapPin,
      color: "text-violet-400",
      borderColor: "border-violet-500/30",
    },
    {
      title: "API Status",
      value: isApiAvailable ? "Connected" : "Offline",
      subtitle: isApiAvailable ? "dashboard_service" : "Start backend on :8000",
      icon: CheckCircle,
      color: isApiAvailable ? "text-emerald-400" : "text-amber-400",
      borderColor: isApiAvailable ? "border-emerald-500/30" : "border-amber-500/30",
    },
  ];

  return (
    <div className="grid gap-6 sm:grid-cols-2 lg:grid-cols-3">
      {cards.map((card) => {
        const Icon = card.icon;
        return (
          <Card
            key={card.title}
            className={`border-2 ${card.borderColor} transition-all hover:border-opacity-50`}
          >
            <CardHeader className="flex flex-row items-center justify-between pb-2">
              <span className="text-sm font-medium text-zinc-400">{card.title}</span>
              <Icon className={`h-5 w-5 ${card.color}`} />
            </CardHeader>
            <CardContent>
              {layersLoading && card.title === "Map Layers" ? (
                <Skeleton className="h-8 w-20" />
              ) : (
                <div className="text-2xl font-bold text-white">{card.value}</div>
              )}
              <p className="mt-1 text-xs text-zinc-500">{card.subtitle}</p>
            </CardContent>
          </Card>
        );
      })}
    </div>
  );
}
