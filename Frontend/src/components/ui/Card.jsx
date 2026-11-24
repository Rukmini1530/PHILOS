import React from "react";
import { cn } from "../../utils/helpers";

const Card = React.forwardRef(
  ({ className, header, footer, children, border, ...props }, ref) => {
    return (
      <div
        ref={ref}
        className={cn(
          "pholis-card",
          "border-border",
          "p-4",
          "mb-4",
          "shadow-sm",
          "transition-shadow",
          "focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-primary focus-visible:ring-offset-2 focus-visible:ring-offset-color-bg-primary",
          className
        )}
        {...props}
      >
        {header && (
          <div className="flex items-start gap-3 mb-4">
            {header}
          </div>
        )}
        {children}
        {footer && (
          <div className="flex justify-end mt-3 pt-2 border-t border-border/50">
            {footer}
          </div>
        )}
      </div>
    );
  }
);

Card.displayName = "Card";

export default Card;
export { Card };