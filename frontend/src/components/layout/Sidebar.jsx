import { NavLink } from "react-router-dom";
import { Activity, Flame, Table2, Tags } from "lucide-react";
import clsx from "clsx";

const NAV = [
  { to: "/", label: "Live Feed", icon: Flame, end: true },
  { to: "/table", label: "Trends Table", icon: Table2 },
  { to: "/keywords", label: "Keywords", icon: Tags },
  { to: "/system", label: "System", icon: Activity },
];

export default function Sidebar({ onNavigate }) {
  return (
    <aside className="flex h-full w-60 flex-col border-r border-line bg-surface">
      <div className="flex items-center gap-2.5 px-5 pb-5 pt-6">
        <div className="flex h-9 w-9 items-center justify-center rounded-xl bg-primary shadow-[0_4px_14px_-4px_rgb(var(--c-primary)/0.6)]">
          <svg viewBox="0 0 24 24" className="h-5 w-5 text-white" fill="none" stroke="currentColor" strokeWidth="2.4" strokeLinecap="round" strokeLinejoin="round">
            <path d="M4 15 L8.5 8 L12 12.5 L15.5 5.5 L18 9.5" />
          </svg>
        </div>
        <div className="leading-tight">
          <div className="font-display text-[17px] font-bold tracking-tight">PulseTube</div>
          <div className="text-[11px] font-medium text-muted">Product trend radar</div>
        </div>
      </div>

      <nav className="flex flex-1 flex-col gap-1 px-3">
        {NAV.map(({ to, label, icon: Icon, end }) => (
          <NavLink
            key={to}
            to={to}
            end={end}
            onClick={onNavigate}
            className={({ isActive }) =>
              clsx(
                "flex items-center gap-3 rounded-xl px-3 py-2.5 text-sm font-semibold transition-colors",
                isActive
                  ? "bg-primary/10 text-primary"
                  : "text-muted hover:bg-raised hover:text-fg"
              )
            }
          >
            <Icon size={17} strokeWidth={2.2} />
            {label}
          </NavLink>
        ))}
      </nav>

      <div className="border-t border-line px-5 py-4 text-[11px] leading-relaxed text-muted">
        Automated YouTube ingestion
        <br />
        every 2 hours · v1.0
      </div>
    </aside>
  );
}
