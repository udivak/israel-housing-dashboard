import { ModelsList } from "@/components/ai/ModelsList";
import { PredictPlayground } from "@/components/ai/PredictPlayground";

export default function AIPage() {
  return (
    <div className="flex flex-col gap-4">
      <div>
        <h1 className="text-2xl font-semibold text-white">AI · Price Prediction</h1>
        <p className="text-sm text-zinc-400">
          Playground to experiment with models, compare predictions, and inspect model performance.
        </p>
      </div>
      <PredictPlayground />
      <ModelsList />
    </div>
  );
}
