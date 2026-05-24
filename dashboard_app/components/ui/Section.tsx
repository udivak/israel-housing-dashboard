import * as React from "react";
import Link from "next/link";
import { ArrowRight } from "lucide-react";
import { cn } from "@/lib/utils";

interface SectionProps {
  title: string;
  subtitle?: string;
  rightLink?: { href: string; label: string };
  eyebrow?: string;
  children: React.ReactNode;
  className?: string;
  headerClassName?: string;
}

export function Section({
  title,
  subtitle,
  rightLink,
  eyebrow,
  children,
  className,
  headerClassName,
}: SectionProps) {
  return (
    <section className={cn("w-full", className)}>
      <div
        className={cn(
          "mb-5 flex items-end justify-between gap-4",
          headerClassName,
        )}
      >
        <div className="min-w-0">
          {eyebrow && (
            <div className="mb-1 text-xs uppercase tracking-[0.18em] text-[--fg-dim]">
              {eyebrow}
            </div>
          )}
          <h2 className="text-xl font-semibold tracking-tight text-[--fg] sm:text-2xl">
            {title}
          </h2>
          {subtitle && (
            <p className="mt-1 max-w-2xl text-sm text-[--fg-muted]">{subtitle}</p>
          )}
        </div>
        {rightLink && (
          <Link
            href={rightLink.href}
            className="inline-flex shrink-0 items-center gap-1 text-sm font-medium text-[--accent-1] hover:text-[--accent-2]"
          >
            {rightLink.label}
            <ArrowRight className="h-3.5 w-3.5 rtl-flip" />
          </Link>
        )}
      </div>
      {children}
    </section>
  );
}
