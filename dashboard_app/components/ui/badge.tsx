import * as React from "react";
import { cn } from "@/lib/utils";

interface BadgeProps extends React.HTMLAttributes<HTMLSpanElement> {
  variant?: "default" | "secondary" | "outline" | "success";
}

const Badge = React.forwardRef<HTMLSpanElement, BadgeProps>(
  ({ className, variant = "default", ...props }, ref) => (
    <span
      ref={ref}
      className={cn(
        "inline-flex items-center rounded-full px-2.5 py-0.5 text-xs font-medium",
        variant === "default" && "bg-cyan-500/20 text-cyan-400 border border-cyan-500/30",
        variant === "secondary" && "bg-zinc-500/20 text-zinc-300 border border-zinc-500/30",
        variant === "outline" && "border border-white/20 text-zinc-300",
        variant === "success" && "bg-emerald-500/20 text-emerald-400 border border-emerald-500/30",
        className
      )}
      {...props}
    />
  )
);
Badge.displayName = "Badge";

export { Badge };
