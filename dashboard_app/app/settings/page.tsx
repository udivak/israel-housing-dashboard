import { Settings as SettingsIcon } from "lucide-react";

export default function SettingsPage() {
  return (
    <div className="flex flex-col items-center justify-center min-h-[60vh] text-center">
      <SettingsIcon className="h-16 w-16 text-zinc-500/50 mb-4" />
      <h2 className="text-2xl font-semibold text-white">Settings</h2>
      <p className="mt-2 text-zinc-400 max-w-md">
        Configuration and preferences coming soon.
      </p>
    </div>
  );
}
