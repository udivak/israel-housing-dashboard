import { ModelsList } from "@/components/ai/ModelsList";
import { PredictPlayground } from "@/components/ai/PredictPlayground";

export default function AIPage() {
  return (
    <div className="space-y-10 px-6 py-10">
      <div>
        <div className="mb-1 text-xs uppercase tracking-[0.18em] text-[var(--fg-dim)]">AI</div>
        <h1 className="text-3xl font-semibold tracking-tight text-[var(--fg)]">
          Price prediction
        </h1>
        <p className="mt-2 max-w-2xl text-sm text-[var(--fg-muted)]">
          Playground to experiment with features, swap between models, and inspect ensemble
          consensus.
        </p>
      </div>
      <PredictPlayground />
      <ModelsList />
    </div>
  );
}
