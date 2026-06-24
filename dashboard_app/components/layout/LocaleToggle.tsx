"use client";

import { useLocale } from "@/lib/i18n/LocaleProvider";
import { cn } from "@/lib/utils";

export function LocaleToggle({ className }: { className?: string }) {
  const { locale, setLocale, t } = useLocale();

  return (
    <div
      role="radiogroup"
      aria-label={t("toggle.aria")}
      className={cn(
        "inline-flex items-center rounded-full border border-[var(--border)] bg-[var(--bg-elev)] p-0.5 text-xs font-medium",
        className,
      )}
    >
      <button
        role="radio"
        aria-checked={locale === "en"}
        onClick={() => setLocale("en")}
        className={cn(
          "rounded-full px-2.5 py-1 transition-colors",
          locale === "en"
            ? "bg-[var(--accent-1)]/15 text-[var(--accent-1)]"
            : "text-[var(--fg-dim)] hover:text-[var(--fg)]",
        )}
      >
        EN
      </button>
      <button
        role="radio"
        aria-checked={locale === "he"}
        onClick={() => setLocale("he")}
        className={cn(
          "rounded-full px-2.5 py-1 transition-colors",
          locale === "he"
            ? "bg-[var(--accent-1)]/15 text-[var(--accent-1)]"
            : "text-[var(--fg-dim)] hover:text-[var(--fg)]",
        )}
      >
        עב
      </button>
    </div>
  );
}
