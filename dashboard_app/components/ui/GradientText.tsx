import * as React from "react";
import { cn } from "@/lib/utils";

interface GradientTextProps extends React.HTMLAttributes<HTMLSpanElement> {
  as?: "span" | "strong" | "em";
}

export function GradientText({
  as: Tag = "span",
  className,
  children,
  ...props
}: GradientTextProps) {
  return (
    <Tag
      className={cn(
        "bg-clip-text text-transparent",
        "bg-[image:linear-gradient(90deg,var(--accent-1),var(--accent-2))]",
        className,
      )}
      style={{ WebkitBackgroundClip: "text" }}
      {...props}
    >
      {children}
    </Tag>
  );
}
