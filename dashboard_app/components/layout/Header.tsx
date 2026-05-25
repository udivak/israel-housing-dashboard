"use client";

import Link from "next/link";
import { usePathname, useRouter } from "next/navigation";
import { SearchBar } from "@/components/map/SearchBar";
import { LocaleToggle } from "./LocaleToggle";
import { cn } from "@/lib/utils";

const NAV = [
  { href: "/", label: "Home" },
  { href: "/map", label: "Map" },
  { href: "/stats", label: "Stats" },
  { href: "/ai", label: "Predict" },
  { href: "/settings", label: "Settings" },
];

export function Header() {
  const router = useRouter();
  const pathname = usePathname() ?? "/";

  const handleSelect = (lon: number, lat: number, zoom = 15) => {
    router.push(`/map?lon=${lon}&lat=${lat}&zoom=${zoom}`);
  };

  const isActive = (href: string) =>
    href === "/" ? pathname === "/" : pathname === href || pathname.startsWith(href + "/");

  return (
    <header className="sticky top-0 z-40 border-b border-[var(--border)] bg-[var(--bg)]/70 backdrop-blur-xl">
      <div className="mx-auto flex h-14 max-w-7xl items-center gap-6 px-6">
        <Link href="/" className="flex shrink-0 items-center gap-2">
          <div className="flex h-7 w-7 items-center justify-center rounded-lg bg-[image:linear-gradient(135deg,var(--accent-1),var(--accent-2))]">
            <span className="text-xs font-bold text-[var(--bg)]">IH</span>
          </div>
          <span className="hidden text-sm font-semibold tracking-tight text-[var(--fg)] sm:inline">
            Israel Housing
          </span>
        </Link>

        <nav className="hidden items-center gap-1 md:flex">
          {NAV.map((item) => (
            <Link
              key={item.href}
              href={item.href}
              className={cn(
                "rounded-md px-3 py-1.5 text-sm font-medium transition-colors",
                isActive(item.href)
                  ? "bg-[var(--accent-1)]/10 text-[var(--accent-1)]"
                  : "text-[var(--fg-muted)] hover:bg-[var(--bg-elev)] hover:text-[var(--fg)]",
              )}
            >
              {item.label}
            </Link>
          ))}
        </nav>

        <div className="ml-auto flex items-center gap-3">
          <SearchBar
            onSelect={handleSelect}
            placeholder="Search address, street, city…"
            className="hidden w-64 sm:block lg:w-80"
            inputClassName="rounded-md border-[var(--border)] bg-[var(--bg-elev)] py-1.5 text-sm focus:border-[var(--accent-1)]/50 focus:ring-1 focus:ring-[var(--accent-1)]/30"
          />
          <LocaleToggle />
        </div>
      </div>
    </header>
  );
}
