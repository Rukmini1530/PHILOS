import React from "react";
import { cn } from "../../utils/helpers";

const Input = React.forwardRef(
  ({ className, type = "text", label, helperText, errorText, disabled, ...props }, ref) => {
    return (
      <div className="space-y-1.5">
        {label && (
          <label
            className="block text-sm font-medium text-gray-300 mb-1.5"
            htmlFor={props.id || undefined}
          >
            {label}
          </label>
        )}
        <input
          type={type}
          className={cn(
            "flex h-10 w-full rounded-lg border-2 border-border bg-gray-800 px-3 py-2 text-sm placeholder:text-gray-500",
            "focus:outline-none focus:ring-2 focus:ring-primary focus:border-transparent",
            "disabled:cursor-not-allowed disabled:opacity-50",
            className
          )}
          ref={ref}
          id={props.id}
          disabled={disabled}
          {...props}
        />
        {helperText && (
          <p className="text-xs text-gray-400">{helperText}</p>
        )}
        {errorText && (
          <p className="text-xs text-error">{errorText}</p>
        )}
      </div>
    );
  }
);

Input.displayName = "Input";

export default Input;
