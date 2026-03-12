import { Sparkles } from "lucide-react";

export default function AIPage() {
  return (
    <div className="flex flex-col items-center justify-center min-h-[60vh] text-center">
      <Sparkles className="h-16 w-16 text-violet-500/50 mb-4" />
      <h2 className="text-2xl font-semibold text-white">AI Modules</h2>
      <p className="mt-2 text-zinc-400 max-w-md">
        AI-powered insights, predictions, and recommendations coming soon.
      </p>
    </div>
  );
}
