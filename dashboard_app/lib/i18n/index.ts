import en, { type Messages } from "./en";
import he from "./he";

export type { Messages };
export type Locale = "en" | "he";
export type TParams = Record<string, string | number>;

export const LOCALES: Locale[] = ["en", "he"];
export const DEFAULT_LOCALE: Locale = "en";
export const LOCALE_COOKIE = "ih_locale";

export const dirOf = (locale: Locale): "ltr" | "rtl" => (locale === "he" ? "rtl" : "ltr");

const DICTS: Record<Locale, Messages> = { en, he };

/** Pure translator: dictionary lookup (en fallback) + `{token}` interpolation. No React. */
export function translate(locale: Locale, key: keyof Messages, params?: TParams): string {
  const dict = DICTS[locale] ?? DICTS[DEFAULT_LOCALE];
  let str: string = dict[key] ?? en[key] ?? (key as string);
  if (params) {
    for (const [token, value] of Object.entries(params)) {
      str = str.replaceAll(`{${token}}`, String(value));
    }
  }
  return str;
}

export function normalizeLocale(raw: string | undefined): Locale {
  return raw === "he" ? "he" : "en";
}

// dev-only informational guard (the `he: Messages` type already hard-fails the build)
if (process.env.NODE_ENV !== "production") {
  const missing = Object.keys(en).filter((k) => !(k in he));
  if (missing.length) console.warn("[i18n] he.ts missing keys:", missing);
}
