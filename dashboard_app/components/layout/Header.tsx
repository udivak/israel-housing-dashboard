"use client";

import { Bell } from "lucide-react";
import { useRouter } from "next/navigation";
import { SearchBar } from "@/components/map/SearchBar";

export function Header() {
  const router = useRouter();

  const handleSelect = (lon: number, lat: number, zoom = 15) => {
    router.push(`/map?lon=${lon}&lat=${lat}&zoom=${zoom}`);
  };

  return (
    <header className="sticky top-0 z-30 flex h-16 items-center justify-between border-b border-white/10 bg-zinc-950/80 backdrop-blur-xl px-8">
      <div className="flex items-center gap-4">
        <SearchBar
          onSelect={handleSelect}
          placeholder="Search address, street, city..."
          className="w-80"
          inputClassName="rounded-lg bg-white/5 py-2 focus:ring-1 focus:ring-cyan-500/30"
        />
      </div>
      <div className="flex items-center gap-4">
        <button className="relative rounded-lg p-2 text-zinc-400 hover:bg-white/5 hover:text-white transition-colors">
          <Bell className="h-5 w-5" />
          <span className="absolute right-1.5 top-1.5 h-2 w-2 rounded-full bg-cyan-500" />
        </button>
        <div className="flex h-9 w-9 items-center justify-center rounded-full bg-gradient-to-br from-cyan-500 to-violet-600 text-sm font-medium text-white">
          U
        </div>
      </div>
    </header>
  );
}
