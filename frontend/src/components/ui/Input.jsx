import clsx from "clsx";

export function Field({ label, hint, children, className }) {
  return (
    <label className={clsx("flex flex-col gap-1.5", className)}>
      {label && <span className="text-xs font-semibold uppercase tracking-wide text-muted">{label}</span>}
      {children}
      {hint && <span className="text-[11px] text-muted">{hint}</span>}
    </label>
  );
}

export function Input({ className, ...props }) {
  return (
    <input
      className={clsx(
        "h-9 w-full rounded-xl border border-line bg-surface px-3 text-sm text-fg placeholder:text-muted/70",
        "transition-colors focus:border-primary/50 focus:outline-none focus:ring-2 focus:ring-primary/25",
        className
      )}
      {...props}
    />
  );
}

export function Select({ className, children, ...props }) {
  return (
    <select
      className={clsx(
        "h-9 w-full cursor-pointer appearance-none rounded-xl border border-line bg-surface px-3 pr-8 text-sm text-fg",
        "bg-[url('data:image/svg+xml;charset=utf-8,%3Csvg%20xmlns%3D%22http%3A//www.w3.org/2000/svg%22%20width%3D%2212%22%20height%3D%2212%22%20viewBox%3D%220%200%2024%2024%22%20fill%3D%22none%22%20stroke%3D%22%23888da0%22%20stroke-width%3D%222.5%22%20stroke-linecap%3D%22round%22%20stroke-linejoin%3D%22round%22%3E%3Cpath%20d%3D%22m6%209%206%206%206-6%22/%3E%3C/svg%3E')] bg-[right_0.65rem_center] bg-no-repeat",
        "transition-colors focus:border-primary/50 focus:outline-none focus:ring-2 focus:ring-primary/25",
        className
      )}
      {...props}
    >
      {children}
    </select>
  );
}

export function Switch({ checked, onChange, disabled }) {
  return (
    <button
      type="button"
      role="switch"
      aria-checked={checked}
      disabled={disabled}
      onClick={() => onChange(!checked)}
      className={clsx(
        "relative h-[22px] w-10 shrink-0 rounded-full transition-colors disabled:opacity-40",
        checked ? "bg-primary" : "bg-line"
      )}
    >
      <span
        className={clsx(
          "absolute top-[3px] h-4 w-4 rounded-full bg-white shadow transition-transform",
          checked ? "translate-x-[21px]" : "translate-x-[3px]"
        )}
      />
    </button>
  );
}
