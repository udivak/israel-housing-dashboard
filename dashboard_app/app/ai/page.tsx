import { AIHeader } from "@/components/ai/AIHeader";
import { ModelsList } from "@/components/ai/ModelsList";
import { PredictPlayground } from "@/components/ai/PredictPlayground";

export default function AIPage() {
  return (
    <div className="space-y-10 px-6 py-10">
      <AIHeader />
      <PredictPlayground />
      <ModelsList />
    </div>
  );
}
