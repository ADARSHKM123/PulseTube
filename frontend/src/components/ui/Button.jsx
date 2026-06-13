import clsx from "clsx";
import { Loader2 } from "lucide-react";

const VARIANTS = {
  primary:
    "bg-primary text-primary-fg hover:bg-primary/90 focus-visible:ring-primary/50 shadow-[0_4px_14px_-4px_rgb(var(--c-primary)/0.5)]",
  outline: "border border-line bg-surface hover:bg-raised focus-visible:ring-line",
  ghost: "hover:bg-raised focus-visible:ring-line",
  danger: "bg-danger/10 text-danger border border-danger/30 hover:bg-danger/20 focus-visible:ring-danger/40",
};

const SIZES = {
  sm: "h-8 px-3 text-xs gap-1.5",
  md: "h-10 px-4 text-sm gap-2",
};

export default function Button({
  variant = "outline",
  size = "md",
  loading = false,
  disabled,
  className,
  children,
  ...props
}) {
  return (
    <button
      className={clsx(
        "inline-flex select-none items-center justify-center whitespace-nowrap rounded-xl font-semibold transition-colors",
        "focus-visible:outline-none focus-visible:ring-2 disabled:pointer-events-none disabled:opacity-50",
        VARIANTS[variant],
        SIZES[size],
        className
      )}
      disabled={disabled || loading}
      {...props}
    >
      {loading && <Loader2 size={14} className="animate-spin" />}
      {children}
    </button>
  );
}
