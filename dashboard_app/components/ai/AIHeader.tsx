"use client";

import { useLocale } from "@/lib/i18n/LocaleProvider";

export function AIHeader() {
  const { t } = useLocale();
  return (
    <div>
      <div className="mb-1 text-xs uppercase tracking-[0.18em] text-[var(--fg-dim)]">
        {t("ai.eyebrow")}
      </div>
      <h1 className="text-3xl font-semibold tracking-tight text-[var(--fg)]">{t("ai.title")}</h1>
      <p className="mt-2 max-w-2xl text-sm text-[var(--fg-muted)]">{t("ai.subtitle")}</p>
    </div>
  );
}
