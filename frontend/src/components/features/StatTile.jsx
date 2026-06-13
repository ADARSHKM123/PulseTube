import clsx from "clsx";

export default function StatTile({ icon: Icon, label, value, sub, tone = "primary" }) {
  const tones = {
    primary: "text-primary bg-primary/10",
    accent: "text-accent bg-accent/10",
    success: "text-success bg-success/10",
    warning: "text-warning bg-warning/10",
  };
  return (
    <div className="card flex items-center gap-4 p-4">
      {Icon && (
        <div className={clsx("flex h-11 w-11 shrink-0 items-center justify-center rounded-xl", tones[tone])}>
          <Icon size={20} strokeWidth={2.2} />
        </div>
      )}
      <div className="min-w-0">
        <div className="num truncate font-display text-2xl font-bold tracking-tight">{value}</div>
        <div className="truncate text-xs font-medium text-muted">{label}</div>
        {sub && <div className="truncate text-[11px] text-muted/80">{sub}</div>}
      </div>
    </div>
  );
}
