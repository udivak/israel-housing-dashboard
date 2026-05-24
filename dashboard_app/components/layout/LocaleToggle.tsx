"use client";

import { useEffect, useState } from "react";
import { cn } from "@/lib/utils";

const STORAGE_KEY = "ih:locale";
type Locale = "en" | "he";

export function LocaleToggle({ className }: { className?: string }) {
  const [locale, setLocale] = useState<Locale>("en");

  useEffect(() => {
    try {
      const stored = (window.localStorage.getItem(STORAGE_KEY) as Locale) ?? "en";
      setLocale(stored);
      document.documentElement.lang = stored;
      document.documentElement.dir = stored === "he" ? "rtl" : "ltr";
    } catch {
      /* ignore */
    }
  }, []);

  const choose = (next: Locale) => {
    setLocale(next);
    try {
      window.localStorage.setItem(STORAGE_KEY, next);
    } catch {
      /* ignore */
    }
    document.documentElement.lang = next;
    document.documentElement.dir = next === "he" ? "rtl" : "ltr";
  };

  return (
    <div
      role="radiogroup"
      aria-label="Language"
      className={cn(
        "inline-flex items-center rounded-full border border-[--border] bg-[--bg-elev] p-0.5 text-xs font-medium",
        className,
      )}
    >
      <button
        role="radio"
        aria-checked={locale === "en"}
        onClick={() => choose("en")}
        className={cn(
          "rounded-full px-2.5 py-1 transition-colors",
          locale === "en"
            ? "bg-[--accent-1]/15 text-[--accent-1]"
            : "text-[--fg-dim] hover:text-[--fg]",
        )}
      >
        EN
      </button>
      <button
        role="radio"
        aria-checked={locale === "he"}
        onClick={() => choose("he")}
        className={cn(
          "rounded-full px-2.5 py-1 transition-colors",
          locale === "he"
            ? "bg-[--accent-1]/15 text-[--accent-1]"
            : "text-[--fg-dim] hover:text-[--fg]",
        )}
      >
        עב
      </button>
    </div>
  );
}
