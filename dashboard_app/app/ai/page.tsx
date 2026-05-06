import { ModelsList } from "@/components/ai/ModelsList";
import { PredictPlayground } from "@/components/ai/PredictPlayground";

export default function AIPage() {
  return (
    <div dir="rtl" className="flex flex-col gap-4">
      <div>
        <h1 className="text-2xl font-semibold text-white">AI · ניבוי מחירים</h1>
        <p className="text-sm text-zinc-400">
          מגרש משחקים לניסוי מודלים, השוואה בין מאמנים, וצפייה בביצועי המודלים.
        </p>
      </div>
      <PredictPlayground />
      <ModelsList />
    </div>
  );
}
