"use client";

import { Card, CardContent, CardHeader } from "@/components/ui/card";
import { Sparkles } from "lucide-react";

export function AIPlaceholder() {
  return (
    <Card className="border-2 border-violet-500/30 bg-gradient-to-br from-violet-500/5 to-transparent">
      <CardHeader className="flex flex-row items-center gap-3">
        <div className="flex h-12 w-12 items-center justify-center rounded-xl bg-gradient-to-br from-violet-500 to-violet-700">
          <Sparkles className="h-6 w-6 text-white" />
        </div>
        <div>
          <h3 className="text-lg font-semibold text-white">AI Modules</h3>
          <p className="text-sm text-zinc-400">Coming soon</p>
        </div>
      </CardHeader>
      <CardContent>
        <p className="text-sm text-zinc-500">
          Advanced AI-powered insights will appear here. Property predictions, market analysis, and intelligent recommendations.
        </p>
      </CardContent>
    </Card>
  );
}
