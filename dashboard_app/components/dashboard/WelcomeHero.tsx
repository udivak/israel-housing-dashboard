"use client";

import { Badge } from "@/components/ui/badge";

export function WelcomeHero() {
  return (
    <div className="relative overflow-hidden rounded-2xl border border-white/10 bg-gradient-to-br from-cyan-500/10 via-transparent to-violet-500/10 p-8">
      <div className="absolute inset-0 bg-[radial-gradient(ellipse_at_top_right,_var(--tw-gradient-stops))] from-cyan-500/5 via-transparent to-transparent" />
      <div className="relative">
        <Badge variant="secondary" className="mb-4">
          AI-Powered
        </Badge>
        <h1 className="text-3xl font-bold tracking-tight text-white md:text-4xl">
          Welcome to Israel Housing
        </h1>
        <p className="mt-2 max-w-2xl text-zinc-400">
          Real estate intelligence platform powered by AI. Explore properties, analyze districts, and get insights with our advanced modules.
        </p>
      </div>
    </div>
  );
}
