import React from "react";
import { cn } from "../../utils/helpers";

const Badge = React.forwardRef(
  ({ variant = "neutral", size = "medium", children, ...props }, ref) => {
    const sizes = {
      sm: "h-4 w-8 rounded text-xs px-1",
      md: "h-5 w-9 rounded text-sm px-2",
      lg: "h-6 w-10 rounded text-base px-3",
    };

    const variants = {
      neutral: "bg-gray-800 text-gray-300",
      success: "bg-success/20 text-success",
      warning: "bg-warning/20 text-warning",
      error: "bg-error/20 text-error",
      info: "bg-info/20 text-info",
    };

    return (
      <span
        ref={ref}
        className={cn(
          "inline-flex items-center gap-1.5 rounded-full",
          sizes[size],
          variants[variant]
        )}
      >
        {children}
      </span>
    );
  }
);

Badge.displayName = "Badge";

export default Badge;
export { Badge };